# US-017 Gantt test raporu

- Tarih / test eden: 01.11.2026 / Hakan.
- Görev: #195; story: #27; gereksinim: FR-045.
- Referans: `docs/analiz/user-stories.md` US-017; `docs/api/api-sozlesmesi.md` 1.3 ve 7.3; #193 API, #194 arayüz.
- Test edilen temel: develop `eb0263fb446b2e785ce32b7b16938a0f7a604233`.
- Ortam: Windows, Python 3.12.14, FastAPI TestClient, her testte ayrı bellek içi SQLite.
- Sentetik kullanıcı/proje/görevler SQL fixture ile hazırlanır; gerçek JWT ve Gantt route'u kullanılır, kimlik doğrulama taklit edilmez. Geliştirme/üretim veritabanı kullanılmaz. Bu çalışma login veya görev oluşturma kabul testi değildir.

## Sonuç

**Gantt API kontrolleri başarılı; grafik üzerindeki görsel kabul #194 nedeniyle bekliyor.** API hazır (#193 kapalı), ana React uygulamasında Gantt ekranı henüz bağlı değil (#194 açık). `frontend/src/App.tsx` ve `features/projects/ProjectDetailPage.tsx` bunu doğruluyor. `frontend/denemeler/takvim-rapor/src/GanttDemo.tsx` sabit deneme verileri kullanan ayrı bir demo olduğundan gerçek Gantt ekranı veya API entegrasyonu kabul kanıtı sayılmadı. Tasarım görselleri de çalışan ürün sayılmadı.

Test edilen API senaryolarında yeni hata bulunmadı. Eksik ekran zaten #194 ile takip edildiğinden mükerrer Hata Raporu açılmadı. US-017'nin tamamlandığı veya çubukların görsel olarak doğru çizildiği iddia edilmez.

## Kapsam ve gözlenen sonuçlar

Yeni dosya: `backend/tests/test_gantt_acceptance.py` — **39 geçti, skip/xfail yok**. Mevcut `test_tasks.py` içinde 4 temel Gantt testi de var; yeni kontroller sınırları ve güvenliği genişletir.

| Kontrol | Adet | Beklenen / gözlenen | Sonuç |
|---|---:|---|---|
| Dört aktif durumda yalnız başlangıç eksik / yalnız teslim eksik / ikisi eksik | 12 | items boş; DB tarihleri, durum ve updated_at değişmez | Geçti |
| Dört aktif durumda tam tarihli, alt görevsiz görev | 4 | Kimlik, Türkçe başlık, tarih, durum aynı; DONE=100, diğerleri=0 | Geçti |
| Tek gün, ay geçişi, yıl geçişi, artık yıl 29 Şubat | 4 | ISO tarihler kaymadan/kırpılmadan döner | Geçti |
| Karışık veride tarihli aktif alt görev; tarihsiz ana görev; onay/red/başka proje görevleri | 1 | Aktif tarihli alt görev parent_id ile döner; diğerleri dışlanır | Geçti |
| Ana görev ilerlemesi: 1/3, 2/3, tümü tamam, hiçbiri tamam değil, DONE ana görevde yarım alt işler, onay/red alt işler | 6 | 33.3, 66.7, 100, 0, 50, 33.3 | Geçti |
| Üye ve proje üyesi yönetici; boş proje | 2 | 200, proje tarihleri ve boş items | Geçti |
| Proje dışı üye ve proje dışı yönetici | 2 | 403 PROJECT_ACCESS_DENIED; items sızmaz | Geçti |
| Token yok / bozuk / süresi geçmiş / gerçek logout sonrası eski token | 4 | 401; items sızmaz | Geçti |
| Gerçek üye çıkarma API'si sonrası eski token | 1 | Çıkarma 204; Gantt 403 PROJECT_ACCESS_DENIED | Geçti |
| Bulunmayan proje | 1 | 404 PROJECT_NOT_FOUND; boş başarı yanıtı sayılmaz | Geçti |
| Görev DONE yapıldıktan sonra Gantt tekrar okuma | 1 | Yeni durum ve 100 ilerleme görünür | Geçti |
| 200 tarihli görev / 20 proje üyesi | 1 | 200 tekil öğe; eksik/yinelenen yok | Geçti (API hacmi) |

Her başarılı yanıtta sözleşme alanları, tekil task_id, aktif durum, parse edilebilir başlangıç/teslim tarihi ve 0..100 ilerleme kontrol edilir. API tarihleri proje aralığına kırpmıyor; 7.3'te böyle bir kural yok. Bu yüzden proje dışına taşan tarih aralıkları da aynen beklenir. Tarihsiz alt görevler Gantt items listesinde bulunmaz ancak sözleşmedeki 'tamamlanan alt görev oranı' hesabına dahildir; payda için belgede aktif/tarihli alt görev kısıtı yoktur. Ana görevin kendi DONE durumu alt görev oranını ezmemelidir.

`depends_on` için #193'ün açık kapsamı esas alındı: Sprint 9'a kadar boş liste. Sözleşmenin gelecekteki örneğindeki [40] bugün zorunlu tutulmadı; bağımlılık okları mevcut sprint kabulüne eklenmedi.

## Tekrarlanabilir çalıştırma

Backend klasöründe:

```powershell
python -m pytest tests/test_gantt_acceptance.py -q
python -m pytest tests/test_tasks.py -k gantt -q
python -m pytest -q
```

