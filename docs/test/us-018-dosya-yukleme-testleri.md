# US-018 Dosya yükleme test raporu

- Tarih / test eden: 02.11.2026 / Hakan.
- Görev #198, story #28; FR-046, FR-047, NFR-006.
- Referanslar: `docs/api/api-sozlesmesi.md` 2 / File, 8.1, 8.2; `docs/analiz/user-stories.md` US-018; `docs/test/test-plani.md` TD-FILE.
- Test edilen temel: develop `ded5ec0bae4c53ad2550c9574fd242002ff2715d` + bu dalın #225 düzeltmesi.
- Ortam: Windows, Python 3.12.14, FastAPI TestClient, izole bellek içi SQLite ve her test için gerçek geçici LocalStorage.
- SQL fixture yalnız sentetik kullanıcı/proje/görev oluşturur; JWT ve multipart route gerçektir. Geliştirme/üretim DB'si veya gerçek ekip dosyaları kullanılmaz. Login/görev oluşturma kabulü sayılmaz.

## Sonuç

**Yerel API yükleme kontrolleri başarılı; #225 hatası bulunup düzeltildi. Arayüz kabulü #197 ve canlı Supabase doğrulaması #212 nedeniyle bekliyor.**

#196 API develop'ta hazır/kapalı. #197 açık; `frontend/src/features/tasks/TaskDetailPage.tsx` içinde yükleme alanı veya entegrasyonu yok. #212 açık. Supabase için gerçek bucket, erişim kuralları ve canlı ortamda kalıcılık bu çalışmada denenmedi; yerel depo testleri bunun yerine sayılmadı. Yeni bir altyapı, canlı dosya veya erişim izni oluşturulmadı.

## Bulunan ve düzeltilen hata: #225

Hata Raporu şablonuyla açıldı: https://github.com/sengka/LUNO/issues/225

Yerel deponun kök dizini oluşturulamadığında gerçek OSError, StorageError'a çevrilmiyordu. Yükleme API'si yalnız StorageError yakaladığından beklenen `503 STORAGE_UNAVAILABLE` JSON yerine `500 text/plain Internal Server Error` dönüyordu. İzole testte depo kökü olması gereken noktaya normal bir dosya konularak gerçek dosya sistemi hatası tekrar üretildi. İlk koşu **49 passed, 1 failed**: beklenen 503, gerçekleşen 500.

`backend/app/services/storage.py` içinde LocalStorage.save artık yazma/yayınlama OSError hatalarını StorageError'a çeviriyor. İçerik aynı dizinde geçici dosyaya yazılıyor; dosya kapatıldıktan sonra atomik replace ile nihai anahtara taşınıyor. Yazma veya yayınlama başarısızsa staging dosyası finally bloğunda temizleniyor (dosya sistemi temizliğe izin verdiği ölçüde). Mevcut dosyalar korunuyor. Supabase davranışı ve dosya türü/boyut politikası değişmedi.

Gerçek kök dizin hatası, kısmi yazma ve atomik yayınlama hatası ayrı regresyon testleriyle doğrulandı. Fix test dalında; develop'a geçiş ekip incelemesi ve PR birleştirmesine bağlıdır. #225 bu aşamada elle kapatılmamalıdır.

## Yeni otomatik kapsam

`backend/tests/test_file_upload_acceptance.py`: **52 passed, 3 warnings in 4.27s**; skip/xfail yok.

