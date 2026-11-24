"""LLM özet uç noktaları testleri (US-053, FR-081, FR-082, sözleşme 13.5–13.6, #297).

Gerçek Groq/Gemini'ye istek gitmez: get_llm_service yerine modele giden metni kaydeden sahte
bir servis verilir. "Bugün" sabitlenir; böylece son 7 günün sınırları ölçülebilir.
"""

from datetime import date, datetime, timedelta, timezone

import httpx
import pytest

from app.main import app
from app.models import Comment, Project, ProjectMember, Sprint, Task, TaskStatus
from app.services.llm import (
    GeminiProvider,
    GroqProvider,
    LLMResult,
    LLMService,
    RateLimiter,
    get_llm_rate_limiter,
    get_llm_service,
)
from tests.test_ai_suggest_points import gemini_says, groq_says, register

TODAY = date(2026, 11, 20)  # Cuma; son 7 gün: 14–20 Kasım


def at(day: date, hour: int = 12) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=timezone.utc)


class RecordingLLM:
    """Modele giden sistem ve kullanıcı metnini kaydeder, hazır bir yanıt döndürür."""

    def __init__(self, output: dict, provider: str = "groq"):
        self.output = output
        self.provider = provider
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append({"system": system, "user": user})
        return LLMResult(provider=self.provider, data=schema.model_validate(self.output))


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch):
    monkeypatch.setattr("app.api.v1.ai.today_utc", lambda: TODAY)


@pytest.fixture(autouse=True)
def limiter():
    limiter = RateLimiter(10)
    app.dependency_overrides[get_llm_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_llm_rate_limiter, None)


def use_llm(output: dict, provider: str = "groq") -> RecordingLLM:
    fake = RecordingLLM(output, provider)
    app.dependency_overrides[get_llm_service] = lambda: fake
    return fake


@pytest.fixture(autouse=True)
def cleanup_llm():
    yield
    app.dependency_overrides.pop(get_llm_service, None)


@pytest.fixture
def setup(client, db_session):
    admin, admin_id = register(client, "can.demir@ornek.com", db_session, "YONETICI")
    member, member_id = register(client, "ayse.kaya@ornek.com", db_session)
    outsider, outsider_id = register(client, "dis.yonetici@ornek.com", db_session, "YONETICI")

    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 31))
    other = Project(name="Başka Proje", start_date=date(2026, 10, 1), end_date=date(2026, 12, 31))
    db_session.add_all([project, other])
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=member_id),
            ProjectMember(project_id=other.id, user_id=outsider_id),
        ]
    )
    task = Task(project_id=project.id, title="Giriş ekranı", status=TaskStatus.IN_PROGRESS, assignee_id=member_id)
    db_session.add(task)
    db_session.commit()
    return {
        "db": db_session,
        "admin": admin,
        "admin_id": admin_id,
        "member": member,
        "member_id": member_id,
        "outsider": outsider,
        "project": project,
        "other": other,
        "task": task,
    }


def add_task(db, project, title, status=TaskStatus.TODO, **fields):
    task = Task(project_id=project.id, title=title, status=status, **fields)
    db.add(task)
    db.commit()
    return task


def add_comments(db, task, author_id, count, start=date(2026, 11, 10)):
    for i in range(count):
        db.add(Comment(task_id=task.id, author_id=author_id, body=f"Yorum {i + 1}", created_at=at(start + timedelta(days=i))))
    db.commit()


def error_code(response):
    return response.status_code, response.json()["error"]["code"]


# --- 13.5 Haftalık proje özeti -------------------------------------------------------------------

def weekly_url(project_id):
    return f"/api/v1/ai/projects/{project_id}/weekly-summary"


def test_haftalik_ozet_sozlesmedeki_bicimde_doner(client, setup):
    use_llm({"summary": "Bu hafta 1 görev tamamlandı."})

    response = client.post(weekly_url(setup["project"].id), headers=setup["admin"])

    assert response.status_code == 200, response.text
    assert response.json() == {
        "provider": "groq",
        "from": "2026-11-14",
        "to": "2026-11-20",
        "summary": "Bu hafta 1 görev tamamlandı.",
    }


