"""Alt görev önerisi testleri (US-052, FR-079, sözleşme 13.3, #303).

Gerçek Groq/Gemini'ye istek gitmez: get_llm_service yerine modele giden metni kaydeden sahte bir servis verilir.
"""

from datetime import date

import pytest

from app.main import app
from app.models import Project, ProjectMember, Task, TaskStatus
from app.services.llm import LLMResult, RateLimiter, get_llm_rate_limiter, get_llm_service
from tests.test_ai_suggest_points import register


class RecordingLLM:
    def __init__(self, output):
        self.output = output
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user})
        return LLMResult(provider="groq", data=schema.model_validate(self.output))


@pytest.fixture(autouse=True)
def overrides():
    limiter = RateLimiter(10)
    app.dependency_overrides[get_llm_rate_limiter] = lambda: limiter
    yield
    app.dependency_overrides.pop(get_llm_rate_limiter, None)
    app.dependency_overrides.pop(get_llm_service, None)


def use_llm(titles) -> RecordingLLM:
    fake = RecordingLLM({"suggestions": [{"title": t} for t in titles]})
    app.dependency_overrides[get_llm_service] = lambda: fake
    return fake


@pytest.fixture
def setup(client, db_session):
    admin, admin_id = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    member, member_id = register(client, "uye@ornek.com", db_session)
    outsider, _ = register(client, "dis@ornek.com", db_session, "YONETICI")
    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 31))
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=member_id),
        ]
    )
    task = Task(project_id=project.id, title="Giriş sistemi", description="E-posta ve şifreyle giriş, JWT.",
                status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    return {"db": db_session, "admin": admin, "member": member, "outsider": outsider,
            "project_id": project.id, "task": task}


def add_subtask(db, task, title):
    subtask = Task(project_id=task.project_id, parent_id=task.id, title=title, status=TaskStatus.TODO)
    db.add(subtask)
    db.commit()
    return subtask


def url(task_id):
    return f"/api/v1/ai/tasks/{task_id}/suggest-subtasks"


def test_sozlesmedeki_bicimde_alt_gorev_onerileri_doner(client, setup):
    use_llm(["Form tasarımı", "JWT entegrasyonu"])

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "provider": "groq",
        "suggestions": [{"title": "Form tasarımı"}, {"title": "JWT entegrasyonu"}],
    }


def test_modele_baslik_aciklama_ve_mevcut_alt_gorevler_gider(client, setup):
    add_subtask(setup["db"], setup["task"], "Form tasarımı")
    fake = use_llm(["JWT entegrasyonu"])

    client.post(url(setup["task"].id), headers=setup["admin"])

    user_text = fake.calls[0]["user"]
    assert user_text.startswith("<veri>") and user_text.endswith("</veri>")
    assert "Başlık: Giriş sistemi" in user_text
    assert "Açıklama: E-posta ve şifreyle giriş, JWT." in user_text
    assert "Mevcut alt görevler (bunları tekrar önerme):\n- Form tasarımı" in user_text
    assert "3 ile 7" in fake.calls[0]["system"] and "Güvenlik kuralı" in fake.calls[0]["system"]


def test_alt_gorevi_ve_aciklamasi_olmayan_gorevde_de_oneri_alinir(client, setup):
    setup["task"].description = None
    setup["db"].commit()
    fake = use_llm(["Form tasarımı"])

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200
    assert "Açıklama: (yok)" in fake.calls[0]["user"]
    assert "Mevcut alt görevler: (yok)" in fake.calls[0]["user"]


def test_tekrar_eden_mevcutla_ayni_ve_bos_oneriler_atilir(client, setup):
    add_subtask(setup["db"], setup["task"], "Form tasarımı")
    use_llm(["form TASARIMI.", "JWT entegrasyonu", "  ", "Jwt  entegrasyonu", "Şifre sıfırlama", "Sifre sifirlama"])

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert response.json()["suggestions"] == [{"title": "JWT entegrasyonu"}, {"title": "Şifre sıfırlama"}]


def test_uzun_baslik_200_karaktere_kisaltilir(client, setup):
    use_llm(["x" * 250])

    response = client.post(url(setup["task"].id), headers=setup["admin"])

    assert len(response.json()["suggestions"][0]["title"]) == 200


def test_alt_gorev_icin_oneri_istenirse_400_ve_modele_gitmez(client, setup):
    subtask = add_subtask(setup["db"], setup["task"], "Form tasarımı")
    fake = use_llm(["Bir şey"])

    response = client.post(url(subtask.id), headers=setup["admin"])

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "NESTED_SUBTASK_NOT_ALLOWED",
            "message": "Alt görevlere alt görev eklenemez.",
            "fields": None,
            "details": None,
        }
    }
    assert fake.calls == []


def test_alt_gorev_istekleri_istek_sinirindan_dusmez(client, setup):
    subtask = add_subtask(setup["db"], setup["task"], "Form tasarımı")
    use_llm(["JWT entegrasyonu"])
    for _ in range(12):
        assert client.post(url(subtask.id), headers=setup["admin"]).status_code == 400

    assert client.post(url(setup["task"].id), headers=setup["admin"]).status_code == 200


def test_yetki_kontrolleri(client, setup):
    fake = use_llm(["Form tasarımı"])
    tid = setup["task"].id

    assert client.post(url(tid), headers=setup["member"]).json()["error"]["code"] == "FORBIDDEN"
    assert client.post(url(tid), headers=setup["outsider"]).json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert client.post(url(999999), headers=setup["admin"]).json()["error"]["code"] == "TASK_NOT_FOUND"
    assert client.post(url(tid)).status_code == 401
    assert fake.calls == []
