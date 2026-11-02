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

Gereksinimler: Windows/macOS/Linux üzerinde çalışan Docker Desktop veya Docker Engine ve Docker Compose v2. Windows'ta Docker Desktop'ın **Linux containers** motoru çalışır durumda olmalıdır. Bu yöntemle uygulamayı çalıştırmak için bilgisayarda ayrıca Python veya Node.js kurmanız gerekmez.

Komutları, `docker-compose.yml` dosyasının bulunduğu **proje kök klasöründe** çalıştırın. Önce klasörün doğru olduğunu kontrol edebilirsiniz:

```bash
ls
```

Listede `docker-compose.yml` ve `.env.example` görünmelidir. Ardından örnek ayar dosyasını kopyalayın. Aynı klasörde önceden oluşturulmuş `.env` dosyanız varsa bu adımı atlayın; komut mevcut dosyayı ezebilir.

```bash
# Git Bash / macOS / Linux
cp .env.example .env
```

PowerShell kullanıyorsanız kopyalama komutu:

```powershell
Copy-Item .env.example .env
```

Proje kökündeki `.env` dosyasını açın. `SECRET_KEY=` satırındaki örnek değeri kendi rastgele anahtarınızla değiştirin. Anahtar üretmek için Python kuruluysa şu komutu çalıştırıp çıkan değeri kullanabilirsiniz:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`.env` dosyasının adı tam olarak `.env` olmalı; `.env.txt` olmamalıdır. Bu dosya kişisel ayarlar ve sırlar içerdiği için GitHub'a gönderilmez. Sonra proje kök klasöründe uygulamayı oluşturup başlatın:

```bash
docker compose up --build
```

İlk çalıştırmada Docker gerekli imajları indirip servisleri oluşturur; bu işlem birkaç dakika sürebilir. Veritabanı hazır olunca backend Alembic migration'larını otomatik çalıştırır. Terminalde `Uvicorn running on http://0.0.0.0:8000` benzeri bir satır gördüğünüzde servisler başlamıştır:

- Arayüz: <http://localhost:5173>
- Backend API dokümantasyonu: <http://localhost:8000/docs>

İlk kez giriş yapıp örnek kullanıcılarla denemek isterseniz ikinci bir terminal açıp proje kökünde şu komutu çalıştırın. Örnek verideki şifre `Luno1234`'tür; örnek veriyi gerçek kullanıcı verisi bulunan bir veritabanına eklemeyin.

```bash
docker compose exec backend python -m app.seed
```

Uygulamayı durdurmak için ilk terminalde `Ctrl+C`, sonra proje kökünde:

```bash
docker compose down
```

`docker compose down` veritabanı verilerini saklar. Veritabanı verilerini de silmek için `docker compose down -v` kullanılabilir; bu komut **PostgreSQL verilerini kalıcı olarak siler**.

#### Sık karşılaşılan sorunlar

| Belirti | Çözüm |
| --- | --- |
| `no configuration file provided: not found` | Terminal proje kök klasöründe değildir. `docker-compose.yml` dosyasının bulunduğu klasöre geçip komutu tekrar çalıştırın. |
| `SECRET_KEY is missing` veya `required variable SECRET_KEY` | Proje kökünde `.env` dosyası olduğundan emin olun; yoksa `.env.example` dosyasını kopyalayın. `SECRET_KEY=` satırındaki değer boş veya örnek değer olarak kalmış olmamalıdır. Dosya adının `.env.txt` olmadığını kontrol edin. |
| `failed to connect to the docker API`, `dockerDesktopLinuxEngine` veya `daemon is not running` | Docker Desktop'ı açın ve motorun başlamasını bekleyin. Windows'ta Docker Desktop'ın WSL 2 / Linux containers ortamının çalışır durumda olduğunu kontrol edin. |
| `port is already allocated` veya `address already in use` | `5173`, `8000` ya da `5432` portlarından biri başka bir uygulama tarafından kullanılıyordur. O uygulamayı kapatın veya `docker-compose.yml` içindeki sol taraftaki port numarasını değiştirin. |
| Sayfa açılmıyor veya servis hata veriyor | `docker compose ps` ile servis durumuna, `docker compose logs --tail=100 backend` ve `docker compose logs --tail=100 frontend` ile son kayıtlara bakın. Veritabanı için `docker compose logs --tail=100 db` kullanın. |

