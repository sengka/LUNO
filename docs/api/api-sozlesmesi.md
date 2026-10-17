# LUNO · API Sözleşmesi

> Bu doküman backend ile frontend arasındaki anlaşmadır: hangi adrese ne gönderileceğini ve ne döneceğini tanımlar. Backend bu sözleşmeye göre uç noktaları yazar, frontend aynı anda bu sözleşmedeki örnek yanıtlarla (mock) ekranları geliştirir.
> **Sürüm:** v1.1 · **Kapsam:** Gereksinim dokümanı v4'teki 86 fonksiyonel gereksinim (FR-001 – FR-086) ve 54 user story (US-001 – US-054)
> **Değişiklik kuralı:** Sözleşmede değişiklik gerekirse önce ilgili frontend geliştiricisine haber verilir ve bu doküman PR ile güncellenir.

## Sürüm geçmişi

| Sürüm | Tarih | Değişiklik |
|---|---|---|
| v1.0 | 5 Ekim 2026 | İlk sürüm |
| v1.1 | 9 Ekim 2026 | Liste uç noktalarında arama parametresi `q` → `search`, sayfa boyutu `size` → `limit` (varsayılan 10). PR #88 ile uyum için |

## İçindekiler

1. Ortak kurallar
2. Veri nesneleri
3. Kimlik doğrulama ve hesap
4. Kullanıcılar ve roller
5. Projeler ve üyeler
6. Görevler
7. Kanban, takvim ve Gantt
8. Dosyalar ve yorumlar
9. Bildirimler
10. Dashboard ve raporlar
11. Sprintler ve kapasite
12. Akıllı özellikler
13. Yapay zekâ (LLM)
14. Arka plan işleri
15. Uç nokta özeti ve sprint eşlemesi

---

## 1. Ortak kurallar

### 1.1 Temel bilgiler

| Konu | Kural |
|---|---|
| Temel adres | Geliştirme: `http://localhost:8000/api/v1` · Canlı: `https://<render-adresi>/api/v1` |
| Veri formatı | JSON (`Content-Type: application/json`). Dosya yükleme `multipart/form-data` |
| Alan adları | `snake_case` |
| Kimlikler | Tam sayı (`"id": 12`) |
| Tarih | `YYYY-MM-DD` (ör. `"2026-10-15"`) |
| Tarih-saat | ISO 8601, UTC (ör. `"2026-10-05T09:30:00Z"`) |
| Boş değer | Değeri olmayan alanlar `null` döner, alan hiçbir zaman yanıttan çıkarılmaz |
| Dil | Hata ve bilgi mesajları Türkçe |
| Swagger | `http://localhost:8000/docs` (FastAPI otomatik üretir) |
| Sağlık kontrolü | `GET /health` → `200 {"status": "ok"}` (giriş gerekmez; Render ve demo öncesi kontrol için) |

### 1.2 Kimlik doğrulama

- Giriş yapıldığında backend bir **JWT erişim token'ı** döndürür. Token 24 saat geçerlidir (NFR-003).
- Korumalı tüm isteklerde başlık: `Authorization: Bearer <token>`
- Token yoksa, geçersizse veya süresi dolmuşsa **401** döner; frontend kullanıcıyı giriş sayfasına yönlendirir.
- Her uç noktanın yanında **Erişim** bilgisi vardır:
  - **Herkese açık:** Giriş gerekmez
  - **Giriş yapmış:** Her rol
  - **Proje üyesi:** İlgili projenin üyesi olan kullanıcı (FR-013)
  - **Yönetici:** Sistem rolü `YONETICI` olan ve ilgili projenin üyesi olan kullanıcı

### 1.3 Sabit değerler (enum)

| Alan | Değerler |
|---|---|
| Sistem rolü (`role`) | `YONETICI`, `EKIP_UYESI` |
| Görev durumu (`status`) | `ONAY_BEKLIYOR`, `REDDEDILDI`, `TODO`, `IN_PROGRESS`, `REVIEW_TESTING`, `DONE` |
| Öncelik (`priority`) | `DUSUK`, `ORTA`, `YUKSEK` |
| Efor puanı (`story_points`) | `1`, `2`, `3`, `5`, `8`, `13` |
| Risk seviyesi (`risk_level`) | `DUSUK`, `ORTA`, `YUKSEK` (Done görevlerde `null`) |
| Rapor dönemi (`period`) | `DAILY`, `WEEKLY`, `MONTHLY` |
| Dışa aktarım formatı (`format`) | `PDF`, `XLSX` |
| Tema (`theme`) | `LIGHT`, `DARK` |

**Aktif görev:** Durumu `TODO`, `IN_PROGRESS`, `REVIEW_TESTING` veya `DONE` olan görev. `ONAY_BEKLIYOR` ve `REDDEDILDI` görevler Kanban, takvim, Gantt ve raporlarda gösterilmez.

### 1.4 Durum kodları

| Kod | Ne zaman |
|---|---|
| 200 | Başarılı okuma veya güncelleme |
| 201 | Yeni kayıt oluşturuldu |
| 202 | İstek kabul edildi, işlem arka planda yapılacak |
| 204 | Başarılı, yanıt gövdesi yok (silme, çıkış) |
| 400 | İş kuralına aykırı istek (ör. bitiş tarihi başlangıçtan önce) |
| 401 | Giriş yapılmamış veya token geçersiz |
| 403 | Giriş yapılmış ama bu işlem için yetki yok |
| 404 | Kayıt bulunamadı |
| 409 | Çakışma (ör. e-posta zaten kayıtlı, kapasite aşımı onayı gerekli) |
| 413 | Dosya çok büyük |
| 415 | Desteklenmeyen dosya türü |
| 422 | Alan doğrulama hatası |
| 429 | Çok fazla istek |
| 503 | Dış servis (LLM) kullanılamıyor |

### 1.5 Hata formatı

Tüm hatalar aynı yapıda döner. Frontend `message`'ı kullanıcıya gösterir; `fields` doluysa her mesajı ilgili form alanının altında gösterir. Bazı hatalar ek bilgi için `details` taşır.

```json
{
  "error": {
    "code": "EMAIL_ALREADY_EXISTS",
    "message": "Bu e-posta adresi zaten kullanımda.",
    "fields": null,
    "details": null
  }
}
```

