# US-023 Rapor testleri — #241

Tarih: 2026-11-23. Story #33; FR-062/063; sözleşme 10.2–10.3.
Test tabanı: develop `2cf6081d3593ff166c26f1b34ac398e64549a813`. Dal: `hakan-us023`.
Windows, Python 3.12.14, SQLite, gerçek FastAPI uçları ve React/Vite arayüzü kullanıldı. Veriler sentetik; gerçek hesaplar ve canlı veritabanı kullanılmadı.

## Sonuç

34 yeni kabul testi + mevcut 3 rapor testi: **37 passed**, 6 Starlette deprecation uyarısı; skip yok.
Rapor/Kanban/durum regresyonları birlikte: **146 passed**, 17 uyarı. Önceki testlerdeki değişmezlik kontrolü yeni completed_at alanının beklenen değişimini ayrıca doğrulayacak şekilde güncellendi; diğer alanlar ve yetkisiz kayıt koruma kontrolleri korunur.

Yeni ilk 30 test düzeltmeden önce **2 failed / 28 passed** idi. Tamamlanmış görevin sonradan düzenlenmesinde tamamlanma gününün kayması ve büyük veride gereksiz ORM yüklemesi doğrulandı ve düzeltildi.

Frontend mevcut testleri: **16 passed / 3 dosya**; lint ve build başarılı. Bu testler yeni rapor UI testleri olarak sayılmadı; aşağıdaki kontroller gerçek tarayıcıda yapıldı. Node 25.7.0 engine uyumluluk uyarıları, mevcut 3 fast-refresh lint uyarısı ve 500 kB bundle uyarısı başarısızlık değildir.

Tam backend son tarama: **790 passed, 83 warnings in 495.04s (0:08:15)**; fail/skip yok. Önceki tam taramadaki 10 eski değişmezlik varsayımı yeni tamamlanma alanını ayrıca doğrulayacak şekilde güncellendi; son paket temiz geçti. Ham sonuç: `us023-full-final.txt`.

## Kabul kapsamı

| Kontrol | Veri / beklenen | Sonuç |
| --- | --- | --- |
| Kişi başı durum ve efor | TODO 1, IN_PROGRESS 1, REVIEW_TESTING 1, DONE 3; yalnız DONE eforu 6 | API geçti |
| Sprint filtresi | Yalnız seçilen sprintteki görevler; DONE 2 | API geçti |
| Sıfır görevli üyeler | Üye satırı var, tüm sayılar 0 | API/UI geçti |
| Proje/hedef ayrımı | Diğer proje, atamasız görev ve aktif olmayan görevler kişi sayımını şişirmez | API geçti |
| Gün sınırları | 00:00 dahil, 23:59:59.999999 dahil; önce/sonra 1 mikrosaniye hariç | API geçti |
| Hafta | Pazartesi–Pazar; Pazar tarihi; yıl taşması 2026-12-28–2027-01-03 | API geçti |
| Ay | 30/31 gün; Şubat 28 ve 2028 artık yıl 29 gün | API geçti |
| Seri | Her gün tam bir satır, sıralı, boş günler 0; seri toplamları özetle aynı | API geçti |
| Varsayılan dönem/tarih | WEEKLY ve sunucunun UTC bugünü | API geçti |
| Hatalı dönem/tarih | YEARLY/daily, geçersiz tarih ve 2026-02-29: 422 | API geçti |
| Sprint hatası | Olmayan/başka proje sprinti 404; metin sprint_id 422 | API geçti |
| Oturumsuz | Her iki rapor 401 UNAUTHORIZED | API geçti |
| Proje üyesi ekip üyesi | Her iki rapor 403 FORBIDDEN; UI yalnız yönetici uyarısı | API/UI geçti |
| Proje dışı yönetici | Her iki rapor 403 PROJECT_ACCESS_DENIED; UI tablo göstermiyor | API/UI geçti |
| Olmayan proje | Yöneticiye her iki rapor 404 PROJECT_NOT_FOUND | API geçti |
| Tamamlandıktan sonra başlık düzenleme | 20 Kasım DONE, 23 Kasım düzenleme: tamamlanma 20 Kasım'da kalır | Regresyon geçti |
| Eski DONE düzenleme | Başlık, atama ve tekrar DONE isteği eski tamamlanma tahminini korur | 3 regresyon geçti |
| Yeniden açma/tamamlama | Mevcut DONE raporu yeniden açılanı çıkarır; tekrar DONE son geçiş gününü sayar | Regresyon geçti |
| Büyük veri | 10.000 görev, 5 tekrar; doğru 10.000 oluşturulan / 5.000 tamamlanan; kişi DONE eforu 15.000 | Geçti |

## Düzeltmeler

