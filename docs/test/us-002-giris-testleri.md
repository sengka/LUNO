# US-002 Kullanıcı Girişi — Test Raporu

- Görev: #70; user story: #12; gereksinimler: FR-005, FR-006.
- Tarih: 19.10.2026.
- Testleri yürüten: Codex; Hakan Aydın'ın talebiyle.
- Temel sürüm: develop, 9fad8ab.
- Dal: hakan-us002 (US-001'in açık PR'ından ayrı teslim).
- Ortam: Windows; Python 3.14.5; yerel SQLite; frontend localhost:5173,
  backend localhost:8000; uygulama içi tarayıcı.

## Ön koşullar ve yöntem

Backend ve frontend çalışıyor. Önceki kayıt testinde oluşturulan
hakan.qa002@example.com hesabı (Ekip Üyesi), Luno123! test şifresi kullanıldı.
Bunlar yalnızca yerel test verileridir.
Arayüz senaryoları tarayıcı kontrolüyle yürütüldü; insan tarafından
elle yapılmış testler olarak değerlendirilmemelidir.
API testleri TestClient ve her testte temizlenen bellek içi SQLite ile
çalıştırıldı. Gerçek kullanıcı veritabanı testlerde kullanılmadı.

## Senaryolar

| ID | Gereksinim / kapsam | Adımlar ve beklenen sonuç | Gözlenen sonuç | Durum |
| --- | --- | --- | --- | --- |
| LG-001 | FR-005 | Doğrudan /giris aç; kayıtlı e-posta ve doğru şifreyi gir; Giriş yap. Yetkisine uygun ana sayfa açılmalı. | / adresindeki kontrol paneli açıldı; Hakan Test ve Ekip Üyesi gösterildi. | Geçti |
| LG-002 | FR-006 | Kayıtlı e-posta ve Yanlis123! ile giriş dene. Oturum açılmamalı, hata gösterilmeli. | /giris üzerinde “E-posta veya şifre hatalı.” gösterildi. | Geçti |
| LG-003 | FR-006 | qa.kayitsiz.70.20261019@example.com ve geçerli biçimli şifreyle giriş dene. Giriş reddedilmeli. | /giris üzerinde aynı genel hata mesajı gösterildi. Mevcut API testi de 401 INVALID_CREDENTIALS sonucunu doğruladı. | Geçti |
| LG-004 | #70, oturum süresi | Test kullanıcısıyla geçerli token al; /auth/me yanıtının 200 olduğunu doğrula. Aynı kullanıcı için bir dakika önce süresi dolmuş, doğru imzalı token üret; /auth/me çağır. | Süresi dolmuş token 401 UNAUTHORIZED ve “Oturumunuzun süresi doldu, lütfen tekrar giriş yapın.” döndürdü. Geçerli token ile sonraki çağrı yine 200. | Geçti (API) |
| LG-005 | #70, korumalı sayfa | Oturum yokken /projeler adresini doğrudan aç. İçerik yerine giriş ekranına yönlendirilmeli. | URL /giris oldu ve giriş formu gösterildi. /auth/me tokensız çağrısı da 401 döndürdü. | Geçti |
| LG-006 | Ek yönlendirme kontrolü | LG-005 sonrasında doğru bilgilerle giriş yap. İstenen korumalı sayfaya dönülmeli. | /projeler açıldı ve kullanıcı oturumu göründü; proje verisi yüklenemedi (aşağıdaki yan bulgu). | Yönlendirme geçti; veri yükleme hatalı |

## Otomatik testler

Eklenen dosya: backend/tests/test_login_session.py.

- Tokensız /auth/me erişiminin reddi.
- Geçerli oturum ile erişim, süresi dolmuş tokenın reddi ve geçerli
  oturumun çalışmaya devam etmesi. Token hatalı imzayla değil, gerçekten
  geçmiş exp değeriyle üretilir; uyutma veya gerçek token süresini değiştirme yoktur.

Mevcut test_auth.py içindeki doğru giriş, yanlış şifre, kayıtsız e-posta,
GET /auth/me, bozuk token ve çıkış testleri de tüm paketle çalıştırıldı.

