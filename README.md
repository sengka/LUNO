# LUNO

Ekiplerin projelerini baştan sona tek bir yerde yönetebileceği, web tabanlı bir proje yönetim uygulaması.

Yönetici proje açar, görevleri tanımlar ve ekip üyelerine atar. Ekip üyeleri görevlerini Kanban panosunda ilerletir, dosya paylaşır ve yorumlarla iletişim kurar. Takvim ve Gantt şeması zamanı, raporlar ve dashboard ise ilerlemeyi görünür kılar.

LUNO'yu benzerlerinden ayıran taraf, geleceğe dair uyarı vermesidir: her görevin gecikme riskini hesaplar, bir kişiye fazla iş yüklenmek üzereyken uyarır ve her kullanıcıya "bugün neye odaklanmalısın" listesi çıkarır. LLM destekli özellikler ise toplantı notlarından görev çıkarma, büyük işleri alt görevlere bölme ve uzun tartışmaları özetleme gibi işleri kısaltır.

## Özellikler

**Temel modüller**

- Proje ve görev yönetimi (To Do / In Progress / Done)
- Kullanıcı ve rol yönetimi (Yönetici, Ekip Üyesi)
- Takvim, Gantt şeması ve Kanban panosu
- Dosya paylaşımı ve görev yorumları
- Raporlama: yüzdelik ilerleme, kişi bazlı ve dönemsel raporlar

**Akıllı özellikler**

- Gecikme riski tahmini ve kapasite uyarısı
- "Bugün ne yapmalıyım?" listesi
- Hızlı görev ekleme (`Rapor API'si @can #backend cuma`)
- Otomasyon kuralları ve akıllı hatırlatmalar
- LLM ile toplantı notundan görev çıkarma, alt görevlere bölme ve yorum özetleme

## Teknolojiler

| Katman         | Teknoloji                                          |
| -------------- | -------------------------------------------------- |
| Frontend       | React + Vite (TypeScript), Tailwind CSS, shadcn/ui |
| Backend        | Python, FastAPI                                    |
| Veritabanı     | PostgreSQL, SQLAlchemy, Alembic                    |
| LLM            | Groq (yedek: Gemini)                               |
| Ortam ve yayın | Docker, GitHub Actions, Render, Supabase           |

## Çalışma düzeni

- Proje Scrum ile, **1 haftalık sprintler** halinde geliştirilir.
- İş takibi GitHub Projects üzerinden yapılır.

### Branch düzeni

- `main`: Sadece çalışan, demo edilebilir kod
- `develop`: Tüm işlerin birleştiği ana geliştirme branch'i
- Her ekip üyesi kendi adıyla bir branch'te çalışır (ör. `sena`). Küçük harf, Türkçe karakter yok.
- `main` ve `develop`'a doğrudan push yapılmaz, değişiklikler Pull Request ile gönderilir.
- PR'lar Proje Yöneticisi veya Scrum Master tarafından onaylanır.

### Günlük akış

1. Çalışmaya başlamadan önce `git pull origin develop` ile branch'ini güncelle.
2. Görev bitince commit'le ve push'la.
3. Kendi branch'inden `develop`'a PR aç, açıklamaya `Closes #issue-no` yaz.

### Commit mesajı kuralı

`tür: kısa açıklama (#issue-no)`

| Tür        | Ne zaman        |
| ---------- | --------------- |
| `feat`     | Yeni özellik    |
| `fix`      | Hata düzeltme   |
| `docs`     | Doküman         |
| `style`    | Görünüm, format |
| `refactor` | Kod düzenleme   |
| `test`     | Test ekleme     |
| `chore`    | Kurulum, ayar   |

Örnek: `feat: görev oluşturma API'si eklendi (#12)`

## Kurulum

### Docker Compose ile çalıştırma

Gereksinim: Docker Desktop ve Docker Compose v2.

Proje kök klasöründe terminal açıp şu komutları çalıştırın:

```bash
cp .env.example .env
```

`.env` dosyasını açıp `SECRET_KEY` değerini uzun, rastgele bir değerle değiştirin. Ardından:

