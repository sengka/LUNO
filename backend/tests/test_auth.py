from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# ==========================================
# US-001 (Issue #65) - Kayıt API'si Testleri
# ==========================================

def test_register_success(client: TestClient):
    payload = {
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "ayse@ornek.com"
    assert data["full_name"] == "Ayşe Yılmaz"
    assert data["role"] == "EKIP_UYESI"
    assert data["theme"] == "LIGHT"
    assert data["avatar_url"] is None
    assert "id" in data
    assert "created_at" in data

def test_register_duplicate_email(client: TestClient):
    payload = {
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    }
    # First registration
    client.post("/api/v1/auth/register", json=payload)
    
    # Second registration with same email
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert data["error"]["message"] == "Bu e-posta adresi zaten kullanımda."

def test_register_short_password(client: TestClient):
    payload = {
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "short"  # Less than 8 characters
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "password" in data["error"]["fields"]

def test_register_invalid_email(client: TestClient):
    payload = {
        "full_name": "Ayşe Yılmaz",
        "email": "invalid-email-format",
        "password": "GucluPassword123"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "email" in data["error"]["fields"]

# ==========================================
# US-002 (Issue #68) - Giriş ve GET /auth/me Testleri
# ==========================================

def test_login_success(client: TestClient):
    # Register user first
    client.post("/api/v1/auth/register", json={
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })

    # Login
    login_payload = {
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 86400  # 24 hours
    assert data["user"]["email"] == "ayse@ornek.com"
    assert data["user"]["role"] == "EKIP_UYESI"

def test_login_wrong_password(client: TestClient):
    # Register user
    client.post("/api/v1/auth/register", json={
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })

    # Login with wrong password
    login_payload = {
        "email": "ayse@ornek.com",
        "password": "WrongPassword999"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert data["error"]["message"] == "E-posta veya şifre hatalı."

def test_login_unregistered_email(client: TestClient):
    # Login with non-existent email
    login_payload = {
        "email": "unregistered@ornek.com",
        "password": "AnyPassword123"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"
    assert data["error"]["message"] == "E-posta veya şifre hatalı."

def test_get_me_success(client: TestClient):
    # Register and login
    client.post("/api/v1/auth/register", json={
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })
    token = login_res.json()["access_token"]

    # Call /auth/me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "ayse@ornek.com"
    assert data["full_name"] == "Ayşe Yılmaz"
    assert data["role"] == "EKIP_UYESI"

def test_get_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
    assert data["error"]["message"] == "Oturumunuzun süresi doldu, lütfen tekrar giriş yapın."

def test_get_me_invalid_token(client: TestClient):
    headers = {"Authorization": "Bearer invalid_or_corrupted_token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "UNAUTHORIZED"

# ==========================================
# US-003 (Issue #71) - Çıkış (Logout) Testleri
# ==========================================

def test_logout_success_and_invalidation(client: TestClient):
    # Register and login
    client.post("/api/v1/auth/register", json={
        "full_name": "Ayşe Yılmaz",
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })
    login_res = client.post("/api/v1/auth/login", json={
        "email": "ayse@ornek.com",
        "password": "GucluPassword123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify access before logout
    res_before = client.get("/api/v1/auth/me", headers=headers)
    assert res_before.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 204

    # Verify access after logout with the same token is revoked
    res_after = client.get("/api/v1/auth/me", headers=headers)
    assert res_after.status_code == 401
    data = res_after.json()
    assert data["error"]["code"] == "UNAUTHORIZED"
