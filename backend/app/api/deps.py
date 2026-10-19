from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RevokedToken, SystemRole
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.core.security import decode_access_token
from app.core.exceptions import (
    UnauthorizedException,
    ForbiddenException,
    ProjectNotFoundException,
    ProjectAccessDeniedException,
)

security_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    
    token = credentials.credentials
    
    # Check if token has been revoked / logged out (US-003, Issue #71)
    revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
    if revoked:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    
    payload = decode_access_token(token)
    if not payload:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    
    try:
        user_id_int = int(user_id)
        user = db.query(User).filter(User.id == user_id_int).first()
    except (ValueError, TypeError):
        user = db.query(User).filter(User.email == str(user_id)).first()

    if not user:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    
    return user

def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Yalnızca YONETICI rolündeki kullanıcılara izin verir (FR-012). Değilse 403 FORBIDDEN."""
    if current_user.role != SystemRole.YONETICI.value:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")
    return current_user

def get_project_member(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ProjectMember:
    """
    Kullanıcının ilgili projenin üyesi olduğunu doğrular (FR-013).
    Proje yoksa 404 PROJECT_NOT_FOUND, üye değilse 403 PROJECT_ACCESS_DENIED.
    `project_id` yol parametresinden okunur.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()
    return member

def get_raw_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> str:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    return credentials.credentials