1. `Task.completed_at` ve `0007` migration eklendi. DONE geçişinde bitiş zamanı tutulur; başlık/atama veya tekrar DONE isteği bu zamanı değiştirmez; yeniden açıldığında temizlenir. API yanıt sözleşmesinin Task alanları değişmedi.
2. Dönem raporu tüm Task nesnelerini ve comments/files/labels ilişkilerini yüklemek yerine iki SQL gruplamasıyla gün ve toplam sütunlarını getirir. Yetki denetimleri korunur.
3. Eski DONE kayıtları migration sırasında mevcut `updated_at` tahminiyle doldurulur. Bu, bilinmeyen gerçek tarihleri geri üretmez; sonraki düzenlemelerin mevcut tahmini değiştirmesini önler. Ham/import edilen nullable kayıtlar için raporda aynı geri dönüş vardır.

## Performans ölçümü

İzole bellek içi SQLite, 10.000 görev, her uç için 5 ardışık gerçek API isteği. Kurulum süre dışıdır; ölçüm auth/üyelik/SQL/yanıtı içerir. Ham süre ve sorgu sayıları `us023-performans.json` dosyasında.

| Uç | Önce ortanca ms | Sonra ortanca ms | Önce SELECT | Sonra SELECT |
| --- | ---: | ---: | --- | --- |
| Kişi raporu | 27.363 | 20.526 | 7,6,6,6,6 | 7,6,6,6,6 |
| Dönem raporu | 590.806 | 35.002 | 65,65,65,65,65 | 6,6,6,6,6 |

Bu süreler tek makine/SQLite ölçümüdür; canlı PostgreSQL, eşzamanlı yük veya NFR-008 sayfa kullanılabilirliği kabulü değildir. CI'da donanıma bağlı süre eşiği yerine doğru sayım ve en fazla 8 SELECT yapısal regresyon sınırı kullanılır; 8 ürün gereksinimi değildir.

## Gerçek HTTP ve tarayıcı kanıtı

Uvicorn localhost:8010 + React localhost:5177, ayrı `us023-ui.db`; gerçek login ile sentetik hesaplar. 14 HTTP kontrolü `us023-api-kaniti.json` dosyasına token/parola olmadan kaydedildi.

UI bilinen veri: üyenin TODO/IN_PROGRESS/REVIEW_TESTING/DONE sayıları 1/1/1/2, efor 6. Sprint seçilince 1/1/1/1, efor 3. 23 Kasım günlük 4 yeni/1 tamamlanan, 22 Kasım günlük 1/1, 23–29 Kasım haftalık 4/1, 16–22 Kasım haftalık 1/1, Kasım aylık 5/2; aylık tabloda başlık dahil 31 satır. Grafik değerleri ve tablo aynı veriyi gösterdi. Sıfır görevli projede yönetici satırı 0 ve “Bu dönemde görev hareketi yok.” görüldü; yenileme başarılı. Üye olmayan yöneticide 0 rapor tablosu ve erişim uyarısı; ekip üyesinde yalnız yönetici uyarısı doğrulandı.

Ekranlar: `us023-raporlar.png`, `us023-sifir-gorev.png`, `us023-yetki.png`.

## Migration ve sınırlamalar

İzole SQLite kopyasında 0007→0006→0007 denendi; 5 görevin id/proje/başlık/durum/created_at/updated_at değerleri korundu. Eski 2 DONE kaydı `updated_at` tahminiyle tamamlandı; diğer durumlar null kaldı. Ham doğrulama `us023-migration.json`.

Downgrade completed_at alanındaki yeni bilgiyi kaldırır; gerçek ortamda geri dönüşten önce yedek gerekir. Bu çalışma canlıya migration/deploy uygulamadı. Gerçek PostgreSQL migration ve sorgu/yük kabulü ayrıca CI/entegrasyon ortamında doğrulanmalıdır.

Eski tamamlanma geçmişi bulunmadığından eski tarihlerin doğruluğu garanti edilemez. Tanımlı mevcut rapor semantiği korunur: şu an DONE olan görevlerin son DONE geçişi sayılır; tüm tarihsel durum olaylarının dökümü oluşturulmaz. Dışa aktarma US-039 / FR-064 kapsamındadır.

## Yeniden çalıştırma

Backend'de:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_report_acceptance.py tests/test_reports.py -q -s
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend'de `npm.cmd ci`, `npm.cmd run lint`, `npm.cmd test`, `npm.cmd run build`.

PR inceleme/onayı ekipten beklenir; onay gelmeden “PR açıldı ve onaylandı” kutusu işaretlenmez. CI ve ekip onayı PR üzerinde ayrıca izlenir; bu rapor yerel test sonuçlarını içerir.
