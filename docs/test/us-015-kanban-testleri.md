# US-015 Kanban test raporu

- Tarih / test eden: 25.10.2026 / Hakan.
- Görev #163; story #25; FR-042, FR-043.
- Referanslar: `docs/analiz/user-stories.md` US-015; `docs/api/api-sozlesmesi.md` 1.2, 1.3, 6.5, 7.1; `docs/test/test-plani.md`.
- Temel commit: develop `3237fc8b5c69cfb580404a90ff2e8f0877aa1aad`.
- Ortam: Windows, Python 3.12.14, FastAPI TestClient; her test için izole bellek içi SQLite.
- Veriler sentetik SQL fixture ile hazırlanır. Kimlik doğrulama değiştirilmedi; gerçek JWT ve route çalışır. Görev oluşturma ve login kabul testi sayılmaz; geliştirme veritabanına dokunulmadı.

## Sonuç ve açık bağımlılıklar

**US-015 kabulü BLOKLU: #161 Kanban GET API'si ve #162 Kanban/sürükle-bırak arayüzü henüz develop'ta yok.** Hazır olan PATCH durum API'sinin 15 kontrolü geçti; bu sonuç, kartların doğru sütunda görüntülendiğini veya tarayıcıda sürükle-bırak/geri dönüşün çalıştığını kanıtlamaz.

25.10.2026 incelemesinde #161 ve #162 açık. `GET /api/v1/projects/{project_id}/board` OpenAPI'de kayıtlı değil. Geçerli üyenin proje detayına isteği 200 dönerken aynı projenin board isteği 404 dönüyor. Sprint parametreli istek de 404. Bu 404'ler yetki kontrolü veya filtreleme başarısı sayılmadı. `frontend/src/App.tsx` ve `features/projects/ProjectDetailPage.tsx` içinde Kanban route/bileşeni yok. Tasarım görseli çalışan uygulama kanıtı sayılmadı.

Eksik geliştirmeler zaten #161 (EmreKaanSensoy) ve #162 (sefakrds) ile takip ediliyor; aynı eksikler için mükerrer hata açılmadı. Test edilen PATCH senaryolarında yeni hata saptanmadı.

## Otomatik kapsam ve gözlenen sonuçlar

`backend/tests/test_kanban_acceptance.py`: **15 passed, 17 skipped, 1 warning in 0.42s**.

| Kapsam | Adet | Beklenen | Sonuç |
|---|---:|---|---|
| Atanan üye / proje üyesi yönetici, dört hedef durum | 8 | 200, DB kalıcı değişir; durum dışı alanlar korunur | Geçti (API) |
| Başka ekip üyesi / dış üye / dış yönetici kart taşıma isteği | 3 | 403 NOT_TASK_ASSIGNEE; tüm DB satırı aynı | Geçti (API) |
| Onay bekleyen / reddedilmiş görev, atanan kişi / yönetici | 4 | 400 TASK_NOT_ACTIVE; tüm DB satırı aynı | Geçti (API) |
| Atanan üye / başka proje üyesi / yönetici panoyu okur | 3 | Sıralı dört sütun; yalnız aktif ana görevler; Task şeması; doğru durum/proje; tekil kart | Bloklu #161 |
| Boş proje | 1 | Dört sütun ve boş tasks dizileri | Bloklu #161 |
| Sprint 2 / 3 / eşleşmeyen sprint filtresi | 3 | Yalnız eşleşen aktif ana görevler; plansız ve başka proje görevleri hariç | Bloklu #161 |
| Dış üye / proje dışı yönetici pano erişimi | 2 | 403 PROJECT_ACCESS_DENIED; kart verisi yok | Bloklu #161 |
| Oturumsuz pano erişimi | 1 | 401 | Bloklu #161 |
| Bulunmayan proje | 1 | 404 PROJECT_NOT_FOUND; boş pano gibi gösterilmez | Bloklu #161 |
| Taşıma ardından dört hedef durum için panoyu yeniden okuma | 4 | Kart yalnız yeni sütunda bir kez görünür | Bloklu #161 |
| Yetkisiz taşıma ardından panoyu yeniden okuma | 1 | API pano içeriği korunur; tarayıcı geri dönüşü ayrıca test edilir | Bloklu #161 |
| 200 ana görev / 20 üye | 1 | 200 tekil kart, sütunlarda 50'şer kart; eksik/yinelenen yok | Bloklu #161 |

`TODO`, `IN_PROGRESS`, `REVIEW_TESTING`, `DONE` sırasıyla To Do, In Progress, Review & Testing, Done sütunlarıdır. Test verisi ayrıca ONAY_BEKLIYOR, REDDEDILDI, her durumdan alt görev, başka proje görevi ve sprint'siz görev içerir. Aktif görev durumları testte sözleşmeden sabit yazılmıştır; uygulamadaki filtreye göre beklenti üretilmez.

## Çalıştırma ve tekrar test kapısı

Backend klasöründe:

```powershell
python -m pytest tests/test_kanban_acceptance.py -q -rs
python -m pytest -q
```

Tam backend sonucu: **191 passed, 18 skipped, 10 warnings in 49.85s**. 17 skip bu işin eksik GET board API'sine, 1 skip önceden mevcut US-005 görev atama bağımlılığına aittir. US-014 PR #181 ayrı dalda/onay beklediğinden bu dalın toplamına eklenmedi. Uyarılar mevcut Starlette/httpx ve HTTP_422 deprecation uyarılarıdır.

