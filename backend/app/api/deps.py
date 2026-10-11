from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RevokedToken
from app.core.security import decode_access_token
from app.core.exceptions import UnauthorizedException

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

def get_raw_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)
) -> str:
    if not credentials or not credentials.credentials:
        raise UnauthorizedException("Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.")
    return credentials.credentials
