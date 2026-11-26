"""Toplantı notundan görev çıkarma testleri (US-051, FR-077, sözleşme 13.2, #302).

- Türkçe tarih ifadelerinin tarihe çevrilmesi (bugün sabit: 16 Kasım 2026 Pazartesi).
- Kişi adının proje üyeleriyle eşleştirilmesi.
- Uç nokta: yanıt biçimi, boş liste, 5000 karakter sınırı, yetki.
Gerçek Groq/Gemini'ye istek gitmez.
"""

from datetime import date
from types import SimpleNamespace

import pytest

from app.main import app
from app.models import Project, ProjectMember, User
from app.services.ai_extract import match_assignee
from app.services.llm import LLMResult, RateLimiter, get_llm_rate_limiter, get_llm_service
from app.services.turkish_dates import resolve_due_date
from tests.test_ai_suggest_points import register

MONDAY = date(2026, 11, 16)


# --- Türkçe tarih ifadeleri -----------------------------------------------------------------------

@pytest.mark.parametrize(
    "expression, expected",
    [
        ("yarın", date(2026, 11, 17)),
        ("bugün", date(2026, 11, 16)),
        ("cuma", date(2026, 11, 20)),
        ("cumaya kadar", date(2026, 11, 20)),
        ("Cuma'ya kadar", date(2026, 11, 20)),
        ("perşembeye kadar", date(2026, 11, 19)),
        ("persembeye kadar", date(2026, 11, 19)),  # Türkçe karaktersiz
        ("çarşamba günü", date(2026, 11, 18)),
        ("çarşamba gününe", date(2026, 11, 18)),  # gerçek model denemesinde Groq böyle yazdı
        ("cuma gününe kadar", date(2026, 11, 20)),
        ("Cuma günü'ne kadar", date(2026, 11, 20)),
        ("perşembe akşamına", date(2026, 11, 19)),
        ("cuma sabahı", date(2026, 11, 20)),
        ("carsamba gunune", date(2026, 11, 18)),
        ("salı", date(2026, 11, 17)),
        ("pazartesiye kadar", date(2026, 11, 23)),  # bugün pazartesi: bir sonraki pazartesi
        ("haftaya salı", date(2026, 11, 24)),
        ("Haftaya Salı", date(2026, 11, 24)),
        ("gelecek hafta salı", date(2026, 11, 24)),
        ("önümüzdeki hafta cuma", date(2026, 11, 27)),
        ("haftaya pazartesi", date(2026, 11, 23)),
        ("2 gün sonra", date(2026, 11, 18)),
        ("3 gün içinde", date(2026, 11, 19)),
        ("20 Kasım", date(2026, 11, 20)),
        ("20 kasıma kadar", date(2026, 11, 20)),
        ("15 aralığa kadar", date(2026, 12, 15)),  # ünsüz yumuşaması: aralığa → aralık
        ("25.11.2026", date(2026, 11, 25)),
    ],
)
def test_turkce_tarih_ifadesi_cozulur(expression, expected):
    assert resolve_due_date(expression, MONDAY) == expected


@pytest.mark.parametrize("expression", [None, "", "   ", "yakında", "ay sonuna kadar", "haftaya bir ara"])
def test_cozulemeyen_ifade_none_doner(expression):
    assert resolve_due_date(expression, MONDAY) is None


def test_haftanin_ayni_gunu_soylenirse_bir_sonraki_hafta_alinir():
    friday = date(2026, 11, 20)

    assert resolve_due_date("cumaya kadar", friday) == date(2026, 11, 27)
    assert resolve_due_date("haftaya cuma", friday) == date(2026, 11, 27)


# --- Kişi eşleştirme ------------------------------------------------------------------------------

MEMBERS = [
    SimpleNamespace(id=1, full_name="Can Demir"),
    SimpleNamespace(id=2, full_name="Ayşe Kaya"),
    SimpleNamespace(id=3, full_name="Ayşe Yılmaz"),
    SimpleNamespace(id=4, full_name="İlker Şahin"),
]


@pytest.mark.parametrize(
    "name, expected",
    [
        ("Can", (1, "Can Demir")),  # yalnız ad, tek kişi
        ("can", (1, "Can Demir")),
        ("Can Demir", (1, "Can Demir")),
        ("CAN DEMİR", (1, "Can Demir")),
        ("ilker", (4, "İlker Şahin")),  # Türkçe büyük İ
        ("Ilker Sahin", (4, "İlker Şahin")),  # Türkçe karaktersiz
        ("Ayse Kaya", (2, "Ayşe Kaya")),  # ad-soyad ile iki Ayşe'den biri seçilir
        ("Ayşe", (None, "Ayşe")),  # birden fazla eşleşme
        ("Mehmet", (None, "Mehmet")),  # projede yok
        ("Can Yılmaz", (None, "Can Yılmaz")),  # soyadı tutmuyor
        (None, (None, None)),
    ],
)
def test_kisi_adi_proje_uyeleriyle_eslestirilir(name, expected):
    assert match_assignee(name, MEMBERS) == expected


# --- Uç nokta -------------------------------------------------------------------------------------

class RecordingLLM:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user})
        return LLMResult(provider="groq", data=schema.model_validate(self.output))


@pytest.fixture(autouse=True)
def overrides(monkeypatch):
    monkeypatch.setattr("app.api.v1.ai.today_utc", lambda: MONDAY)
    limiter = RateLimiter(10)
    app.dependency_overrides[get_llm_rate_limiter] = lambda: limiter
    yield
    app.dependency_overrides.pop(get_llm_rate_limiter, None)
    app.dependency_overrides.pop(get_llm_service, None)