Yalnızca GET board route'u OpenAPI'de yokken 17 kabul testi skip olur; route eklendiğinde otomatik çalışırlar. HTTP 400/403/404/500 gibi gerçek yanıt hataları skip gerekçesi değildir. Tekrar testte eksik route'u da başarısızlık saydırmak için:

```powershell
$env:LUNO_REQUIRE_KANBAN = '1'
try {
  python -m pytest tests/test_kanban_acceptance.py -q -rs
} finally {
  Remove-Item Env:LUNO_REQUIRE_KANBAN
}
```

Bu kapı, boş pano testi üzerinde ayrıca denendi: route eksik olduğu için beklenen `US-015 BLOCKED` setup hatasını verdi (1 error). Böylece skip'lerin kabul başarısı gibi değerlendirilmesi önlenir. Bu kasıtlı kontrol, normal suite sonucu ile karıştırılmamalıdır. Mevcut CI'nin yeşil olması Kanban kabulü anlamına gelmez.

## İstek / yanıt kanıtı

`us-015-api-kaniti.json`: gerçek TestClient ile 9 istek; geçerli proje erişimi, eksik pano GET'si (sprint'li/sprint'siz), yetkili PATCH, yetkisiz PATCH, yönetici PATCH ve onay bekleyen görev kontrolü. PATCH kayıtları DB önce/sonra görüntüsü içerir. Token veya şifre yayınlanmaz. Sentetik fixture ve SQLite kapsamı, tarayıcı veya üretim PostgreSQL ölçümü sayılmaz.

## Arayüz kabul senaryoları — henüz uygulanamadı

Önkoşul: #161 ve #162 develop'a birleştirilmeli; mevcut PATCH durum API'si çalışmalı. Test projesinde atanan kişi, başka ekip üyesi, proje üyesi yönetici, proje dışı kullanıcı; dört aktif durum, onay bekleyen/reddedilmiş görev, alt görev, ikinci proje ve boş proje bulunmalı.

| ID | İşlem | Beklenen | Durum |
|---|---|---|---|
| UI-015-01 | Proje detayından Kanban'a geç | To Do, In Progress, Review & Testing, Done; her aktif ana kart doğru sütunda, bir kez | Bloklu #161/#162 |
| UI-015-02 | Onay bekleyen, reddedilen, alt ve başka proje görevlerini kontrol et | Panoda görünmez; ana görev sayısı doğru | Bloklu #161/#162 |
| UI-015-03 | Atanan üye olarak kartı dört sütun arasında taşı; yenile ve tekrar aç | PATCH hedefi doğru; tek kart yeni sütunda kalıcı; eski sütun sayısı azalır, yenisi artar | Bloklu #161/#162 |
| UI-015-04 | Proje üyesi yöneticiyle başkasına atanmış ve atamasız kartı taşı | Güncelleme başarılı ve yeniden açınca korunur | Bloklu #161/#162 |
| UI-015-05 | Başka ekip üyesiyle kartı yetkisiz taşı; 403 yanıtını gözle | Açıklayıcı mesaj; kart eski sütununa geri döner; hayalet/yinelenen kart ve yanlış sayaç oluşmaz; yenileme de eski durumu gösterir | Bloklu #161/#162 |
| UI-015-06 | Boş proje ve varsa sprint seçimini aç/değiştir | Boş dört sütun; filtre doğru, diğer sprint/plansız kart sızıntısı yok | Bloklu #161/#162 |
| UI-015-07 | Proje dışı kullanıcı veya oturumsuzken pano URL'sini aç | Kart verisi gösterilmez; yetki/oturum davranışı anlaşılır | Bloklu #161/#162 |
| UI-015-08 | Ağ hatası/5xx veya süresi dolmuş oturum sırasında taşıma dene | Sahte başarı yok; kart ve sayaçlar tutarlı; hata/yeniden deneme veya oturum bildirimi | Bloklu #161/#162 |
| UI-015-09 | 200 görev/20 üyeli test projesini aç ve kart taşı | NFR-011: hata/eksik/çift kart yok; 100 görev ve uyanık sunucuda NFR-008 kullanılabilirlik süresi <=2 saniye ayrıca ölçülür | Bloklu #161/#162 |

Fixture'daki 200 görev kontrolü yalnız API hacim doğrulamasıdır; render/sürükle-bırak veya süre ölçümü yapılmış sayılmaz. Kartların sütun içi sıralaması için sözleşmede olmayan bir iş kuralı eklenmedi.

## Takip / tamamlanma koşulu

**#161 ve #162 tamamlanıp develop'a birleştirildikten sonra US-015 tekrar gözden geçirilecek: 17 API kabul testi zorunlu modda ve yukarıdaki 9 arayüz senaryosu çalıştırılacak; yeni hata varsa Hata Raporu şablonuyla açılacak; kanıtlar, bu rapor ve #163 güncellenecek.**

Şu anda #163'teki üç ürün kabul tiki (doğru sütun, sürükle-bırak/geri dönüş, onay bekleyenlerin gizlenmesi) işaretlenmemeli. Test kodu çalışıyor ve board güncellendi işaretlenebilir. PR ekip tarafından onaylanmadan “PR açıldı ve onaylandı” işaretlenmez. Görev In progress ve açık kalır; bu test teslimi tam ürün kabulü değildir.
