"""#249, #250 ve #251 güvenlik/hata düzeltmeleri için testler."""

from datetime import date, datetime, timezone

from app.core.security import create_access_token, decode_access_token, get_password_hash
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import SystemRole, User


def _create_user(db, email: str, password: str = "Guclu1234", role: str = SystemRole.EKIP_UYESI.value, full_name: str = "Test Kullanıcı"):
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# --- #249: Token jti, iat, iptal kontrolü ---


def test_token_contains_jti_and_iat_and_same_second_logins_differ(client, db_session):
    _create_user(db_session, "esra@ornek.com", "Guclu1234")

    res1 = client.post("/api/v1/auth/login", json={"email": "esra@ornek.com", "password": "Guclu1234"})
    res2 = client.post("/api/v1/auth/login", json={"email": "esra@ornek.com", "password": "Guclu1234"})
    assert res1.status_code == 200
    assert res2.status_code == 200

    token1 = res1.json()["access_token"]
    token2 = res2.json()["access_token"]
    assert token1 != token2

    payload1 = decode_access_token(token1)
    payload2 = decode_access_token(token2)
    assert payload1 is not None and payload2 is not None
    assert "jti" in payload1 and "iat" in payload1
    assert "jti" in payload2 and "iat" in payload2
    assert payload1["jti"] != payload2["jti"]

    # 1. oturumdan çıkış yapılınca 1. token geçersiz olur, 2. oturum çalışmaya devam eder
    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token1}"})
    assert logout_res.status_code == 204

    me1 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert me1.status_code == 401
    assert me1.json()["error"]["code"] == "UNAUTHORIZED"

    me2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token2}"})
    assert me2.status_code == 200


def test_revoked_token_rejected_even_with_modified_base64_representation(client, db_session):
    _create_user(db_session, "guvenlik@ornek.com", "Guclu1234")
    res = client.post("/api/v1/auth/login", json={"email": "guvenlik@ornek.com", "password": "Guclu1234"})
    token = res.json()["access_token"]

    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 204

    # Aynı jti'ye sahip yeniden imzalanmış/değiştirilmiş token biçimi de reddedilmeli
    payload = decode_access_token(token)
    assert payload is not None
    # Payload'daki aynı jti ile tekrar encode edilen token da 401 dönmeli
    import jwt
    from app.config import settings

    forged_same_jti = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    res_check = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {forged_same_jti}"})
    assert res_check.status_code == 401


# --- #250: 72 bayt şifre sınırı, Türkçe 422 mesajları, e-posta küçük harf ---


def test_register_password_over_72_bytes_returns_422_turkish(client):
    # 40 adet 'Ş' -> UTF-8'de 80 bayt
    res = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ayşe Yılmaz", "email": "uzun@ornek.com", "password": "Ş" * 40},
    )
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "72 bayt" in body["error"]["fields"]["password"]

    # 73 adet ASCII karakter -> 73 bayt
    res2 = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ayşe Yılmaz", "email": "uzun2@ornek.com", "password": "a" * 73},
    )
    assert res2.status_code == 422
    assert "72 bayt" in res2.json()["error"]["fields"]["password"]


def test_validation_error_messages_are_turkish(client):
    res = client.post(
        "/api/v1/auth/register",
        json={"full_name": "A", "email": "gecersiz-eposta", "password": "123"},
    )
    assert res.status_code == 422
    fields = res.json()["error"]["fields"]
    assert "En az 2 karakter" in fields["full_name"]
    assert "e-posta" in fields["email"].lower()
    assert "En az 8 karakter" in fields["password"]
    for msg in fields.values():
        assert "String should" not in msg
        assert "value is not a valid" not in msg


def test_email_case_insensitive_register_login_and_add_member(client, db_session):
    # Büyük harfli e-posta ile kayıt -> küçük harfle saklanır
    reg = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ali Veli", "email": "Ali.Veli@Ornek.COM", "password": "Guclu1234"},
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "ali.veli@ornek.com"

    # Küçük harfle tekrar kayıt -> 409 EMAIL_ALREADY_EXISTS
    dup = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Ali İki", "email": "ali.veli@ornek.com", "password": "Guclu1234"},
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    # Karışık harfle giriş -> 200
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "ALI.VELI@ORNEK.COM", "password": "Guclu1234"},
    )
    assert login_res.status_code == 200

    # Proje üyesi eklerken büyük harfli e-posta -> 201
    admin = _create_user(db_session, "admin@ornek.com", role=SystemRole.YONETICI.value, full_name="Yönetici")
    project = Project(
        name="Test Projesi",
        description="Açıklama",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=admin.id, joined_at=datetime.now(timezone.utc)))
    db_session.commit()

    admin_token = create_access_token({"sub": str(admin.id), "email": admin.email, "role": admin.role})
    add_res = client.post(
        f"/api/v1/projects/{project.id}/members",
        json={"email": "ALI.VELI@ornek.com"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert add_res.status_code == 201
    assert add_res.json()["email"] == "ali.veli@ornek.com"


# --- #251: Çıkarılan üye eski davet bağlantısıyla geri katılamamalı ---


def test_removed_member_cannot_rejoin_with_old_invite_link(client, db_session):
    admin = _create_user(db_session, "yonetici@ornek.com", role=SystemRole.YONETICI.value, full_name="Yönetici")
    member = _create_user(db_session, "uye@ornek.com", role=SystemRole.EKIP_UYESI.value, full_name="Üye")

    project = Project(
        name="Gizli Proje",
        description="Açıklama",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    db_session.flush()
    db_session.add(ProjectMember(project_id=project.id, user_id=admin.id, joined_at=datetime.now(timezone.utc)))
    db_session.commit()

    admin_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(admin.id), 'email': admin.email, 'role': admin.role})}"}
    member_headers = {"Authorization": f"Bearer {create_access_token({'sub': str(member.id), 'email': member.email, 'role': member.role})}"}

    # Davet bağlantısı oluştur
    inv_res = client.post(f"/api/v1/projects/{project.id}/invites", headers=admin_headers)
    assert inv_res.status_code == 201
    invite_token = inv_res.json()["invite_url"].rstrip("/").split("/")[-1]

    # Üye davetle katılır
    join_res = client.post(f"/api/v1/invites/{invite_token}/accept", headers=member_headers)
    assert join_res.status_code == 200

    # Yönetici üyeyi çıkarır -> aktif davetler geçersiz kılınmalı
    rem_res = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}", headers=admin_headers)
    assert rem_res.status_code == 204

    # Çıkarılan üye aynı davet bağlantısıyla geri katılamaz
    rejoin_res = client.post(f"/api/v1/invites/{invite_token}/accept", headers=member_headers)
    assert rejoin_res.status_code == 400
    assert rejoin_res.json()["error"]["code"] == "INVITE_INVALID"