## Canlı yayın (Render + Supabase)

Canlı ortamın Render ayarları proje kökündeki `render.yaml` dosyasında tanımlıdır. Frontend Render Static Site olarak derlenir; backend Docker ile çalışır. Veritabanı Supabase PostgreSQL'dir. Yayın için GitHub deposunu Render'a bağlayıp **New > Blueprint** ile bu dosyadaki kaynakları oluşturun.

### 1. Supabase PostgreSQL bağlantısı

1. Supabase'te bir proje oluşturun ve veritabanı parolasını güvenli bir yere kaydedin.
2. Projede **Connect > Session pooler** bölümünü açıp bağlantı adresini kopyalayın. Parolada `@`, `#`, `?`, `/` gibi özel karakterler varsa URL içinde kodlanmalıdır.
3. Render Blueprint ilk kurulum sırasında `DATABASE_URL` ister. Supabase adresini SQLAlchemy/psycopg2 biçimine dönüştürün: baştaki `postgresql://` yerine `postgresql+psycopg2://` kullanın ve sona `?sslmode=require` ekleyin (adreste zaten `?` varsa `&sslmode=require`). Bu değeri yalnızca Render'a girin; GitHub'a veya sohbete koymayın.

### 2. Render servisleri ve ortam değişkenleri

Blueprint, `luno-api` backend servisini ve `luno-frontend` statik sitesini oluşturur. Gizli değişkenler ve henüz bilinmeyen canlı adresler Blueprint'in ilk kurulum ekranında geçici değerlerle doldurulabilir; servis URL'leri oluştuktan sonra Render Dashboard'da gerçek değerlerle güncellenmelidir.

Backend'in **Environment** bölümünde:

| Değişken | Değer |
|---|---|
| `SECRET_KEY` | Blueprint'in Render'da ürettiği rastgele değer |
| `DATABASE_URL` | Yukarıdaki Supabase bağlantısı |
| `CORS_ORIGINS` | Frontend'in Render URL'si, ör. `https://luno-frontend.onrender.com` |
| `FRONTEND_URL` | Aynı frontend URL'si |

Frontend'in **Environment** bölümünde `VITE_API_URL` değerini backend URL'si ve `/api/v1` ile ayarlayın. Vite bu adresi derleme sırasında pakete eklediği için değişiklikten sonra frontend'i yeniden deploy edin. Frontend API adresini ve backend'in CORS değişkenlerini servislerin oluşturduğu gerçek URL'lere göre doldurun.

Backend başlangıçta `alembic upgrade head` çalıştırır. Canlı veritabanına **`python -m app.seed` çalıştırmayın**; bu komut herkesçe bilinen demo hesaplarını ekler. API'nin `https://<backend-adresi>/health` adresi `{"status":"ok"}` döndürmelidir.

#### Canlı adresler

- **Frontend:** https://luno-frontend.onrender.com
- **Backend API:** https://luno-api-mu54.onrender.com/api/v1
- **Backend sağlık kontrolü:** https://luno-api-mu54.onrender.com/health

Render'ın ücretsiz backend servisi bir süre kullanılmadığında uykuya geçebilir; sonraki ilk istek yaklaşık 50 saniye veya daha uzun sürebilir.

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

#### Dosya depolama (US-018)

Yerel geliştirmede dosyalar `backend/uploads/` klasöründe tutulur. Bu klasör `.gitignore` içindedir ve Git'e eklenmez. `.env.example` dosyasını `.env` olarak kopyaladıktan sonra varsayılan ayarlar (`STORAGE_BACKEND=local`, `UPLOAD_DIR=./uploads`) yeterlidir.

