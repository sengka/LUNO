# US-006 Proje oluşturma kabul testi

**Issue:** #102 (parent: #16) · **Gereksinimler:** FR-015, FR-016
**Test eden:** Gizem Tangel · **Ortam:** develop (PR #129 sonrası), yerel kurulum
**Hesap:** Sena Gül Kara (YONETICI)

## Sonuçlar

| # | Kabul kriteri | Senaryo | Beklenen | Gerçekleşen | Sonuç |
|---|---|---|---|---|---|
| 1 | FR-015 | Ad, açıklama, başlangıç ve bitiş tarihi girilip kaydedildi | Proje oluşur | Proje oluştu ve proje listesinde göründü | Geçti |
| 2 | FR-016 | Bitiş tarihi başlangıçtan önceye alınmaya çalışıldı | Proje kaydedilmez, tarih hatası mesajı gösterilir | Form, başlangıçtan önceki günlerin seçilmesine izin vermiyor, hatalı proje kaydedilemiyor. Hata mesajı görünmüyor | Kısmen geçti |

## Notlar

- Aynı gün başlangıç ve bitiş seçimi kabul ediliyor (API sözleşmesiyle uyumlu).
- Kriter 2'de "kaydedilmez" kısmı sağlanıyor. "Mesaj gösterilir" kısmı arayüzden gözlemlenemedi, çünkü kullanıcı hatalı seçimi yapamıyor.
- Karar bekleyen soru: engelleme davranışı kriteri karşılıyor sayılır mı, yoksa forma bilgi mesajı mı eklensin?
