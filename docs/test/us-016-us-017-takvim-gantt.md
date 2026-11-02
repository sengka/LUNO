# US-016 / US-017 — Takvim ve Gantt doğrulaması

Tarih: 1 Kasım 2026. Kapsam: #191, #194; güncel mockup #174 ve API sözleşmesi 7.2–7.3.

## Uygulama

- Proje detayında Kanban, Takvim ve Gantt bağlantıları; doğrudan açılabilir korumalı adresler: `/projeler/:projectId/takvim` ve `/projeler/:projectId/gantt`.
- FullCalendar 7: Türkçe ay/hafta, Pazartesi başlangıcı, görünür aralıkla API sorgusu. FullCalendar'ın hariç bitişi API'nin dahil `to` tarihine çevrilir. Etkinliğin hariç bitişi `due_date + 1 gün`; tek tarihi olan görevler bir günlük gösterilir.
- Frappe Gantt: sözleşmedeki kimlik, başlık, tarihler ve kesirli ilerleme alanları doğrudan eşlenir. Gün/hafta/ay ölçeği ve alt görev filtresi bulunur. Tarih ve ilerleme sürükleme ile değiştirilmez; görev detayındaki mevcut yetki kuralları kullanılır.
- Her iki görünüm `React.lazy` ile yüklenir. Görev açıldığında detay ekranı kapanınca kaynak görünüme dönülür. Sorgular mevcut `tasks` önbellek anahtarı altında yer alır; görev değişikliklerinin mevcut invalidation akışına dahildir.
- Bağımlılık okları #194 uyarınca Sprint 9'a bırakıldı. Gantt API başlıkları, kütüphanenin SVG HTML sınırında escape edilir. Erişilebilir görev tablosu alternatif gezinme sağlar.

## Çalıştırılan kontroller

| Kontrol | Sonuç |
| --- | --- |
| `npm run build` | Geçti; takvim ve Gantt ayrı dinamik parçalarda. Gantt JS yaklaşık 51,6 kB / gzip 14,8 kB. Ana uygulama parçası için 500 kB uyarısı mevcut. |
| `npm run lint` | Geçti; mevcut `button.tsx`, `badge.tsx`, `tabs.tsx` dosyalarında üç Fast Refresh uyarısı. |
| `npm test` | 8 test geçti. Gerçek FullCalendar/Frappe, jsdom ortamında; görsel tarayıcı testi değildir. |
| `python -m pytest -p no:cacheprovider tests -q` | 396 geçti; tek test Windows geçici dizin izni nedeniyle setup aşamasında çalışamadı. |
| `python -m pytest -p no:cacheprovider tests/test_models.py::test_app_engine_enables_sqlite_foreign_keys -q` (gerekli izinle) | Kalan test geçti. Toplam 397 backend testi başarılı; deprecation uyarıları mevcut. |
| Mevcut SQLite + FastAPI TestClient, kimlik doğrulamalı GET | Takvim: 200, `events`; Gantt: 200, `project` ve `items`. Salt okunur smoke kontrolü. |
| Alembic | Mevcut SQLite yedeklendi; develop'tan gelen `0003 → 0004` uygulandı, `0004 (head)` doğrulandı. |
| Veri koruma | Migration öncesi/sonrası: 10 kullanıcı, 2 proje, 19 görev. Veritabanı sıfırlanmadı. |

Frontend testleri ay/yıl/artık gün sınırlarını, eksik tarihleri, kesirli Gantt ilerlemesini, bağımlılıkların aktarılmamasını, Türkçe görünüm geçişini, Pazartesi başlangıcını, görev detayına geçişi, yeniden denemeyi, boş/403 durumlarını, alt görev filtresini ve SVG başlık güvenliğini kapsar. jsdom SVG ölçüm ve kaydırma işlevleri test içinde taklit edilir; gerçek yerleşim ölçülmez.

## Engeller ve kalan doğrulama

- Tarayıcı aracı envanteri `Browsers: Error: The browser access host is unavailable` döndürdü. Gerçek tarayıcıda görsel, responsive ve uçtan uca kullanıcı oturumu testi yapılamadı; ekran görüntüsü üretilemedi. Mockup dosyaları test ekran görüntüsü olarak sunulmadı.
- `npm audit` 13 bulgu bildirdi (1 düşük, 6 orta, 6 yüksek); bildirilen paketler mevcut shadcn/zod ve bunların bağımlılıkları. Yeni FullCalendar/Frappe/test paketleri için bulgu listelenmedi. Kapsam dışı toplu bağımlılık güncellemesi yapılmadı.
- PR incelemesi, onayı, merge ve board durumu değişikliği bu doğrulamanın parçası değildir. PR kendiliğinden onaylanmaz veya birleştirilmez.

Yerel veritabanı yedeği ve ham audit çıktısı commit kapsamına alınmaz. `LUNO-api-test` klasöründe işlem yapılmadı.
