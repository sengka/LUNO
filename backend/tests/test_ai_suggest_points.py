"""Efor puanı önerisi testleri (US-052 basit hali, FR-080, sözleşme 13.4, #258).

Gerçek Groq/Gemini'ye istek gitmez:
- Yetki ve yanıt biçimi testlerinde get_llm_service yerine sahte bir servis verilir.
- Puan doğrulama testlerinde gerçek LLMService, httpx.MockTransport'lu sağlayıcılarla kurulur.
"""

import json
from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models import Project, ProjectMember, Task, TaskStatus, User
from app.services.llm import (
    GeminiProvider,
    GroqProvider,
    LLMResult,
    LLMService,
    get_llm_service,
)

PASSWORD = "Password123"


def register(client: TestClient, email: str, db: Session, role: str = "EKIP_UYESI"):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": email.split("@")[0].title(), "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    if role != "EKIP_UYESI":
        db.get(User, user_id).role = role
        db.commit()
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}, user_id


class FakeLLM:
    """complete_json çağrılarını kaydeder ve hazır bir sonuç döndürür."""

    def __init__(self, provider="groq", story_points=5, reason="Birden fazla ekran ve API bağlantısı içeriyor."):
        self.provider = provider
        self.story_points = story_points
        self.reason = reason
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user, "schema": schema})
        data = schema(story_points=self.story_points, reason=self.reason)
        return LLMResult(provider=self.provider, data=data)


@pytest.fixture
def fake_llm():
    fake = FakeLLM()
    app.dependency_overrides[get_llm_service] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_service, None)


@pytest.fixture
def setup(client: TestClient, db_session: Session):
    admin, admin_id = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    member, member_id = register(client, "uye@ornek.com", db_session)
    other_admin, other_admin_id = register(client, "baska.yonetici@ornek.com", db_session, "YONETICI")

    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    other = Project(name="Web Sitesi", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db_session.add_all([project, other])
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=member_id),
            ProjectMember(project_id=other.id, user_id=other_admin_id),
        ]
    )
    task = Task(
        project_id=project.id,
        title="Şifre sıfırlama",
        description="E-postayla bağlantı gönderen API ve yeni şifre formu.",
        status=TaskStatus.TODO,
    )
    db_session.add(task)
    db_session.commit()
    return {"task": task, "admin": admin, "member": member, "other_admin": other_admin}


def url(task_id: int) -> str:
    return f"/api/v1/ai/tasks/{task_id}/suggest-points"


# --- Başarılı yanıt -----------------------------------------------------------------------

def test_yonetici_oneri_alir_yanitta_provider_puan_ve_gerekce_var(client, setup, fake_llm):
    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "provider": "groq",
        "story_points": 5,
        "reason": "Birden fazla ekran ve API bağlantısı içeriyor.",
    }


def test_modele_gorev_basligi_ve_aciklamasi_gonderilir(client, setup, fake_llm):
    client.post(url(setup["task"].id), headers=setup["admin"])

    assert len(fake_llm.calls) == 1
    user_text = fake_llm.calls[0]["user"]
    assert "Şifre sıfırlama" in user_text
    assert "E-postayla bağlantı gönderen API" in user_text
    assert "1, 2, 3, 5, 8, 13" in fake_llm.calls[0]["system"]


def test_aciklamasi_olmayan_gorevde_de_oneri_alinir(client, setup, fake_llm, db_session):
    task = setup["task"]
    task.description = None
    db_session.commit()

    response = client.post(url(task.id), headers=setup["admin"])

    assert response.status_code == 200
    assert "Açıklama: (yok)" in fake_llm.calls[0]["user"]


def test_yedek_servis_kullanildiysa_provider_gemini_doner(client, setup, fake_llm):
    fake_llm.provider = "gemini"

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"


def test_oneri_veritabanina_yazilmaz(client, setup, fake_llm, db_session):
    task_id = setup["task"].id

    client.post(url(task_id), headers=setup["admin"])

    db_session.expire_all()
    assert db_session.get(Task, task_id).story_points is None


# --- Yetki --------------------------------------------------------------------------------

def test_giris_yapmamis_kullanici_401(client, setup, fake_llm):
    response = client.post(url(setup["task"].id))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert fake_llm.calls == []


def test_ekip_uyesi_403_forbidden_ve_modele_istek_gitmez(client, setup, fake_llm):
    response = client.post(url(setup["task"].id), headers=setup["member"])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert fake_llm.calls == []


def test_projenin_uyesi_olmayan_yonetici_403_project_access_denied(client, setup, fake_llm):
    response = client.post(url(setup["task"].id), headers=setup["other_admin"])

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert fake_llm.calls == []


def test_olmayan_gorev_404_task_not_found(client, setup, fake_llm):
    response = client.post(url(999999), headers=setup["admin"])

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
    assert fake_llm.calls == []


# --- Puan doğrulama (gerçek LLMService, sahte HTTP) -----------------------------------------

def groq_says(payload):
    return lambda request: httpx.Response(
        200, json={"choices": [{"message": {"content": json.dumps(payload)}}]}
    )


def gemini_says(payload):
    return lambda request: httpx.Response(
        200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}]}
    )


def use_real_service(groq_handler, gemini_handler):
    service = LLMService(
        providers=[
            GroqProvider("g-key", "groq-model", httpx.Client(transport=httpx.MockTransport(groq_handler))),
            GeminiProvider("m-key", "gemini-model", httpx.Client(transport=httpx.MockTransport(gemini_handler))),
        ],
        timeout=10,
    )
    app.dependency_overrides[get_llm_service] = lambda: service


@pytest.fixture
def cleanup_llm_override():
    yield
    app.dependency_overrides.pop(get_llm_service, None)


def test_gecersiz_puan_donerse_yedek_servisin_gecerli_puani_kullanilir(client, setup, cleanup_llm_override):
    use_real_service(
        groq_says({"story_points": 4, "reason": "Orta büyüklükte."}),
        gemini_says({"story_points": 3, "reason": "Tek ekran."}),
    )

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200
    assert response.json() == {"provider": "gemini", "story_points": 3, "reason": "Tek ekran."}


def test_iki_servis_de_gecersiz_puan_donerse_503(client, setup, cleanup_llm_override):
    use_real_service(
        groq_says({"story_points": 4, "reason": "Orta."}),
        gemini_says({"story_points": 21, "reason": "Çok büyük."}),
    )

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "LLM_UNAVAILABLE"


@pytest.mark.parametrize("points", [1, 2, 3, 5, 8, 13])
def test_sozlesmedeki_tum_puanlar_kabul_edilir(client, setup, cleanup_llm_override, points):
    use_real_service(groq_says({"story_points": points, "reason": "Gerekçe."}), gemini_says({}))

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200
    assert response.json()["story_points"] == points
