"""Test ve demo için örnek veri.

Kullanım (backend/ klasöründen, önce `alembic upgrade head`):
    python -m app.seed            # veri yoksa ekler
    python -m app.seed --reset    # tüm tabloları boşaltıp yeniden ekler
    python -m app.seed --buyuk    # ayrıca 200 görev / 20 üyeli yük testi projesi (NFR-011)

Tüm kullanıcıların şifresi: Luno1234
Yönetici hesapları: sena@ornek.com, aybuke@ornek.com
"""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.core.security import get_password_hash
from app.database import Base, SessionLocal
from app.models import (
    Priority,
    Project,
    ProjectMember,
    SystemRole,
    Task,
    TaskStatus,
    User,
)

SEED_PASSWORD = "Luno1234"
TURKEY_TZ = timezone(timedelta(hours=3))  # tarihler Türkiye saatine göre

# (ad soyad, e-posta, sistem rolü, teknik rol, kapasite puanı)
USERS = [
    ("Sena Gül Kara", "sena@ornek.com", SystemRole.YONETICI, "Proje Yöneticisi", None),
    ("Aybüke Turgun", "aybuke@ornek.com", SystemRole.YONETICI, "Scrum Master", None),
    ("Esra Musul", "esra@ornek.com", SystemRole.EKIP_UYESI, "Backend Geliştirici", 13),
    ("Emre Kaan Şensoy", "emre@ornek.com", SystemRole.EKIP_UYESI, "Backend Geliştirici", 13),
    ("Esma Otur", "esma@ornek.com", SystemRole.EKIP_UYESI, "Veritabanı Geliştirici", 13),
    ("Mehmet Sefa Karadaş", "mehmet@ornek.com", SystemRole.EKIP_UYESI, "Frontend Geliştirici", 8),
    ("Havva Zülal Ertürk", "havva@ornek.com", SystemRole.EKIP_UYESI, "Frontend Geliştirici", 13),
    ("Gizem Tangel", "gizem@ornek.com", SystemRole.EKIP_UYESI, "UI/UX Tasarımcı", 13),
    ("Hakan Aydın", "hakan@ornek.com", SystemRole.EKIP_UYESI, "Test Uzmanı", 13),
    ("Salih Bilgin", "salih@ornek.com", SystemRole.EKIP_UYESI, "DevOps", None),
]

LOAD_PROJECT_NAME = "Yük Testi Projesi"
LOAD_MEMBER_COUNT = 20
LOAD_TASK_COUNT = 200


def today():
    return datetime.now(TURKEY_TZ).date()


def reset(db) -> None:
    """Tüm tabloları boşaltır (SQLite ve PostgreSQL'de çalışır)."""
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def seed(db) -> None:
    if db.scalar(select(User).limit(1)) is not None:
        print(
            "Veritabanında zaten kullanıcı var, seed atlandı. Yeniden yüklemek için --reset kullanın."
        )
        return

    day = today()
    # NFR-001: şifreler giriş API'siyle aynı fonksiyonla (bcrypt) hash'lenir.
    hashed_password = get_password_hash(SEED_PASSWORD)

    users = {}
    for full_name, email, role, _, _ in USERS:
        user = User(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            role=role.value,
            theme="LIGHT",
        )
        db.add(user)
        users[email.split("@")[0]] = user
    db.flush()

    # 1. proje: tüm ekip üye, görevlerin her durumu temsil ediliyor.
    mobil = Project(
        name="Mobil Uygulama",
        description="Müşteri için mobil uygulama geliştirme projesi",
        start_date=day - timedelta(days=5),
        end_date=day + timedelta(days=50),
        created_by=users["sena"],
    )
    # 2. proje: sadece birkaç üye; proje erişim kısıtını (FR-013) test etmek için.
    web = Project(
        name="Kurumsal Web Sitesi",
        description="Tanıtım sitesi yenileme",
        start_date=day,
        end_date=day + timedelta(days=30),
        created_by=users["aybuke"],
    )
    db.add_all([mobil, web])

    for _, email, _, technical_role, capacity in USERS:
        db.add(
            ProjectMember(
                project=mobil,
                user=users[email.split("@")[0]],
                technical_role=technical_role,
                capacity_points=capacity,
            )
        )
    for key in ("aybuke", "gizem", "mehmet"):
        db.add(ProjectMember(project=web, user=users[key]))

    def task(
        project,
        title,
        status,
        assignee=None,
        priority=None,
        points=None,
        start=None,
        due=None,
        parent=None,
        created_by=None,
        description=None,
    ):
        t = Task(
            project=project,
            title=title,
            description=description,
            status=status,
            assignee=users[assignee] if assignee else None,
            priority=priority,
            story_points=points,
            start_date=day + timedelta(days=start) if start is not None else None,
            due_date=day + timedelta(days=due) if due is not None else None,
            parent=parent,
            created_by=created_by or users["sena"],
        )
        db.add(t)
        return t

    T, P = TaskStatus, Priority
    giris = task(
        mobil,
        "Giriş ekranı",
        T.IN_PROGRESS,
        "mehmet",
        P.YUKSEK,
        5,
        -1,
        3,
        description="E-posta ve şifre ile giriş ekranı",
    )
    task(mobil, "Form tasarımı", T.DONE, "mehmet", P.ORTA, 2, -1, 1, parent=giris)
    task(mobil, "Hata mesajları", T.TODO, "mehmet", P.ORTA, 1, 1, 3, parent=giris)
    task(mobil, "Token saklama", T.TODO, "mehmet", P.DUSUK, 1, 2, 3, parent=giris)

    task(mobil, "Kayıt API'si", T.DONE, "esra", P.YUKSEK, 3, -5, -2)
    task(mobil, "Giriş API'si", T.REVIEW_TESTING, "esra", P.YUKSEK, 3, -3, 1)
    task(mobil, "Veritabanı modelleri", T.IN_PROGRESS, "esma", P.YUKSEK, 5, -5, 1)
    task(mobil, "Seed verisi", T.TODO, "esma", P.ORTA, 2, 0, 2)
    task(mobil, "Proje API'si", T.TODO, "emre", P.YUKSEK, 5, 2, 8)
    task(
        mobil, "Görev API'si", T.TODO, "emre", P.YUKSEK, 8, 5, 12
    )  # Emre: 13 / 13 puan, kapasite dolu
    task(mobil, "Docker ortamı", T.IN_PROGRESS, "salih", P.ORTA, 3, -4, -1)  # teslim tarihi geçmiş
    task(mobil, "Test planı", T.TODO, "hakan", P.ORTA, 3, 0, 6)
    task(mobil, "Wireframe'ler", T.DONE, "gizem", P.YUKSEK, 5, -5, -1)
    task(mobil, "Takvim kütüphanesi denemesi", T.TODO, None, P.DUSUK, 2, 1, 5)  # atanmamış
    task(mobil, "Tarihsiz araştırma görevi", T.TODO, "havva")  # tarih ve puan yok

    # Ekip üyesi önerileri (FR-026 – FR-029): Kanban ve raporlarda görünmemeli.
    task(mobil, "Rapor ekranı", T.ONAY_BEKLIYOR, created_by=users["mehmet"])
    task(mobil, "Bildirim sesleri", T.REDDEDILDI, created_by=users["havva"])

    task(web, "Ana sayfa tasarımı", T.TODO, "gizem", P.YUKSEK, 5, 0, 7, created_by=users["aybuke"])
    task(web, "Ana sayfa kodlaması", T.TODO, "mehmet", P.ORTA, 3, 7, 14, created_by=users["aybuke"])

    db.commit()
    task_count = db.scalar(select(func.count()).select_from(Task))
    print(
        f"Seed tamamlandı: {len(users)} kullanıcı, 2 proje, {task_count} görev. Şifre: {SEED_PASSWORD}"
    )