Alan doğrulama hatası (422):

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Lütfen hatalı alanları düzeltin.",
    "fields": {
      "password": "Şifre en az 8 karakter olmalıdır.",
      "full_name": "Ad soyad zorunludur."
    },
    "details": null
  }
}
```

**Ortak hata kodları**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 401 | `UNAUTHORIZED` | Oturumunuzun süresi doldu, lütfen tekrar giriş yapın. |
| 403 | `FORBIDDEN` | Bu işlem için yetkiniz yok. (FR-012) |
| 403 | `PROJECT_ACCESS_DENIED` | Bu projeye erişim yetkiniz yok. (FR-013) |
| 404 | `NOT_FOUND` | Aradığınız kayıt bulunamadı. |
| 422 | `VALIDATION_ERROR` | Lütfen hatalı alanları düzeltin. |
| 500 | `INTERNAL_ERROR` | Beklenmeyen bir hata oluştu. |

Modüle özel kodlar ilgili uç noktada yazılıdır.

### 1.6 Listeleme ve sayfalama

Liste döndüren uç noktalar `page` (varsayılan 1) ve `limit` (varsayılan 10, en fazla 100) parametrelerini kabul eder. Arama yapılabilen listelerde arama parametresi `search`'tür:

```json
{ "items": [], "total": 42, "page": 1, "limit": 10 }
```

---

## 2. Veri nesneleri

Uç noktalar aşağıdaki nesneleri döndürür. "Yanıt: **Task**" gibi ifadeler bu tanımlara işaret eder.

### User

```json
{
  "id": 7,
  "full_name": "Ayşe Yılmaz",
  "email": "ayse@ornek.com",
  "role": "EKIP_UYESI",
  "avatar_url": null,
  "theme": "LIGHT",
  "created_at": "2026-10-05T09:30:00Z"
}
```

**UserSummary** (başka nesnelerin içinde kullanılan kısa hali): `{ "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null }`

### Project

```json
{
  "id": 3,
  "name": "Mobil Uygulama",
  "description": "Müşteri için mobil uygulama geliştirme projesi",
  "start_date": "2026-10-05",
  "end_date": "2026-11-30",
  "progress_percent": 42.5,
  "member_count": 6,
  "created_by": { "id": 1, "full_name": "Sena Gül Kara", "avatar_url": null },
  "created_at": "2026-10-05T09:30:00Z",
  "updated_at": "2026-10-06T14:00:00Z"
}
```

`progress_percent`: Aktif ana görevler içinde `DONE` olanların yüzdesi (FR-061). Görev yoksa `0`.

### ProjectMember

```json
{
  "user": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
  "email": "ayse@ornek.com",
  "system_role": "EKIP_UYESI",
  "technical_role": "Frontend Geliştirici",
  "capacity_points": 13,
  "joined_at": "2026-10-05T10:00:00Z"
}
```

`capacity_points`: Kapasite sınırı tanımlanmamışsa `null` (FR-074).

### Task

```json
{
  "id": 42,
  "project_id": 3,
  "parent_id": null,
  "title": "Giriş ekranı",
  "description": "E-posta ve şifre ile giriş ekranı",
  "status": "IN_PROGRESS",
  "priority": "YUKSEK",
  "story_points": 5,
  "start_date": "2026-10-06",
  "due_date": "2026-10-10",
  "assignee": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
  "created_by": { "id": 1, "full_name": "Sena Gül Kara", "avatar_url": null },
  "sprint_id": 2,
  "labels": [ { "id": 1, "name": "frontend", "color": "#3A4CA0" } ],
  "subtask_count": 3,
  "subtask_done_count": 1,
  "depends_on": [40],
  "risk_level": "ORTA",
  "comment_count": 4,
  "file_count": 1,
  "created_at": "2026-10-05T11:00:00Z",
  "updated_at": "2026-10-07T09:00:00Z"
}
```

- `parent_id`: Alt görevse ana görevin `id`'si, değilse `null` (FR-038).
- `risk_level`: Görev `DONE` ise `null` (FR-072). Kurallar bölüm 12.1'de.
- `depends_on`: Bu görevin bağlı olduğu görevlerin `id` listesi (FR-040).

### Label

`{ "id": 1, "name": "frontend", "color": "#3A4CA0" }` (proje bazında tanımlanır)

### File

```json
{
  "id": 15,
  "name": "gereksinimler.pdf",
  "size_bytes": 482133,
  "mime_type": "application/pdf",
  "project_id": 3,
  "task_id": 42,
  "uploaded_by": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
  "comment_count": 0,
  "created_at": "2026-10-07T12:00:00Z"
}
```

`task_id`: Dosya doğrudan projeye yüklendiyse `null`.

### Comment

```json
{
  "id": 88,
  "body": "API hazır, ekranı bağlayabilirsin.",
  "author": { "id": 4, "full_name": "Emre Kaan Şensoy", "avatar_url": null },
  "task_id": 42,
  "file_id": null,
  "created_at": "2026-10-07T13:15:00Z"
}
```

Yorum ya göreve (`task_id`) ya da dosyaya (`file_id`) bağlıdır (FR-050).

### Notification

```json
{
  "id": 301,
  "type": "TASK_ASSIGNED",
  "message": "Sena Gül Kara size 'Giriş ekranı' görevini atadı.",
  "project_id": 3,
  "task_id": 42,
  "is_read": false,
  "created_at": "2026-10-07T09:00:00Z"
}
```

| `type` | Ne zaman | FR |
|---|---|---|
| `TASK_ASSIGNED` | Kullanıcıya görev atandığında | FR-052 |
| `COMMENT_ADDED` | Kullanıcının görevine veya dahil olduğu yorum zincirine yorum eklendiğinde | FR-054 |
| `DUE_DATE_SOON` | Teslim tarihine 2 gün veya daha az kaldığında | FR-056 |
| `TASK_STALE` | Görev 4 gündür güncellenmediğinde | FR-057 |
| `TASK_PENDING_APPROVAL` | Ekip üyesi görev önerdiğinde (yöneticilere) | FR-051 |
| `TASK_APPROVED`, `TASK_REJECTED` | Önerilen görev onaylandığında / reddedildiğinde (öneren kişiye) | FR-051 |

### Sprint

```json
{
  "id": 2,
  "project_id": 3,
  "name": "Sprint 2",
  "goal": "Giriş sistemi çalışsın",
  "start_date": "2026-10-05",
  "end_date": "2026-10-11",
  "capacity_points": 40,
  "total_points": 12,
  "done_points": 5,
  "progress_percent": 41.7,
  "is_active": true
}
```

`progress_percent`: `done_points / total_points × 100` (FR-068). `is_active`: Bugün sprint tarihleri arasındaysa `true`.

---

## 3. Kimlik doğrulama ve hesap

### 3.1 Kayıt ol
`POST /auth/register` · Herkese açık · US-001 · FR-001 – FR-004 · Sprint 2

**İstek**
```json
{ "full_name": "Ayşe Yılmaz", "email": "ayse@ornek.com", "password": "Guclu1234" }
```

| Alan | Kural |
|---|---|
| `full_name` | Zorunlu, 2–100 karakter |
| `email` | Zorunlu, geçerli e-posta |
| `password` | Zorunlu, en az 8 karakter |

**Yanıt · 201:** **User** (rol her zaman `EKIP_UYESI`, FR-010). Frontend "Kayıt başarılı" mesajı gösterip giriş sayfasına yönlendirir (FR-002).

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 409 | `EMAIL_ALREADY_EXISTS` | Bu e-posta adresi zaten kullanımda. | FR-003 |
| 422 | `VALIDATION_ERROR` | Lütfen hatalı alanları düzeltin. (`fields` ile) | FR-004 |

### 3.2 Giriş yap
`POST /auth/login` · Herkese açık · US-002 · FR-005, FR-006 · Sprint 2

**İstek:** `{ "email": "ayse@ornek.com", "password": "Guclu1234" }`

**Yanıt · 200**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "user": { "id": 7, "full_name": "Ayşe Yılmaz", "email": "ayse@ornek.com", "role": "EKIP_UYESI", "avatar_url": null, "theme": "LIGHT", "created_at": "2026-10-05T09:30:00Z" }
}
```

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 401 | `INVALID_CREDENTIALS` | E-posta veya şifre hatalı. | FR-006 |
| 422 | `VALIDATION_ERROR` | Lütfen hatalı alanları düzeltin. | — |

Güvenlik için kayıtsız e-posta ve yanlış şifre **aynı** mesajı döndürür.

### 3.3 Çıkış yap
`POST /auth/logout` · Giriş yapmış · US-003 · FR-007 · Sprint 2

**Yanıt · 204.** Backend token'ı geçersizler listesine ekler; aynı token ile sonraki istekler 401 döner. Frontend token'ı siler ve giriş sayfasına yönlendirir.

### 3.4 Oturumdaki kullanıcı
`GET /auth/me` · Giriş yapmış · US-002 · Sprint 2

**Yanıt · 200:** **User**. Uygulama açılışında ve sayfa yenilendiğinde oturumu ve rolü doğrulamak için kullanılır.

### 3.5 Profili ve temayı düzenle
`PATCH /auth/me` · Giriş yapmış · US-028, US-049 · FR-009, FR-065 · Sprint 8 (tema Sprint 9)

**İstek** (gönderilen alanlar güncellenir): `{ "full_name": "Ayşe Yılmaz Demir", "theme": "DARK" }`

**Yanıt · 200:** **User** · Hatalar: 422 `VALIDATION_ERROR`

### 3.6 Profil fotoğrafı yükle
`PUT /auth/me/avatar` · Giriş yapmış · US-028 · FR-009 · Sprint 8

**İstek:** `multipart/form-data`, alan adı `file`. PNG veya JPG, en fazla 2 MB.

**Yanıt · 200:** **User** (güncel `avatar_url` ile)

| Kod | `error.code` | Mesaj |
|---|---|---|
| 413 | `FILE_TOO_LARGE` | Profil fotoğrafı en fazla 2 MB olabilir. |
| 415 | `UNSUPPORTED_FILE_TYPE` | Profil fotoğrafı PNG veya JPG olmalıdır. |

### 3.7 Şifremi unuttum
`POST /auth/password/forgot` · Herkese açık · US-027 · FR-008 · Sprint 8

**İstek:** `{ "email": "ayse@ornek.com" }`

**Yanıt · 202:** `{ "message": "E-posta adresiniz kayıtlıysa şifre yenileme bağlantısı gönderildi." }`

E-posta kayıtlı olsun olmasın aynı yanıt döner. Kayıtlıysa 30 dakika geçerli bir bağlantı gönderilir: `https://<frontend>/sifre-yenile?token=...`

