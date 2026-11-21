"""#252 (#219 madde 4) Genel 500 yakalayıcısı (INTERNAL_ERROR) testleri.

Beklenmeyen hatalar CORS katmanının içinde yakalanmalı ve sözleşme formatında
`{"error": {"code": "INTERNAL_ERROR", ...}}` dönmelidir.
"""

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def boom_route():
    router = APIRouter()

    @router.get("/__test__/boom")
    def boom():
        raise RuntimeError("beklenmeyen test hatası")

    app.include_router(router)
    yield
    app.router.routes[:] = [
        r for r in app.router.routes if getattr(r, "path", "") != "/__test__/boom"
    ]


def test_unhandled_exception_returns_500_contract_with_cors(boom_route):
    origin = "http://localhost:5173"
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test__/boom", headers={"Origin": origin})

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Beklenmeyen bir hata oluştu.",
            "fields": None,
            "details": None,
        }
    }
    # Hata CORS katmanının içinde yakalandığı için tarayıcı yanıtı okuyabilir.
    assert response.headers.get("access-control-allow-origin") == origin


def test_password_over_72_bytes_returns_contract_error_with_cors():
    """72 byte'tan uzun şifre gönderildiğinde CORS başlığıyla sözleşme formatında yanıt dönmeli."""
    origin = "http://localhost:5173"
    long_password = "A" * 80 + "1!"
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/auth/register",
            headers={"Origin": origin},
            json={
                "full_name": "Uzun Şifre Test",
                "email": "uzunsifre@ornek.com",
                "password": long_password,
            },
        )

    assert response.headers.get("access-control-allow-origin") == origin
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] in ("VALIDATION_ERROR", "INTERNAL_ERROR")
