# LUNO Backend - Proje & Görev API Servisi

Bu modül, LUNO uygulamasının Proje, Görev, Takvim, Gantt ve Raporlama API servislerini içerir.

## Sorumlu Backend Geliştirici
**Emre Kaan Şensoy** (Backend Geliştirici: Proje & Görev · Backend & Veri)

## Sunulan Servisler ve Endpoint'ler

### 1. Proje API'leri (`/api/v1/projects`)
- `POST /api/v1/projects/` - Yeni proje oluşturma (isim, açıklama, başlangıç-bitiş tarihi, durum).
- `GET /api/v1/projects/` - Projeleri listeleme ve durum bazlı filtreleme.
- `GET /api/v1/projects/{id}` - Proje detayını getirme.
- `PUT /api/v1/projects/{id}` - Proje bilgilerini düzenleme/güncelleme.
- `DELETE /api/v1/projects/{id}` - Projeyi silme.

### 2. Görev API'leri (`/api/v1/tasks`)
- `POST /api/v1/tasks/` - Yeni görev oluşturma.
- `GET /api/v1/tasks/` - Görevleri listeleme (proje, atanan kişi ve duruma göre filtreleme).
- `GET /api/v1/tasks/{id}` - Görev detayını getirme.
- `PUT /api/v1/tasks/{id}` - Görev ayrıntılarını güncelleme.
- `PATCH /api/v1/tasks/{id}/assign` - Görevi bir kullanıcıya atama (`assigned_to_id`).
- `PATCH /api/v1/tasks/{id}/status` - Görev durumunu güncelleme (`TODO`, `IN_PROGRESS`, `DONE`).
- `PATCH /api/v1/tasks/{id}/dates` - Görev başlangıç (`start_date`) ve bitiş (`due_date`) tarihlerini ekleme/güncelleme.
- `DELETE /api/v1/tasks/{id}` - Görev silme.

### 3. Takvim & Gantt Endpoint'leri (`/api/v1/calendar`, `/api/v1/gantt`)
- `GET /api/v1/calendar/events` - Takvim görünümü için tarih içeren proje ve görev etkinlikleri.
- `GET /api/v1/gantt/timeline` - Gantt şeması için proje ve alt görev zaman çizelgesi verileri.

### 4. Raporlama API'leri (`/api/v1/reports`)
- `GET /api/v1/reports/projects/{id}/progress` - Proje ilerleme yüzdesi (% completed) ve görev sayıları.
- `GET /api/v1/reports/users/{id}/tasks-summary` - Kişi bazlı görev durumları ve başarı oranı.
- `GET /api/v1/reports/stats` - Günlük, haftalık ve aylık görev oluşturma/tamamlama istatistikleri.

## Kurulum ve Çalıştırma

```bash
# 1. backend dizinine geçin
cd backend

# 2. Sanal ortam oluşturun ve aktif edin
python -m venv venv
# Windows:
venv\Scripts\activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Sunucuyu başlatın
uvicorn app.main:app --reload
```

Interactive Swagger API Dokümantasyonu: `http://localhost:8000/docs`