### 3.8 Şifreyi yenile
`POST /auth/password/reset` · Herkese açık · US-027 · FR-008 · Sprint 8

**İstek:** `{ "token": "c2lmcmUt...", "new_password": "YeniSifre123" }`

**Yanıt · 204**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `RESET_TOKEN_INVALID` | Şifre yenileme bağlantısı geçersiz veya süresi dolmuş. |
| 422 | `VALIDATION_ERROR` | Şifre en az 8 karakter olmalıdır. |

---

## 4. Kullanıcılar ve roller

### 4.1 Kullanıcıları listele
`GET /users?search=ayse&page=1&limit=10` · Yönetici · US-004, US-010 · Sprint 2

`search`: Ad veya e-postada arama (isteğe bağlı, büyük/küçük harf duyarsız). Rol değiştirme ve projeye üye ekleme ekranlarında kullanılır.

**Yanıt · 200:** Sayfalı **User** listesi · Hatalar: 403 `FORBIDDEN` (FR-012)

### 4.2 Sistem rolünü değiştir
`PATCH /users/{user_id}/role` · Yönetici · US-004 · FR-011 · Sprint 2

**İstek:** `{ "role": "YONETICI" }`

**Yanıt · 200:** **User**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `CANNOT_CHANGE_OWN_ROLE` | Kendi rolünüzü değiştiremezsiniz. |
| 403 | `FORBIDDEN` | Bu işlem için yetkiniz yok. |
| 404 | `USER_NOT_FOUND` | Kullanıcı bulunamadı. |
| 422 | `VALIDATION_ERROR` | Geçersiz rol değeri. |

---

## 5. Projeler ve üyeler

### 5.1 Projelerimi listele
`GET /projects?page=1&limit=10` · Giriş yapmış · US-007 · FR-017 · Sprint 3

**Yanıt · 200:** Sayfalı **Project** listesi. **Yalnızca kullanıcının üyesi olduğu projeler** döner.

### 5.2 Proje oluştur
`POST /projects` · Sistem rolü Yönetici · US-006 · FR-015, FR-016 · Sprint 3

**İstek**
```json
{
  "name": "Mobil Uygulama",
  "description": "Müşteri için mobil uygulama geliştirme projesi",
  "start_date": "2026-10-05",
  "end_date": "2026-11-30"
}
```

| Alan | Kural |
|---|---|
| `name` | Zorunlu, 2–100 karakter |
| `description` | İsteğe bağlı, en fazla 2000 karakter |
| `start_date`, `end_date` | Zorunlu |

**Yanıt · 201:** **Project**. Oluşturan yönetici otomatik olarak projenin üyesi olur.

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 400 | `INVALID_DATE_RANGE` | Bitiş tarihi başlangıç tarihinden önce olamaz. | FR-016 |
| 403 | `FORBIDDEN` | Bu işlem için yetkiniz yok. | FR-012 |
| 422 | `VALIDATION_ERROR` | Lütfen hatalı alanları düzeltin. | — |

### 5.3 Proje detayı
`GET /projects/{project_id}` · Proje üyesi · US-022 · FR-013, FR-061 · Sprint 3

**Yanıt · 200:** **Project** · Hatalar: 403 `PROJECT_ACCESS_DENIED`, 404 `PROJECT_NOT_FOUND`

### 5.4 Projeyi düzenle
`PATCH /projects/{project_id}` · Yönetici · US-008 · FR-018 · Sprint 3

**İstek:** `name`, `description`, `start_date`, `end_date` alanlarından gönderilenler güncellenir.

**Yanıt · 200:** **Project** · Hatalar: 400 `INVALID_DATE_RANGE`, 403 `FORBIDDEN`, 404 `PROJECT_NOT_FOUND`

### 5.5 Projeyi sil
`DELETE /projects/{project_id}` · Yönetici · US-009 · FR-019, FR-020 · Sprint 3

Onay penceresi (FR-019) frontend'de gösterilir; kullanıcı onaylayınca bu istek atılır. Projeye bağlı görevler, dosyalar, yorumlar ve sprintler de silinir.

