# US-040 Sprint planlama testleri — #244

Tarih: 2026-11-23. Gereksinimler: FR-066, FR-067; user story #50.
Temel sürüm: develop `2cf6081`; branch: `hakan-us040`.
Sözleşme: `docs/api/api-sozlesmesi.md`, 11.1–11.3.

**Durum:** API kabul kontrolleri geçti. Sprint planlama ekranı bulunmadığından
tarayıcı üzerinden uçtan uca kabul **Engelli**; bağımlılık #243 (sefakrds).
Ekran tamamlanıp develop'a alındığında aşağıdaki UI senaryoları tekrar çalıştırılacak.
API testlerinin geçmesi UI testlerinin çalıştırıldığı anlamına gelmez.

## Ortam ve kanıt

- Windows, Python 3.12.14; pytest/FastAPI TestClient, test başına ayrı bellek içi SQLite.
- Gerçek HTTP: izole SQLite ve uvicorn `127.0.0.1:8011`; 2 sentetik hesapla gerçek giriş,
  17 HTTP kontrolü. Kullanıcının geliştirme/canlı veritabanı kullanılmadı; token saklanmadı.
- Frontend: Node 25.7.0, npm 11.10.1; 16 test, lint ve build geçti.
  Mevcut fast-refresh ve büyük bundle uyarıları hata değildir.
- PostgreSQL uygulama sorguları yerelde çalıştırılmadı. CI, PostgreSQL migration ve
  tüm backend/frontend kontrollerini ayrıca doğrular; pytest fixture'ı SQLite kullanır.
- Önce/sonra çıktıları: `us040-before.txt`, `us040-focused.txt`, `us040-full.txt`,
  `us040-frontend.txt`, `us040-http-evidence.json`.

## API senaryoları ve sonuçları

Yeni dosya: `backend/tests/test_sprint_planning_acceptance.py` — 90 parametrik vaka.
Mevcut `test_sprints_crud.py` ve `test_sprints.py` ile toplam **139 geçti**.
Tam backend regresyonu: **846 geçti, 100 uyarı, 262.30 saniye**; başarısız/atlanmış test yok.
Bu branch yalnız develop temelini içerir; henüz birleşmeyen US-023 PR #274 değişikliklerini içermez.

| Grup | Kontrol | Sonuç |
|---|---|---|
| FR-066 oluşturma | Ad, hedef, kapasite ve tarihler kaydedilir; detail/list aynı veriyi döner | Geçti |
| Tarih sınırı | Baş/son ortak gün, birebir eşit, içinde kalan ve kapsayan çakışmalar; POST ve PATCH | Geçti — 400 SPRINT_OVERLAP |
| Ters tarih | Oluşturma, yalnız başlangıç veya yalnız bitişi güncelleme | Geçti — 400 INVALID_DATE_RANGE |
| Geçerli tarihler | Bitişik gün, tek günlük sprint, artık yıl 29 Şubat; sıralama ve proje izolasyonu | Geçti |
| Güncelleme | Kendi tarihleriyle çakışmaz; ad trim edilir; goal/kapasite null ile temizlenir | Geçti |
| Girdi doğrulama | Boş/uzun ad, uzun hedef, sıfır/negatif kapasite, geçersiz tarih | Geçti — 422 VALIDATION_ERROR |
| Null regresyonu | name/start_date/end_date null: alan bazlı 422; kayıtlar değişmez | Düzeltmeden sonra geçti |
| FR-067 ilişki | Mevcut görevi bağla, yinelenen ID/istek, aynı projede başka sprinte taşı, çıkar | Geçti |
| İçerik koruma | İlişki değişirken görev başlığı, açıklaması, atananı, durumu ve diğer içerik alanları korunur | Geçti |
| Atomiklik | Geçerli + olmayan/başka projenin görevi içeren toplu istek kısmi atama yapmaz | Geçti — 404 TASK_NOT_FOUND |
| Hatalı ilişki | Boş/bozuk/null ID listesi; bağlı olmayan veya başka projenin görevini çıkarma | Geçti |
| Kapasite | Tam kapasite: uyarı yok; aşım: ekleme başarılı + uyarı; kapasite yok: uyarı yok | Geçti |
| Yetki | 7 endpoint × 5 kimlik (üye, dış yönetici, dış üye, anonim, geçersiz token) | 35 vaka geçti |
| Yetki veri bütünlüğü | Reddedilen çağrılarda sprint/görev/üyelik tablolarındaki tüm satırlar aynı kalır | Geçti |
| Kaynak bulunamadı | 7 endpoint için eksik proje/sprint: sözleşmeye uygun 404 | Geçti |
| Silme | Sprint silinir; görev içerikleri kalır, sprint_id null olur; diğer proje etkilenmez | Geçti |

