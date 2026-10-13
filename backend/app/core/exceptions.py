from typing import Optional, Dict, Any

class CustomAPIException(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        fields: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = fields
        self.details = details

class InvalidCredentialsException(CustomAPIException):
    def __init__(self):
        super().__init__(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="E-posta veya şifre hatalı."
        )

class UnauthorizedException(CustomAPIException):
    def __init__(self, message: str = "Oturumunuzun süresi doldu, lütfen tekrar giriş yapın."):
        super().__init__(
            status_code=401,
            code="UNAUTHORIZED",
            message=message
        )

class EmailAlreadyExistsException(CustomAPIException):
    def __init__(self):
        super().__init__(
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
            message="Bu e-posta adresi zaten kullanımda."
        )

class ForbiddenException(CustomAPIException):
    def __init__(self, message: str = "Bu işlem için yetkiniz yok."):
        super().__init__(
            status_code=403,
            code="FORBIDDEN",
            message=message
        )

class CannotChangeOwnRoleException(CustomAPIException):
    def __init__(self):
        super().__init__(
            status_code=400,
            code="CANNOT_CHANGE_OWN_ROLE",
            message="Kendi rolünüzü değiştiremezsiniz."
        )

class UserNotFoundException(CustomAPIException):
    def __init__(self, message: str = "Kullanıcı bulunamadı."):
        super().__init__(
            status_code=404,
            code="USER_NOT_FOUND",
            message=message
        )

class InvalidDateRangeException(CustomAPIException):
    def __init__(self, message: str = "Bitiş tarihi başlangıç tarihinden önce olamaz."):
        super().__init__(
            status_code=400,
            code="INVALID_DATE_RANGE",
            message=message
        )

class ProjectNotFoundException(CustomAPIException):
    def __init__(self, message: str = "Proje bulunamadı."):
        super().__init__(
            status_code=404,
            code="PROJECT_NOT_FOUND",
            message=message
        )

class ProjectAccessDeniedException(CustomAPIException):
    def __init__(self, message: str = "Bu projeye erişim yetkiniz yok."):
        super().__init__(
            status_code=403,
            code="PROJECT_ACCESS_DENIED",
            message=message
        )

class AlreadyMemberException(CustomAPIException):
    def __init__(self, message: str = "Bu kullanıcı zaten projenin üyesi."):
        super().__init__(
            status_code=409,
            code="ALREADY_MEMBER",
            message=message
        )

class MemberNotFoundException(CustomAPIException):
    def __init__(self, message: str = "Bu kullanıcı projenin üyesi değil."):
        super().__init__(
            status_code=404,
            code="MEMBER_NOT_FOUND",
            message=message
        )

class CannotRemoveSelfException(CustomAPIException):
    def __init__(self, message: str = "Kendinizi projeden çıkaramazsınız."):
        super().__init__(
            status_code=400,
            code="CANNOT_REMOVE_SELF",
            message=message
        )


