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

Kurulum adımları proje iskeleti hazırlandığında eklenecektir.

## Ekip

YZM397 Yazılım Proje Yönetimi dersi kapsamında 11 kişilik bir ekip tarafından geliştirilmektedir.
