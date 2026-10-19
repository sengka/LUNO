# US-004 Sistem Rolü Yönetimi — Test Raporu

- Görev: #76; story: #14; gereksinimler: FR-010, FR-011.
- Tarih: 19.10.2026.
- Yürüten: Codex, Hakan Aydın'ın talebiyle.
- Temel sürüm: develop 9fad8ab; teslim dalı: hakan-us004.
- Ortam: Windows, Python 3.14.5, SQLite; localhost:5173 ve localhost:8000.
- Tarayıcı: Codex uygulama içi tarayıcı.

## Kapsam

1. Yeni kullanıcı varsayılan olarak Ekip Üyesi olmalı (FR-010).
2. Yönetici, başka kullanıcının rolünü Yönetici/Ekip Üyesi olarak değiştirebilmeli (FR-011).
3. Ekip Üyesi kullanıcı listesine ve rol değiştirmeye erişememeli (#76).

Arayüz testleri tarayıcı otomasyonuyla yürütüldü; insan tarafından elle
yapılmış testler olarak sunulmamıştır. API testleri TestClient ve her testte
temizlenen bellek içi SQLite üzerinde çalışır; mevcut yerel veritabanına dokunmaz.

## Yerel arayüz testi hazırlığı ve temizlik

Sadece localhost uygulamasında iki yeni QA hesabı kayıt API'siyle oluşturuldu:

- qa.us004.admin.20261019@example.com — QA Rol Yönetici
- qa.us004.member.20261019@example.com — QA Rol Hedef

Test şifresi: LunoRole123! (yalnızca bu yerel test hesapları).
Her iki kayıt yanıtında rol EKIP_UYESI olarak doğrulandı.
Yerelde hazır yönetici bulunmadığından yalnızca yeni QA Rol Yönetici
hesabına test hazırlığı için veritabanından Yönetici rolü verildi; bu hazırlık
uygulamadaki rol değiştirme işleminin başarılı olduğuna kanıt sayılmadı.
Sonraki hedef rol değişimleri gerçek arayüzden yapıldı.

Test sonunda hedef rol arayüzden Ekip Üyesine döndürüldü. Yönetici hazırlık
hesabının rolü de veritabanından Ekip Üyesine geri alındı. İki test hesabının
son rolü EKIP_UYESI olarak doğrulandı; başka kullanıcıların rolleri değiştirilmedi.
Test hesapları yerel test verisi olarak kaldı; veri silinmedi.

## Tarayıcı senaryoları

| ID | Gereksinim | Adımlar ve beklenen sonuç | Gözlenen | Sonuç |
| --- | --- | --- | --- | --- |
| RL-001 | FR-010 | Yeni hesapla giriş yap; varsayılan rol Ekip Üyesi olmalı. | QA Rol Hedef için Ekip Üyesi etiketi gösterildi; kayıt API yanıtı da EKIP_UYESI. | Geçti |
| RL-002 | #76 | Ekip Üyesi olarak /kullanicilar adresini doğrudan aç. Kullanıcı listesi veya rol değiştirme kontrolleri açılmamalı. | / kontrol paneline yönlendirme; Kullanıcılar menüsü yok. | Geçti |
| RL-003 | FR-011 | Test yöneticisiyle /kullanicilar aç. Kullanıcılar ve rol seçimleri görünmeli. | Liste açıldı. Kendi rol seçimi devre dışı, hedef hesabınki etkin. | Geçti |
| RL-004 | FR-011 | Hedef için Yönetici seç; sayfayı yenile. Rol kaydedilmeli. | “QA Rol Hedef artık Yönetici.” bildirimi; yenilemeden sonra Yönetici değeri korundu. | Geçti |
| RL-005 | FR-011 | Yönetici yapılan hedefle yeniden giriş yap ve /kullanicilar aç. | Yeni yönetici kullanıcı listesine erişti; kendi rol seçimi devre dışı. | Geçti |
| RL-006 | FR-011 | İlk test yöneticisiyle hedef rolü Ekip Üyesine geri al; yenile. | “QA Rol Hedef artık Ekip Üyesi.” bildirimi; rol yenilemeden sonra korundu. | Geçti |
| RL-007 | #76 | Düşürülen hedefle yeniden giriş yap, /kullanicilar aç. | Ekip Üyesi etiketi; kontrol paneline dönüş ve yönetim menüsünün gizlenmesi. | Geçti |

## Eklenen API regresyonları

Dosya: backend/tests/test_role_management.py; toplam 8 parametrik test örneği.

| Kontrol | Beklenen ve gözlenen |
| --- | --- |
| Kayıt isteğine role=YONETICI veya SUPER_ADMIN eklenmesi (2 örnek) | Hesap yine EKIP_UYESI; /auth/me rolü doğruluyor ve /users 403. İstemci kayıt sırasında kendine yönetici yetkisi veremiyor. |
| Rolün yükseltilmesi ve düşürülmesi, aynı tokenla yetki kontrolü (1 örnek) | PATCH 200; /auth/me ve yönetici listesi yeni rolü döndürüyor. Mevcut kullanıcı tokenı /users için önce 403, yükseltme sonrası 200, düşürme sonrası 403. |
| Tokensız veya Ekip Üyesiyle kendi rolünü yükseltme (2 örnek) | Sırasıyla 401 UNAUTHORIZED ve 403 FORBIDDEN. Hedef rol /auth/me üzerinden halen EKIP_UYESI. |
| Yöneticinin SUPER_ADMIN, null veya eksik role göndermesi (3 örnek) | 422 VALIDATION_ERROR; mevcut kullanıcı rolü değişmedi. |

Mevcut test_users.py testleri de çalıştırıldı: liste, arama, sayfalama,
yetkisiz liste erişimi, iki yönlü rol değişimi, kendi rolünü değiştirme yasağı,
bulunmayan kullanıcı ve geçersiz rol. Kendi rolünü değiştirme isteği
400 CANNOT_CHANGE_OWN_ROLE döndürüyor.

## Çalıştırma ve sonuç

Depo kökünden:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests --basetemp <yazilabilir-gecici-klasor>
```

**83 passed, 7 warnings in 28.92s**.
Develop'taki mevcut 75 teste bu görevde 8 örnek eklendi. Önceki görevlerin
henüz birleştirilmemiş testleri bu dalın toplamına dahil değildir.
Uyarılar TestClient/httpx kullanımı ve eski HTTP 422 sabitiyle ilgili
StarletteDeprecationWarning bildirimleridir; üç ek 422 senaryosu uyarı sayısını artırır.

## Kanıtlar

- [RL-001: Yeni kullanıcının varsayılan rolü](kanitlar/us-004/varsayilan-rol.png)
- [RL-002: Ekip Üyesi erişim engeli](kanitlar/us-004/uye-erisim-engeli.png)
- [RL-003: Yönetici listesi ve kendi rol seçiminin kilitli olması](kanitlar/us-004/yonetici-listesi.png)
- [RL-004: Yöneticiye yükseltme bildirimi](kanitlar/us-004/yoneticiye-yukseltme.png)
- [RL-004: Yenilemeden sonra rolün korunması](kanitlar/us-004/rol-kalici.png)
- [RL-005: Yeni yöneticinin kullanıcı listesine erişimi](kanitlar/us-004/yeni-yonetici-erisim.png)
- [RL-006: Ekip Üyesine düşürme bildirimi](kanitlar/us-004/uyeye-dusurme.png)
- [RL-007: Düşürme sonrası erişimin kaldırılması](kanitlar/us-004/rol-sonrasi-engel.png)

## Bulgular ve son kapsam kontrolü

- FR-010, FR-011 ve #76'nın üç yapılacak maddesi testlerle karşılandı.
- Bu kapsamda yeni hata görülmedi; hata issue'su açılması uygulanamaz (N/A).
- Rol değişiminden sonra mevcut tokenın API yetkisi ayrıca test edildi.
  Başka sekmede açık kalan ekranın anlık görsel güncellenmesi test edilmedi.
- Üretim hesabı veya gerçek ekip üyelerinin yetkileri değiştirilmedi; yalnızca
  iki yeni yerel QA hesabı kullanıldı ve başlangıç rolleri geri yüklendi.
- .env, token süresi ve uygulama kaynak kodunda değişiklik yapılmadı.
- Rapor bağlantıları, GitHub dosya içerikleri ve CI kontrolleri teslimde
  kontrol edilir; PR onayı ve birleştirme ekip sorumlularını bekler.
