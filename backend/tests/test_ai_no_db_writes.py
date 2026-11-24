"""Hiçbir AI uç noktasının veritabanına yazmadığını doğrulayan test (FR-078, FR-086, sözleşme 13.1, #288).

Nasıl çalışır?
- AI isteği sırasında veritabanına giden her SQL komutu dinlenir. INSERT, UPDATE veya DELETE
  görülürse test kalır. Giriş yapma gibi hazırlık adımları ölçüme dahil edilmez.
- AI_ENDPOINTS listesi, uygulamadaki /api/v1/ai/ adreslerinin tamamıyla karşılaştırılır.
  Yeni bir AI uç noktası eklenip bu listeye eklenmezse test kalır; böylece hiçbir uç nokta
  bu kontrolden kaçamaz.

Yeni uç nokta eklerken: AI_ENDPOINTS'e adresini, istek gövdesini ve modelin döndüreceği örnek
JSON'u ekleyin.
"""

from dataclasses import dataclass, field
from datetime import date

import pytest
from sqlalchemy import event

from app.main import app
from app.models import Comment, Project, ProjectMember, Task, TaskStatus
from app.services.llm import LLMResult, RateLimiter, get_llm_rate_limiter, get_llm_service
from tests.conftest import engine
from tests.test_ai_suggest_points import register


@dataclass
class AIEndpoint:
    method: str
    path: str  # {task_id} ve {project_id} test verisiyle doldurulur
    llm_output: dict  # modelin döndürdüğü varsayılan geçerli JSON
    body: dict = field(default_factory=dict)


AI_ENDPOINTS = [
    AIEndpoint(
        "POST",
        "/api/v1/ai/tasks/{task_id}/suggest-points",
        llm_output={"story_points": 5, "reason": "Birden fazla ekran içeriyor."},
    ),
]


class SchemaFakeLLM:
    """Verilen şemayı uç noktanın örnek JSON'uyla doldurur; gerçek servise gitmez."""

    def __init__(self, output: dict):
        self.output = output
        self.calls = 0

    def complete_json(self, system, user, schema):
        self.calls += 1
        return LLMResult(provider="groq", data=schema.model_validate(self.output))


def ai_routes_in_app() -> set[tuple[str, str]]:
    # Uygulamanın yayımladığı OpenAPI şemasından okunur (FastAPI sürümünden bağımsız).
    return {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api/v1/ai/")
        for method in operations
    }


def test_tum_ai_uc_noktalari_bu_testte_listelenmis():
    listed = {(e.method, e.path) for e in AI_ENDPOINTS}

    assert ai_routes_in_app() == listed, (
        "AI uç noktaları ile AI_ENDPOINTS listesi farklı. Yeni uç noktayı listeye ekleyin "
        "ya da silinen uç noktayı listeden çıkarın."
    )


@pytest.fixture
def data(client, db_session):
    admin, admin_id = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=admin_id))
    task = Task(project_id=project.id, title="Şifre sıfırlama", description="API ve form.", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.flush()
    # Yorum özeti gibi uç noktalar için yeterli yorum (13.6: en az 5).
    db_session.add_all([Comment(task_id=task.id, author_id=admin_id, body=f"Yorum {i}") for i in range(6)])
    db_session.commit()
    return {"admin": admin, "task_id": task.id, "project_id": project.id}


@pytest.fixture
def write_watcher():
    writes = []

    def on_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().split(" ", 1)[0].upper() in {"INSERT", "UPDATE", "DELETE"}:
            writes.append(statement.split("\n", 1)[0])

    event.listen(engine, "before_cursor_execute", on_execute)
    yield writes
    event.remove(engine, "before_cursor_execute", on_execute)


@pytest.mark.parametrize("endpoint", AI_ENDPOINTS, ids=lambda e: e.path.rsplit("/", 1)[-1])
def test_ai_uc_noktasi_veritabanina_yazmaz(client, data, endpoint, request):
    fake = SchemaFakeLLM(endpoint.llm_output)
    limiter = RateLimiter(10)
    app.dependency_overrides[get_llm_service] = lambda: fake
    app.dependency_overrides[get_llm_rate_limiter] = lambda: limiter
    url = endpoint.path.format(task_id=data["task_id"], project_id=data["project_id"])

    writes = request.getfixturevalue("write_watcher")  # ölçüm yalnızca AI isteği sırasında
    response = client.request(endpoint.method, url, headers=data["admin"], json=endpoint.body or None)

    assert response.status_code == 200, response.text
    assert fake.calls == 1
    assert writes == [], f"AI uç noktası veritabanına yazdı: {writes}"
