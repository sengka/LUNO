"""US-018 / #198: real multipart routes, SQLite and temporary LocalStorage.

Fixtures contain small format-recognition samples, not Office/image rendering
certification. Live Supabase, browser progress and UI messages need separate QA.
"""
import hashlib
import io
import zipfile
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app
from app.models import Project, ProjectFile, ProjectMember, Task, User
from app.services.storage import LocalStorage, StorageError, get_storage
from app.services import storage as storage_module


# Regression of the current 10 MiB implementation, not a decision that the
# contract's ambiguous "10 MB" means MiB. See the report / existing test plan.
LIMIT = 10 * 1024 * 1024


def office_sample(marker):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("[Content_Types].xml", '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        archive.writestr(marker, '<?xml version="1.0"?><sample/>')
    return stream.getvalue()


SAMPLES = {
    "pdf": (b"%PDF-1.4\n% synthetic recognition sample\n%%EOF", "application/pdf"),
    "docx": (office_sample("word/document.xml"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "xlsx": (office_sample("xl/workbook.xml"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "pptx": (office_sample("ppt/presentation.xml"), "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "png": (b"\x89PNG\r\n\x1a\n" + b"\x00" * 16, "image/png"),
    "jpg": (b"\xff\xd8\xff\xe0" + b"\x00" * 16, "image/jpeg"),
    "txt": ("Türkçe dosya: ğüşİöç\n".encode(), "text/plain"),
}


@pytest.fixture
def upload_case(client, db_session, tmp_path):
    users = {}
    for name, role in (("admin", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("colleague", "EKIP_UYESI"), ("outsider", "EKIP_UYESI"),
                       ("external_admin", "YONETICI")):
        user = User(full_name=name, email=f"upload-{name}@example.com",
                    role=role, hashed_password="unused-synthetic-fixture")
        db_session.add(user)
        db_session.flush()
        users[name] = user
    projects = []
    for name in ("Upload QA", "Foreign project"):
        project = Project(name=name, start_date=date(2026, 11, 1), end_date=date(2026, 12, 31))
        db_session.add(project)
        db_session.flush()
        projects.append(project)
    for name in ("admin", "member", "colleague"):
        db_session.add(ProjectMember(project_id=projects[0].id, user_id=users[name].id))
    db_session.add(ProjectMember(project_id=projects[1].id, user_id=users["outsider"].id))
    task = Task(project_id=projects[0].id, title="Assigned task", assignee_id=users["member"].id)
    foreign_task = Task(project_id=projects[1].id, title="Foreign task")
    db_session.add_all([task, foreign_task])
    db_session.commit()
    storage = LocalStorage(str(tmp_path / "uploads"))
    app.dependency_overrides[get_storage] = lambda: storage
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
               for name, user in users.items()}
    case = dict(users=users, projects=projects, task=task, foreign_task=foreign_task,
                storage=storage, headers=headers, url=f"/api/v1/projects/{projects[0].id}/files")
    # Preserve an existing object in all failure scenarios, not only an empty store.
    baseline = send(client, case, name="baseline.txt", content=b"keep this object")
    assert baseline.status_code == 201, baseline.text
    yield case
    app.dependency_overrides.pop(get_storage, None)


def send(client, case, *, name="new.txt", content=b"new content", actor="member",
         mime="application/octet-stream", task_id=None, headers=None, url=None):
    return client.post(url or case["url"], headers=case["headers"][actor] if headers is None else headers,
                       files={"file": (name, content, mime)},
                       data={} if task_id is None else {"task_id": str(task_id)})


def snapshot(db, case):
    records = [(row.id, row.name, row.storage_key, row.size_bytes, row.task_id)
               for row in db.query(ProjectFile).order_by(ProjectFile.id)]
    root = case["storage"].root
    objects = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
               for path in root.rglob("*") if path.is_file()}
    return records, objects


def assert_rejected(response, code, error, db, case, before):
    assert response.status_code == code, response.text
    assert response.json()["error"]["code"] == error
    assert snapshot(db, case) == before, "Rejected upload mutated DB/storage"


@pytest.mark.parametrize("extension", list(SAMPLES))
@pytest.mark.parametrize("target", ["project", "task"])
def test_seven_formats_persist_bytes_metadata_and_list_membership(client, db_session, upload_case, extension, target):
    case = upload_case
    content, mime = SAMPLES[extension]
    task_id = case["task"].id if target == "task" else None
    name = f"Türkçe belge.{extension}"
    response = send(client, case, name=name, content=content, task_id=task_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["name"], body["size_bytes"], body["mime_type"]) == (name, len(content), mime)
    assert (body["project_id"], body["task_id"], body["uploaded_by"]["id"]) == (
        case["projects"][0].id, task_id, case["users"]["member"].id)
    assert body["comment_count"] == 0 and body["created_at"].endswith("Z")
    row = db_session.get(ProjectFile, body["id"])
    assert case["storage"].read(row.storage_key) == content
    assert "storage_key" not in body
    listed = client.get(case["url"], headers=case["headers"]["colleague"],
                        params={} if task_id is None else {"task_id": task_id})
    assert listed.status_code == 200
    assert body["id"] in [item["id"] for item in listed.json()["items"]]


@pytest.mark.parametrize("size,expected", [(LIMIT - 1, 201), (LIMIT, 201), (LIMIT + 1, 413)])
def test_exact_size_boundary_and_no_orphan_for_rejection(client, db_session, upload_case, size, expected):
    case = upload_case
    before = snapshot(db_session, case)
    data = b"a" * size
    response = send(client, case, content=data)
    if expected == 413:
        assert_rejected(response, 413, "FILE_TOO_LARGE", db_session, case, before)
        assert response.json()["error"]["message"] == "Dosya en fazla 10 MB olabilir."
    else:
        assert response.status_code == 201, response.text
        row = db_session.get(ProjectFile, response.json()["id"])
        assert row.size_bytes == size
        assert case["storage"].read(row.storage_key) == data


@pytest.mark.parametrize("name,content,mime", [
    ("forbidden.exe", b"MZ\x00\x90", "application/pdf"),
    ("file.zip", SAMPLES["docx"][0], "application/zip"),
    ("file.gif", b"GIF89a", "image/gif"),
    ("file.svg", b"<svg/>", "image/svg+xml"),
    ("file.pdf.exe", SAMPLES["pdf"][0], "application/pdf"),
    ("no-extension", SAMPLES["pdf"][0], "application/pdf"),
    ("disguised.pdf", b"MZ\x00\x90", "application/pdf"),
    ("disguised.png", SAMPLES["pdf"][0], "image/png"),
    ("disguised.jpg", SAMPLES["png"][0], "image/jpeg"),
    ("disguised.docx", SAMPLES["xlsx"][0], SAMPLES["docx"][1]),
    ("disguised.xlsx", SAMPLES["pptx"][0], SAMPLES["xlsx"][1]),
    ("disguised.pptx", SAMPLES["docx"][0], SAMPLES["pptx"][1]),
    ("broken.docx", b"PK\x03\x04 truncated", SAMPLES["docx"][1]),
    ("binary.txt", b"hello\x00binary", "text/plain"),
])
def test_invalid_extension_or_content_leaves_both_stores_unchanged(client, db_session, upload_case,
                                                                 name, content, mime):
    before = snapshot(db_session, upload_case)
    response = send(client, upload_case, name=name, content=content, mime=mime)
    assert_rejected(response, 415, "UNSUPPORTED_FILE_TYPE", db_session, upload_case, before)
    assert response.json()["error"]["message"] == "Desteklenen formatlar: PDF, DOCX, XLSX, PPTX, PNG, JPG, TXT."


@pytest.mark.parametrize("mime", ["application/octet-stream", "application/pdf"])
def test_untrusted_client_mime_does_not_override_detected_png(client, upload_case, mime):
    response = send(client, upload_case, name="image.PNG", content=SAMPLES["png"][0], mime=mime)
    assert response.status_code == 201
    assert response.json()["mime_type"] == "image/png"


@pytest.mark.parametrize("actor", ["admin", "colleague"])
def test_project_members_can_upload_to_someone_elses_task(client, upload_case, actor):
    response = send(client, upload_case, actor=actor, task_id=upload_case["task"].id)
    assert response.status_code == 201
    assert response.json()["uploaded_by"]["id"] == upload_case["users"][actor].id


@pytest.mark.parametrize("actor", ["outsider", "external_admin"])
def test_project_nonmembers_cannot_upload_even_with_admin_role(client, db_session, upload_case, actor):
    before = snapshot(db_session, upload_case)
    response = send(client, upload_case, actor=actor)
    assert_rejected(response, 403, "PROJECT_ACCESS_DENIED", db_session, upload_case, before)


@pytest.mark.parametrize("session", ["missing", "invalid", "expired", "logged_out"])
def test_invalid_sessions_do_not_create_objects(client, db_session, upload_case, session):
    case = upload_case
    headers = {}
    if session == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif session == "expired":
        token = create_access_token({"sub": str(case["users"]["member"].id)},
                                    expires_delta=timedelta(seconds=-60))
        headers = {"Authorization": "Bearer " + token}
    elif session == "logged_out":
        headers = case["headers"]["member"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    before = snapshot(db_session, case)
    assert_rejected(send(client, case, headers=headers), 401, "UNAUTHORIZED", db_session, case, before)


@pytest.mark.parametrize("task", ["foreign", "missing", "malformed"])
def test_bad_task_target_never_creates_file(client, db_session, upload_case, task):
    task_id = {"foreign": upload_case["foreign_task"].id, "missing": 999999, "malformed": "invalid"}[task]
    before = snapshot(db_session, upload_case)
    response = send(client, upload_case, task_id=task_id)
    assert_rejected(response, 422 if task == "malformed" else 404,
                    "VALIDATION_ERROR" if task == "malformed" else "TASK_NOT_FOUND",
                    db_session, upload_case, before)


def test_missing_file_field_preserves_existing_data(client, db_session, upload_case):
    before = snapshot(db_session, upload_case)
    response = client.post(upload_case["url"], headers=upload_case["headers"]["member"], data={})
    assert_rejected(response, 422, "VALIDATION_ERROR", db_session, upload_case, before)


def test_missing_project_creates_no_file(client, db_session, upload_case):
    before = snapshot(db_session, upload_case)
    response = send(client, upload_case, url="/api/v1/projects/999999/files")
    assert_rejected(response, 404, "PROJECT_NOT_FOUND", db_session, upload_case, before)


def test_same_name_uploads_never_overwrite_each_other(client, db_session, upload_case):
    first = send(client, upload_case, name="same.txt", content=b"first").json()
    second = send(client, upload_case, name="same.txt", content=b"second", task_id=upload_case["task"].id).json()
    row1, row2 = (db_session.get(ProjectFile, item["id"]) for item in (first, second))
    assert row1.storage_key != row2.storage_key
    assert upload_case["storage"].read(row1.storage_key) == b"first"
    assert upload_case["storage"].read(row2.storage_key) == b"second"


def test_removed_member_old_token_cannot_upload(client, db_session, upload_case):
    case = upload_case
    assert client.delete(f'/api/v1/projects/{case["projects"][0].id}/members/{case["users"]["member"].id}',
                         headers=case["headers"]["admin"]).status_code == 204
    before = snapshot(db_session, case)
    assert_rejected(send(client, case), 403, "PROJECT_ACCESS_DENIED", db_session, case, before)


def test_storage_error_is_explicit_and_existing_objects_survive(client, db_session, upload_case, monkeypatch):
    before = snapshot(db_session, upload_case)
    def unavailable(*args):
        raise StorageError("simulated storage outage")
    monkeypatch.setattr(upload_case["storage"], "save", unavailable)
    response = send(client, upload_case)
    assert_rejected(response, 503, "STORAGE_UNAVAILABLE", db_session, upload_case, before)


def test_real_local_storage_oserror_is_reported_as_storage_unavailable(client, db_session, upload_case, tmp_path):
    # Regression #225: real filesystem failure used to return unstructured 500.
    before = snapshot(db_session, upload_case)
    blocked = tmp_path / "not-a-directory"
    blocked.write_text("blocks storage directory creation", encoding="utf-8")
    broken_storage = LocalStorage(str(blocked))
    app.dependency_overrides[get_storage] = lambda: broken_storage
    with TestClient(app, raise_server_exceptions=False) as error_client:
        response = send(error_client, upload_case)
    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert snapshot(db_session, upload_case) == before


def test_failed_publish_cleans_staging_object_and_preserves_existing_files(client, db_session, upload_case, monkeypatch):
    before = snapshot(db_session, upload_case)
    def failed_replace(self, target):
        assert self.is_file() and self.read_bytes() == b"new content"
        raise OSError("simulated filesystem publish failure")
    monkeypatch.setattr(Path, "replace", failed_replace)
    response = send(client, upload_case)
    assert_rejected(response, 503, "STORAGE_UNAVAILABLE", db_session, upload_case, before)


def test_partial_write_cleans_staging_object(client, db_session, upload_case, monkeypatch):
    before = snapshot(db_session, upload_case)
    real_temporary_file = storage_module.NamedTemporaryFile
    class InterruptedWrite:
        def __enter__(self):
            self.stream = real_temporary_file(dir=upload_case["storage"].root, delete=False)
            self.name = self.stream.name
            return self
        def write(self, data):
            self.stream.write(data[:3])
            raise OSError("simulated disk full after partial write")
        def __exit__(self, *args):
            self.stream.close()
    monkeypatch.setattr(storage_module, "NamedTemporaryFile", lambda **kwargs: InterruptedWrite())
    response = send(client, upload_case)
    assert_rejected(response, 503, "STORAGE_UNAVAILABLE", db_session, upload_case, before)