def test_haftalik_ozete_son_7_gunun_verileri_gider(client, setup):
    db, project = setup["db"], setup["project"]
    add_task(db, project, "Bu hafta biten API", TaskStatus.DONE, completed_at=at(date(2026, 11, 14)),
             assignee_id=setup["member_id"])
    add_task(db, project, "Geçen hafta biten tasarım", TaskStatus.DONE, completed_at=at(date(2026, 11, 13)))
    add_task(db, project, "Gecikmiş test", TaskStatus.TODO, due_date=date(2026, 11, 18))
    add_task(db, project, "Yaklaşan rapor", TaskStatus.REVIEW_TESTING, due_date=date(2026, 11, 25))
    add_task(db, project, "Uzak iş", TaskStatus.TODO, due_date=date(2026, 12, 15))
    add_task(db, setup["other"], "Başka projenin görevi", TaskStatus.DONE, completed_at=at(TODAY))
    db.add(Sprint(project_id=project.id, name="Sprint 7", goal="LLM özellikleri",
                  start_date=date(2026, 11, 17), end_date=date(2026, 11, 23)))
    db.commit()
    fake = use_llm({"summary": "Özet."})

    client.post(weekly_url(project.id), headers=setup["admin"])

    text = fake.calls[0]["user"]
    assert text.startswith("<veri>") and text.endswith("</veri>")
    assert "Proje: Mobil Uygulama" in text
    assert "Dönem: 2026-11-14 – 2026-11-20" in text
    assert "Aktif sprint: Sprint 7" in text and "LLM özellikleri" in text
    assert "Bu hafta tamamlanan görevler: 1" in text
    assert "- Bu hafta biten API (sorumlu: Ayse.Kaya)" in text
    assert "Geçen hafta biten tasarım" not in text.split("Bu hafta oluşturulan")[0]
    assert "Teslim tarihi geçmiş açık görevler: 1\n- Gecikmiş test" in text
    assert "Önümüzdeki 7 günde teslim edilecek açık görevler: 1\n- Yaklaşan rapor" in text
    assert "Uzak iş" not in text  # ne bu hafta bitti/oluşturuldu ne gecikti ne de 7 gün içinde teslim
    assert "Başka projenin görevi" not in text
    assert "Güvenlik kuralı" in fake.calls[0]["system"]


def test_gorevi_olmayan_projede_de_ozet_alinir(client, setup, db_session):
    db_session.delete(setup["task"])
    db_session.commit()
    fake = use_llm({"summary": "Bu hafta kayıtlı bir hareket yok."})

    response = client.post(weekly_url(setup["project"].id), headers=setup["admin"])

    assert response.status_code == 200
    assert "Durumlara göre: projede görev yok" in fake.calls[0]["user"]


def test_haftalik_ozet_yetki_kontrolleri(client, setup):
    fake = use_llm({"summary": "Özet."})
    pid = setup["project"].id

    assert error_code(client.post(weekly_url(pid), headers=setup["member"])) == (403, "FORBIDDEN")
    assert error_code(client.post(weekly_url(pid), headers=setup["outsider"])) == (403, "PROJECT_ACCESS_DENIED")
    assert error_code(client.post(weekly_url(999999), headers=setup["admin"])) == (404, "PROJECT_NOT_FOUND")
    assert client.post(weekly_url(pid)).status_code == 401
    assert fake.calls == []


def test_haftalik_ozette_model_bos_ozet_donerse_yedege_gecilir_ikisi_de_bossa_503(client, setup):
    service = LLMService(
        providers=[
            GroqProvider("g", "m", httpx.Client(transport=httpx.MockTransport(groq_says({"summary": "  "})))),
            GeminiProvider("k", "m", httpx.Client(transport=httpx.MockTransport(gemini_says({"summary": ""})))),
        ],
        timeout=10,
    )
    app.dependency_overrides[get_llm_service] = lambda: service

    response = client.post(weekly_url(setup["project"].id), headers=setup["admin"])

    assert error_code(response) == (503, "LLM_UNAVAILABLE")


# --- 13.6 Yorum zinciri özeti --------------------------------------------------------------------

def comments_url(task_id):
    return f"/api/v1/ai/tasks/{task_id}/summarize-comments"


SUMMARY = {
    "decisions": ["Giriş API'si önce yazılacak."],
    "open_questions": ["Şifre sıfırlama bu sprintte mi?"],
    "summary": "Ekip API'nin önce yazılmasında anlaştı.",
}


def test_yorum_ozeti_sozlesmedeki_bicimde_doner(client, setup):
    add_comments(setup["db"], setup["task"], setup["admin_id"], 5)
    use_llm(SUMMARY, provider="gemini")

    response = client.post(comments_url(setup["task"].id), headers=setup["admin"])

    assert response.status_code == 200, response.text
    assert response.json() == {"provider": "gemini", **SUMMARY}


