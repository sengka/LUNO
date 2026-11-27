# Sprint 7 frontend doğrulaması — 27 Kasım 2026

Kapsam: #278, #281, #287, #292. Güncel görevlerde yorum veya ek düzeltme talebi yok. Atanmış güncel frontend görevleri bu dört görevdir; eski #272 işleri yeniden uygulanmadı.

## Uygulananlar

- Ortak RiskBadge: API risk_level alanı Türkçe gösterilir; DONE veya null riskte render edilmez. Kart, görev detayı ve yeni listeler aynı bileşeni kullanır.
- Proje detayında en düşük risk filtresiyle gerçek /projects/:id/risks listesi. Sıralama backend'den geldiği gibi korunur.
- Ana sayfada /me/today listesi: yüklenme, boş, hata, tekrar deneme ve görev detayına bağlantı. Eksik API boş listeye çevrilmez.
- Üye tablosunda null kapasite “Kapasite tanımsız”; 0 kapasite “0 puan”. Sprint ekranındaki null kapasite de açıkça tanımsızdır; mevcut null kontrollü uyarı mantığı korunur.
- Mevcut ortak MutationCache tasks invalidation akışı yeni risk/today sorgularını da kapsar.

## Testler

- npm run build başarılı (ana paket boyutu uyarısı mevcut).
- npm run lint başarılı (mevcut üç Fast Refresh uyarısı).
- npm test: 22 test başarılı. Done→açık geçişi, null risk, null/0 kapasite, boş/hata/tekrar deneme, API sıra koruması ve görev detay linki dahil.
- Backend izole testleri: test_risk_levels.py, test_risks_endpoint.py, test_capacity_undefined.py: 59 başarılı, iki deprecation uyarısı.
- Gerçek localhost API: /projects/1/risks?level=ORTA 200, 11 görev. /me/today 404; /projects/1/workload 404.
- SQLite yedeği alındı; 0006→0007 migration uygulandı. 10 kullanıcı, 2 proje, 19 görev korundu. .env değişmedi, seed/reset yok, LUNO-api-test'e dokunulmadı.
- git diff --check başarılı.

## Bekleyenler

- #291 (Esma / esmaotur): https://github.com/sengka/LUNO/issues/291 — bugün listesi gerçek entegrasyonu. API görev açıklaması risk/öncelik dese de sözleşme ve #52 teslim tarihi/öncelik der; frontend API sırasını değiştirmez.
- #283 (Esma / esmaotur): https://github.com/sengka/LUNO/issues/283 — workload API yok. Bu çalışmada backend hesabı veya başka kişinin atama akışı kopyalanmadı.
- Güncel origin branch'leri salt okunur incelendi; esma/esra/aybuke branch'lerinde develop üzerinde bekleyen commit ve açık PR bulunmadı.
- Tarayıcı envanteri erişilebilir, ancak eski localhost hata sayfasını seçme adımı URL politikasıyla engellendi. Masaüstü/mobil, gerçek Done geçişi ve görev detayı görsel kontrolleri tamamlanmadı; ekran görüntüsü üretilmedi. jsdom testleri görsel test olarak sunulmaz.
- PR taslak kalmalı. Board kartları güncellenmedi; görevler kapatılmadı.

Yerel bağlantılar: http://localhost:5173/ ve http://localhost:5173/projeler/1 . Backend localhost:8000. Sunucular kontrol için çalışır bırakılır.