| Kontrol | Adet | Beklenen / gözlenen | Sonuç |
|---|---:|---|---|
| PDF/DOCX/XLSX/PPTX/PNG/JPG/TXT × proje veya görev | 14 | 201; doğru proje/görev/yükleyen/boyut/MIME; gerçek depodaki baytlar aynı; üye listede görür | Geçti |
| Mevcut 10 MiB uygulama eşiği -1 / eşit / +1 bayt | 3 | 201 / 201 / 413 FILE_TOO_LARGE; reddedilende DB ve depo aynı | Geçti (regresyon; birim notuna bakın) |
| İzin dışı uzantı, çift uzantı, MIME taklidi, format uyuşmazlığı, bozuk ZIP, ikili TXT | 14 | 415 UNSUPPORTED_FILE_TYPE; önceki DB satırları ve depo SHA-256 değerleri aynı | Geçti |
| Güvenilmeyen istemci Content-Type başlığı / büyük harf PNG uzantısı | 2 | Gerçek içerik türü esas alınır; response image/png | Geçti |
| Proje üyesi yönetici ve atanan kişi dışındaki proje üyesi, başkasının görevine yükler | 2 | 201; yetki proje üyeliğidir, yalnız atanan kişi kısıtı yok | Geçti |
| Proje dışı üye ve proje dışı yönetici | 2 | 403 PROJECT_ACCESS_DENIED; DB/depo aynı | Geçti |
| Oturum yok / bozuk / süresi geçmiş / logout sonrası eski token | 4 | 401; DB/depo aynı | Geçti |
| Başka proje görevi / bulunmayan görev / geçersiz task_id | 3 | 404 TASK_NOT_FOUND / 404 / 422 VALIDATION_ERROR; DB/depo aynı | Geçti |
| file alanı eksik | 1 | 422 VALIDATION_ERROR; DB/depo aynı | Geçti |
| Proje bulunamadı | 1 | 404 PROJECT_NOT_FOUND; DB/depo aynı | Geçti |
| Aynı adlı iki yükleme | 1 | Farklı anahtarlar, iki içerik de korunur; üzerine yazılmaz | Geçti |
| Üye çıkarıldıktan sonra eski token ile yükleme | 1 | 403; DB/depo aynı | Geçti |
| Simüle StorageError / gerçek yerel OSError / yayınlama hatası / kısmi yazma hatası | 4 | 503 STORAGE_UNAVAILABLE; DB/depo aynı, staging artığı yok | Geçti |

Her hata senaryosu önceden var olan bir dosya varken çalışır; yalnız boş depoda dosya sayısı değil, var olan satır ve içerik hash'leri de kontrol edilir. Yeni testler mevcut `test_files.py` içindeki temel yükleme/listeleme/indirme/silme ve depolama testlerini genişletir. US-019 indirme ve US-035 silmenin tam kabulü bu görevin kapsamına eklenmedi.

Örnekler küçük sentetik format tanıma verileridir: PDF/image sihirli baytları ve Office ZIP işaretleri kullanılır; Office veya resim uygulamasında açılabilir gerçek belge sertifikasyonu yapılmaz. Asıl API davranışı ve bayt bütünlüğü doğrulanır. #197 sonrası kullanıcı testinde normal açılabilir belgeler ayrıca kullanılmalıdır. İstemci MIME başlığını zorunlu doğru kabul eden yeni bir iş kuralı eklenmedi; mevcut API baytlardan tür tespiti yapıyor.

## Boyut birimi — açık sözleşme notu

Sözleşme yalnız '10 MB' diyor. Mevcut test planı, 10.000.000 ve 10.485.760 bayt yorumunun sözleşme sahibiyle netleştirilmesini istiyor. Uygulama şu an **10 × 1024 × 1024 = 10.485.760 bayt (10 MiB)** kullanıyor. Buradaki -1/eşit/+1 kontrolleri bu gözlenen politikanın regresyonudur; sözleşme belirsizliğini çözülmüş veya tam sınır kabulünü verilmiş saymaz. #198 takibinde birim kararı netleşince API/UI eşikleri ve test beklentisi birlikte güncellenmelidir.

## Çalıştırma

Backend klasöründe requirements.txt bağımlılıklarını kurduktan sonra:

```powershell
python -m pytest tests/test_file_upload_acceptance.py -q
python -m pytest -q -o cache_dir=../../pytest-cache-us018 --basetemp=../../pytest-us018-full
```

Tam backend sonucu: **504 passed, 48 warnings in 400.29s (0:06:40)**. Başarısız, atlanan veya xfail test yok. Bu sayı ded5ec0 temelindeki suite ve bu dalın 52 yeni testidir; başka açık QA dallarının sayıları eklenmemiştir.