def test_proje_uyesi_yonetici_olmasa_da_yorum_ozeti_alabilir(client, setup):
    add_comments(setup["db"], setup["task"], setup["admin_id"], 5)
    use_llm(SUMMARY)

    response = client.post(comments_url(setup["task"].id), headers=setup["member"])

    assert response.status_code == 200


def test_bes_yorumdan_azsa_400_not_enough_comments_ve_modele_gitmez(client, setup):
    add_comments(setup["db"], setup["task"], setup["admin_id"], 4)
    fake = use_llm(SUMMARY)

    response = client.post(comments_url(setup["task"].id), headers=setup["member"])

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "NOT_ENOUGH_COMMENTS",
            "message": "Özet için görevde en az 5 yorum olmalıdır.",
            "fields": None,
            "details": None,
        }
    }
    assert fake.calls == []


def test_yetersiz_yorum_istekleri_istek_sinirindan_dusmez(client, setup):
    task = setup["task"]
    for _ in range(12):
        assert client.post(comments_url(task.id), headers=setup["member"]).status_code == 400
    add_comments(setup["db"], task, setup["admin_id"], 5)
    use_llm(SUMMARY)

    assert client.post(comments_url(task.id), headers=setup["member"]).status_code == 200


def test_yorumlar_tarih_sirasiyla_yazar_adiyla_gider_baska_gorevin_yorumu_gitmez(client, setup):
    db, task = setup["db"], setup["task"]
    db.add(Comment(task_id=task.id, author_id=setup["member_id"], body="Son yorum", created_at=at(date(2026, 11, 19))))
    db.add(Comment(task_id=task.id, author_id=setup["admin_id"], body="İlk yorum", created_at=at(date(2026, 11, 1))))
    db.commit()
    add_comments(db, task, setup["admin_id"], 3, start=date(2026, 11, 5))
    other_task = add_task(db, setup["project"], "Başka görev")
    db.add(Comment(task_id=other_task.id, author_id=setup["admin_id"], body="Başka görevin yorumu"))
    db.commit()
    fake = use_llm(SUMMARY)

    client.post(comments_url(task.id), headers=setup["admin"])

    text = fake.calls[0]["user"]
    assert "Görev: Giriş ekranı" in text
    assert text.index("[2026-11-01] Can.Demir: İlk yorum") < text.index("Yorum 1") < text.index(
        "[2026-11-19] Ayse.Kaya: Son yorum"
    )
    assert "Başka görevin yorumu" not in text


def test_uzun_yorum_zincirinde_en_eski_yorumlar_cikarilir(client, setup, monkeypatch):
    db, task = setup["db"], setup["task"]
    for i in range(30):
        db.add(Comment(task_id=task.id, author_id=setup["admin_id"], body=f"Yorum-{i:02d} " + "x" * 80,
                       created_at=at(date(2026, 10, 1) + timedelta(days=i))))
    db.commit()
    monkeypatch.setattr("app.services.ai_summaries.settings.LLM_MAX_INPUT_CHARS", 1300)
    fake = use_llm(SUMMARY)

    client.post(comments_url(task.id), headers=setup["admin"])

    text = fake.calls[0]["user"]
    assert "Yorum-29" in text and "Yorum-00" not in text
    assert "Uzunluk sınırı nedeniyle en eski" in text
    assert "kısaltıldı" not in text  # yorumlar bütün olarak çıkarılır, ortadan kesilmez


def test_yorum_ozeti_yetki_ve_bulunamadi(client, setup):
    add_comments(setup["db"], setup["task"], setup["admin_id"], 5)
    fake = use_llm(SUMMARY)

    assert error_code(client.post(comments_url(setup["task"].id), headers=setup["outsider"])) == (
        403,
        "PROJECT_ACCESS_DENIED",
    )
    assert error_code(client.post(comments_url(999999), headers=setup["member"])) == (404, "TASK_NOT_FOUND")
    assert fake.calls == []


def test_bos_karar_ve_acik_konu_listeleri_kabul_edilir_bos_maddeler_temizlenir(client, setup):
    add_comments(setup["db"], setup["task"], setup["admin_id"], 5)
    use_llm({"decisions": [], "open_questions": ["  ", "Test kim yazacak?"], "summary": " Henüz karar yok. "})

    response = client.post(comments_url(setup["task"].id), headers=setup["admin"])

    assert response.json() == {
        "provider": "groq",
        "decisions": [],
        "open_questions": ["Test kim yazacak?"],
        "summary": "Henüz karar yok.",
    }