**Yanıt · 204** · Hatalar: 403 `FORBIDDEN`, 404 `PROJECT_NOT_FOUND`

### 5.6 Proje üyelerini listele
`GET /projects/{project_id}/members` · Proje üyesi · US-010, US-029 · FR-014 · Sprint 3

**Yanıt · 200:** **ProjectMember** listesi (sayfasız). Sistem rolü ve teknik rol birlikte döner.

### 5.7 Projeye üye ekle (e-posta ile)
`POST /projects/{project_id}/members` · Yönetici · US-010 · FR-021 · Sprint 3

**İstek:** `{ "email": "can@ornek.com", "technical_role": "Backend Geliştirici" }` (`technical_role` isteğe bağlı)

**Yanıt · 201:** **ProjectMember**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 404 | `USER_NOT_FOUND` | Bu e-posta ile kayıtlı kullanıcı bulunamadı. |
| 409 | `ALREADY_MEMBER` | Bu kullanıcı zaten projenin üyesi. |

### 5.8 Davet bağlantısı oluştur
`POST /projects/{project_id}/invites` · Yönetici · US-010 · FR-021 · Sprint 3

**Yanıt · 201**
```json
{ "invite_url": "https://<frontend>/davet/5f2c9a...", "expires_at": "2026-10-12T10:00:00Z" }
```

Bağlantı 7 gün geçerlidir.

### 5.9 Daveti kabul et
`POST /invites/{token}/accept` · Giriş yapmış · US-010 · FR-021 · Sprint 3

Davet bağlantısını açan kullanıcı giriş yapmamışsa frontend önce giriş veya kayıt ekranına yönlendirir, ardından bu isteği atar.

**Yanıt · 200:** **Project**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `INVITE_INVALID` | Davet bağlantısı geçersiz veya süresi dolmuş. |
| 409 | `ALREADY_MEMBER` | Zaten bu projenin üyesisiniz. |

### 5.10 Üyeyi projeden çıkar
`DELETE /projects/{project_id}/members/{user_id}` · Yönetici · US-010 · FR-022 · Sprint 3

Onay penceresi frontend'de gösterilir. Çıkarılan üyeye atanmış görevlerin `assignee` alanı `null` yapılır.

**Yanıt · 204**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `CANNOT_REMOVE_SELF` | Kendinizi projeden çıkaramazsınız. |
| 404 | `MEMBER_NOT_FOUND` | Bu kullanıcı projenin üyesi değil. |

### 5.11 Üyenin teknik rolünü ve kapasitesini güncelle
`PATCH /projects/{project_id}/members/{user_id}` · Yönetici · US-025, US-029 · FR-023, FR-075 · Sprint 7 (teknik rol Sprint 8)

**İstek** (gönderilen alanlar güncellenir): `{ "technical_role": "Frontend Geliştirici", "capacity_points": 13 }`

`capacity_points: null` gönderilirse kapasite sınırı kaldırılır.

**Yanıt · 200:** **ProjectMember** · Hatalar: 404 `MEMBER_NOT_FOUND`, 422 `VALIDATION_ERROR`

---

## 6. Görevler

### 6.1 Görevleri listele ve filtrele
`GET /projects/{project_id}/tasks` · Proje üyesi · US-034 · FR-041 · Sprint 4 (filtreler Sprint 8)

| Parametre | Açıklama |
|---|---|
| `search` | Görev adında arama |
| `assignee_id` | Atanan kişi |
| `status` | Durum (virgülle birden fazla: `TODO,IN_PROGRESS`) |
| `priority` | Öncelik |
| `label_id` | Etiket |
| `sprint_id` | Sprint |
| `parent_id` | Alt görevleri getirmek için ana görev `id`'si. Gönderilmezse sadece ana görevler döner |
| `include_pending` | `true` ise `ONAY_BEKLIYOR` ve `REDDEDILDI` görevler de döner (varsayılan `false`) |
| `page`, `limit` | Sayfalama |

**Yanıt · 200:** Sayfalı **Task** listesi

### 6.2 Görev oluştur
`POST /projects/{project_id}/tasks` · Proje üyesi · US-011, US-030, US-032, US-033 · FR-024 – FR-026, FR-035 – FR-038 · Sprint 4

**İstek**
```json
{
  "title": "Giriş ekranı",
  "description": "E-posta ve şifre ile giriş ekranı",
  "assignee_id": 7,
  "start_date": "2026-10-06",
  "due_date": "2026-10-10",
  "priority": "YUKSEK",
  "story_points": 5,
  "label_ids": [1],
  "sprint_id": 2,
  "confirm_over_capacity": false
}
```

| Alan | Kural |
|---|---|
| `title` | Zorunlu, 2–200 karakter |
| Diğer alanlar | İsteğe bağlı |
| `story_points` | Yalnızca 1, 2, 3, 5, 8, 13 (FR-036) |
| `assignee_id` | Proje üyesi olmalı |

**Rol kuralı:**
- **Yönetici** oluşturursa görev `TODO` durumunda kaydedilir.
- **Ekip üyesi** oluşturursa görev `ONAY_BEKLIYOR` durumunda kaydedilir, `assignee_id` yok sayılır ve projenin yöneticilerine `TASK_PENDING_APPROVAL` bildirimi gider (FR-026).
- `assignee_id` gönderildiyse kapasite kontrolü yapılır (bkz. 6.6).

**Yanıt · 201:** **Task**

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 400 | `INVALID_DATE_RANGE` | Teslim tarihi başlangıç tarihinden önce olamaz. | FR-025 |
| 400 | `ASSIGNEE_NOT_MEMBER` | Atanan kişi projenin üyesi değil. | — |
| 409 | `CAPACITY_EXCEEDED` | bkz. 6.6 | FR-073 |
| 422 | `VALIDATION_ERROR` | Görev başlığı zorunludur. / Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır. | FR-025, FR-036 |

### 6.3 Görev detayı
`GET /tasks/{task_id}` · Proje üyesi · Sprint 4

**Yanıt · 200:** **Task** · Hatalar: 403 `PROJECT_ACCESS_DENIED`, 404 `TASK_NOT_FOUND`

### 6.4 Görevi düzenle
`PATCH /tasks/{task_id}` · Yönetici · US-013, US-032, US-033, US-046 · FR-031, FR-035 – FR-037, FR-039 · Sprint 4

**İstek:** `title`, `description`, `start_date`, `due_date`, `priority`, `story_points`, `label_ids`, `sprint_id` alanlarından gönderilenler güncellenir. Atama için 6.6, durum için 6.5 kullanılır.

**Yanıt · 200:** **Task** · Hatalar: 6.2 ile aynı, ek olarak 403 `FORBIDDEN`, 404 `TASK_NOT_FOUND`

### 6.5 Görev durumunu değiştir
`PATCH /tasks/{task_id}/status` · Görevin atandığı kişi veya Yönetici · US-014, US-015 · FR-033, FR-034, FR-043 · Sprint 4

Kanban'da sürükle-bırak da bu uç noktayı kullanır.

