# US-003 Çıkış Yapma — Test Raporu

- Görev: #73; user story: #13; gereksinim: FR-007.
- Tarih: 19.10.2026.
- Yürüten: Codex, Hakan Aydın'ın talebiyle.
- Temel sürüm: develop 9fad8ab; teslim dalı: hakan-us003.
- Ortam: Windows, Python 3.14.5, yerel SQLite, localhost:5173/8000.
- Tarayıcı: Codex uygulama içi tarayıcı.

## Kapsam ve yöntem

Kabul kriteri: Çıkış yap seçilince oturum sonlandırılır ve giriş sayfasına dönülür.
Görev ayrıca eski token ile korumalı API erişiminin ve çıkış sonrası korumalı
sayfa erişiminin engellenmesini ister.

Tarayıcı senaryoları otomasyonla yürütüldü; insan tarafından elle yapılmış
test olarak sunulmamıştır. UI için önceki yerel test hesabı
hakan.qa002@example.com / Luno123! kullanıldı. API testleri her testte
ayrı, bellek içi SQLite ve yeni test kullanıcısı kullanır; yerel uygulama
veritabanındaki veriler otomatik testler tarafından değiştirilmez.

## Tarayıcı senaryoları

| ID | Adımlar | Beklenen | Gözlenen | Sonuç |
| --- | --- | --- | --- | --- |
| LO-001 | Geçerli test hesabıyla giriş yap, kontrol panelinde Çıkış yap düğmesine bas. | Oturum sonlanır, giriş ekranı açılır. | Kullanıcı adı ve Ekip Üyesi rolüyle açık oturum görüldü; çıkışta URL /giris oldu ve giriş formu açıldı. | Geçti |
| LO-002 | Çıkış sonrasında / adresini doğrudan aç; sayfayı yenile. | Kontrol paneli görünmemeli. | Her iki işlemde /giris gösterildi. | Geçti |
| LO-003 | Çıkış sonrası /projeler adresini doğrudan aç. | Projeler içeriği yerine girişe yönlendirme. | /giris açıldı, giriş formu gösterildi. | Geçti |
| LO-004 | Yeniden giriş yap; /projeler ve / sayfalarını ziyaret ederek geçmiş oluştur; çıkış yap; tarayıcı Geri düğmesine bas. | Geçmişteki korumalı sayfa açılamamalı. | /giris gösterildi; korumalı içerik görünmedi. | Geçti |
| LO-005 | Çıkış sonrası aynı hesapla tekrar giriş yap; / kontrol paneline git. | Yeni oturum kullanılabilir olmalı. | Kontrol paneli, kullanıcı adı ve Ekip Üyesi rolü görüntülendi. | Geçti |

## API senaryoları ve yeni otomatik testler

Dosya: backend/tests/test_logout_session.py.

| ID | Deneme | Sonuç |
| --- | --- | --- |
| API-001 | Geçerli token ile /auth/me erişimi 200; çıkış 204 ve boş gövde; aynı token tekrar kullanılır. | /auth/me artık 401 UNAUTHORIZED. Aynı tokenla tekrarlanan çıkış da 401; erişim tekrar açılamıyor. |
| API-002 | Ekip Üyesi tokenıyla /users önce 403; çıkış sonrası aynı tokenla tekrar dene. | 401 UNAUTHORIZED. Yetki hatası ile geçersiz oturum ayrımı doğrulandı. |
| API-003 | Tokensız çıkış dene; ayrı geçerli oturumu kontrol et. | Çıkış denemesi 401; geçerli oturum /auth/me üzerinden 200. |
| API-004 | Bozuk token ile çıkış dene. | 401; mevcut geçerli oturum etkilenmedi. |
| API-005 | Geçmiş exp değerli doğru imzalı tokenla çıkış dene. | 401; mevcut geçerli oturum etkilenmedi. |
| API-006 | Aynı kullanıcı için iki farklı geçerli token hazırla; biriyle çıkış yap. | Çıkış yapılan token 401; diğer farklı token 200 ve doğru kullanıcı kimliği döndürüyor. |

API-006 diğer tokenın geçerliliğini doğrular; tüm cihazlardan çıkış talep
edilmediğinden yalnızca mevcut tokenın iptali değerlendirilir. İkinci token
test yardımcı fonksiyonuyla farklı exp süresiyle üretilir; iki tarayıcıda
gerçek kullanıcı girişi simüle edildiği iddia edilmez.

## Çalıştırma

Depo kökünde:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --basetemp <yazilabilir-gecici-klasor>
```

**81 passed, 4 warnings in 23.43s**: develop'taki mevcut 75 teste bu görev
kapsamında 6 test eklendi. US-002'nin ayrı ve henüz birleştirilmemiş dalındaki
iki test bu toplamda yer almıyor.
Uyarılar mevcut TestClient/httpx ve eski HTTP 422 sabitiyle ilgili.

## Ekran görüntüleri

- [LO-001: Çıkış öncesi oturum](kanitlar/us-003/oturum-acik.png)
- [LO-001: Çıkış sonrası giriş ekranı](kanitlar/us-003/cikis-sonrasi.png)
- [LO-002: Kontrol paneli erişimi ve yenileme engellendi](kanitlar/us-003/kontrol-paneli-engelli.png)
- [LO-003: Projeler erişimi engellendi](kanitlar/us-003/projeler-engelli.png)
- [LO-004: Geri düğmesiyle erişim engellendi](kanitlar/us-003/geri-tusu.png)
- [LO-005: Yeniden giriş başarılı](kanitlar/us-003/yeniden-giris.png)

## Bulgular ve sınırlar

- Yukarıdaki FR-007 ve #73 senaryolarında yeni hata görülmedi.
- Yeniden girişte /projeler sayfasındaki önceden bilinen veri yükleme hatası
  #140 tekrar gözlendi. Aynı hata için yeni issue açılmadı; kimlik doğrulaması
  ve çıkış sonrası erişim engeli sonuçlarından ayrı değerlendirildi.
- UI oturum sonlanması yönlendirme, yenileme ve korumalı sayfa denemeleriyle
  doğrulandı; localStorage içindeki token değeri doğrudan okunmadı.
- Ağ kesintisi, çoklu sekmelerin anlık eşzamanlanması ve tüm cihazlardan çıkış
  bu görevin kabul kriterlerinde yer almıyor; test edilmiş sayılmamalıdır.
- Uygulama kodu, .env ve token süresi bu görevde değiştirilmedi.

## Teslim kontrolü

- Kabul kriteri ile görevdeki iki yapılacak madde senaryolara eşlendi.
- Tüm senaryolar çalıştırıldı, 6 kanıt eklendi, backend testleri geçti.
- Rapor bağlantıları ve değişiklik kapsamı kontrol edilir; görev kartı
  In progress tutulur, onay olmadan PR onaylandı kutusu işaretlenmez.
- Son GitHub kontrolleri ve ekip onayı PR üzerinde izlenmelidir.
