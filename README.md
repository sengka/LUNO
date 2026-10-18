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

# 5. (İsteğe bağlı) Örnek veri: 10 kullanıcı, 2 proje, 19 görev · şifre: Luno1234
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

**Örnek veri seçenekleri:** `python -m app.seed --reset` tabloları boşaltıp yeniden yükler; `python -m app.seed --buyuk` ayrıca 200 görev ve 20 üyeli bir yük testi projesi ekler.

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
