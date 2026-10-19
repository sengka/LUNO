# US-001 Kullanıcı Kaydı — Manuel Test Raporu

- Test eden: Hakan Aydın
- Tarih: 19.10.2026
- İlgili görev: #67
- User story: #11 — US-001
- Gereksinimler: FR-001, FR-002, FR-003, FR-004
- Test edilen commit: 8c957ba
- Ortam: Windows, yerel geliştirme, SQLite
- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Python: 3.14.5
- Node.js: 25.7.0
- npm: 11.10.1

## Yöntem

Testler kayıt ekranında manuel olarak yürütüldü.
Sonuçlar ekranda gösterilen mesajlar ve yönlendirmeler üzerinden
değerlendirildi. Veritabanı kayıt sayıları ve doğrudan API
yanıtları bu çalışma kapsamında kontrol edilmedi.

## Ön koşullar

- Backend ve frontend çalışır durumda.
- Alembic migration'ları uygulanmış.
- İlk denemeden önce aşağıdaki test e-postaları kayıtlı değil:
  - hakan.qa001@example.com
  - hakan.qa002@example.com

## Test senaryoları ve sonuçları

Her senaryoda belirtilen bilgiler girilerek Kayıt ol düğmesine basıldı.

| ID | Gereksinim | Senaryo ve veri | Beklenen sonuç | Gözlenen sonuç | Durum |
| --- | --- | --- | --- | --- | --- |
| TC-001 | FR-001, FR-002 | Geçerli ad, hakan.qa001@example.com ve LunoTest123! ile kayıt | Kayıt başarılı olur, başarı mesajı gösterilir | Test eden başarı mesajını gördüğünü bildirdi; giriş ekranına geçildi ve e-posta dolduruldu | Geçti |
| TC-002 | FR-003 | Kayıtlı hakan.qa001@example.com adresi ve geçerli diğer alanlarla tekrar kayıt | Kayıt reddedilir, e-postanın kullanımda olduğu belirtilir | E-posta alanında “Bu e-posta adresi zaten kullanımda.” gösterildi | Geçti |
| TC-003 | FR-004 | Ad boş; hakan.qa003@example.com; şifre: LunoTest123! | Boş ad nedeniyle kayıt engellenir, ad alanında hata gösterilir | “Ad soyad en az 2 karakter olmalıdır.” gösterildi | Geçti |
| TC-004 | FR-004 | Ad: Hakan Test; e-posta boş; geçerli şifre | Kayıt engellenir, e-posta alanında hata gösterilir | “Geçerli bir e-posta adresi gir.” gösterildi | Geçti |
| TC-005 | FR-004 | Ad: Hakan Test; hakan.qa002@example.com; şifre boş | Kayıt engellenir, şifre alanında hata gösterilir | “Şifre en az 8 karakter olmalıdır.” gösterildi | Geçti |
| TC-006 | FR-004 | Ad: Hakan Test; hakan.qa002@example.com; şifre: Luno12! (7 karakter) | Kısa şifre reddedilir | “Şifre en az 8 karakter olmalıdır.” gösterildi | Geçti |
| TC-007 | FR-001, FR-002 | Ad: Hakan Test; hakan.qa002@example.com; şifre: Luno123! (8 karakter) | Kayıt başarılı olur, başarı mesajı gösterilir | “Kayıt başarılı! Şimdi giriş yapabilirsin.” gösterildi ve giriş ekranına geçildi | Geçti |

## Ek doğrulama

TC-007 sonrasında hakan.qa002@example.com ve Luno123! ile giriş
yapıldı. Kontrol paneli açıldı; kullanıcı “Hakan Test” ve rolü
“Ekip Üyesi” olarak görüntülendi.

## Notlar ve kapsam sınırları

- Boş ad kontrolü, kayıtlı olmayan hakan.qa003@example.com adresiyle
  tekrar denendi ve ad alanında beklenen hata gösterildi.
- Test edenin paylaştığı 8 ekran görüntüsü aşağıdaki kanıtlar bölümüne eklendi.
- Bu denemelerde hata raporu açılmasını gerektiren bir davranış gözlenmedi.

- npm install çıktısında 7 yüksek önem dereceli güvenlik açığı
  bildirildi. Ayrıntıları henüz incelenmedi; ayrı değerlendirme gerektirir.
- Tekrar çalıştırmada başarılı kayıt senaryoları için yeni test
  e-postaları kullanılmalıdır.
## Mevcut otomatik testlerin çalıştırılması

Backend klasöründe çalıştırılan komut:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Test edenin paylaştığı terminal çıktısı: **75 passed, 4 warnings in 23.73s**.

Mevcut 75 otomatik testin tamamı geçti. Yeni otomatik test eklenmedi.
Dört StarletteDeprecationWarning bildirildi: biri TestClient/httpx
kullanımıyla, üçü HTTP 422 sabitinin eski adıyla ilgili.

## Ekran görüntüsü kanıtları

Görseller manuel test sırasında test eden tarafından alındı.
TC-001 görseli kayıt sonrası giriş ekranını gösterir; başarı mesajı
bu görselde görünmez ve test edenin beyanına dayanır.
TC-007 görselinde başarı mesajı doğrudan görünür.

| Test | Kanıt |
| --- | --- |
| TC-001 | [Kayıt sonrası giriş ekranı](kanitlar/us-001/tc-001-kayit-sonrasi.png) |
| TC-002 | [Kayıtlı e-posta hatası](kanitlar/us-001/tc-002-kayitli-eposta.png) |
| TC-003 | [Yeni e-posta ile boş ad kontrolü](kanitlar/us-001/tc-003-bos-ad.png) |
| TC-004 | [Boş e-posta kontrolü](kanitlar/us-001/tc-004-bos-eposta.png) |
| TC-005 | [Boş şifre kontrolü](kanitlar/us-001/tc-005-bos-sifre.png) |
| TC-006 | [7 karakterli şifre kontrolü](kanitlar/us-001/tc-006-kisa-sifre.png) |
| TC-007 | [8 karakterli şifre ve başarı mesajı](kanitlar/us-001/tc-007-sekiz-karakter.png) |
| Ek doğrulama | [Yeni hesapla giriş ve Ekip Üyesi rolü](kanitlar/us-001/ek-dogrulama-giris.png) |

## Hata raporu durumu

Bu kayıt senaryolarında hata gözlenmediği için Hata Raporu şablonuyla
issue açılması uygulanamaz (N/A). Bu değerlendirme yalnızca yukarıdaki
senaryoları kapsar; npm güvenlik bulgularının incelemesi ayrı takip işidir.