**İstek:** `{ "status": "REVIEW_TESTING" }` (`TODO`, `IN_PROGRESS`, `REVIEW_TESTING`, `DONE`)

**Yanıt · 200:** **Task**

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 400 | `TASK_NOT_ACTIVE` | Onay bekleyen veya reddedilen görevin durumu değiştirilemez. | — |
| 403 | `NOT_TASK_ASSIGNEE` | Size atanmamış bir görevin durumunu değiştiremezsiniz. | FR-034 |

Frontend 403 aldığında kartı Kanban'da eski sütununa geri döndürür.

### 6.6 Görevi ata
`PATCH /tasks/{task_id}/assignee` · Yönetici · US-012, US-025, US-044 · FR-030, FR-052, FR-053, FR-073, FR-074 · Sprint 4 (kapasite kontrolü Sprint 7)

**İstek:** `{ "assignee_id": 7, "confirm_over_capacity": false }`

**Kapasite kontrolü (FR-073, FR-074):**
1. Kişinin `DONE` olmayan görevlerinin toplam `story_points`'i ile bu görevin puanının toplamı kişinin `capacity_points`'ini aşıyorsa ve `confirm_over_capacity` `false` ise atama **yapılmaz**, 409 döner.
2. Frontend uyarıyı gösterir. Yönetici "Yine de ata" derse aynı istek `confirm_over_capacity: true` ile tekrar gönderilir.
3. Kişinin kapasitesi tanımlı değilse (`null`) kontrol yapılmaz, uyarı verilmez.

**Yanıt · 200:** **Task**. Atanan kişiye `TASK_ASSIGNED` bildirimi, e-posta tercihi açıksa e-posta gönderilir.

**409 örneği**
```json
{
  "error": {
    "code": "CAPACITY_EXCEEDED",
    "message": "Ayşe Yılmaz'ın kapasitesi aşılacak (16 / 13 puan).",
    "fields": null,
    "details": {
      "user": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
      "current_points": 11,
      "task_points": 5,
      "total_points": 16,
      "capacity_points": 13,
      "suggested_members": [
        { "user": { "id": 9, "full_name": "Can Demir", "avatar_url": null }, "total_points": 6, "capacity_points": 13 }
      ]
    }
  }
}
```

`suggested_members`: Kapasitesi uygun üyeler (US-050). Sprint 9'a kadar boş liste dönebilir.

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `ASSIGNEE_NOT_MEMBER` | Atanan kişi projenin üyesi değil. |
| 409 | `CAPACITY_EXCEEDED` | (yukarıdaki gibi) |

### 6.7 Görevi sil
`DELETE /tasks/{task_id}` · Yönetici · US-013 · FR-032 · Sprint 4

Onay penceresi frontend'de gösterilir. Alt görevler, yorumlar ve dosyalar da silinir.

**Yanıt · 204** · Hatalar: 403 `FORBIDDEN`, 404 `TASK_NOT_FOUND`

### 6.8 Önerilen görevi onayla
`POST /tasks/{task_id}/approve` · Yönetici · US-031 · FR-027, FR-028 · Sprint 8

**İstek** (isteğe bağlı düzenlemelerle): `{ "title": "Rapor ekranı", "priority": "ORTA", "story_points": 3 }`

Görev `TODO` durumuna geçer, öneren kişiye `TASK_APPROVED` bildirimi gider.

**Yanıt · 200:** **Task** · Hatalar: 400 `TASK_NOT_PENDING` (Görev onay beklemiyor.)

### 6.9 Önerilen görevi reddet
`POST /tasks/{task_id}/reject` · Yönetici · US-031 · FR-027, FR-029 · Sprint 8

**İstek:** `{ "reason": "Bu iş Sprint 5 kapsamında yapılacak." }` (isteğe bağlı)

Görev `REDDEDILDI` durumuna geçer, öneren kişiye `TASK_REJECTED` bildirimi gider.

**Yanıt · 200:** **Task** · Hatalar: 400 `TASK_NOT_PENDING`

### 6.10 Alt görev ekle
`POST /tasks/{task_id}/subtasks` · Proje üyesi · US-033, US-046 · FR-038, FR-039 · Sprint 4

**İstek:** 6.2 ile aynı alanlar. `parent_id` otomatik atanır. Alt görevin alt görevi olamaz.

**Yanıt · 201:** **Task** · Hatalar: 400 `NESTED_SUBTASK_NOT_ALLOWED` (Alt görevlere alt görev eklenemez.)

### 6.11 Etiketleri listele / oluştur
`GET /projects/{project_id}/labels` · `POST /projects/{project_id}/labels` · Proje üyesi · US-033 · FR-037 · Sprint 4

**İstek:** `{ "name": "frontend", "color": "#3A4CA0" }`

**Yanıt:** 200 **Label** listesi / 201 **Label** · Hatalar: 409 `LABEL_EXISTS` (Bu etiket zaten var.)

### 6.12 Bağımlılık ekle / kaldır
`POST /tasks/{task_id}/dependencies` · `DELETE /tasks/{task_id}/dependencies/{depends_on_id}` · Yönetici · US-047 · FR-040 · Sprint 9

**İstek:** `{ "depends_on_id": 40 }` ("Bu görev, 40 numaralı görev bitmeden başlayamaz.")

**Yanıt:** 201 **Task** / 204

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `CIRCULAR_DEPENDENCY` | Bu bağımlılık döngü oluşturur. |
| 400 | `DIFFERENT_PROJECT` | Bağımlılık yalnızca aynı projedeki görevler arasında kurulabilir. |

---

## 7. Kanban, takvim ve Gantt

### 7.1 Kanban panosu
`GET /projects/{project_id}/board?sprint_id=2` · Proje üyesi · US-015 · FR-042 · Sprint 4

`sprint_id` isteğe bağlı. Yalnızca aktif ana görevler döner.

**Yanıt · 200**
```json
{
  "columns": [
    { "status": "TODO", "tasks": [] },
    { "status": "IN_PROGRESS", "tasks": [] },
    { "status": "REVIEW_TESTING", "tasks": [] },
    { "status": "DONE", "tasks": [] }
  ]
}
```

`tasks` dizileri **Task** nesneleri içerir. Kart taşıma için 6.5 kullanılır.

### 7.2 Takvim
`GET /projects/{project_id}/calendar?from=2026-10-01&to=2026-10-31` · Proje üyesi · US-016 · FR-044 · Sprint 5

`from` ve `to` zorunlu, aralık en fazla 93 gün. Başlangıç veya teslim tarihi bu aralıkta olan aktif görevler döner.

**Yanıt · 200**
```json
{
  "events": [
    {
      "task_id": 42,
      "title": "Giriş ekranı",
      "start_date": "2026-10-06",
      "due_date": "2026-10-10",
      "status": "IN_PROGRESS",
      "assignee": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null }
    }
  ]
}
```

Hatalar: 400 `INVALID_DATE_RANGE`

### 7.3 Gantt şeması
`GET /projects/{project_id}/gantt` · Proje üyesi · US-017 · FR-045 · Sprint 5

