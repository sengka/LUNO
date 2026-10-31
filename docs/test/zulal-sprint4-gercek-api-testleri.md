# Görev ekranları API doğrulaması (#156, #165, #168)

Tarih: 26 Ekim 2026. Branch: `zulal`. `origin/develop` (`976f5ea`, #185 birleşimi) alındı; #156, #165, #168 ve `f747c9c` korundu. README okundu; erişilebilir proje dizinlerinde AGENTS.md bulunmadı.

## Ortam ve yöntem

- Backend mevcut `backend/.venv/Scripts/python.exe` ile çalıştırıldı. Öncesinde `python -m alembic upgrade head` başarılı oldu; veritabanı zaten head seviyesindeydi.
- Uvicorn `127.0.0.1:8000`, Vite `127.0.0.1:5173` üzerinde çalıştı; frontend HTTP 200 döndü.
- API sözleşmesinin 6.1–6.11 bölümleri ve güncel görev/etiket şemaları incelendi.
- HTTPX ile çalışan gerçek API ve mevcut yerel veritabanına 62 istek gönderildi. İstek gövdeleri, durum kodları ve ilgili yanıt alanları [kanıt dosyasında](zulal-sprint4-live-api.json) kayıtlıdır. Token/şifre kaydedilmedi. Bu çalışma mock veya tarayıcı testi değildir.
- Tarayıcı envanteri boştu; `cua.createBrowserTab('iab', ...)` çağrısı `Browser is not available: iab` döndürdü. Gerçek tarayıcı testi yapılamadı.

## Gerçek API sonuçları

| Senaryo | Sonuç |
| --- | --- |
| Geçici görev oluşturma ve detay | POST 201, GET 200 |
| Boş/tek karakter/201 karakter başlık | PATCH 422 VALIDATION_ERROR |
| Teslim tarihi başlangıçtan önce | PATCH 400 INVALID_DATE_RANGE |
| Başlık, açıklama, tarihler kaydı | PATCH 200; sonraki GET değerleri birebir korudu |
| Üç öncelik ve altı Fibonacci efor değeri | Her değer PATCH 200; ayrı GET ile kalıcılık doğrulandı |
| Geçersiz öncelik ve efor 4 | PATCH 422 |
| Renk gönderilmeden etiket oluşturma | POST 201; color #6B7280 |
| #3a4CA0 rengiyle etiket oluşturma | POST 201 |
| Aynı etiketin büyük harfli adı | POST 409 LABEL_EXISTS |
| Boş/uzun ad, kısa/başında boşluk olan/boş renk | POST 422 |
| Mevcut etiketi koruyarak ikinci etiketi ekleme | Önce [1], sonra [1,2] ile PATCH 200; GET iki etiketi de döndürdü |
| Alt görev ekleme ve parent_id ile listeleme | POST 201, GET 200; oluşturulan alt görev listede |
| Alt görevi DONE yapma ve ana görev ilerlemesi | PATCH 200; ana görev GET yanıtında 1/1 tamamlandı |
| İç içe alt görev | POST 400 NESTED_SUBTASK_NOT_ALLOWED |
| Ekip üyesinin alt görev eklemesi | POST 201, ONAY_BEKLIYOR |
| Ekip üyesinin detay erişimi / düzenleme / silme | GET 200; PATCH ve DELETE 403 FORBIDDEN |
| Üyesi olunmayan projenin görevi | GET /tasks/16: 403 PROJECT_ACCESS_DENIED |
| Oturumsuz detay erişimi | GET 401 |
| Yalnızca testte oluşturulan ana görevleri silme | DELETE 204; ana ve alt görevlerin sonraki GET istekleri 404 |

Testte oluşturulan iki ana görev ve iki alt görev silindi. İlk akışta id'ler 20, 21 ve 22 idi; ikinci akışta SQLite ana görev için id 20'yi yeniden kullandı. Önceden var olan görevler değiştirilmedi/silinmedi. Proje 1 içinde `API test 898dc6d1` (id 1) ve `API test color 898dc6d1` (id 2) etiketleri kaldı; etiket silme endpoint'i bulunmadığından doğrudan veritabanı müdahalesi yapılmadı. `can@ornek.com` ile giriş 401 verdi; üye olmayan erişimi Sena'nın proje 2 göreviyle test edildi.

## İlk API çalışmasından sonra tarayıcıda bekleyen doğrulamalar

- Görev detayını açma ve sayfayı yenileme; düzenleme, öncelik/efor ve etiket sonuçlarının yenilemeden sonra görünmesi.
- Başlık/tarih/etiket alan hatalarının Türkçe ve ilgili alan altında görünmesi.
- Alt görev listesi, ilerleme çubuğu ve iç içe ekleme kontrolünün görünümü.
- Ekip üyesinde düzenle/sil kontrollerinin gizlenmesi.
- Yalnızca yeni geçici görev üzerinde silme penceresinde iptal/onay ve silme sonrası proje yönlendirmesi.

API'den tekrar GET yapılması, tarayıcı yenilemesi veya silme iptal/onay akışının doğrulandığı anlamına gelmez. İncelenen frontend kodunda somut hata doğrulanmadığından frontend kaynak değişikliği yapılmadı. Test edilen API akışlarında backend hatası görülmedi; backend kaynakları ve LUNO-api-test değiştirilmedi, seed/reset çalıştırılmadı.

## İlk API çalışması sırasındaki entegrasyon ve kontroller

- [#185](https://github.com/sengka/LUNO/pull/185) develop'a birleşmiş durumda.
- [#187](https://github.com/sengka/LUNO/pull/187) kontrol anında **açık, merged=false**, hedefi develop. Sefa branch'i birleştirilmedi. Görev oluşturma formunda öncelik/efor ile Kanban rozetleri/alt görev ilerlemesi entegrasyonu bekliyor.
- `npm run build`: başarılı; mevcut 500 kB paket boyutu uyarısı var.
- `npm run lint`: başarılı; badge, button ve tabs dosyalarında mevcut üç Fast Refresh uyarısı var.
- `git diff --check`: başarılı.
- PR taslak durumu ve görevlerin açık durumu değiştirilmedi.

## Güncel entegrasyon ve kullanıcı tarafından yapılan manuel kontroller

26 Ekim 2026: #178 ve #187 develop'a birleşti. Yerel `zulal`, `origin/develop` (`6c2bbae`) seviyesine fast-forward ile güncellendi. Kanban'ın görünmemesinin nedeni, doğru LUNO klasöründen çalışan Vite'ın henüz #187'yi içermeyen eski yerel kodu sunmasıydı.

Bu teslimde görev oluşturma formuna Düşük/Orta/Yüksek öncelik ve 1, 2, 3, 5, 8, 13 efor seçimleri eklendi. Seçilmemiş alanlar istekten çıkarılıyor. #187 ile gelen öncelik/efor rozetleri korundu; Kanban kartlarına tamamlanan/toplam alt görev sayısı ve ilerleme çubuğu eklendi. Oluşturulan görevin detayı önbelleğe yazılıyor; durum/sorumlu değişikliklerinde ilgili görev detayları, alt görev listeleri, Kanban ve proje verileri yenileniyor.

Aşağıdaki kontrolleri **kullanıcı kendi yerel tarayıcısında** yaptı ve sonuçlarını bildirdi. Bunlar ajan tarafından yürütülen tarayıcı testleri değildir; önceki kanıt dosyasındaki **62 API isteğinin sayısı değişmemiştir**.

| Kullanıcının manuel kontrolü | Bildirilen sonuç |
| --- | --- |
| Proje 1 Kanban | Dört sütun görünüyor |
| Görev #1 kartı | Orta öncelik, 8 efor, Arayüz Testi etiketi ve 1/3 alt görev ilerlemesi göründü |
| Oluşturma formu | “Geçici entegrasyon testi” Yüksek öncelik ve 5 efor ile oluşturuldu; değerler detayda ve kartta doğru göründü |
| Alt görev ekleme | Geçici görevin kartı 0/1 gösterdi |
| Alt görevi Done yapma | Kart 1/1 ve dolu ilerleme çubuğuna güncellendi |
| Mehmet hesabıyla geçici görev | Düzenle/Sil görünmedi; durum ve sorumlu alanları değiştirilemiyordu |
| Sena ile silmeyi iptal etme | Geçici görev kaldı |
| Sena ile silmeyi onaylama | Geçici ana görev kaldırıldı |

Bu manuel silme kontrolü, alt görevin kaskad silindiğini ayrıca doğrulamaz. Silme sonrası yönlendirme, sayfa yenilemesiyle kalıcılık, alan hatalarının görünümü ve iç içe alt görev engelinin tarayıcıdaki davranışı bu kullanıcı bildirimi kapsamında doğrulanmış sayılmamıştır. Önceki API sonuçları kendi kapsamıyla geçerlidir.

Son kod değişikliklerinden sonra `npm run build`, `npm run lint` ve `git diff --check` başarılı oldu. Build'de mevcut paket boyutu uyarısı, lint'te button/badge/tabs bileşenlerindeki üç Fast Refresh uyarısı sürüyor. Bu teslim hazırlığında kod değiştirilmedi; yalnızca bu rapor güncellendi ve diff kontrolü tekrarlandı. Güncel origin/develop ile uyum kontrol edildi. Veritabanına müdahale edilmedi; LUNO-api-test değiştirilmedi.
