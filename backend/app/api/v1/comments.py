"""Yorumlar API uç noktaları (US-020, FR-050, sözleşme 8.5 ve 8.6)."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import (
    FileNotFoundException,
    ProjectAccessDeniedException,
    TaskNotFoundException,
)
from app.database import get_db
from app.models.comment import Comment
from app.models.file import ProjectFile
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreateRequest, CommentListResponse, CommentResponse
from app.schemas.project import UserSummary

router = APIRouter(tags=["Yorumlar"])


def _verify_task_access(db: Session, task_id: int, user_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise TaskNotFoundException()

    membership = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise ProjectAccessDeniedException()

    return task


def _verify_file_access(db: Session, file_id: int, user_id: int) -> ProjectFile:
    file = db.get(ProjectFile, file_id)
    if file is None:
        raise FileNotFoundException()
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == file.project_id, ProjectMember.user_id == user_id
    ).first()
    if membership is None:
        raise ProjectAccessDeniedException()
    return file


def _list_comments(query, page: int, limit: int) -> CommentListResponse:
    total = query.count()
    comments = (
        query.order_by(Comment.created_at.asc(), Comment.id.asc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    items = [
        CommentResponse(
            id=c.id,
            body=c.body,
            author=UserSummary(
                id=c.author.id,
                full_name=c.author.full_name,
                avatar_url=c.author.avatar_url,
            ),
            task_id=c.task_id,
            file_id=c.file_id,
            created_at=c.created_at,
        )
        for c in comments
    ]
    return CommentListResponse(items=items, total=total, page=page, limit=limit)

@router.get(
    "/tasks/{task_id}/comments",
    response_model=CommentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Görev yorumlarını listele (US-020 / 8.5)",
)
def list_task_comments(
    task_id: int,
    page: int = Query(1, ge=1, description="Sayfa numarası (varsayılan 1)"),
    limit: int = Query(50, ge=1, le=100, description="Sayfa boyutu (varsayılan 50)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Göreve ait yorumları eskiden yeniye sıralı ve sayfalı olarak listeler (US-020, FR-050, sözleşme 8.5).
    Erişim: Proje üyesi (403 PROJECT_ACCESS_DENIED, 404 TASK_NOT_FOUND).
    """
    _verify_task_access(db, task_id, current_user.id)

    return _list_comments(db.query(Comment).filter(Comment.task_id == task_id), page, limit)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Göreve yorum ekle (US-020 / 8.5)",
)
def create_task_comment(
    task_id: int,
    comment_in: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Göreve yeni bir yorum ekler (US-020, FR-050, sözleşme 8.5).
    Erişim: Proje üyesi (403 PROJECT_ACCESS_DENIED, 404 TASK_NOT_FOUND).
    İstek: {"body": "..."} (1-2000 karakter).
    """
    task = _verify_task_access(db, task_id, current_user.id)

    comment = Comment(
        body=comment_in.body,
        author_id=current_user.id,
        task_id=task.id,
        file_id=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommentResponse(
        id=comment.id,
        body=comment.body,
        author=UserSummary(
            id=current_user.id,
            full_name=current_user.full_name,
            avatar_url=current_user.avatar_url,
        ),
        task_id=comment.task_id,
        file_id=comment.file_id,
        created_at=comment.created_at,
    )


@router.get(
    "/files/{file_id}/comments",
    response_model=CommentListResponse,
    status_code=status.HTTP_200_OK,
    summary="Dosya yorumlarını listele (US-020 / 8.6)",
)
def list_file_comments(
    file_id: int,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proje üyesine dosya yorumlarını eskiden yeniye ve sayfalı döndürür."""
    _verify_file_access(db, file_id, current_user.id)
    return _list_comments(db.query(Comment).filter(Comment.file_id == file_id), page, limit)


@router.post(
    "/files/{file_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dosyaya yorum ekle (US-020 / 8.6)",
)
def create_file_comment(
    file_id: int,
    comment_in: CommentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Proje üyesinin erişebildiği dosyaya yorum ekler (US-020 / 8.6)."""
    file = _verify_file_access(db, file_id, current_user.id)
    comment = Comment(body=comment_in.body, author_id=current_user.id,
                      task_id=None, file_id=file.id, created_at=datetime.now(timezone.utc))
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return CommentResponse(
        id=comment.id, body=comment.body,
        author=UserSummary(id=current_user.id, full_name=current_user.full_name,
                           avatar_url=current_user.avatar_url),
        task_id=None, file_id=comment.file_id, created_at=comment.created_at,
    )