Canlı Render ortamında dosyalar Supabase Storage'daki **özel (private)** `luno-files` bucket'ında tutulur. Uygulama yükleme, indirme ve silme işlemlerini kimliği doğrulanmış backend API'si üzerinden yapar; bucket public yapılmamalı ve `service_role` anahtarı yalnızca backend'de tutulmalıdır.

**Supabase kurulumu:**

1. Supabase Dashboard'da LUNO projesini açıp **Storage → New bucket** seçin.
2. Bucket adını `luno-files` yapın ve **Public bucket** seçeneğini kapalı bırakın.
3. **Project Settings → Data API** bölümünden Project URL'yi; **Project Settings → API Keys → Legacy API Keys** bölümünden `service_role` anahtarını alın. `anon` anahtarını kullanmayın.
4. Render'da `luno-api` servisini açıp **Environment** bölümüne şu değerleri ekleyin:

   | Değişken | Değer |
   |---|---|
   | `STORAGE_BACKEND` | `supabase` |
   | `SUPABASE_URL` | Supabase Project URL (`https://….supabase.co`) |
   | `SUPABASE_SERVICE_KEY` | Supabase `service_role` anahtarı |
   | `SUPABASE_BUCKET` | `luno-files` |

5. **Save Changes** ile servisin yeniden dağıtılmasını bekleyin. Ardından uygulamada bir projeye dosya yükleyip Supabase **Storage → luno-files** alanında nesnenin oluştuğunu kontrol edin.

`SUPABASE_SERVICE_KEY` gizli bir anahtardır: Git'e, `.env.example` dosyasına, frontend ayarlarına veya sohbete koymayın. Yalnızca Render backend servisinin gizli Environment değişkeni olarak saklayın. `STORAGE_BACKEND=supabase` seçildiğinde eksik URL, anahtar veya bucket ayarı uygulamanın başlangıcında açık bir yapılandırma hatası verir; sessizce geçici yerel diske dönmez.

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

Gereksinim: **Node.js 22.22 veya üzeri** (react-router 8 bu sürümü istiyor). Sürümünü `node -v` ile kontrol edebilirsin. Komutlar `frontend/` klasöründe çalıştırılır.

```bash
cd frontend

# 1. Paketler (bir kez ve package.json değiştiğinde)
npm install

# 2. Geliştirme sunucusu
npm run dev
```

Arayüz `http://localhost:5173` adresinde açılır. Giriş yapabilmek için backend'in de çalışıyor olması gerekir (yukarıdaki Backend bölümü). Örnek veri yüklediysen `sena@ornek.com` (yönetici) veya `mehmet@ornek.com` (ekip üyesi) ile `Luno1234` şifresiyle giriş yapabilirsin.

**Backend adresi:** Varsayılan `http://localhost:8000/api/v1`. Farklı bir adres için `.env.example` dosyasını `.env.local` olarak kopyalayıp `VITE_API_URL` değerini değiştir.

**Diğer komutlar:**

| Komut | Ne yapar |
| --- | --- |
| `npm run build` | TypeScript kontrolü yapıp yayın sürümünü `dist/` klasörüne üretir |
| `npm run lint` | Kod kalitesi kontrolü (oxlint) |
| `npm run preview` | Üretilen yayın sürümünü yerelde açar |

**Klasör yapısı:**

- `src/features/` · Özelliğe göre ekranlar ve API çağrıları (`auth`, `users`, `projects`)
- `src/components/ui/` · shadcn/ui bileşenleri. Yeni bileşen: `npx shadcn@latest add <ad>`
- `src/components/` · Ortak bileşenler (düzen, form alanları, logo)
- `src/lib/api.ts` · Backend istemcisi: token ekleme, ortak hata formatı, 401'de oturumu kapatma
- `src/types/api.ts` · API sözleşmesindeki veri tipleri

## Ekip

YZM397 Yazılım Proje Yönetimi dersi kapsamında 11 kişilik bir ekip tarafından geliştirilmektedir.