Başlangıç ve teslim tarihi olan aktif görevler, alt görevleri ve bağımlılıklarıyla döner.

**Yanıt · 200**
```json
{
  "project": { "start_date": "2026-10-05", "end_date": "2026-11-30" },
  "items": [
    {
      "task_id": 42,
      "title": "Giriş ekranı",
      "start_date": "2026-10-06",
      "due_date": "2026-10-10",
      "progress_percent": 33.3,
      "status": "IN_PROGRESS",
      "parent_id": null,
      "depends_on": [40]
    }
  ]
}
```

`progress_percent`: Alt görevi varsa tamamlanan alt görev oranı; yoksa `DONE` ise 100, değilse 0.

---

## 8. Dosyalar ve yorumlar

### 8.1 Dosya yükle
`POST /projects/{project_id}/files` · Proje üyesi · US-018 · FR-046, FR-047 · Sprint 5

**İstek:** `multipart/form-data`
- `file`: Dosya (zorunlu)
- `task_id`: Göreve yükleniyorsa görev `id`'si (isteğe bağlı)

**Kurallar:** PDF, DOCX, XLSX, PPTX, PNG, JPG veya TXT; en fazla 10 MB. Uzantı ve içerik türü (MIME) birlikte kontrol edilir (NFR-006).

**Yanıt · 201:** **File**

| Kod | `error.code` | Mesaj | FR |
|---|---|---|---|
| 413 | `FILE_TOO_LARGE` | Dosya en fazla 10 MB olabilir. | FR-047 |
| 415 | `UNSUPPORTED_FILE_TYPE` | Desteklenen formatlar: PDF, DOCX, XLSX, PPTX, PNG, JPG, TXT. | FR-047 |

### 8.2 Dosyaları listele
`GET /projects/{project_id}/files?task_id=42` · Proje üyesi · US-018 · Sprint 5

`task_id` gönderilirse yalnızca o görevin dosyaları döner.

**Yanıt · 200:** Sayfalı **File** listesi

### 8.3 Dosya indir
`GET /files/{file_id}/download` · Proje üyesi · US-019 · FR-048 · Sprint 5

**Yanıt · 200:** Dosyanın kendisi (`Content-Disposition: attachment; filename="..."`) · Hatalar: 403 `PROJECT_ACCESS_DENIED`, 404 `FILE_NOT_FOUND`

### 8.4 Dosya sil
`DELETE /files/{file_id}` · Dosyayı yükleyen kişi veya Yönetici · US-035 · FR-049 · Sprint 5

Onay penceresi frontend'de gösterilir. Dosyaya ait yorumlar da silinir.

**Yanıt · 204** · Hatalar: 403 `FORBIDDEN`, 404 `FILE_NOT_FOUND`

### 8.5 Görev yorumlarını listele / yorum ekle
`GET /tasks/{task_id}/comments?page=1&limit=50` · `POST /tasks/{task_id}/comments` · Proje üyesi · US-020, US-037 · FR-050, FR-054 · Sprint 5

**İstek:** `{ "body": "API hazır, ekranı bağlayabilirsin." }` (1–2000 karakter)

**Yanıt:** 200 sayfalı **Comment** listesi (eskiden yeniye) / 201 **Comment**

Yorum eklenince görevin atandığı kişiye ve daha önce yorum yazmış kişilere (yazan hariç) `COMMENT_ADDED` bildirimi gider.

### 8.6 Dosya yorumlarını listele / yorum ekle
`GET /files/{file_id}/comments` · `POST /files/{file_id}/comments` · Proje üyesi · US-020 · FR-050 · Sprint 5

8.5 ile aynı yapı.

---

## 9. Bildirimler

### 9.1 Bildirimleri listele
`GET /notifications?unread_only=true&page=1&limit=20` · Giriş yapmış · US-021 · FR-051 · Sprint 6

**Yanıt · 200:** Sayfalı **Notification** listesi (yeniden eskiye) ve okunmamış sayısı:

```json
{ "items": [], "total": 12, "page": 1, "limit": 20, "unread_count": 3 }
```

Frontend üst bardaki bildirim simgesini güncellemek için bu uç noktayı 30 saniyede bir çağırır (polling).

### 9.2 Bildirimi okundu işaretle
`PATCH /notifications/{notification_id}/read` · Giriş yapmış · Sprint 6

**Yanıt · 200:** **Notification**

### 9.3 Tümünü okundu işaretle
`POST /notifications/read-all` · Giriş yapmış · Sprint 6

**Yanıt · 204**

### 9.4 Bildirim tercihlerini getir / güncelle
`GET /notifications/preferences` · `PATCH /notifications/preferences` · Giriş yapmış · US-036, US-048 · FR-053, FR-058, FR-059 · Sprint 8

```json
{ "in_app_enabled": true, "email_enabled": false, "weekly_summary_enabled": false }
```

**Yanıt · 200:** Güncel tercihler

---

## 10. Dashboard ve raporlar

### 10.1 Dashboard
`GET /dashboard` · Giriş yapmış · US-022 · FR-060 · Sprint 6

**Yanıt · 200**
```json
{
  "projects": [
    { "id": 3, "name": "Mobil Uygulama", "progress_percent": 42.5, "my_open_tasks": 4 }
  ],
  "my_task_counts": { "TODO": 3, "IN_PROGRESS": 2, "REVIEW_TESTING": 1, "DONE": 8 },
  "upcoming_tasks": [],
  "unread_notification_count": 3
}
```

`upcoming_tasks`: Kullanıcıya atanmış, teslim tarihi en yakın 5 aktif **Task**.

### 10.2 Kişi bazlı rapor
`GET /projects/{project_id}/reports/members?sprint_id=2` · Yönetici · US-023 · FR-062 · Sprint 6

**Yanıt · 200**
```json
{
  "members": [
    {
      "user": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
      "counts": { "TODO": 2, "IN_PROGRESS": 1, "REVIEW_TESTING": 0, "DONE": 5 },
      "done_points": 18
    }
  ]
}
```

### 10.3 Dönemsel rapor
`GET /projects/{project_id}/reports/period?period=WEEKLY&date=2026-10-07` · Yönetici · US-023 · FR-063 · Sprint 6

`date`: Raporun ait olduğu gün, hafta veya ayın içindeki herhangi bir tarih (varsayılan bugün).

**Yanıt · 200**
```json
{
  "period": "WEEKLY",
  "from": "2026-10-05",
  "to": "2026-10-11",
  "completed_count": 7,
  "created_count": 10,
  "series": [
    { "date": "2026-10-05", "completed": 1, "created": 4 },
    { "date": "2026-10-06", "completed": 2, "created": 1 }
  ]
}
```

`series`: Grafik için gün bazında dağılım.

### 10.4 Raporu dışa aktar
`GET /projects/{project_id}/reports/export?report=MEMBERS&format=PDF` · Yönetici · US-039 · FR-064 · Sprint 9

| Parametre | Değerler |
|---|---|
| `report` | `MEMBERS` veya `PERIOD` |
| `format` | `PDF` veya `XLSX` |
| `period`, `date`, `sprint_id` | İlgili rapordaki gibi |

