"""LLM servis katmanı testleri (#172, US-026, US-045).

Gerçek Groq/Gemini'ye istek gitmez: httpx.MockTransport ile sahte yanıtlar kullanılır.
"""

import json

import httpx
import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMUnavailableException, RateLimitedException
from app.services.llm import (
    GeminiProvider,
    GroqProvider,
    LLMService,
    RateLimiter,
    parse_json_response,
)


class Points(BaseModel):
    story_points: int
    reason: str


GOOD = {"story_points": 5, "reason": "Birden fazla ekran içeriyor."}


def groq_ok(payload=GOOD, wrap=lambda s: s):
    return httpx.Response(200, json={"choices": [{"message": {"content": wrap(json.dumps(payload))}}]})


def gemini_ok(payload=GOOD):
    return httpx.Response(
        200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    )


def make_service(groq_handler=None, gemini_handler=None, groq_key="g-key", gemini_key="m-key"):
    calls = {"groq": 0, "gemini": 0}

    def wrap(name, handler):
        def inner(request: httpx.Request):
            calls[name] += 1
            return handler(request)
        return httpx.Client(transport=httpx.MockTransport(inner))

    providers = [
        GroqProvider(groq_key, "groq-model", wrap("groq", groq_handler or (lambda r: groq_ok()))),
        GeminiProvider(gemini_key, "gemini-model", wrap("gemini", gemini_handler or (lambda r: gemini_ok()))),
    ]
    return LLMService(providers, timeout=10), calls


def test_ana_servis_basariliysa_groq_kullanilir_yedege_gidilmez():
    service, calls = make_service()
    result = service.complete_json("sistem", "kullanıcı", Points)
    assert result.provider == "groq"
    assert result.data.story_points == 5
    assert calls == {"groq": 1, "gemini": 0}


def test_groq_istegi_dogru_baslik_ve_govde_ile_gider():
    seen = {}

    def handler(request: httpx.Request):
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return groq_ok()

    service, _ = make_service(groq_handler=handler)
    service.complete_json("Sistem metni", "Kullanıcı metni", Points)
    assert seen["auth"] == "Bearer g-key"
    assert seen["body"]["model"] == "groq-model"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    assert seen["body"]["messages"][0] == {"role": "system", "content": "Sistem metni"}
    assert seen["body"]["messages"][1] == {"role": "user", "content": "Kullanıcı metni"}


@pytest.mark.parametrize(
    "groq_handler",
    [
        pytest.param(lambda r: httpx.Response(429, json={"error": "limit"}), id="429"),
        pytest.param(lambda r: httpx.Response(503), id="503"),
        pytest.param(lambda r: httpx.Response(401), id="401-gecersiz-anahtar"),
        pytest.param(lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("zaman aşımı")), id="zaman-asimi"),
        pytest.param(lambda r: (_ for _ in ()).throw(httpx.ConnectError("internet yok")), id="baglanti-hatasi"),
        pytest.param(lambda r: httpx.Response(200, json={"choices": []}), id="bos-choices"),
        pytest.param(lambda r: httpx.Response(200, text="json degil"), id="gecersiz-govde"),
        pytest.param(lambda r: groq_ok(wrap=lambda s: "bu JSON değil"), id="bozuk-json"),
        pytest.param(lambda r: groq_ok(payload={"story_points": "çok"}), id="sema-uyumsuz"),
    ],
)
def test_groq_basarisiz_olursa_gemini_yedegine_gecilir(groq_handler):
    service, calls = make_service(groq_handler=groq_handler)
    result = service.complete_json("s", "u", Points)
    assert result.provider == "gemini"
    assert result.data.reason == GOOD["reason"]
    assert calls["groq"] == 1 and calls["gemini"] == 1


