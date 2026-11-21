import logging
from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError
from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import settings
from app.api.v1.api import api_router
from app.core.exceptions import CustomAPIException

logger = logging.getLogger(__name__)


class InternalErrorMiddleware:
    """Beklenmeyen 500 hatalarını CORS katmanının içinde yakalar (#252).

    Starlette'te `@app.exception_handler(Exception)` CORS middleware'inin dışında çalışır;
    bu yüzden tarayıcı 500 yanıtını CORS/bağlantı hatası gibi görür. Bu middleware CORS'tan
    önce eklendiği için CORS'un içinde çalışır ve sözleşme formatında 500 INTERNAL_ERROR döner.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def tracked_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, receive, tracked_send)
        except Exception:
            logger.exception("Beklenmeyen sunucu hatası")
            if response_started:
                raise
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Beklenmeyen bir hata oluştu.",
                        "fields": None,
                        "details": None,
                    }
                },
            )
            await response(scope, receive, send)


# Tablolar uygulama açılışında oluşturulmaz; şema yalnızca Alembic ile yönetilir (NFR-018).
# Kurulumda bir kez: alembic upgrade head

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="LUNO Kimlik & Roller API Servisleri (Backend)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# İç katman: beklenmeyen 500 hatalarını yakalar (CORS'un içinde kalır)
app.add_middleware(InternalErrorMiddleware)

# Dış katman: CORS başlıklarını tüm yanıtlara (500 dahil) ekler
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers matching LUNO API Contract
@app.exception_handler(CustomAPIException)
async def custom_api_exception_handler(request: Request, exc: CustomAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "fields": exc.fields,
                "details": exc.details
            }
        }
    )

def _translate_validation_error(err: dict) -> str:
    err_type = str(err.get("type", ""))
    ctx = err.get("ctx") or {}
    msg = err.get("msg", "Geçersiz değer.")

    if "email" in err_type or (isinstance(msg, str) and "valid email" in msg.lower()):
        return "Geçerli bir e-posta adresi giriniz."
    if err_type == "value_error":
        if isinstance(msg, str) and msg.startswith("Value error, "):
            return msg[len("Value error, "):]
        return str(msg)
    if err_type == "missing":
        return "Bu alan zorunludur."
    if err_type == "string_too_short":
        return f"En az {ctx.get('min_length')} karakter olmalıdır."
    if err_type == "string_too_long":
        return f"En fazla {ctx.get('max_length')} karakter olmalıdır."
    if err_type == "string_type":
        return "Metin değeri girilmelidir."
    if err_type in ("int_parsing", "int_type"):
        return "Geçerli bir tam sayı girilmelidir."
    if err_type in ("float_parsing", "float_type"):
        return "Geçerli bir sayı girilmelidir."
    if err_type in ("bool_parsing", "bool_type"):
        return "Geçerli bir mantıksal değer girilmelidir."
    if err_type == "greater_than_equal":
        return f"En az {ctx.get('ge')} olmalıdır."
    if err_type == "greater_than":
        return f"{ctx.get('gt')} değerinden büyük olmalıdır."
    if err_type == "less_than_equal":
        return f"En fazla {ctx.get('le')} olmalıdır."
    if err_type == "less_than":
        return f"{ctx.get('lt')} değerinden küçük olmalıdır."
    if err_type in ("enum", "literal_error"):
        return "Geçersiz değer seçildi."
    if err_type in ("date_from_datetime_parsing", "date_parsing", "date_type"):
        return "Geçerli bir tarih girilmelidir (YYYY-AA-GG)."
    if err_type in ("datetime_parsing", "datetime_type"):
        return "Geçerli bir tarih ve saat girilmelidir."
    if err_type == "list_type":
        return "Geçerli bir liste girilmelidir."
    if err_type == "json_invalid":
        return "Geçersiz JSON biçimi."
    if "email" in err_type or (isinstance(msg, str) and "valid email" in msg.lower()):
        return "Geçerli bir e-posta adresi giriniz."

    if isinstance(msg, str) and msg.startswith("Value error, "):
        return msg[len("Value error, "):]
    return "Geçersiz değer."


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = {}
    for err in exc.errors():
        field_name = err["loc"][-1] if err["loc"] else "general"
        fields[str(field_name)] = _translate_validation_error(err)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Lütfen hatalı alanları düzeltin.",
                "fields": fields,
                "details": None
            }
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "HTTP_ERROR"
    if exc.status_code == 401:
        code = "UNAUTHORIZED"
    elif exc.status_code == 403:
        code = "FORBIDDEN"
    elif exc.status_code == 404:
        code = "NOT_FOUND"
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": code,
                "message": str(exc.detail),
                "fields": None,
                "details": None
            }
        }
    )

# Veritabanı benzersizlik/bağlantı kuralına takılan istek (ör. aynı kaydın aynı anda iki kez
# oluşturulması) 500 yerine 409 döner (#219, #253). Uç noktalar kendi hata kodlarını
# (LABEL_EXISTS gibi) önceden kontrol eder; bu yalnızca eşzamanlı istekler için yedektir.
@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": {
                "code": "CONFLICT",
                "message": "Bu işlem başka bir işlemle çakıştı. Lütfen sayfayı yenileyip tekrar deneyin.",
                "fields": None,
                "details": None
            }
        }
    )

# Health Check Endpoint (Bölüm 1.1)
@app.get("/health", tags=["Sağlık Kontrolü"], summary="Sağlık Kontrolü")
def health_check():
    return {"status": "ok"}

# Include API Router (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