Uyarılar mevcut Starlette/httpx TestClient ve HTTP_422 deprecation uyarılarıdır. İlk yükleme için requirements.txt'de zaten belirtilen python-multipart test ortamına kuruldu; bağımlılık listesi değiştirilmedi. SQLite/LocalStorage doğrulaması PostgreSQL veya Supabase canlı kabulü sayılmaz. CI ayrıca PostgreSQL migration, backend suite ve frontend lint/build çalıştırır.

## API kanıtı

`us-018-api-kaniti.json`: **15 gerçek multipart POST**. Yedi izinli format, görev hedefi, mevcut eşikte yükleme, büyük dosya 413, izin dışı tür 415, iki dış rol 403, yabancı task_id 404, oturumsuz 401 ve düzeltilmiş gerçek yerel depo hatasında 503 içerir. Her kayıtta dosya adı/boyut/SHA-256, yanıt, DB/depo önce-sonra sayısı, önceki verilerin korunması ve başarıda bayt eşitliği vardır. Dosya içeriği, token, parola veya Supabase anahtarı yayınlanmaz.

## Arayüz ve canlı depo tekrar test planı

#197 develop'a birleştirildiğinde:

| ID | İşlem | Beklenen | Durum |
|---|---|---|---|
| UI-018-01 | Üye olarak görev detayına yedi izinli formatta normal belge yükle | Yükleme ilerlemesi ve başarı görünür; doğru görev/proje listesinde, yenilemede kalıcı | Bloklu #197 |
| UI-018-02 | Normal boyut, sözleşme sahibiyle netleşmiş eşik alt/eşit/üst dosyalar seç | Alt/eşit kabul; üst dosya kaydedilmez, açıklayıcı boyut hatası; UI/API aynı eşiği kullanır | Bloklu #197 + birim kararı |
| UI-018-03 | İzin dışı ve uzantısı/içeriği uyuşmayan dosyayı dene | Anlaşılır tür hatası; başarı mesajı veya hayalet liste satırı yok | Bloklu #197 |
| UI-018-04 | Proje dışı hesap / çıkarılmış üye / oturumu bitmiş kullanıcıyla yüklemeyi dene | İşlem engellenir; anlaşılır yetki/oturum bildirimi; dosya kaydedilmez | Bloklu #197 |
| UI-018-05 | Aynı adlı farklı içerikleri yükle; sayfayı yenile | İki kayıt ve doğru hedefler korunur; sessiz üzerine yazma yok | Bloklu #197 |
| UI-018-06 | Ağ/503 hatası sırasında yükleme yap; sonra yeniden dene | Hata gösterilir; sahte başarı/bozuk kayıt yok; tekrar deneme mümkün | Bloklu #197 |
| UI-018-07 | Türkçe ad ve görev hedefiyle yükle; görevden/projeden dosyayı kontrol et | Ad ve hedef doğru; sayfa yenilemede uyumlu | Bloklu #197 |

#212 test ortamında hazır olduğunda: özel test bucket'ında proje üyesi yüklemesi, dış kullanıcı reddi, bayt bütünlüğü ve uygulama yeniden başlatma/deploy sonrası kalıcılık doğrulanmalı. Supabase'in gerçek erişim kuralları ayrıca incelenmeli; anahtarlar kanıt dosyasına konmamalıdır. Canlı üretim bucket'ında bu çalışma için veri oluşturulmadı.

**#197 ve #212 tamamlanıp test ortamı hazır olduktan sonra bu görev yeniden gözden geçirilecek; 52 API kontrolü, 7 UI senaryosu ve canlı depo kontrolleri çalıştırılıp rapor/#198 güncellenecek. Yeni hatalar Hata Raporu şablonuyla açılacak.** Boyut birimi ayrıca sözleşme sahibiyle netleştirilecek. Ekip PR onayı ve bu kabul adımları tamamlanana kadar görev In progress/açık kalır. #198'in ilk iki tiki bu rapordaki API kapsamının tamamlandığını gösterir, ekran/canlı kabulünün verildiği anlamına gelmez.
