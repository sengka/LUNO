"""Dosya API'si testleri (US-018, US-019, US-035; sözleşme 8.1 – 8.4; #196, #199, #205)."""

import io
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.main import app
from app.models import Comment, Project, ProjectFile, ProjectMember, Task, User
from app.services import storage as storage_module
from app.services.file_validation import MAX_FILE_SIZE, clean_filename, detect_mime_type
from app.services.storage import (
    LocalStorage,
    StorageError,
    SupabaseStorage,
    get_storage,
)

PASSWORD = "Password123"


# --- Örnek dosyalar --------------------------------------------------------------


def office(marker: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr(marker, "<x/>")
    return buffer.getvalue()


SAMPLES = {
    "rapor.pdf": (b"%PDF-1.4\n%test\n", "application/pdf"),
    "gereksinim.docx": (
        office("word/document.xml"),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    "butce.xlsx": (
        office("xl/workbook.xml"),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    "sunum.pptx": (
        office("ppt/presentation.xml"),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    "ekran.png": (b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
    "foto.jpg": (b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg"),
    "foto.jpeg": (b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg"),
    "notlar.txt": ("Toplantı notu: çalışma ğüşiöç".encode("utf-8"), "text/plain"),
    "eski.txt": ("Türkçe Windows metni".encode("cp1254"), "text/plain"),
}


# --- Ortak hazırlık ----------------------------------------------------------------


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
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def storage(tmp_path):
    local = LocalStorage(str(tmp_path / "uploads"))
    app.dependency_overrides[get_storage] = lambda: local
    yield local
    app.dependency_overrides.pop(get_storage, None)


@pytest.fixture
def setup(client: TestClient, db_session: Session, storage):
    admin_id, admin = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    member_id, member = register(client, "uye@ornek.com", db_session)
    other_id, other = register(client, "diger@ornek.com", db_session)
    outsider_id, outsider = register(client, "disari@ornek.com", db_session)

    project = Project(
        name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1)
    )
    foreign = Project(name="Web Sitesi", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db_session.add_all([project, foreign])
    db_session.flush()
    for uid in (admin_id, member_id, other_id):
        db_session.add(ProjectMember(project_id=project.id, user_id=uid))
    db_session.add(ProjectMember(project_id=foreign.id, user_id=outsider_id))
    task = Task(project_id=project.id, title="Giriş ekranı", assignee_id=member_id)
    foreign_task = Task(project_id=foreign.id, title="Başka proje görevi")
    db_session.add_all([task, foreign_task])
    db_session.commit()
    return {
        "project": project,
        "foreign": foreign,
        "task": task,
        "foreign_task": foreign_task,
        "admin": admin,
        "member": member,
        "member_id": member_id,
        "other": other,
        "outsider": outsider,
        "storage": storage,
    }


def upload(client, setup, headers=None, name="rapor.pdf", data=None, task_id=None, project_id=None):
    data = SAMPLES[name][0] if data is None else data
    form = {"task_id": str(task_id)} if task_id is not None else {}
    return client.post(
        f"/api/v1/projects/{project_id or setup['project'].id}/files",
        headers=headers or setup["member"],
        files={"file": (name, data, "application/octet-stream")},
        data=form,
    )


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


# --- 8.1 Yükleme --------------------------------------------------------------------


@pytest.mark.parametrize("name", list(SAMPLES))
def test_upload_allowed_types(client, setup, db_session, name):
    """FR-046: yedi format kabul edilir; MIME türü içerikten belirlenir."""
    data, mime = SAMPLES[name]
    response = upload(client, setup, name=name)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == name
    assert body["mime_type"] == mime
    assert body["size_bytes"] == len(data)
    assert body["project_id"] == setup["project"].id
    assert body["task_id"] is None
    assert body["uploaded_by"]["id"] == setup["member_id"]
    assert body["comment_count"] == 0
    stored = db_session.get(ProjectFile, body["id"])
    assert setup["storage"].read(stored.storage_key) == data


def test_upload_to_task(client, setup):
    response = upload(client, setup, task_id=setup["task"].id)
    assert response.status_code == 201
    assert response.json()["task_id"] == setup["task"].id


def test_upload_to_task_of_another_project_rejected(client, setup, db_session):
    response = upload(client, setup, task_id=setup["foreign_task"].id)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
    assert count(db_session, ProjectFile) == 0


def test_upload_exactly_10mb_allowed(client, setup):
    data = b"a" * MAX_FILE_SIZE
    assert upload(client, setup, name="buyuk.txt", data=data).status_code == 201


def test_upload_over_10mb_rejected(client, setup, db_session):
    """FR-047: 10 MB'tan büyük dosya kaydedilmez."""
    response = upload(client, setup, name="buyuk.txt", data=b"a" * (MAX_FILE_SIZE + 1))
    assert response.status_code == 413
    assert response.json()["error"] == {
        "code": "FILE_TOO_LARGE",
        "message": "Dosya en fazla 10 MB olabilir.",
        "fields": None,
        "details": None,
    }
    assert count(db_session, ProjectFile) == 0


@pytest.mark.parametrize(
    "name,data",
    [
        ("program.exe", b"MZ\x90\x00"),
        ("resim.gif", b"GIF89a"),
        ("uzantisiz", b"%PDF-1.4"),
        ("sahte.pdf", b"MZ\x90\x00 bu aslinda exe"),  # NFR-006: uzantı değiştirilmiş
        ("sahte.png", b"%PDF-1.4"),
        ("sahte.jpg", b"\x89PNG\r\n\x1a\n"),
        ("sahte.docx", office("xl/workbook.xml")),  # xlsx içeriği, docx adı
        ("bozuk.xlsx", b"PK\x03\x04 bozuk zip"),
        ("ikili.txt", b"metin\x00ikili"),
        ("bos.pdf", b""),
    ],
)
def test_upload_unsupported_rejected(client, setup, db_session, name, data):
    """FR-047, NFR-006: desteklenmeyen tür veya uzantısıyla içeriği uyuşmayan dosya."""
    response = upload(client, setup, name=name, data=data)
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert response.json()["error"]["message"] == (
        "Desteklenen formatlar: PDF, DOCX, XLSX, PPTX, PNG, JPG, TXT."
    )
    assert count(db_session, ProjectFile) == 0


def test_uppercase_extension_accepted(client, setup):
    response = upload(client, setup, name="RAPOR.PDF", data=SAMPLES["rapor.pdf"][0])
    assert response.status_code == 201
    assert response.json()["mime_type"] == "application/pdf"


def test_filename_path_is_stripped(client, setup, db_session):
    """Kullanıcının gönderdiği klasör yolu atılır; depo anahtarını sunucu üretir."""
    response = upload(client, setup, name="../../etc/notlar.txt", data=b"merhaba")
    assert response.status_code == 201
    assert response.json()["name"] == "notlar.txt"
    stored = db_session.get(ProjectFile, response.json()["id"])
    assert stored.storage_key.startswith(f"projects/{setup['project'].id}/")
    assert ".." not in stored.storage_key


def test_non_member_cannot_upload(client, setup, db_session):
    response = upload(client, setup, headers=setup["outsider"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert count(db_session, ProjectFile) == 0


def test_upload_to_missing_project(client, setup):
    response = upload(client, setup, project_id=9999)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_upload_requires_login(client, setup):
    response = client.post(
        f"/api/v1/projects/{setup['project'].id}/files",
        files={"file": ("a.txt", b"x", "text/plain")},
    )
    assert response.status_code == 401


def test_upload_without_file_field(client, setup):
    response = client.post(
        f"/api/v1/projects/{setup['project'].id}/files", headers=setup["member"], data={}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_storage_failure_returns_503(client, setup, db_session):
    class BrokenStorage:
        def save(self, *args):
            raise StorageError("kapalı")

    app.dependency_overrides[get_storage] = lambda: BrokenStorage()
    response = upload(client, setup)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert count(db_session, ProjectFile) == 0


# --- 8.2 Listeleme ------------------------------------------------------------------


def test_list_files_newest_first_with_pagination(client, setup):
    for name in ("notlar.txt", "rapor.pdf", "ekran.png"):
        upload(client, setup, name=name)

    url = f"/api/v1/projects/{setup['project'].id}/files"
    first = client.get(url, headers=setup["other"], params={"limit": 2}).json()
    assert first["total"] == 3
    assert (first["page"], first["limit"]) == (1, 2)
    assert [f["name"] for f in first["items"]] == ["ekran.png", "rapor.pdf"]

    second = client.get(url, headers=setup["other"], params={"limit": 2, "page": 2}).json()
    assert [f["name"] for f in second["items"]] == ["notlar.txt"]


def test_list_files_filtered_by_task(client, setup):
    upload(client, setup, name="rapor.pdf")
    upload(client, setup, name="ekran.png", task_id=setup["task"].id)
    response = client.get(
        f"/api/v1/projects/{setup['project'].id}/files",
        headers=setup["member"],
        params={"task_id": setup["task"].id},
    )
    assert [f["name"] for f in response.json()["items"]] == ["ekran.png"]


def test_list_shows_comment_count(client, setup, db_session):
    file_id = upload(client, setup).json()["id"]
    author = db_session.scalar(select(User).where(User.email == "uye@ornek.com"))
    db_session.add_all(
        [Comment(body="Güzel", author_id=author.id, file_id=file_id) for _ in range(2)]
    )
    db_session.commit()
    items = client.get(
        f"/api/v1/projects/{setup['project'].id}/files", headers=setup["member"]
    ).json()["items"]
    assert items[0]["comment_count"] == 2


def test_non_member_cannot_list(client, setup):
    response = client.get(
        f"/api/v1/projects/{setup['project'].id}/files", headers=setup["outsider"]
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


# --- 8.3 İndirme --------------------------------------------------------------------


def test_member_downloads_file(client, setup):
    """FR-048: proje üyesi dosyayı yüklendiği adla indirir."""
    data = SAMPLES["gereksinim.docx"][0]
    file_id = upload(client, setup, name="Gereksinim Dokümanı.docx", data=data).json()["id"]

    response = client.get(f"/api/v1/files/{file_id}/download", headers=setup["other"])
    assert response.status_code == 200
    assert response.content == data
    assert response.headers["content-type"].startswith(SAMPLES["gereksinim.docx"][1])
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "filename*=UTF-8''Gereksinim%20Dok%C3%BCman%C4%B1.docx" in disposition


def test_non_member_cannot_download(client, setup):
    file_id = upload(client, setup).json()["id"]
    response = client.get(f"/api/v1/files/{file_id}/download", headers=setup["outsider"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_download_missing_file(client, setup):
    response = client.get("/api/v1/files/9999/download", headers=setup["member"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FILE_NOT_FOUND"


# --- 8.4 Silme ----------------------------------------------------------------------


def test_uploader_deletes_file(client, setup, db_session):
    """FR-049: yükleyen kişi siler; dosya depodan da silinir."""
    file_id = upload(client, setup).json()["id"]
    key = db_session.get(ProjectFile, file_id).storage_key

    response = client.delete(f"/api/v1/files/{file_id}", headers=setup["member"])
    assert response.status_code == 204
    assert count(db_session, ProjectFile) == 0
    with pytest.raises(StorageError):
        setup["storage"].read(key)
    assert (
        client.get(f"/api/v1/files/{file_id}/download", headers=setup["member"]).status_code == 404
    )


def test_admin_deletes_others_file(client, setup, db_session):
    file_id = upload(client, setup).json()["id"]
    assert client.delete(f"/api/v1/files/{file_id}", headers=setup["admin"]).status_code == 204
    assert count(db_session, ProjectFile) == 0


def test_other_member_cannot_delete(client, setup, db_session):
    file_id = upload(client, setup).json()["id"]
    response = client.delete(f"/api/v1/files/{file_id}", headers=setup["other"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert count(db_session, ProjectFile) == 1


def test_non_member_cannot_delete(client, setup, db_session):
    file_id = upload(client, setup).json()["id"]
    response = client.delete(f"/api/v1/files/{file_id}", headers=setup["outsider"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert count(db_session, ProjectFile) == 1


def test_delete_missing_file(client, setup):
    response = client.delete("/api/v1/files/9999", headers=setup["admin"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_deleting_file_deletes_its_comments(client, setup, db_session):
    """Sözleşme 8.4: dosyaya ait yorumlar da silinir; görev yorumları etkilenmez."""
    file_id = upload(client, setup).json()["id"]
    author = db_session.scalar(select(User).where(User.email == "uye@ornek.com"))
    db_session.add_all(
        [
            Comment(body="Dosya yorumu", author_id=author.id, file_id=file_id),
            Comment(body="Görev yorumu", author_id=author.id, task_id=setup["task"].id),
        ]
    )
    db_session.commit()

    assert client.delete(f"/api/v1/files/{file_id}", headers=setup["member"]).status_code == 204
    db_session.expire_all()
    assert [c.body for c in db_session.scalars(select(Comment))] == ["Görev yorumu"]


# --- İlişkiler ------------------------------------------------------------------------


def test_deleting_task_keeps_file_in_project(client, setup, db_session):
    file_id = upload(client, setup, task_id=setup["task"].id).json()["id"]
    db_session.delete(db_session.get(Task, setup["task"].id))
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(ProjectFile, file_id).task_id is None


def test_deleting_project_deletes_file_records(client, setup, db_session):
    upload(client, setup)
    db_session.delete(db_session.get(Project, setup["project"].id))
    db_session.commit()
    assert count(db_session, ProjectFile) == 0


def test_task_response_counts_files(client, setup):
    """Task nesnesindeki file_count alanı (sözleşme 2. bölüm)."""
    task_id = setup["task"].id
    upload(client, setup, task_id=task_id)
    upload(client, setup, name="ekran.png", task_id=task_id)
    response = client.patch(
        f"/api/v1/tasks/{task_id}/status", headers=setup["member"], json={"status": "IN_PROGRESS"}
    )
    assert response.json()["file_count"] == 2


# --- Yardımcılar ve depolama ------------------------------------------------------------


def test_detect_mime_type_rejects_unknown_extension():
    assert detect_mime_type("a.gif", b"GIF89a") is None
    assert detect_mime_type("a.PDF", b"%PDF-1.7") == "application/pdf"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("rapor.pdf", "rapor.pdf"),
        ("C:\\Users\\a\\b.txt", "b.txt"),
        ("", "dosya"),
        ("a\x00b.txt", "ab.txt"),
    ],
)
def test_clean_filename(raw, expected):
    assert clean_filename(raw) == expected


def test_local_storage_blocks_path_traversal(tmp_path):
    local = LocalStorage(str(tmp_path))
    with pytest.raises(StorageError):
        local.save("../disari.txt", b"x", "text/plain")


def test_supabase_storage_requests(monkeypatch):
    """Supabase Storage REST çağrıları doğru adrese ve anahtarla gider (gerçek ağ kullanılmaz)."""
    calls = []

    class FakeResponse:
        def __init__(self, code, content=b""):
            self.status_code, self.content = code, content

    def fake_request(method, url, headers=None, timeout=None, **kwargs):
        calls.append((method, url, headers, kwargs))
        return FakeResponse(200, b"icerik")

    monkeypatch.setattr(storage_module.httpx, "request", fake_request)
    s = SupabaseStorage("https://abc.supabase.co/", "gizli", "luno-files")
    s.save("projects/1/x.pdf", b"veri", "application/pdf")
    assert s.read("projects/1/x.pdf") == b"icerik"
    s.delete("projects/1/x.pdf")

    url = "https://abc.supabase.co/storage/v1/object/luno-files/projects/1/x.pdf"
    assert [(c[0], c[1]) for c in calls] == [("POST", url), ("GET", url), ("DELETE", url)]
    assert calls[0][2]["Authorization"] == "Bearer gizli"
    assert calls[0][2]["Content-Type"] == "application/pdf"
    assert calls[0][3]["content"] == b"veri"


def test_supabase_storage_error(monkeypatch):
    class FakeResponse:
        status_code = 500
        content = b""

    monkeypatch.setattr(storage_module.httpx, "request", lambda *a, **k: FakeResponse())
    with pytest.raises(StorageError):
        SupabaseStorage("https://abc.supabase.co", "gizli", "b").save("k", b"x", "text/plain")


def test_get_storage_follows_setting(monkeypatch):
    monkeypatch.setattr(storage_module.settings, "STORAGE_BACKEND", "local")
    assert isinstance(get_storage(), LocalStorage)
    monkeypatch.setattr(storage_module.settings, "STORAGE_BACKEND", "supabase")
    monkeypatch.setattr(storage_module.settings, "SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setattr(storage_module.settings, "SUPABASE_SERVICE_KEY", "gizli")
    assert isinstance(get_storage(), SupabaseStorage)