```bash
docker compose up --build
```

İlk açılışta veritabanı hazır olunca backend Alembic migration'larını çalıştırır. Arayüz `http://localhost:5173`, backend dokümantasyonu `http://localhost:8000/docs` adresindedir. Durdurmak için terminalde `Ctrl+C` tuşlarına basıp `docker compose down` çalıştırın.

### Backend

Gereksinim: Python 3.11 veya üzeri. Komutlar `backend/` klasöründe çalıştırılır.

```bash
cd backend

# 1. Sanal ortam (bir kez)
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash)
# .venv\Scripts\Activate.ps1       # Windows (PowerShell)
# source .venv/bin/activate        # macOS / Linux

# 2. Paketler
pip install -r requirements.txt

# 3. Ortam değişkenleri (bir kez)
cp .env.example .env               # PowerShell: Copy-Item .env.example .env
# .env içindeki SECRET_KEY zorunludur, boşsa uygulama başlamaz. Anahtar üretmek için:
python -c "import secrets; print(secrets.token_urlsafe(48))"

# 4. Veritabanı tabloları
alembic upgrade head

# 5. (İsteğe bağlı) Örnek veri: 11 kullanıcı, 2 proje, 19 görev, 2 davet · şifre: Luno1234
python -m app.seed

# 6. Uygulamayı başlat
uvicorn app.main:app --reload
```

Uygulama `http://localhost:8000`, API dokümantasyonu `http://localhost:8000/docs` adresinde açılır.

**Veritabanı:** Varsayılan `.env` SQLite kullanır (`backend/luno.db`). PostgreSQL için `.env` içindeki adresi değiştirin:
`DATABASE_URL=postgresql+psycopg2://kullanici:sifre@localhost:5432/luno`

**Tablolar yalnızca Alembic ile oluşturulur ve değiştirilir.** Uygulama açılışta tablo oluşturmaz.

- `develop`'u her çektiğinizde `alembic upgrade head` çalıştırın; yeni migration varsa uygulanır.
- Bir modele alan veya tablo eklediyseniz migration oluşturun, oluşan dosyayı kontrol edip modelle birlikte commit'leyin:
  ```bash
  alembic revision --autogenerate -m "kisa aciklama"
  alembic upgrade head
  ```
- `alembic upgrade head` "table already exists" hatası verirse veritabanınız Alembic'ten önce oluşturulmuştur. SQLite kullanıyorsanız `backend/luno.db` dosyasını silip komutu tekrar çalıştırın.

