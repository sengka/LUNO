# US-020 Yorum testleri — #204

Tarih: 2026-11-02. İlgili story: #30; FR-050; API sözleşmesi 8.5–8.6.
Test edilen develop tabanı: `53144e7fec6999dfce2d12db3f673e724a40e672`.
Dal: `hakan-us020`. Sentetik kullanıcılar ve izole SQLite kullanıldı; gerçek kullanıcı verisine dokunulmadı.

## Sonuç ve bulunan hata

Görev yorumları için API ve gerçek React arayüzü doğrulandı. Dosya yorumlarında mevcut dosya için bile koşulsuz 404 dönen hata bulundu: #227. Dosya bulma ve proje üyeliği denetimi bağlandı; dosya yorumları oluşturulup sayfalı listeleniyor. Görev/dosya yorumları aynı sıralama ve yanıt oluşturma yardımcısını kullanıyor.

Düzeltme öncesi yeni testler: **10 failed, 40 passed**. Düzeltme sonrası yeni 50 test ve mevcut 8 yorum testi: **58 passed**, 24 deprecation uyarısı; skip yok.

Tüm backend regresyon paketi: **541 passed, 68 warnings in 399.74s**; fail/skip yok. Uyarılar mevcut Starlette deprecation bildirimleri. Ham çıktı `us020-backend-tests.txt` dosyasındadır.

## API kabul matrisi

Her senaryo görev ve dosya hedeflerinde çalışır. Test kurulumu model üzerinden sentetik veri oluşturur; kimlik doğrulama dependency'si ve yorum uçları mock edilmez. Geçerli JWT oluşturma yardımcısı kullanılır; login bu yeni testlerin konusu değildir.

| Senaryo | Beklenen | Sonuç / test sayısı |
| --- | --- | --- |
| Üye ve üye yönetici ekleme/listeleme; yazar, hedef, tarih ve DB kalıcılığı | 201 / 200; yazar sunucudaki kullanıcı; dış boşluklar temizlenir | Geçti / 4 |
| 1 ve 2000 karakter, Türkçe metin | 201; metin eksiksiz | Geçti / 4 |
| Eksik/null/sayı/boş/boşluk/2001 karakter body | 422, DB'ye yorum eklenmez | Geçti / 12 |
| Oturumsuz GET/POST | 401 UNAUTHORIZED | Geçti / 4 |
| Proje üyesi olmayan ekip üyesi ve yönetici GET/POST | 403 PROJECT_ACCESS_DENIED; yorum eklenmez | Geçti / 8 |
| Olmayan görev/dosya GET/POST | 404 TASK_NOT_FOUND / FILE_NOT_FOUND | Geçti / 4 |
| page=0/-1/x, limit=0/101 | 422 | Geçti / 10 |
| Aynı tarihte id sırası; sayfa 1/2/boş sayfa; diğer hedef yorumunun sızmaması | Eskiden yeniye; doğru total; tekrarsız sayfalama | Geçti / 2 |
| Üyelik silindikten sonra aynı tokenla GET/POST | 403; yazma yok | Geçti / 2 |

Ek gerçek HTTP kontrolü: localhost:8010 üzerinde 13 istek; gerçek multipart TXT yükleme → projeye ait, task_id=null dosya → dosya yorumu ekleme/listeleme; dosya listesinde comment_count; whitespace 422; oturumsuz 401; üye olmayan kullanıcı GET/POST 403; görev yorum listeleme ve uzunluk reddi. Tam yanıtlar `us-020-api-kaniti.json` dosyasındadır; token/parola kaydedilmedi.

## Gerçek tarayıcı kabul kontrolleri

React/Vite localhost:5177 + gerçek Uvicorn localhost:8010; ayrı `us020-ui.db` ve sentetik hesaplar.

| Kontrol | Gözlenen sonuç |
| --- | --- |
| Boş yorum listesi | “Henüz yorum yok. İlk yorumu sen yaz.” |
| Boş / yalnızca whitespace form | Gönder düğmesi devre dışı |
| Türkçe çok satırlı yorum gönderme | Listeye eklendi; ad ve saat görüldü; sayaç 0→1 |
| HTML benzeri `<script>` metni | Ekranda düz metin; çalıştırılmadı |
| Sayfa yenileme | Kaydedilen yorum yeniden listelendi |
| 2001 karakter | Sayaç 2001/2000; Gönder devre dışı |
| 2000 karakter | Gönder etkin (2000 karakterin kaydı ayrıca API kabul testinde doğrulandı) |
| Ctrl+Enter | İkinci yorum kaydedildi; form temizlendi; sayaç 2 |
| 51 yorumla sayfalama | İlk yüklemede 50 time öğesi; son yorum görünmüyor; “Daha fazla yorum göster” sonrası 51, son yorum görünüyor |
| Üye olmayan kullanıcının /gorevler/1 erişimi | Yetki uyarısı; yorum metni ve form görünmüyor |

Ekran kanıtları: `us020-yorum-arayuzu.png`, `us020-yetkisiz-arayuz.png` (bu raporla aynı klasör).

## Çalıştırma

Backend klasöründe:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_comment_acceptance.py tests/test_comments.py -q
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend klasöründe `npm.cmd ci`, `npm.cmd run build` , `npm.cmd run lint` ve `npm.cmd test` çalıştırıldı: build başarılı, mevcut frontend testleri **8 passed**. Bu 8 mevcut test, yeni yorum UI testleri olarak sayılmamıştır; yukarıdaki tarayıcı kontrolleri gerçek arayüz üzerinden yapılmıştır. Node 25.7.0 için bazı paketlerin engine uyarısı ve build'de 500 kB chunk uyarısı var; build/test başarısızlığı yok. CI desteklenen Node sürümünde ayrıca kontrol edilir.

## Açık kabul ve tekrar test koşulu

**Dosya yorum arayüzü bu develop sürümünde bulunmuyor.** #203 görev yorum ekranı tamamlanmış olsa da bu, #30'daki belge yorum arayüzünün doğrulandığı anlamına gelmez. Dosya arayüzü çalışması #197 açık; dosya detayında yorum formu/liste ekranı teslim edilince bu görev tekrar gözden geçirilmeli. Dosya yorum arayüzü için dosya yükle → yorum ekle/listele → yenile → boş/uzun yorum reddi → üye olmayan erişim senaryoları uçtan uca tekrarlanmalıdır. Backend 200/201 sonuçları UI kabulünün yerine geçmez.

Canlı Render/Supabase ortamında bu dal deploy edilmedi; canlı kabul geçildi olarak işaretlenmedi. Yorum bildirimi US-037 / FR-054 kapsamındadır, bu US-020 kabul sonucu bildirim teslimini kapsamaz.

#204 kapatılmamalı ve board Done yapılmamalı: dosya yorum UI tekrar testi ve ekip PR inceleme/onayı bekliyor. “PR açıldı ve onaylandı” kutusu ekip onayından önce işaretlenmez. “Yorum ekleme ve listeleme” maddesi belge arayüzü kabulü tamamlanana kadar açık bırakılmıştır. Boş yorum/üye olmayan kullanıcı, çalışan kod ve board güncellemesi doğrulandı.