def seed_load_test(db) -> None:
    """NFR-011: 200 görev ve 20 üyeli bir projeyle Kanban, takvim ve Gantt testi."""
    if db.scalar(select(Project).where(Project.name == LOAD_PROJECT_NAME)) is not None:
        print("Yük testi projesi zaten var, atlandı.")
        return

    day = today()
    hashed_password = get_password_hash(SEED_PASSWORD)
    manager = db.scalar(select(User).where(User.email == "sena@ornek.com"))

    users = list(db.scalars(select(User).order_by(User.id)).all())
    for i in range(len(users) + 1, LOAD_MEMBER_COUNT + 1):
        user = User(
            full_name=f"Test Kullanıcı {i}",
            email=f"test{i}@ornek.com",
            hashed_password=hashed_password,
            role=SystemRole.EKIP_UYESI.value,
            theme="LIGHT",
        )
        db.add(user)
        users.append(user)
    users = users[:LOAD_MEMBER_COUNT]

    project = Project(
        name=LOAD_PROJECT_NAME,
        description="NFR-011 için 200 görev ve 20 üyeli test projesi",
        start_date=day - timedelta(days=30),
        end_date=day + timedelta(days=60),
        created_by=manager,
    )
    db.add(project)
    for user in users:
        db.add(ProjectMember(project=project, user=user, capacity_points=21))

    statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING, TaskStatus.DONE]
    priorities = list(Priority)
    for i in range(LOAD_TASK_COUNT):
        start = day + timedelta(days=(i % 80) - 30)
        db.add(
            Task(
                project=project,
                title=f"Test görevi {i + 1}",
                status=statuses[i % len(statuses)],
                priority=priorities[i % len(priorities)],
                story_points=(1, 2, 3, 5, 8, 13)[i % 6],
                start_date=start,
                due_date=start + timedelta(days=(i % 7) + 1),
                assignee=users[i % len(users)],
                created_by=manager,
            )
        )

    db.commit()
    print(f"Yük testi projesi eklendi: {LOAD_MEMBER_COUNT} üye, {LOAD_TASK_COUNT} görev.")


def main() -> None:
    parser = argparse.ArgumentParser(description="LUNO örnek verisi")
    parser.add_argument("--reset", action="store_true", help="Tabloları boşaltıp yeniden yükle")
    parser.add_argument(
        "--buyuk",
        action="store_true",
        help="NFR-011 için 200 görev ve 20 üyeli yük testi projesini de ekle",
    )
    args = parser.parse_args()
    with SessionLocal() as db:
        if args.reset:
            reset(db)
        seed(db)
        if args.buyuk:
            seed_load_test(db)


if __name__ == "__main__":
    main()