**Örnek veri seçenekleri:** `python -m app.seed --reset` tabloları boşaltıp yeniden yükler (id'ler de sıfırlanır); `python -m app.seed --buyuk` ayrıca 200 görev ve 20 üyeli bir yük testi projesi ekler. Örnek veri yalnızca yerel geliştirme ve demo içindir: şifre ve davet anahtarları herkesçe bilinir, gerçek kullanıcıların olduğu bir veritabanında çalıştırmayın.

**Örnek veride kimler var?**

| Kullanıcı | Rol | Mobil Uygulama (id 1) | Kurumsal Web Sitesi (id 2) |
|---|---|---|---|
| `sena@ornek.com` (id 1) | Yönetici | üye | — |
| `aybuke@ornek.com` (id 2) | Yönetici | üye | üye |
| `esra@ornek.com` (id 3) | Ekip Üyesi | üye | — |
| `gizem@`, `mehmet@` | Ekip Üyesi | üye | üye |
| `emre@`, `esma@`, `havva@`, `hakan@`, `salih@` | Ekip Üyesi | üye | — |
| `can@ornek.com` (id 11) | Ekip Üyesi | — | — |

Davet bağlantıları: `http://localhost:5173/davet/demo-web-davet` (geçerli, Kurumsal Web Sitesi) ve `http://localhost:5173/davet/demo-suresi-dolmus` (süresi dolmuş, Mobil Uygulama). Tüm şifreler `Luno1234`.

### Sprint 3 demo senaryosu

Sprint hedefi: Yönetici proje oluşturup düzenleyebilsin, üye ekleyebilsin; yetkisiz işlemler engellensin (US-005 – US-010).

**Hazırlık:**

1. `python -m app.seed --reset` ile örnek veriyi yükleyin ve `uvicorn app.main:app --reload` ile backend'i başlatın.
2. `http://localhost:8000/docs` adresini açın. Her kullanıcı için `POST /api/v1/auth/login` ile giriş yapın, yanıttaki `access_token` değerini sağ üstteki **Authorize** düğmesine yapıştırın. Kullanıcı değiştirirken önce **Logout**, sonra yeni token ile **Authorize**.

Aynı adımlar arayüzde de denenebilir (`http://localhost:5173`); aşağıdaki tablo API karşılıklarını ve beklenen sonuçları gösterir.

| # | Kim | İstek | Beklenen sonuç | Gereksinim |
|---|---|---|---|---|
| 1 | Esra (Ekip Üyesi) | `POST /api/v1/projects` | `403 FORBIDDEN`, ekip üyesi proje oluşturamaz | US-005, FR-012 |
| 2 | Sena | `POST /api/v1/projects` → `{"name": "Sprint 3 Demo", "start_date": "2026-10-20", "end_date": "2026-12-01"}` | `201`, yeni proje (id 3); Sena otomatik olarak üye olur | US-006, FR-015 |
| 3 | Sena | Aynı istek, bitiş tarihi başlangıçtan önce | `400 INVALID_DATE_RANGE` | FR-016 |
| 4 | Sena, Esra, Can | `GET /api/v1/projects` | Herkes yalnızca üyesi olduğu projeleri görür: Sena → Mobil Uygulama, Sprint 3 Demo · Esra → Mobil Uygulama · Can → boş liste | US-007, FR-017 |
| 5 | Esra | `GET /api/v1/projects/2` | `403 PROJECT_ACCESS_DENIED`, üyesi olmadığı projeyi göremez | US-005, FR-013 |
| 6 | Sena | `PATCH /api/v1/projects/3` → `{"name": "Sprint 3 Demo (güncel)"}` | `200`, proje adı güncellenir | US-008, FR-018 |
| 7 | Sena | `POST /api/v1/projects/3/members` → `{"email": "can@ornek.com"}` | `201`, Can üye olur. Aynı istek tekrar: `409 ALREADY_MEMBER` · kayıtlı olmayan e-posta: `404 USER_NOT_FOUND` | US-010, FR-021 |
| 8 | Aybüke | `POST /api/v1/projects/2/invites` | `201`, 7 gün geçerli yeni bir `invite_url` | US-010, FR-021 |
| 9 | Esra | `POST /api/v1/invites/demo-web-davet/accept` | `200`, Esra Kurumsal Web Sitesi'ne katılır ve artık projeler listesinde görür. Tekrar: `409 ALREADY_MEMBER` | US-010, FR-021 |
| 10 | Can | `POST /api/v1/invites/demo-suresi-dolmus/accept` | `400 INVITE_INVALID`, süresi dolmuş bağlantı | US-010, FR-021 |
| 11 | Aybüke | `DELETE /api/v1/projects/2/members/3` | `204`, Esra projeden çıkarılır, projeye tekrar erişemez. Kendini çıkarmayı denerse (`.../members/2`): `400 CANNOT_REMOVE_SELF` | US-010, FR-022 |
| 12 | Sena | `DELETE /api/v1/projects/3` | `204`, proje görevleri, üyelikleri ve davetleriyle birlikte silinir; `GET` ile `404 PROJECT_NOT_FOUND` | US-009, FR-020 |

Senaryoyu baştan oynatmak için `python -m app.seed --reset` yeterlidir.

**Testler:**

```bash
python -m pytest
```

Testler bellek içi ayrı bir SQLite veritabanı kullanır, geliştirme veritabanınıza dokunmaz.

### Frontend

Frontend kurulum adımları, frontend iskeleti `develop`'a eklendiğinde yazılacaktır.

## Ekip

YZM397 Yazılım Proje Yönetimi dersi kapsamında 11 kişilik bir ekip tarafından geliştirilmektedir.