**Yanıt · 200:** Dosyanın kendisi (`application/pdf` veya `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

---

## 11. Sprintler ve kapasite

### 11.1 Sprintleri listele / sprint oluştur
`GET /projects/{project_id}/sprints` · Proje üyesi · US-040 · Sprint 6
`POST /projects/{project_id}/sprints` · Yönetici · US-040 · FR-066 · Sprint 6

**İstek**
```json
{
  "name": "Sprint 2",
  "goal": "Giriş sistemi çalışsın",
  "start_date": "2026-10-05",
  "end_date": "2026-10-11",
  "capacity_points": 40
}
```

**Yanıt:** 200 **Sprint** listesi / 201 **Sprint**

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `INVALID_DATE_RANGE` | Bitiş tarihi başlangıç tarihinden önce olamaz. |
| 400 | `SPRINT_OVERLAP` | Bu tarihler başka bir sprintle çakışıyor. |

### 11.2 Sprint detayı, düzenleme ve silme
`GET /sprints/{sprint_id}` · Proje üyesi · US-041 · FR-068 · Sprint 6
`PATCH /sprints/{sprint_id}` · `DELETE /sprints/{sprint_id}` · Yönetici · US-040, US-025 · FR-066, FR-075 · Sprint 6

`GET` yanıtı sprint ilerlemesini (`total_points`, `done_points`, `progress_percent`) içerir. Silinen sprintteki görevlerin `sprint_id`'si `null` yapılır. `capacity_points: null` sprint kapasitesini kaldırır.

**Yanıt:** 200 **Sprint** / 204

### 11.3 Görevleri sprinte ekle / çıkar
`POST /sprints/{sprint_id}/tasks` · `DELETE /sprints/{sprint_id}/tasks/{task_id}` · Yönetici · US-040 · FR-067 · Sprint 6

**İstek:** `{ "task_ids": [42, 43, 44] }`

**Yanıt:** 200 **Sprint** (güncel puanlarla) ve `"capacity_warning": true/false` alanı / 204

Sprint kapasitesi tanımlıysa ve görevlerle `total_points` kapasiteyi aşacaksa görevler yine eklenir, ancak `capacity_warning: true` döner; frontend uyarı gösterir.

---

## 12. Akıllı özellikler

### 12.1 Gecikme risk seviyesi
US-024, US-043 · FR-070 – FR-072 · Sprint 7

Risk seviyesi her **Task** nesnesinde `risk_level` alanında döner; ayrı bir istek gerekmez.

1. Görev `DONE` ise `risk_level` = `null` (FR-072).
2. Teslim tarihi geçmiş ve görev `DONE` değilse `risk_level` = `YUKSEK` (FR-071).
3. Teslim tarihi yoksa `null`.
4. Diğer durumlarda seviye; teslim tarihine kalan süre, durum, alt görev tamamlanma oranı, efor puanı ve atanan kişinin aktif görev yükü kullanılarak hesaplanır (FR-070). Eşikler ve formül Sprint 7'de belirlenip bu bölüme eklenecektir.

### 12.2 Riskli görevler
`GET /projects/{project_id}/risks?level=ORTA` · Proje üyesi · US-024 · Sprint 7

**Yanıt · 200:** `risk_level`'ı belirtilen seviyede veya üstünde olan **Task** listesi (en riskliden aza)

### 12.3 Bugün ne yapmalıyım?
`GET /me/today` · Giriş yapmış · US-042 · FR-069 · Sprint 7

Kullanıcıya atanmış, `DONE` olmayan ve teslim tarihine 3 gün veya daha az kalmış ya da tarihi geçmiş görevler; önce teslim tarihine, sonra önceliğe göre sıralı.

**Yanıt · 200:** **Task** listesi (tüm projelerden)

### 12.4 Proje iş yükü ve dağılım önerisi
`GET /projects/{project_id}/workload` · Yönetici · US-025, US-050 · FR-073, FR-076 · Sprint 7 (öneriler Sprint 9)

**Yanıt · 200**
```json
{
  "members": [
    {
      "user": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
      "open_points": 16,
      "capacity_points": 13,
      "is_over_capacity": true
    }
  ],
  "suggestions": [
    {
      "task_id": 51,
      "task_title": "Rapor ekranı",
      "from_user": { "id": 7, "full_name": "Ayşe Yılmaz", "avatar_url": null },
      "to_user": { "id": 9, "full_name": "Can Demir", "avatar_url": null }
    }
  ]
}
```

Öneriler yalnızca öneridir; uygulanması için yönetici 6.6 ile atamayı değiştirir.

---

## 13. Yapay zekâ (LLM)

### 13.1 Ortak kurallar

- **Hiçbir LLM uç noktası veritabanına yazmaz** (FR-078, FR-086). Uç noktalar yalnızca **öneri** döndürür. Kullanıcı öneriyi onaylarsa frontend normal uç noktaları (ör. 6.2 Görev oluştur) çağırır.
- Backend önce birincil servise (Groq) gider; 10 saniye içinde yanıt alamazsa yedek servise (Gemini) geçer (FR-083).
- İki servis de yanıt vermezse **503** döner (FR-084):
  ```json
  { "error": { "code": "LLM_UNAVAILABLE", "message": "Yapay zekâ özelliği şu an kullanılamıyor. Lütfen daha sonra tekrar deneyin.", "fields": null, "details": null } }
  ```
- Kullanıcı başına dakikada en fazla 10 LLM isteği yapılabilir. Aşılırsa **429** `RATE_LIMITED` (Çok fazla istek gönderdiniz, lütfen biraz bekleyin.)
- Yanıtlarda kullanılan servis `"provider": "groq"` veya `"gemini"` olarak döner.

### 13.2 Toplantı notundan görev çıkar
`POST /ai/projects/{project_id}/extract-tasks` · Yönetici · US-051 · FR-077 · Sprint 9

**İstek:** `{ "text": "Can API'yi cumaya kadar yapacak. Ayşe giriş ekranını tasarlayacak..." }` (en fazla 5000 karakter)

**Yanıt · 200**
```json
{
  "provider": "groq",
  "suggestions": [
    { "title": "API geliştirme", "assignee_id": 9, "assignee_name": "Can Demir", "due_date": "2026-10-09" },
    { "title": "Giriş ekranı tasarımı", "assignee_id": null, "assignee_name": "Ayşe", "due_date": null }
  ]
}
```

Kişi adı projede bulunamazsa veya birden fazla eşleşme varsa `assignee_id` `null` döner; frontend kullanıcıdan kişiyi seçmesini ister.

### 13.3 Alt görev önerisi
`POST /ai/tasks/{task_id}/suggest-subtasks` · Yönetici · US-052 · FR-079 · Sprint 9

**Yanıt · 200:** `{ "provider": "groq", "suggestions": [ { "title": "Form tasarımı" }, { "title": "JWT entegrasyonu" } ] }`

### 13.4 Efor puanı önerisi
`POST /ai/tasks/{task_id}/suggest-points` · Yönetici · US-052 · FR-080 · Sprint 7 (basit hali) / Sprint 9

**Yanıt · 200:** `{ "provider": "groq", "story_points": 5, "reason": "Birden fazla ekran ve API bağlantısı içeriyor." }`

`story_points` her zaman 1, 2, 3, 5, 8 veya 13'ten biridir.

### 13.5 Haftalık proje özeti
`POST /ai/projects/{project_id}/weekly-summary` · Yönetici · US-053 · FR-081 · Sprint 9

**Yanıt · 200:** `{ "provider": "groq", "from": "2026-10-01", "to": "2026-10-07", "summary": "Bu hafta 7 görev tamamlandı..." }`

### 13.6 Yorum zinciri özeti
`POST /ai/tasks/{task_id}/summarize-comments` · Proje üyesi · US-053 · FR-082 · Sprint 9

**Yanıt · 200:** `{ "provider": "groq", "decisions": ["..."], "open_questions": ["..."], "summary": "..." }`

| Kod | `error.code` | Mesaj |
|---|---|---|
| 400 | `NOT_ENOUGH_COMMENTS` | Özet için görevde en az 5 yorum olmalıdır. |

### 13.7 Proje chatbotu
`POST /ai/projects/{project_id}/chat` · Proje üyesi · US-054 · FR-085, FR-086 · Sprint 10 (zaman kalırsa)

**İstek**
```json
{
  "message": "Bu hafta kimin işi gecikti?",
  "history": [ { "role": "user", "content": "..." }, { "role": "assistant", "content": "..." } ]
}
```

**Yanıt · 200**
```json
{
  "provider": "groq",
  "reply": "Bu hafta 2 görev gecikti: Can Demir'in 'API geliştirme' görevi ve ...",
  "proposed_action": null
}
```

Chatbot yalnızca kullanıcının erişebildiği proje verilerini kullanır (FR-085). Veri değiştiren bir işlem önerirse `proposed_action` dolu gelir ama işlem **yapılmaz**; kullanıcı onaylarsa frontend ilgili normal uç noktayı çağırır (FR-086):

```json
"proposed_action": {
  "type": "CREATE_TASK",
  "description": "Ayşe'ye 'Rapor ekranı' görevini oluştur",
  "endpoint": "POST /projects/3/tasks",
  "payload": { "title": "Rapor ekranı", "assignee_id": 7 }
}
```

---

## 14. Arka plan işleri

Bu işler uç nokta değildir; backend'de APScheduler ile zamanlanmış görev olarak çalışır. Saatler Türkiye saatine (UTC+3) göredir.

| İş | Ne zaman | Ne yapar | FR | Sorumlu |
|---|---|---|---|---|
| Teslim tarihi hatırlatması | Her gün 09:00 | Teslimine 2 gün veya daha az kalmış, `DONE` olmayan görevlerin sahibine `DUE_DATE_SOON` bildirimi (aynı görev için günde en fazla bir kez) | FR-056 | Salih Bilgin |
| Güncellenmeyen görev hatırlatması | Her gün 09:00 | 4 gündür güncellenmemiş, `DONE` olmayan görevlerin sahibine `TASK_STALE` bildirimi | FR-057 | Salih Bilgin |
| E-posta bildirimleri | Bildirim oluştuğunda | Kullanıcının `email_enabled` tercihi açıksa ilgili bildirimi e-postayla gönderir | FR-053, FR-055 | Salih Bilgin |
| Haftalık özet e-postası | Pazartesi 09:00 | `weekly_summary_enabled` açık kullanıcılara proje ilerlemesi ve görev durumları özeti | FR-059 | Salih Bilgin |
| Süresi dolmuş token temizliği | Her gün 03:00 | Geçersizler listesindeki süresi dolmuş token'ları siler | — | Esra Musul |

---

## 15. Uç nokta özeti ve sprint eşlemesi

| Sprint | Uç noktalar | Backend |
|---|---|---|
| 2 | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `GET /users`, `PATCH /users/{id}/role`, `GET /health` | Esra Musul |
| 3 | `GET/POST /projects`, `GET/PATCH/DELETE /projects/{id}`, `GET/POST /projects/{id}/members`, `DELETE /projects/{id}/members/{user_id}`, `POST /projects/{id}/invites`, `POST /invites/{token}/accept` | Emre Kaan Şensoy, Esra Musul |
| 4 | `GET/POST /projects/{id}/tasks`, `GET/PATCH/DELETE /tasks/{id}`, `PATCH /tasks/{id}/status`, `PATCH /tasks/{id}/assignee`, `POST /tasks/{id}/subtasks`, `GET/POST /projects/{id}/labels`, `GET /projects/{id}/board` | Emre Kaan Şensoy, Esma Otur |
| 5 | `GET /projects/{id}/calendar`, `GET /projects/{id}/gantt`, `GET/POST /projects/{id}/files`, `GET /files/{id}/download`, `DELETE /files/{id}`, `GET/POST /tasks/{id}/comments`, `GET/POST /files/{id}/comments` | Emre Kaan Şensoy, Esma Otur |
| 6 | `GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all`, `GET /dashboard`, `GET /projects/{id}/reports/members`, `GET /projects/{id}/reports/period`, `GET/POST /projects/{id}/sprints`, `GET/PATCH/DELETE /sprints/{id}`, `POST/DELETE /sprints/{id}/tasks` | Salih Bilgin, Emre Kaan Şensoy |
| 7 | `risk_level` hesaplaması, `GET /projects/{id}/risks`, `GET /me/today`, `GET /projects/{id}/workload`, `PATCH /projects/{id}/members/{user_id}` (kapasite), kapasite kontrolü (6.6), LLM servis katmanı, `POST /ai/tasks/{id}/suggest-points` (basit hali) | Sena Gül Kara, Emre Kaan Şensoy |
| 8 | `PATCH /auth/me`, `PUT /auth/me/avatar`, `POST /auth/password/forgot`, `POST /auth/password/reset`, teknik rol (5.11), `POST /tasks/{id}/approve`, `POST /tasks/{id}/reject`, görev filtreleri (6.1), `GET/PATCH /notifications/preferences`, hatırlatma işleri, yedek LLM servisi | Esra Musul, Emre Kaan Şensoy, Salih Bilgin, Sena Gül Kara |
| 9 | `GET /projects/{id}/reports/export`, `POST/DELETE /tasks/{id}/dependencies`, iş yükü önerileri, `POST /ai/projects/{id}/extract-tasks`, `POST /ai/tasks/{id}/suggest-subtasks`, `POST /ai/projects/{id}/weekly-summary`, `POST /ai/tasks/{id}/summarize-comments`, haftalık özet e-postası, tema | Salih Bilgin, Emre Kaan Şensoy, Sena Gül Kara |
| 10 | `POST /ai/projects/{id}/chat` (zaman kalırsa) | Sena Gül Kara |

Tüm fonksiyonel gereksinimler (FR-001 – FR-086) en az bir uç noktaya veya arka plan işine karşılık gelir.