def test_gemini_istegi_dogru_baslik_ve_govde_ile_gider():
    seen = {}

    def gemini(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        return gemini_ok()

    service, _ = make_service(groq_handler=lambda r: httpx.Response(503), gemini_handler=gemini)
    service.complete_json("Sistem", "Kullanıcı", Points)
    assert seen["url"].endswith("/models/gemini-model:generateContent")
    assert seen["key"] == "m-key"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "Sistem"
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "Kullanıcı"


def test_iki_servis_de_basarisizsa_503_llm_unavailable():
    service, calls = make_service(
        groq_handler=lambda r: httpx.Response(503),
        gemini_handler=lambda r: (_ for _ in ()).throw(httpx.ReadTimeout("zaman aşımı")),
    )
    with pytest.raises(LLMUnavailableException) as exc:
        service.complete_json("s", "u", Points)
    assert exc.value.status_code == 503
    assert exc.value.code == "LLM_UNAVAILABLE"
    assert exc.value.message == "Yapay zekâ özelliği şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin."
    assert calls == {"groq": 1, "gemini": 1}


def test_anahtari_olmayan_servis_denenmez():
    service, calls = make_service(groq_key="")
    result = service.complete_json("s", "u", Points)
    assert result.provider == "gemini"
    assert calls == {"groq": 0, "gemini": 1}


def test_hic_anahtar_yoksa_istek_atilmadan_503():
    service, calls = make_service(groq_key="  ", gemini_key="")
    with pytest.raises(LLMUnavailableException):
        service.complete_json("s", "u", Points)
    assert calls == {"groq": 0, "gemini": 0}


def test_hata_mesaji_ve_gunlukler_kullanici_metnini_sizdirmaz(caplog):
    secret = "GIZLI-PROJE-NOTU"
    service, _ = make_service(
        groq_handler=lambda r: httpx.Response(500, text=f"hata: {secret}"),
        gemini_handler=lambda r: httpx.Response(500, text=f"hata: {secret}"),
    )
    with caplog.at_level("WARNING"):
        with pytest.raises(LLMUnavailableException) as exc:
            service.complete_json("s", secret, Points)
    assert secret not in caplog.text
    assert secret not in exc.value.message


class TestParseJson:
    def test_kod_citi_siyrilir(self):
        text = '```json\n{"story_points": 3, "reason": "küçük iş"}\n```'
        assert parse_json_response(text, Points).story_points == 3

    def test_turkce_karakterler_korunur(self):
        text = json.dumps({"story_points": 2, "reason": "Şifre sıfırlama ekranı"}, ensure_ascii=False)
        assert parse_json_response(text, Points).reason == "Şifre sıfırlama ekranı"


class TestRateLimiter:
    def test_dakikada_10_istege_izin_verir_11_inciyi_reddeder(self):
        limiter = RateLimiter(10)
        for i in range(10):
            limiter.check(user_id=1, now=100.0 + i)
        with pytest.raises(RateLimitedException) as exc:
            limiter.check(user_id=1, now=110.0)
        assert exc.value.status_code == 429
        assert exc.value.code == "RATE_LIMITED"
        assert exc.value.message == "Çok fazla istek gönderdiniz, lütfen biraz bekleyin."

    def test_limit_kullanici_basinadir(self):
        limiter = RateLimiter(10)
        for _ in range(10):
            limiter.check(user_id=1, now=100.0)
        limiter.check(user_id=2, now=100.0)  # başka kullanıcı etkilenmez

    def test_pencere_dolunca_yeniden_izin_verilir(self):
        limiter = RateLimiter(10)
        for _ in range(10):
            limiter.check(user_id=1, now=100.0)
        with pytest.raises(RateLimitedException):
            limiter.check(user_id=1, now=159.9)
        limiter.check(user_id=1, now=160.0)  # 60 saniye sonra


class TestAyarlar:
    def test_varsayilanlar_sozlesmeye_uygun(self):
        from app.config import settings

        assert settings.LLM_TIMEOUT_SECONDS == 10  # FR-083
        assert settings.LLM_RATE_LIMIT_PER_MINUTE == 10