Çalıştırma (depo kökünden):

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --basetemp <yazilabilir-gecici-klasor>
```

Sonuç: **77 passed, 4 warnings in 42.39s**.
Uyarılar TestClient/httpx ve eski HTTP 422 sabitiyle ilgili
StarletteDeprecationWarning bildirimleridir.

## Kanıtlar

- [LG-001: Başarılı giriş ve kontrol paneli](kanitlar/us-002/dogru-giris.png)
- [LG-002: Yanlış şifre](kanitlar/us-002/yanlis-sifre.png)
- [LG-003: Kayıtsız e-posta](kanitlar/us-002/kayitsiz.png)
- [LG-005: Oturumsuz korumalı sayfadan girişe yönlendirme](kanitlar/us-002/oturumsuz.png)
- [LG-006: Giriş sonrası projeler ekranı hatası](kanitlar/us-002/projeler-hata.png)

## Yan bulgu: Projeler ekranı veriyi yükleyemiyor

Hata raporu: https://github.com/sengka/LUNO/issues/140

Tekrar: oturumsuz /projeler aç, girişe yönlendirilince geçerli hesapla giriş yap.
Beklenen: kullanıcının proje listesi veya boş liste durumu.
Gerçekleşen: kullanıcı oturumu açılıyor ancak “Beklenmeyen bir hata oluştu.” görünüyor.

Aynı sürümde TestClient ile GET /api/v1/projects çağrısı 404 döndürdü.
Kaynak incelemesinde api/v1/api.py yalnızca auth, users ve invites router'larını
bağlıyor; projects router'ı bulunmuyor. Bu bulgu US-007 / FR-017 proje listeleme
alanıyla ilişkilidir; giriş kimlik doğrulaması başarısızlığı olarak sınıflandırılmadı.
İlk test taslağında /projects üzerinde beklenen 401/200 kontrolleri bu nedenle
başarısız oldu; nihai oturum testleri mevcut korumalı /auth/me üzerinden yürütüldü.

## Kapsam sınırları

- Süresi dolmuş token hem API seviyesinde hem tarayıcıda sayfa yenileme akışında doğrulandı.
- Yönetici hesabıyla ayrı giriş senaryosu çalıştırılmadı; FR-005'in Ekip Üyesi
  akışı doğrulandı. Bu rapor tüm rol izinlerinin denetlendiği anlamına gelmez.
- npm güvenlik bulguları ve proje listeleme yan bulgusu ayrı değerlendirilmelidir.
- PR onayı ve birleştirme ekip sorumlularını bekler.

## LG-007 — Tarayıcıda süresi dolmuş oturum (ek doğrulama)

19.10.2026 tarihinde localhost:5173 üzerinde yürütüldü.

1. Yerel backend oturum süresi yalnızca test için 5 saniyeye indirildi.
   /auth/login yanıtındaki expires_in=5 ile ayar doğrulandı.
2. Önceki test oturumundan çıkılıp hakan.qa002@example.com ile giriş yapıldı.
   Kontrol paneli ve kullanıcı adı görüldü.
3. Token süresinden uzun beklendi ve sayfa yenilendi; böylece /auth/me isteği tetiklendi.
4. Tarayıcı /giris adresine yönlendirildi ve “Oturumunun süresi doldu,
   lütfen tekrar giriş yap.” bildirimi gösterildi.
5. / adresine yeniden gidildiğinde yine /giris açıldı; korumalı içerik görünmedi.
6. Backend oturum süresi eski değerine döndürüldü ve yeni giriş yanıtında
   expires_in=86400 doğrulandı. .env veya uygulama kaynaklarında kalıcı değişiklik yapılmadı.

Sonuç: **Geçti.** Oturumun kullanılamaz hale gelmesi, uyarı ve yönlendirme
tarayıcıdan doğrulandı. Tarayıcı depolamasındaki token değeri doğrudan okunmadı.
Bu kontrol sayfa yenilenince yapılan doğrulamayı kapsar; boşta açık kalan
sayfada tam süre dolduğu anda otomatik çıkış yapıldığı iddiasını içermez.

[LG-007 kanıtı: Süresi dolmuş oturum uyarısı](kanitlar/us-002/suresi-dolmus-oturum.png)