Üye liste/detay okuyabilir; yazma işlemleri YONETICI ve ilgili proje üyeliğini gerektirir.
Anonim/geçersiz token 401, yetkisiz rol 403 FORBIDDEN, dış yönetici
403 PROJECT_ACCESS_DENIED alır. Başka projede aynı tarihler mevcut fixture ile
oluşturma/güncelleme doğrulamasını engellemez.

## Bulunan ve düzeltilen hata

[Hata #275](https://github.com/sengka/LUNO/issues/275): PATCH'te zorunlu alanlara açık
null gönderilmesi. Temel sürümde `name: null` → 409 CONFLICT;
`start_date: null` / `end_date: null` → 500 INTERNAL_ERROR.
Yeni testler düzeltme öncesinde **87 geçti / 3 kaldı**.

`SprintUpdate` doğrulayıcısı yalnız açık null değerleri reddeder. Gönderilmeyen
alanlar değişmez; hedef ve kapasiteyi null ile temizleme korunur. Yeni migration
gerekmez. Hata maskelenmedi; istemciye ilgili alanı gösteren 422 yanıtı döner.

## UI kabul — #243 tamamlanınca yeniden çalıştırılacak

| ID | Adımlar ve beklenen sonuç | Şimdiki durum |
|---|---|---|
| UI-01 | Proje üyesi yönetici formdan ad/hedef/tarih/kapasiteyle sprint açar; sayfa yenilenince veri kalır | Engelli #243 |
| UI-02 | Ters ve ortak uç günü olan çakışan tarihler alan/iş kuralı hatası gösterir; yeni kayıt oluşmaz | Engelli #243 |
| UI-03 | Boş, uzun ve geçersiz alanlar anlaşılır mesaj verir; geçerli tek günlük/bitişik sprint kabul edilir | Engelli #243 |
| UI-04 | Mevcut görevleri seçip ekle/çıkar; başka sprinte taşı; yenileyince ilişki ve görev içeriği korunur | Engelli #243 |
| UI-05 | Kapasite eşitken uyarı yok; aşımda görevler eklenir ve uyarı görünür | Engelli #243 |
| UI-06 | Üye yazma yapamaz; proje dışı kullanıcı erişemez; oturumsuz kullanıcı girişe yönlenir | Engelli #243 |
| UI-07 | Sprint silinirken görevlerin korunması, boş sprint, sunucu hatası/tekrar dene ve çift tıklama | Engelli #243 |

Yeniden test tetikleyicisi: #243'ün develop'a alınması. Yeni commit/ortam bilgisiyle
bu senaryolar yürütülüp ekran kanıtları eklenmeli; #244 ancak UI sonucu ve ekip PR
onayı sonrasında kapatılmalı. Efor ilerlemesinin ayrıntılı hesapları US-041 kapsamındadır;
bu görevde ilişki değişikliği/kapasiteye etkisi kontrol edildi. Eşzamanlı çoklu istek
ve PostgreSQL yük testi yürütülmedi; tamamlandı olarak raporlanmadı.

## Son kontrol

- FR-066/FR-067 için otomatik ve gerçek HTTP kanıtları hazır.
- Yetkisiz/başarısız işlemlerde veri değişmezliği ve mutasyon sonrası yeniden okuma doğrulandı.
- API kabul tikleri işaretlenebilir. UI ve ekip onayı tamamlanmadan bütün görev Done yapılamaz.
- Tam regresyon sonucu `us040-full.txt`; son CI ve ekip incelemesi PR üzerinden izlenir.
