from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, RevokedToken, SystemRole
from app.schemas.user import (
    UserRegisterRequest,
    LoginRequest,
    UserResponse,
    TokenResponse
)
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token
)
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidCredentialsException
)
from app.api.deps import get_current_user, get_raw_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["Kimlik Doğrulama"])

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kullanıcı Kaydı (US-001)"
)
def register(
    user_in: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Yeni kullanıcı kaydı oluşturur.
    Varsayılan rol: EKIP_UYESI
    """
    # Check if email is already registered
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise EmailAlreadyExistsException()

    user = User(
        full_name=user_in.full_name,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=SystemRole.EKIP_UYESI.value,
        avatar_url=None,
        theme="LIGHT",
        created_at=datetime.now(timezone.utc)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Kullanıcı Girişi (US-002)"
)
def login(
    login_in: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    E-posta ve şifre ile giriş yapar, 24 saat geçerli JWT döndürür.
    Kayıtsız e-posta veya yanlış şifrede aynı hata (INVALID_CREDENTIALS) döner.
    """
    user = db.query(User).filter(User.email == login_in.email).first()
    if not user:
        raise InvalidCredentialsException()

    if not verify_password(login_in.password, user.hashed_password):
        raise InvalidCredentialsException()

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
        user=UserResponse.model_validate(user)
    )

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Çıkış Yap (US-003)"
)
def logout(
    current_user: User = Depends(get_current_user),
    raw_token: str = Depends(get_raw_token),
    db: Session = Depends(get_db)
):
    """
    Oturumu sonlandırır ve mevcut token'ı geçersizler listesine ekler.
    """
    already_revoked = db.query(RevokedToken).filter(RevokedToken.token == raw_token).first()
    if not already_revoked:
        revoked = RevokedToken(token=raw_token, created_at=datetime.now(timezone.utc))
        db.add(revoked)
        db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Oturumdaki Kullanıcı Bilgisi (US-002)"
)
def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Geçerli token'a sahip oturumdaki kullanıcının profil bilgilerini döndürür.
    """
    return current_user
