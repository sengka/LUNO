# US-014 Görev durumu test raporu

- Tarih: 25.10.2026; test eden: Hakan.
- Görev: #160; story: #24; FR-033 ve FR-034.
- Referans: `docs/analiz/user-stories.md`, `docs/api/api-sozlesmesi.md` bölüm 1.2 ve 6.5.
- Test edilen temel: `develop`, `3237fc8b5c69cfb580404a90ff2e8f0877aa1aad`.
- Ortam: Windows, Python 3.12.14, FastAPI TestClient, her testte ayrı bellek içi SQLite.
- Test verisi: sentetik kullanıcı/proje/görev SQL fixture'ı; uygulama veritabanı kullanılmadı. Kimlik doğrulama bağımlılığı değiştirilmedi, gerçek JWT kontrolü çalıştırıldı. Bu testler giriş akışının veya görev oluşturma API'sinin kabul testi değildir.

## Sonuç

**API kontrolleri başarılı; arayüz kabul testi #159 bağımlılığı nedeniyle BEKLİYOR.** Yeni API hatası saptanmadı. Story'nin uçtan uca tamamlandığı iddia edilmez.

Yeni dosya `backend/tests/test_task_status_regression.py`: **77 geçti, atlanan yok**. Mevcut `test_tasks.py` temel yetki, atamasız görev, bulunamayan görev ve yanıt şeması kontrollerini zaten içerir; yeni testler bunları aşağıdaki sınırlarla genişletir.

| Kontrol | Adet | Beklenen / gözlenen | Sonuç |
|---|---:|---|---|
| Atanan üye ve proje üyesi yönetici; dört aktif durumun 4x4 geçiş matrisi | 32 | 200; DB kalıcı güncelleme, updated_at ilerler; diğer alanlar ve komşu görev aynı | Geçti |
| Başka ekip üyesi, dışarıdaki üye, proje dışındaki yönetici; dört hedef durum | 12 | 403 NOT_TASK_ASSIGNEE ve açıklayıcı mesaj; tüm DB satırı aynı | Geçti |
| ONAY_BEKLIYOR ve REDDEDILDI; atanan kişi/yönetici; dört hedef durum | 16 | 400 TASK_NOT_ACTIVE; tüm DB satırı aynı | Geçti |
| Eksik/null/boş/küçük harf/bilinmeyen/onay/red/sayı/boolean/liste/nesne durum | 11 | 422; DB değişmez | Geçti |
| Token yok, bozuk token, süresi geçmiş token, gerçek logout sonrası eski token | 4 | 401; DB değişmez | Geçti |
| Gerçek üye çıkarma API'si sonrası eski token ile güncelleme | 1 | Çıkarma 204, atama null; güncelleme 403; DB değişmez | Geçti |
| Yönetici rolü kaldırıldıktan sonra mevcut token ile başkasının görevini güncelleme | 1 | 403; güncel DB rolü esas alınır; görev değişmez | Geçti |

TODO=To Do, IN_PROGRESS=In Progress, REVIEW_TESTING=Review & Testing, DONE=Done. Geri geçişler ve aynı durumu tekrar gönderme de matrise dahildir; sözleşmede geçiş sırası kısıtı yoktur.

## Tekrarlanabilir çalıştırma

Backend klasöründe bağımlılıkları kurduktan sonra:

```powershell
python -m pytest tests/test_tasks.py tests/test_task_status_regression.py -q
python -m pytest -q
```

Bu çalışmada yeni dosya: `77 passed, 12 warnings in 1.30s`.
Tam backend: **`253 passed, 1 skipped, 21 warnings in 51.24s`**.
Tek skip mevcut US-005 görev atama API bağımlılığıdır; US-014 testlerinde skip yoktur.
Uyarılar mevcut Starlette/httpx TestClient ve HTTP_422_UNPROCESSABLE_ENTITY kullanımının deprecation uyarılarıdır. SQLite API testleri PostgreSQL yük/üretim testi sayılmaz. CI ayrıca PostgreSQL migration, backend test, frontend lint ve build çalıştırır.

## API kanıtı

`us-014-api-kaniti.json` aynı uygulamanın gerçek TestClient isteklerinden üretilmiştir: atanan kişinin dört durum akışı, başka üyenin 403 yanıtı, proje dışındaki yöneticinin 403 yanıtı, yöneticinin başarılı güncellemesi ve onay bekleyen görevde 400 yanıtı. Her kayıtta istek/yanıt ve DB önce/sonra görüntüsü vardır; token ve şifre yoktur. Otomatik test dosyası tüm 77 senaryonun tekrar üretilebilir doğrulamasıdır.

## Arayüz tekrar testi — açık bağımlılık

25.10.2026 kontrolünde #159 açık, görev detayında durum seçimi ve 403 mesajı henüz develop'ta bulunmuyor (`frontend/src/App.tsx`, `features/projects/ProjectDetailPage.tsx`). Bu nedenle aşağıdakiler uygulanmış/başarılı olarak işaretlenmedi:

| ID | #159 develop'a birleştikten sonra adımlar | Beklenen | Durum |
|---|---|---|---|
| UI-014-01 | Atanan üye ile görevi aç; dört durumu seç; sayfayı yenile/tekrar aç | Seçim kaydedilir ve kalıcı görünür | Bloklu |
| UI-014-02 | Başka ekip üyesiyle aynı görevi aç; durum değişikliği dene | Açıklayıcı yetki mesajı; eski durum korunur | Bloklu |
| UI-014-03 | Proje üyesi yöneticiyle başka üyeye atanmış ve atamasız görevi güncelle | Durum kaydedilir ve yeniden açınca korunur | Bloklu |
| UI-014-04 | Onay bekleyen görevi atanan kişi/yöneticiyle güncellemeyi dene | İşlem engellenir, durum korunur, açıklayıcı mesaj görünür | Bloklu |

**#159 tamamlanıp develop'a birleştirildikten sonra bu dört arayüz senaryosu ve API regresyonu yeniden çalıştırılacak; sonuçlar bu rapora ve #160'a eklenecektir.** Kanban sürükle-bırak/403 sonrası sütuna dönüş, US-015 arayüzü hazır olduğunda ayrıca doğrulanmalıdır; burada Kanban testi yapılmış sayılmaz.

#160 kontrol listesindeki ilk iki iş API seviyesinde yerine getirildi. Arayüz bağımlılığı nedeniyle kart In progress kalmalı; PR açılmış olsa da ekip onayı alınmadan “PR açıldı ve onaylandı” işaretlenmemeli ve görev kapatılmamalıdır.