Yeni dosya sonucu: `39 passed, 2 warnings in 1.93s`. Uyarılardan biri mevcut Starlette/httpx deprecation, diğeri eski çalışma klasörünün pytest cache yazma izni uyarısıdır; ürün hatası değildir. Genel koşuda cache yazımı ayrı çalışma alanına yönlendirildi:

```powershell
python -m pytest -q -o cache_dir=../../pytest-cache-us017 --basetemp=../../pytest-us017-full
```

Tam backend sonucu: **436 passed, 45 warnings in 264.60s (0:04:24)**. Başarısız, atlanan veya xfail test yok. Genel koşudaki 45 uyarı mevcut Starlette/httpx ve HTTP_422 deprecation uyarılarıdır; cache yazma uyarısı ayrı cache klasörüyle giderildi.

Testler SQLite kullanır; üretim PostgreSQL yük testi veya tarayıcı render süresi ölçümü sayılmaz. CI, PostgreSQL migration ile backend testlerini ve frontend lint/build kontrollerini ayrıca çalıştırır.

## API kanıtı

`us-017-api-kaniti.json` gerçek uygulamaya yapılan 7 TestClient GET isteğinden üretilmiştir: boş Gantt, tarihli/tarihsiz/onay/red görevlerinin karışık yanıtı, yönetici erişimi, iki proje dışı rol, oturumsuz erişim ve bulunmayan proje. Kanıt üretirken dönen kimlik kümesi, dışlanan görevler, tam tarihler, 33.3 ve 100 ilerleme ayrıca assert edilmiştir. Token ve şifre içermez. API kanıtı grafik çizimi kanıtı sayılmaz.

## #194 sonrası arayüz kabul adımları

Önkoşul: #194 develop'a birleştirilmeli; API aynı güncel sürümde çalışmalı. Sentetik test projesinde aktif dört durum, eksik tarih kombinasyonları, alt görevler, onay/red görevleri, Türkçe başlık ve farklı yetkili kullanıcılar bulunmalı.

| ID | İşlem | Beklenen | Durum |
|---|---|---|---|
| UI-017-01 | Proje detayından Gantt ekranını aç, tarihli görevi API yanıtı ve gün ekseniyle karşılaştır | Görev çubuğu doğru başlangıç/teslim günlerini kapsar; bir gün kayma yok | Bloklu #194 |
| UI-017-02 | Yalnız başlangıç, yalnız teslim ve her iki tarihi eksik görevleri kontrol et | API items listesinde olmayan görevlere uydurma tarihli çubuk çizilmez; ekran çökmez | Bloklu #194 |
| UI-017-03 | Tek günlük, ay/yıl geçişi ve 29 Şubat görevlerini aç | Çubuk uzunluğu ve tarih sınırları doğru; yerel saat dilimi kayması yok | Bloklu #194 |
| UI-017-04 | Alt görevsiz DONE/diğer durumları ve alt görev oranı 33.3/66.7/100 olan ana görevleri karşılaştır | Dolgular API progress_percent ile aynı, ana/alt görev ilişkisi doğru | Bloklu #194 |
| UI-017-05 | Onay bekleyen/reddedilen ve başka projedeki görevleri ara | Grafik üzerinde görünmez, proje verisi karışmaz | Bloklu #194 |
| UI-017-06 | Boş projeyi ve yalnız tarihsiz görevli projeyi aç | Anlaşılır boş durum; sahte çubuk veya JS hatası yok | Bloklu #194 |
| UI-017-07 | Görevin durumunu/tarihlerini yetkili akıştan değiştirip Gantt'ı yeniden aç | Son tarih/durum/ilerleme API ile uyumlu, eski çizim kalmaz | Bloklu #194 |
| UI-017-08 | Proje dışı hesap, oturumsuz erişim ve ağ/5xx hatası dene | Veri sızmaz; uygun hata/oturum/yeniden deneme davranışı, eski projenin çubukları kalmaz | Bloklu #194 |
| UI-017-09 | Alan eşlemesini ve ekran yüklemesini denetle | task_id→id string, title→name, start_date→start, due_date→end, progress_percent→progress; React.lazy entegrasyonu doğrulanır | Bloklu #194 |
| UI-017-10 | 200 görev/20 üyeli proje, sonra 100 görev/uyanık sunucu ile ölç | NFR-011: eksik/çift çubuk/çökme yok; NFR-008 kullanılabilirlik <=2 saniye ayrıca ölçülür | Bloklu #194 |

Bu senaryolar uygulanmış/başarılı sayılmadı; API hacim testi tarayıcı performansı ölçümü değildir. Bağımlılık okları Sprint 9'da ayrıca doğrulanmalı.

## Takip ve tamamlanma koşulu

**#194 tamamlanıp develop'a birleştirildikten sonra 39 API kontrolü ve yukarıdaki 10 arayüz senaryosu tekrar çalıştırılacak. Sonuçlar, ekran kanıtları, bu rapor ve #195 güncellenecek; bulunan hatalar Hata Raporu şablonuyla açılacaktır.**

#195'te 'Görev çubuklarının doğru tarihlerde görünmesi' görsel kontrolü açık kalmalı. 'Tarihi olmayan görevlerin davranışı' API tarafında doğrulandı ancak arayüz kabulü beklediğinden tam tik verilmemeli. Yeni hata bulunmadığı not edilmeli; yapılmayan hata raporu veya ekip PR onayı tamamlandı sayılmamalı. Test kodu ve board güncellemesi işaretlenebilir. Kart In progress ve görev açık kalır.
