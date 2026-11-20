"""LLM uç noktalarında istek sınırı ve hata durumu testleri (US-026, FR-083, FR-084, sözleşme 13.1, #259).

Gerçek Groq/Gemini'ye istek gitmez. Uç nokta olarak efor puanı önerisi (13.4) kullanılır.
"""

import httpx
import pytest

from app.main import app
from app.services.llm import (
    GeminiProvider,
    GroqProvider,
    LLMService,
    RateLimiter,
    get_llm_rate_limiter,
    get_llm_service,
)
from tests.test_ai_suggest_points import FakeLLM, gemini_says, groq_says, register, url

LIMIT = 10  # sözleşme 13.1: kullanıcı başına dakikada en fazla 10 LLM isteği


class Clock:
    """RateLimiter'a verilen elle ilerletilebilir saat; testte gerçekten 60 sn beklenmez."""

    def __init__(self):
        self.now = 1000.0


class ClockedLimiter(RateLimiter):
    def __init__(self, clock: Clock):
        super().__init__(LIMIT)
        self.clock = clock

    def check(self, user_id, now=None):
        super().check(user_id, now=self.clock.now)


@pytest.fixture
def clock():
    clock = Clock()
    limiter = ClockedLimiter(clock)
    app.dependency_overrides[get_llm_rate_limiter] = lambda: limiter
    yield clock
    app.dependency_overrides.pop(get_llm_rate_limiter, None)


@pytest.fixture
def fake_llm():
    fake = FakeLLM()
    app.dependency_overrides[get_llm_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_service, None)


@pytest.fixture
def setup(client, db_session):
    from datetime import date

    from app.models import Project, ProjectMember, Task

    admin, admin_id = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    admin2, admin2_id = register(client, "yonetici2@ornek.com", db_session, "YONETICI")
    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=admin2_id),
        ]
    )
    task = Task(project_id=project.id, title="Giriş ekranı", description="Form ve API.")
    db_session.add(task)
    db_session.commit()
    return {"task_id": task.id, "admin": admin, "admin2": admin2}


# --- 429 RATE_LIMITED ----------------------------------------------------------------------

def test_dakikada_10_istek_yapilabilir_11_inci_429_doner(client, setup, clock, fake_llm):
    for _ in range(LIMIT):
        assert client.post(url(setup["task_id"]), headers=setup["admin"]).status_code == 200

    response = client.post(url(setup["task_id"]), headers=setup["admin"])

    assert response.status_code == 429
    assert response.json() == {
        "error": {
            "code": "RATE_LIMITED",
            "message": "Çok fazla istek gönderdiniz, lütfen biraz bekleyin.",
            "fields": None,
            "details": None,
        }
    }
    # Sınırı aşan istek modele gitmez.
    assert len(fake_llm.calls) == LIMIT


def test_sinir_kullanici_basinadir_baska_yonetici_etkilenmez(client, setup, clock, fake_llm):
    for _ in range(LIMIT):
        client.post(url(setup["task_id"]), headers=setup["admin"])
    assert client.post(url(setup["task_id"]), headers=setup["admin"]).status_code == 429

    response = client.post(url(setup["task_id"]), headers=setup["admin2"])

    assert response.status_code == 200


def test_bir_dakika_gecince_yeniden_istek_yapilabilir(client, setup, clock, fake_llm):
    for _ in range(LIMIT):
        client.post(url(setup["task_id"]), headers=setup["admin"])
    clock.now += 59
    assert client.post(url(setup["task_id"]), headers=setup["admin"]).status_code == 429

    clock.now += 1  # ilk isteğin üzerinden 60 sn geçti

    assert client.post(url(setup["task_id"]), headers=setup["admin"]).status_code == 200


def test_yetki_veya_bulunamadi_hatasi_alan_istekler_sinira_sayilmaz(client, setup, clock, fake_llm):
    for _ in range(LIMIT + 5):
        assert client.post(url(999999), headers=setup["admin"]).status_code == 404

    response = client.post(url(setup["task_id"]), headers=setup["admin"])

    assert response.status_code == 200


# --- Yedeğe geçiş ve 503 LLM_UNAVAILABLE (gerçek LLMService, sahte HTTP) --------------------

def fails_with(exc_type):
    def handler(request: httpx.Request):
        raise exc_type("sahte hata", request=request)

    return handler


def server_error(request):
    return httpx.Response(500, json={"error": "sunucu hatası"})


def use_service(groq_handler, gemini_handler, gemini_key="m-key"):
    service = LLMService(
        providers=[
            GroqProvider("g-key", "groq-model", httpx.Client(transport=httpx.MockTransport(groq_handler))),
            GeminiProvider(gemini_key, "gemini-model", httpx.Client(transport=httpx.MockTransport(gemini_handler))),
        ],
        timeout=10,
    )
    app.dependency_overrides[get_llm_service] = lambda: service


@pytest.fixture
def real_service_cleanup():
    yield
    app.dependency_overrides.pop(get_llm_service, None)


LLM_UNAVAILABLE = {
    "error": {
        "code": "LLM_UNAVAILABLE",
        "message": "Yapay zekâ özelliği şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.",
        "fields": None,
        "details": None,
    }
}


def test_groq_zaman_asimina_ugrarsa_gemini_yaniti_doner(client, setup, clock, real_service_cleanup):
    use_service(fails_with(httpx.ReadTimeout), gemini_says({"story_points": 3, "reason": "Tek ekran."}))

    response = client.post(url(setup["task_id"]), headers=setup["admin"])

    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"


@pytest.mark.parametrize(
    "groq_handler, gemini_handler",
    [
        (fails_with(httpx.ReadTimeout), fails_with(httpx.ReadTimeout)),
        (fails_with(httpx.ConnectError), fails_with(httpx.ConnectError)),
        (server_error, server_error),
        (groq_says({"beklenmeyen": "alan"}), gemini_says({"beklenmeyen": "alan"})),
    ],
    ids=["zaman-asimi", "baglanti-hatasi", "http-500", "bozuk-json"],
)
def test_iki_servis_de_yanit_vermezse_503_llm_unavailable(
    client, setup, clock, real_service_cleanup, groq_handler, gemini_handler
):
    use_service(groq_handler, gemini_handler)

    response = client.post(url(setup["task_id"]), headers=setup["admin"])

    assert response.status_code == 503
    assert response.json() == LLM_UNAVAILABLE


def test_canlida_gemini_anahtari_bos_iken_groq_duserse_503(client, setup, clock, real_service_cleanup):
    # Ekip kararı (#257): canlıda GEMINI_API_KEY boş; gerçek veri Gemini'ye gitmez.
    gemini_calls = []

    def gemini_handler(request):
        gemini_calls.append(request)
        return gemini_says({"story_points": 3, "reason": "Tek ekran."})(request)

    use_service(fails_with(httpx.ConnectError), gemini_handler, gemini_key="")

    response = client.post(url(setup["task_id"]), headers=setup["admin"])

    assert response.status_code == 503
    assert response.json() == LLM_UNAVAILABLE
    assert gemini_calls == []