def use_llm(output) -> RecordingLLM:
    fake = RecordingLLM(output)
    app.dependency_overrides[get_llm_service] = lambda: fake
    return fake


@pytest.fixture
def setup(client, db_session):
    admin, admin_id = register(client, "can.demir@ornek.com", db_session, "YONETICI")
    member, member_id = register(client, "ayse.kaya@ornek.com", db_session)
    outsider, _ = register(client, "dis@ornek.com", db_session, "YONETICI")
    db_session.get(User, admin_id).full_name = "Can Demir"
    db_session.get(User, member_id).full_name = "Ayşe Kaya"
    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 31))
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=member_id),
        ]
    )
    db_session.commit()
    return {"admin": admin, "admin_id": admin_id, "member": member, "member_id": member_id,
            "outsider": outsider, "project_id": project.id}


def url(project_id):
    return f"/api/v1/ai/projects/{project_id}/extract-tasks"


NOTE = "Can API'yi cumaya kadar yapacak. Ayşe giriş ekranını tasarlayacak. Mehmet haftaya salı testleri yazar."


def test_sozlesmedeki_ornek_gibi_gorev_onerileri_doner(client, setup):
    fake = use_llm(
        {
            "suggestions": [
                {"title": "API geliştirme", "assignee_name": "Can", "due_expression": "cumaya kadar"},
                {"title": "Giriş ekranı tasarımı", "assignee_name": "Ayşe", "due_expression": None},
                {"title": "Testleri yazma", "assignee_name": "Mehmet", "due_expression": "haftaya salı"},
            ]
        }
    )

    response = client.post(url(setup["project_id"]), headers=setup["admin"], json={"text": NOTE})

    assert response.status_code == 200, response.text
    assert response.json() == {
        "provider": "groq",
        "suggestions": [
            {"title": "API geliştirme", "assignee_id": setup["admin_id"], "assignee_name": "Can Demir",
             "due_date": "2026-11-20"},
            {"title": "Giriş ekranı tasarımı", "assignee_id": setup["member_id"], "assignee_name": "Ayşe Kaya",
             "due_date": None},
            {"title": "Testleri yazma", "assignee_id": None, "assignee_name": "Mehmet", "due_date": "2026-11-24"},
        ],
    }
    # Not, ortak şablonla (veri etiketleri) modele gider; model tarih değil ifade döndürmeye yönlendirilir.
    assert fake.calls[0]["user"] == f"<veri>\n{NOTE}\n</veri>"
    assert "due_expression" in fake.calls[0]["system"] and "Tarihi hesaplama" in fake.calls[0]["system"]


def test_gorev_icermeyen_notta_bos_liste(client, setup):
    use_llm({"suggestions": []})

    response = client.post(url(setup["project_id"]), headers=setup["admin"], json={"text": "Retroyu yaptık."})

    assert response.status_code == 200
    assert response.json() == {"provider": "groq", "suggestions": []}


def test_basligi_bos_oneriler_atilir_uzun_baslik_200_karaktere_kisaltilir(client, setup):
    use_llm({"suggestions": [{"title": "  "}, {"title": "x" * 250}]})

    response = client.post(url(setup["project_id"]), headers=setup["admin"], json={"text": "not"})

    suggestions = response.json()["suggestions"]
    assert len(suggestions) == 1 and len(suggestions[0]["title"]) == 200


def test_5000_karakter_kabul_edilir_5001_reddedilir(client, setup):
    fake = use_llm({"suggestions": []})
    pid = setup["project_id"]

    assert client.post(url(pid), headers=setup["admin"], json={"text": "a" * 5000}).status_code == 200
    response = client.post(url(pid), headers=setup["admin"], json={"text": "a" * 5001})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert len(fake.calls) == 1


@pytest.mark.parametrize("body", [{}, {"text": ""}, {"text": "   "}])
def test_bos_not_422(client, setup, body):
    fake = use_llm({"suggestions": []})

    response = client.post(url(setup["project_id"]), headers=setup["admin"], json=body)

    assert response.status_code == 422
    assert fake.calls == []


def test_yetki_kontrolleri(client, setup):
    fake = use_llm({"suggestions": []})
    pid, body = setup["project_id"], {"text": NOTE}

    assert client.post(url(pid), headers=setup["member"], json=body).json()["error"]["code"] == "FORBIDDEN"
    assert client.post(url(pid), headers=setup["outsider"], json=body).json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert client.post(url(999999), headers=setup["admin"], json=body).json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert client.post(url(pid), json=body).status_code == 401
    assert fake.calls == []


def test_gecersiz_govdeli_istekler_istek_sinirindan_dusmez(client, setup):
    use_llm({"suggestions": []})
    pid = setup["project_id"]
    for _ in range(12):
        assert client.post(url(pid), headers=setup["admin"], json={"text": "a" * 5001}).status_code == 422

    assert client.post(url(pid), headers=setup["admin"], json={"text": NOTE}).status_code == 200


def test_gecerli_isteklerde_dakikada_10_istek_siniri_calisir(client, setup):
    fake = use_llm({"suggestions": []})
    pid = setup["project_id"]
    for _ in range(10):
        assert client.post(url(pid), headers=setup["admin"], json={"text": NOTE}).status_code == 200

    response = client.post(url(pid), headers=setup["admin"], json={"text": NOTE})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert len(fake.calls) == 10
