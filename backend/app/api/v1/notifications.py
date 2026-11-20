"""Uygulama içi bildirim uç noktaları (US-021, FR-051, sözleşme 9.1 – 9.3)."""

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ForbiddenException, NotificationNotFoundException
from app.core.pagination import MAX_PAGE
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationListResponse, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Bildirimler"])


def _build_notification_response(notification: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=notification.id,
        type=notification.type.value if hasattr(notification.type, "value") else str(notification.type),
        message=notification.message,
        project_id=notification.project_id,
        task_id=notification.task_id,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Bildirimleri listele (US-021 / 9.1)",
)
def list_notifications(
    unread_only: bool = Query(False, description="Yalnızca okunmamış bildirimleri getir"),
    page: int = Query(1, ge=1, le=MAX_PAGE, description="Sayfa numarası"),
    limit: int = Query(20, ge=1, le=100, description="Sayfa başına öge sayısı"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    base_query = db.query(Notification).filter(Notification.user_id == current_user.id)
    unread_count = base_query.filter(Notification.is_read.is_(False)).count()

    query = base_query
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return NotificationListResponse(
        items=[_build_notification_response(n) for n in items],
        total=total,
        page=page,
        limit=limit,
        unread_count=unread_count,
    )


@router.patch(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Bildirimi okundu işaretle (US-021 / 9.2)",
)
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise NotificationNotFoundException()

    if notification.user_id != current_user.id:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return _build_notification_response(notification)


@router.post(
    "/read-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Tüm bildirimleri okundu işaretle (US-021 / 9.3)",
)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True}, synchronize_session=False)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
