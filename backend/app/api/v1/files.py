"""Proje ve görev dosyaları (US-018, US-019, US-035; sözleşme 8.1 – 8.4)."""

from pathlib import PurePath
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_member
from app.core.exceptions import (
    FileNotFoundException,
    FileTooLargeException,
    ForbiddenException,
    ProjectAccessDeniedException,
    StorageUnavailableException,
    TaskNotFoundException,
    UnsupportedFileTypeException,
)
from app.database import get_db
from app.models.comment import Comment
from app.models.file import ProjectFile
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User
from app.schemas.file import FileListResponse, FileResponse
from app.schemas.project import UserSummary
from app.services.file_validation import MAX_FILE_SIZE, clean_filename, detect_mime_type
from app.services.storage import StorageError, get_storage

router = APIRouter(tags=["Dosyalar"])


def _comment_counts(db: Session, file_ids: list[int]) -> dict[int, int]:
    if not file_ids:
        return {}
    rows = (
        db.query(Comment.file_id, func.count(Comment.id))
        .filter(Comment.file_id.in_(file_ids))
        .group_by(Comment.file_id)
        .all()
    )
    return dict(rows)


def build_file_response(f: ProjectFile, comment_count: int = 0) -> FileResponse:
    uploader = f.uploaded_by
    return FileResponse(
        id=f.id,
        name=f.name,
        size_bytes=f.size_bytes,
        mime_type=f.mime_type,
        project_id=f.project_id,
        task_id=f.task_id,
        uploaded_by=(
            UserSummary(
                id=uploader.id, full_name=uploader.full_name, avatar_url=uploader.avatar_url
            )
            if uploader
            else None
        ),
        comment_count=comment_count,
        created_at=f.created_at,
    )


def _membership(db: Session, project_id: int, user_id: int) -> ProjectMember | None:
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )


def _get_file_for_member(db: Session, file_id: int, user: User) -> ProjectFile:
    """Dosyayı bulur; yoksa 404 FILE_NOT_FOUND, kullanıcı projenin üyesi değilse 403."""
    f = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not f:
        raise FileNotFoundException()
    if not _membership(db, f.project_id, user.id):
        raise ProjectAccessDeniedException()
    return f


@router.post(
    "/projects/{project_id}/files",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dosya yükle (US-018 / 8.1)",
)
def upload_file(
    project_id: int,
    file: UploadFile = File(
        ..., description="PDF, DOCX, XLSX, PPTX, PNG, JPG veya TXT; en fazla 10 MB"
    ),
    task_id: int | None = Form(None, description="Göreve yükleniyorsa görevin id'si"),
    current_user: User = Depends(get_current_user),
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """
    Projeye veya göreve dosya yükler (FR-046, FR-047, NFR-006). Erişim: proje üyesi.
    - 10 MB'tan büyükse 413 FILE_TOO_LARGE
    - Desteklenmeyen tür veya uzantısıyla içeriği uyuşmayan dosya: 415 UNSUPPORTED_FILE_TYPE
    - task_id bu projenin görevi değilse 404 TASK_NOT_FOUND
    """
    if task_id is not None:
        task = db.query(Task).filter(Task.id == task_id, Task.project_id == project_id).first()
        if not task:
            raise TaskNotFoundException()

    # Belleği korumak için en fazla sınır + 1 bayt okunur.
    data = file.file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise FileTooLargeException()

    name = clean_filename(file.filename)
    mime_type = detect_mime_type(name, data)
    if mime_type is None:
        raise UnsupportedFileTypeException()

    ext = PurePath(name).suffix.lower()
    storage_key = f"projects/{project_id}/{uuid4().hex}{ext}"
    try:
        storage.save(storage_key, data, mime_type)
    except StorageError:
        raise StorageUnavailableException()

    record = ProjectFile(
        project_id=project_id,
        task_id=task_id,
        name=name,
        storage_key=storage_key,
        size_bytes=len(data),
        mime_type=mime_type,
        uploaded_by_id=current_user.id,
    )
    db.add(record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)  # kayıt oluşmadıysa depoda da kalmasın
        raise
    db.refresh(record)
    return build_file_response(record)


@router.get(
    "/projects/{project_id}/files",
    response_model=FileListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dosyaları listele (US-018, US-019 / 8.2)",
)
def list_files(
    project_id: int,
    task_id: int | None = Query(None, description="Yalnızca bu görevin dosyaları"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    """Projenin dosyalarını en yeniden eskiye sayfalı döner. Erişim: proje üyesi."""
    query = db.query(ProjectFile).filter(ProjectFile.project_id == project_id)
    if task_id is not None:
        query = query.filter(ProjectFile.task_id == task_id)

    total = query.count()
    files = (
        query.order_by(ProjectFile.created_at.desc(), ProjectFile.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    counts = _comment_counts(db, [f.id for f in files])
    return FileListResponse(
        items=[build_file_response(f, counts.get(f.id, 0)) for f in files],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/files/{file_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Dosya indir (US-019 / 8.3)",
    responses={
        200: {"content": {"application/octet-stream": {}}, "description": "Dosyanın kendisi"}
    },
)
def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """
    Dosyayı yüklendiği adla indirir (FR-048). Erişim: dosyanın projesinin üyesi.
    Hatalar: 404 FILE_NOT_FOUND, 403 PROJECT_ACCESS_DENIED.
    """
    f = _get_file_for_member(db, file_id, current_user)
    try:
        data = storage.read(f.storage_key)
    except StorageError:
        raise StorageUnavailableException()

    # Türkçe karakterli adlar için RFC 5987 (filename*), eski tarayıcılar için ASCII yedek.
    ascii_name = f.name.encode("ascii", "replace").decode().replace("?", "_").replace('"', "")
    disposition = f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(f.name)}"
    return Response(
        content=data, media_type=f.mime_type, headers={"Content-Disposition": disposition}
    )


@router.delete(
    "/files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Dosya sil (US-035 / 8.4)",
)
def delete_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage=Depends(get_storage),
):
    """
    Dosyayı depodan ve veritabanından siler; dosyanın yorumları da silinir (FR-049).
    Erişim: dosyayı yükleyen kişi veya projenin Yöneticisi (YONETICI rolünde ve üye).
    Hatalar: 404 FILE_NOT_FOUND, 403 PROJECT_ACCESS_DENIED (üye değil), 403 FORBIDDEN (yetkisiz).
    """
    f = _get_file_for_member(db, file_id, current_user)
    is_uploader = f.uploaded_by_id == current_user.id
    is_admin = current_user.role == SystemRole.YONETICI.value
    if not (is_uploader or is_admin):
        raise ForbiddenException("Bu dosyayı yalnızca yükleyen kişi veya Yönetici silebilir.")

    # Önce depodan silinir; depo hata verirse kayıt da kalır, tutarsızlık oluşmaz.
    try:
        storage.delete(f.storage_key)
    except StorageError:
        raise StorageUnavailableException()

    db.delete(f)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
