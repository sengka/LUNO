from fastapi import FastAPI, Request, status, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.api.v1.api import api_router
from app.core.exceptions import CustomAPIException

# Tablolar uygulama açılışında oluşturulmaz; şema yalnızca Alembic ile yönetilir (NFR-018).
# Kurulumda bir kez: alembic upgrade head

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="LUNO Kimlik & Roller API Servisleri (Backend)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS setup
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

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    fields = {}
    for err in exc.errors():
        field_name = err["loc"][-1] if err["loc"] else "general"
        msg = err.get("msg", "Geçersiz değer")
        if isinstance(msg, str) and msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        fields[str(field_name)] = msg

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
