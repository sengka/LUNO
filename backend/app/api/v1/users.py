from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.user import User, SystemRole
from app.schemas.user import UserResponse, UserRoleUpdateRequest, UserListResponse
from app.core.exceptions import (
    ForbiddenException,
    CannotChangeOwnRoleException,
    UserNotFoundException
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/users", tags=["Kullanıcı Yönetimi"])

@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcıları Listeleme ve Arama (US-004 / 4.1)"
)
def get_users(
    search: Optional[str] = Query(None, description="Ad ve e-postada arama (case-insensitive)"),
    page: int = Query(1, ge=1, description="Sayfa numarası (varsayılan: 1)"),
    limit: int = Query(10, ge=1, le=100, description="Sayfa başına öge sayısı (varsayılan: 10)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Sisteme kayıtlı tüm kullanıcıları listeler ve ad/e-posta bazında arama yapar.
    Sadece YONETICI rolüne sahip kullanıcılar erişebilir.
    """
    if current_user.role != SystemRole.YONETICI.value:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")

    query = db.query(User)

    if search and search.strip():
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.email.ilike(search_term)
            )
        )

    total = query.count()
    offset = (page - 1) * limit
    users = query.order_by(User.id.asc()).offset(offset).limit(limit).all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        limit=limit
    )

@router.patch(
    "/{user_id}/role",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Rolü Güncelleme (US-004 / 4.2)"
)
def update_user_role(
    user_id: int,
    role_in: UserRoleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Belirtilen kullanıcının sistem rolünü günceller.
    Sadece YONETICI rolüne sahip kullanıcılar erişebilir.
    Yöneticinin kendi rolünü değiştirmesi engellenmiştir (400 CANNOT_CHANGE_OWN_ROLE).
    """
    if current_user.role != SystemRole.YONETICI.value:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")

    if current_user.id == user_id:
        raise CannotChangeOwnRoleException()

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise UserNotFoundException()

    target_user.role = role_in.role.value
    db.commit()
    db.refresh(target_user)

    return target_user
