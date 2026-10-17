# LUNO — Rakip Analizi (Benchmark)

|                       |                                                     |
| --------------------- | --------------------------------------------------- |
| **Sprint**            | 1                                                   |
| **Hazırlayan**        | (UI/UX Tasarımcı + Müşteri Temsilcisi) Gizem Tangel |
| **İncelenen ürünler** | Jira, Trello, Asana, ClickUp                        |
| **Durum**             | Taslak v1 — ekip incelemesine açık                  |

> **Önemli not (fiyatlar):** Fiyatlar USD, kullanıcı başına/ay ve çoğunlukla **yıllık faturalandırma** içindir. Fiyat sayfaları sık değiştiği ve üçüncü taraf kaynaklar kendi aralarında küçük farklar gösterdiği için PR'dan önce her ürünün resmî fiyat sayfasından son kez doğrulanmalıdır. Farklı çıkan yerler aşağıda ayrıca belirtilmiştir.

---

## 1. Amaç ve Yöntem

Bu doküman, LUNO'nun konumlanmasını ve Sprint 2'deki detaylı arayüz tasarımını beslemek için dört yaygın proje yönetimi aracını **kullanıcı gözüyle** karşılaştırır. Her ürün için aynı beş başlık kullanılmıştır:

1. Öne çıkan özellikler
2. Güçlü yönler
3. Zayıf yönler
4. Kimler kullanıyor
5. Fiyatlandırma
6. Yapay zekâ özellikleri

Kaynaklar: ürünlerin resmî sayfaları ve Ekim 2026 itibarıyla yayımlanmış fiyat/özellik karşılaştırma yazıları (sonda listelenmiştir). "Güçlü/zayıf yön" değerlendirmeleri kaynaklardan ve genel sektör gözleminden derlenmiş **yorumdur**; ekip içi tartışmaya açıktır.

---

## 2. Jira (Atlassian)

Yazılım ekipleri için tasarlanmış, çok güçlü ama öğrenme eğrisi dik bir iş takip ve çevik (Agile) yönetim aracı.

### Öne çıkan özellikler

- Scrum ve Kanban panoları, backlog, sprint yönetimi
- Liste, pano, zaman çizelgesi (timeline), takvim ve özet görünümleri
- Özelleştirilebilir iş akışları (workflow), issue tipleri, roller ve izinler
- Güçlü otomasyon motoru (kural tabanlı)
- Raporlar: burndown, velocity vb.
- Geniş marketplace ve entegrasyon ekosistemi (Confluence, Bitbucket, Slack, GitHub…)
- Premium'da: projeler arası bağımlılık yönetimi, gelişmiş planlama, SLA garantisi

### Güçlü yönler

- Yazılım geliştirme süreçleri için sektör standardı
- Çok esnek ve derinlemesine özelleştirilebilir
- Kurumsal ölçekte güvenlik, izin ve denetim kontrolleri
- Çok geniş eklenti/entegrasyon ekosistemi

### Zayıf yönler

- Arayüz karmaşık; yeni ve teknik olmayan kullanıcılar için öğrenme süresi uzun
- Kurulum/yapılandırma için çoğu zaman bir "Jira yöneticisi" gerekir
- Gerçek maliyet başlık fiyatın üstüne çıkabilir (Confluence ayrı ücretli, marketplace eklentileri, otomasyon kotası)
- AI özelliklerinin tamamı Premium ve üstünde; kullanım **kredi** ile ölçülüyor

### Kimler kullanıyor

Yazılım/ürün geliştirme ekipleri, DevOps, QA; ayrıca IT servis ekipleri (Jira Service Management). Küçük ekiplerden büyük kurumlara kadar yayılır, ağırlık teknik ekiplerdedir.

### Fiyatlandırma (Ekim 2026, aylık/kullanıcı)

| Plan       | Fiyat            | Notlar                                                                                  |
| ---------- | ---------------- | --------------------------------------------------------------------------------------- |
| Free       | $0               | En fazla 10 kullanıcı, 2 GB depolama, ayda 100 otomasyon çalıştırması, topluluk desteği |
| Standard   | ≈ $7,91 (yıllık) | 250 GB depolama, ayda 1.700 otomasyon (site genelinde), kullanıcı rolleri/izinleri      |
| Premium    | ≈ $14,54         | Sınırsız depolama, 7/24 destek, %99,9 SLA, projeler arası bağımlılık                    |
| Enterprise | Özel teklif      | Gelişmiş yönetim ve güvenlik                                                            |

_Kaynaklar arasında fark:_ Standard için $7,91 – $8,60, Premium için $14,54 – $15,25 aralığında rakamlar görülüyor (aylık/yıllık ve bölgesel farklar). Confluence ayrıca ücretlidir.

### Yapay zekâ

**Var — Rovo ve Atlassian Intelligence.**

- Görev/epik'i alt işlere ayırma (work breakdown), issue özeti, AI destekli yazım, doğal dille arama
- Rovo Chat, Rovo Agents (özel ajanlar), Rovo Studio (kendi ajanını oluşturma)
- Confluence, Slack, Google Drive gibi bağlı uygulamalarda arama ve bağlam
- **Sınır:** Tüm AI özellikleri için Premium/Enterprise gerekir. Kullanıcı başına aylık kredi kotası: Standard 25, Premium 70, Enterprise 150. Bir sohbet/ajan çalıştırması yaklaşık 10 kredi, derin araştırma yaklaşık 100 kredi harcar. Kredi aşımı için ek ücretlendirme 3 Aralık 2026'da başlıyor.

---

## 3. Trello (Atlassian)

Kart-liste mantığıyla çalışan, öğrenmesi en kolay görsel Kanban aracı.

### Öne çıkan özellikler

- Pano / liste / kart yapısı; sürükle-bırak
- Kart içinde kontrol listesi, son tarih, etiket, ek dosya, yorum
- Butler ile kural/düğme tabanlı otomasyon
- 200'den fazla Power-Up (eklenti)
- Premium'da: Takvim, Zaman Çizelgesi, Tablo, Pano (dashboard) ve Harita görünümleri
- Gelen kutusu (Inbox) ve Planlayıcı (Planner)

### Güçlü yönler

- Çok sade ve sezgisel arayüz; dakikalar içinde kullanılabilir
- Ücretsiz plan kişisel ve küçük ekipler için yeterli
- Düşük fiyat
- Mobil deneyimi iyi

### Zayıf yönler

- Karmaşık projelerde (bağımlılıklar, kaynak planlama, çok projeli portföy) yetersiz kalır
- Gantt/zaman çizelgesi ve gelişmiş raporlama yalnızca üst planlarda
- Pano sayısı arttıkça genel görünürlük zorlaşır
- Güçlü raporlama ve iş yükü yönetimi yok; bunun için Power-Up'lara bağımlı

### Kimler kullanıyor

Bireyler, küçük ekipler, serbest çalışanlar, pazarlama/içerik/eğitim ekipleri, kişisel organizasyon ve basit süreç takibi yapanlar.

### Fiyatlandırma (Ekim 2026, aylık/kullanıcı, yıllık faturalandırma)

| Plan       | Fiyat                      | Notlar                                                                    |
| ---------- | -------------------------- | ------------------------------------------------------------------------- |
| Free       | $0                         | 10 pano, 10 iş birlikçi, ayda 250 Butler çalıştırması                     |
| Standard   | $5 (aylık ödemede $6)      | Sınırsız pano, özel alanlar, gelişmiş kontrol listeleri, ayda 1.000 komut |
| Premium    | $10 (aylık ödemede $12,50) | Tüm görünümler, sınırsız komut, yönetici kontrolleri, AI                  |
| Enterprise | $17,50 (yalnızca yıllık)   | SSO, kurumsal yönetim; kaynaklara göre en az 50 koltuk                    |

### Yapay zekâ

**Var — Atlassian Intelligence tabanlı, sınırlı kapsamda.**

- Kart açıklamalarını ve yorumları geliştirme (dil bilgisi, netlik, beyin fırtınası), AI ile içerik üretimi
- Hızlı not/görev yakalama (quick capture)
- **Sınır:** Kaynaklar arasında farklılık var; çoğu kaynak AI'nın **Premium ve Enterprise**'a özel olduğunu söylüyor, bazıları hızlı yakalamanın Standard'da da bulunduğunu belirtiyor. Ücretsiz planda AI yok. Jira'daki gibi ajan/otomasyon düzeyinde bir AI deneyimi yok.

---

## 4. Asana

Ekipler arası iş akışları, hedefler ve portföy yönetimi için tasarlanmış, "iş grafiği" (Work Graph) mantığıyla çalışan orta-büyük ölçek aracı.

### Öne çıkan özellikler

- Liste, pano, takvim, zaman çizelgesi (Gantt) görünümleri
- Formlar, özel alanlar, kurallarla otomasyon, iş akışı oluşturucu
- Panolar (dashboard) ve raporlama
- Advanced'da: portföyler, hedefler (goals), iş yükü (workload) yönetimi, onay akışları, yerleşik zaman takibi
- Sınırsız ücretsiz misafir (Starter ve üstü)
- Güçlü entegrasyonlar (Slack, Google Workspace, Salesforce vb.)

### Güçlü yönler

- Temiz ve profesyonel arayüz; farklı rollerdeki (yazılımcı olmayan) ekipler için uygun
- Şirket hedefleri → proje → görev bağlantısı güçlü
- Olgun otomasyon ve iş akışı yetenekleri
- Büyük kurumlar için yönetişim ve güvenlik özellikleri

### Zayıf yönler

- **Pahalı:** Starter ile Advanced arasındaki fiyat farkı çok büyük
- Ücretsiz plan 2 kullanıcıya düşürüldü (Kasım 2025 sonrası açılan hesaplar için); küçük ekipler için giriş bariyeri yükseldi
- Gantt/zaman çizelgesi ücretsiz planda yok
- Yazılım geliştirme ekipleri için Jira kadar derin değil
- AI kullanımı hesap bazında kredi limitine bağlı; üst AI katmanları "satışla görüşün" modeli

### Kimler kullanıyor

Pazarlama, operasyon, ürün ve proje ofisi ekipleri; orta ve büyük ölçekli şirketler; ekipler arası koordinasyon gereken kurumlar.

### Fiyatlandırma (Ekim 2026, aylık/kullanıcı, yıllık faturalandırma)

| Plan                     | Fiyat                         | Notlar                                                           |
| ------------------------ | ----------------------------- | ---------------------------------------------------------------- |
| Personal                 | $0                            | En fazla 2 kullanıcı (yeni hesaplar); AI Studio yok              |
| Starter                  | $10,99 (aylık ödemede $13,49) | Zaman çizelgesi/Gantt, otomasyon, formlar, özel alanlar, panolar |
| Advanced                 | $24,99 (aylık ödemede $30,49) | Portföy, hedefler, iş yükü, onaylar, zaman takibi                |
| Enterprise / Enterprise+ | Özel teklif                   | Gelişmiş yönetim ve güvenlik                                     |

Ek: Zaman ve bütçe takibi eklentisi yaklaşık $5,99/kullanıcı/ay.

### Yapay zekâ

**Var — AI Studio ve AI Teammates (ajanlar).**

- AI Studio Basic ücretli planlara dahil: hesap başına aylık **50 bin (Starter) / 75 bin (Advanced) / 200 bin (Enterprise)** kredi
- AI Studio Plus/Pro ve AI Teammates (iş akışlarını kendi yürüten ajanlar) ek ücretli, "satışla görüşün" modeliyle
- Akıllı özetler, görev/iş akışı otomasyonu, kural bazlı AI adımları
- **Sınır:** Krediler hesap bazında, aylık ve devretmiyor; ücretsiz planda AI yok

---

## 5. ClickUp

"Her şey tek uygulamada" iddiasıyla görev, doküman, hedef, zaman takibi ve sohbeti bir araya getiren, en çok özelliği en düşük taban fiyatla sunan araç.

### Öne çıkan özellikler

- 15'ten fazla görünüm: liste, pano, takvim, Gantt, tablo, iş yükü, harita vb.
- Dokümanlar, beyaz tahta, formlar, hedefler, zaman takibi, panolar
- Özel alanlar ve güçlü otomasyon; planlara göre ayda 100 – 25.000 otomasyon
- Sınırsız görev ve sınırsız üye (ücretsiz planda bile)
- Birçok araçtan içe aktarma ve geniş entegrasyon listesi

### Güçlü yönler

- Fiyat/özellik oranı çok iyi; ücretli plan başlangıcı rakiplerin altında
- Neredeyse her ihtiyaç için görünüm ve özellik var
- Yüksek özelleştirme: farklı ekipler aynı çalışma alanında kendi düzenini kurabilir
- Ücretsiz planda sınırsız üye

### Zayıf yönler

- **Özellik yoğunluğu:** Arayüz kalabalık, öğrenme eğrisi dik; yeni kullanıcı için bunaltıcı olabilir
- Hiyerarşi (Çalışma alanı → Space → Klasör → Liste → Görev) karmaşık
- AI ayrı ücretli eklenti; **AI'sız fiyat yanıltıcı** olabilir
- Ücretsiz planda depolama ve özellik sınırları sıkı (örneğin 100 MB depolama, 100 otomasyon)
- Performans geri bildirimleri büyük çalışma alanlarında yavaşlama yönünde olabiliyor (genel kullanıcı gözlemi, doğrulanmalı)

### Kimler kullanıyor

Ajanslar, startup'lar, küçük-orta ölçekli ekipler, birden çok aracı tek yerde toplamak isteyen ekipler; serbest çalışanlar.

### Fiyatlandırma (Ekim 2026, aylık/kullanıcı, yıllık faturalandırma)

| Plan          | Fiyat                     | Notlar                                                                                   |
| ------------- | ------------------------- | ---------------------------------------------------------------------------------------- |
| Free Forever  | $0                        | Sınırsız üye ve görev; sınırlı depolama/otomasyon/özellik                                |
| Unlimited     | $7 (aylık ödemede ≈ $10)  | Sınırsız depolama, Gantt, hedefler, zaman takibi, ayda 1.000 otomasyon                   |
| Business      | $12 (aylık ödemede ≈ $19) | Gelişmiş panolar, iş yükü, zaman çizelgeleri, ayda 10.000 otomasyon                      |
| Business Plus | ≈ $19                     | Gelişmiş izinler, rol yönetimi (kaynaklara göre; resmî sayfada her zaman görünmeyebilir) |
| Enterprise    | Özel teklif               | Gelişmiş güvenlik ve yönetim                                                             |

### Yapay zekâ

**Var — ClickUp Brain; ancak ayrı ücretli eklenti.**

- AI yazım, özetleme, çalışma alanında "derin arama", takvim entegrasyonu, proje özetleri
- **Brain: yaklaşık $9/kullanıcı/ay**, **Everything AI (Autopilot): yaklaşık $28/kullanıcı/ay** (ajanlar, otomatik atama, AI alanları). Bazı kaynaklar Brain için $7 verir.
- Ücret, AI kullanmayanlar dahil **tüm ücretli koltuklara** yansır; hiçbir temel planın içinde değildir
- Business + Brain ≈ $21/kullanıcı/ay

---

## 6. Karşılaştırma Tablosu

| Kriter                      | Jira                                     | Trello                  | Asana                     | ClickUp                        |
| --------------------------- | ---------------------------------------- | ----------------------- | ------------------------- | ------------------------------ |
| **Ana odak**                | Yazılım / Agile                          | Basit Kanban            | Ekipler arası iş akışı    | Hepsi bir arada                |
| **Kullanım kolaylığı**      | ⭐⭐                                     | ⭐⭐⭐⭐⭐              | ⭐⭐⭐⭐                  | ⭐⭐                           |
| **Kanban panosu**           | ✅                                       | ✅ (çekirdek)           | ✅                        | ✅                             |
| **Gantt / zaman çizelgesi** | ✅ (Ücretsiz dahil, Premium'da gelişmiş) | Premium+                | Starter+                  | Unlimited+                     |
| **Takvim**                  | ✅                                       | Premium+                | ✅                        | ✅                             |
| **Raporlama / panolar**     | ✅                                       | Premium+                | Starter+                  | Business+ (gelişmiş)           |
| **Yorum + dosya ekleme**    | ✅                                       | ✅                      | ✅                        | ✅                             |
| **Ücretsiz plan**           | 10 kullanıcı                             | 10 iş birlikçi, 10 pano | 2 kullanıcı               | Sınırsız üye, kısıtlı          |
| **Başlangıç ücretli fiyat** | ≈ $7,91                                  | $5                      | $10,99                    | $7                             |
| **AI var mı?**              | Evet (Rovo)                              | Evet (sınırlı)          | Evet (AI Studio, ajanlar) | Evet (Brain)                   |
| **AI fiyat modeli**         | Premium+ plana bağlı + kredi             | Premium+ plana bağlı    | Hesap bazlı kredi         | Koltuk başı ek ücret           |
| **Türkçe arayüz**           | Var\*                                    | Var\*                   | Var\*                     | Kısmi\*                        |
| **Hedef kitle**             | Teknik ekipler                           | Küçük ekip / bireysel   | Orta-büyük şirket         | Ajans / çok amaçlı             |
| **Başlıca dezavantaj**      | Karmaşıklık                              | Derinlik eksikliği      | Fiyat                     | Aşırı özellik / ek AI maliyeti |

\* Dil desteği Sprint 2'den önce resmî sayfalardan doğrulanmalıdır; bu tablodaki satır **doğrulanmamıştır**.

---

## 7. Piyasadaki Boşluklar (Fırsat Alanları)

İncelemeden çıkan ortak gözlemler:

1. **Basitlik ile güç arasında boşluk var.** Trello kolay ama sığ, Jira ve ClickUp güçlü ama karmaşık. Hem sade hem yeterince derin bir orta nokta açıkta.
2. **Fiyat öngörülemez.** AI kredileri (Jira, Asana), koltuk başı AI eklentisi (ClickUp), plan atlamalı özellik kilitleri (Trello, Asana) toplam maliyeti belirsizleştiriyor.
3. **AI çoğunlukla pahalı planlara kilitli.** Küçük ekipler en çok işine yarayacak AI'dan ya mahrum ya da ek ücret ödemek zorunda.
4. **Ücretsiz planlar daralıyor.** Asana 2 kullanıcıya indi, Jira ve Trello 10 kullanıcıda sınırlı; küçük ekipler için gerçekten kullanılabilir bir başlangıç bölgesi azaldı.
5. **Gantt, takvim ve rapor genelde üst planda.** Bunlar proje takibinin temelidir ama çoğu rakipte ücretli duvarın arkasında.
6. **Yerelleştirme zayıf.** Türkçe odaklı, Türkiye'deki ekiplerin çalışma biçimine uygun bir ürün yok (doğrulanması gereken bir varsayım, bkz. 8. bölüm).

---

## 8. LUNO Bunlardan Neden Farklı?

> **Taslak notu:** LUNO'nun resmî vizyonu ve gereksinim dokümanı (v4) bu analize henüz bağlanmadı. Bu bölüm, yukarıdaki pazar boşluklarına ve Sprint 1 ekran listesine (giriş/kayıt, dashboard, proje listesi, Kanban, görev detayı, takvim + Gantt, raporlar) dayalı bir **öneri çerçevesidir**. Madde madde ürün sahibi ve gereksinim dokümanıyla doğrulanıp netleştirilmelidir. Doğrulanmayan hiçbir iddia "LUNO yapar" diye kesinleştirilmemiştir.

### Önerilen konumlandırma

**"Küçük ve orta ekipler için, kurulum gerektirmeyen, temel proje takibinin tamamını (Kanban + takvim + Gantt + rapor) tek planda sunan sade proje yönetimi."**

### Farklılaşma ekseni (doğrulanacak)

| Eksen                              | Pazar durumu                                        | LUNO için öneri                                                                                               |
| ---------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **Sadelik**                        | Jira/ClickUp karmaşık, Trello sığ                   | Az ekran, net akış; yeni kullanıcı ilk projeyi birkaç dakikada kurabilmeli                                    |
| **Tüm temel görünümler tek yerde** | Gantt/rapor çoğunda üst planda                      | Kanban, takvim, Gantt ve rapor aynı kapsamda; plan duvarı yok veya çok az                                     |
| **Şeffaf fiyat**                   | Kredi ve AI eklentileri maliyeti belirsizleştiriyor | Koltuk başı net fiyat; gizli kredi/ek ücret yok                                                               |
| **Yapay zekâ**                     | Pahalı katmanlara kilitli                           | Temel AI yardımı (özet, görev önerisi) herkese açık olabilir — **kapsam gereksinim dokümanıyla belirlenmeli** |
| **Türkçe ve yerel kullanım**       | Güçlü yerel ürün yok                                | Türkçe arayüz ve destek, yerel müşteri iletişimi                                                              |
| **Kullanıcı gözüyle tasarım**      | Özellik odaklı arayüzler                            | Rol bazlı sade ekranlar (Yönetici / Ekip Üyesi); dashboard'da "bugün ne yapmalıyım" odağı                     |

### LUNO'nun bilinçli olarak yapmayacağı şeyler (önerilen)

- Jira gibi yazılım ekiplerine özel derin Agile/DevOps özelliklerini hedeflemek
- ClickUp gibi "her şey tek uygulamada" olmaya çalışmak (doküman, beyaz tahta, sohbet vb.)
- Asana gibi büyük kurum yönetişimine yatırım yapmak (ilk sürümde)

### Karşılaştırmalı kısa özet

| Rakip       | LUNO'nun farkı                                                             |
| ----------- | -------------------------------------------------------------------------- |
| **Jira**    | Daha sade, kurulum ve yönetici gerektirmez, yazılım dışı ekiplere de uygun |
| **Trello**  | Kanban'ın ötesinde Gantt, takvim ve raporu aynı ürünün içinde sunar        |
| **Asana**   | Daha uygun maliyetli ve küçük ekipler için erişilebilir                    |
| **ClickUp** | Daha az karmaşık; ek AI ücreti gibi sürprizler yok                         |

---

## 9. Açık Sorular ve Sonraki Adımlar

1. **Gereksinim dokümanı v4** ile 8. bölümdeki iddialar karşılaştırılacak (özellikle AI kapsamı ve fiyat modeli).
2. Türkçe arayüz desteği ve yerel ödeme/fatura seçenekleri her rakip için doğrulanacak.
3. Hedef kitle netleştirilecek: yalnızca yazılım dışı küçük/orta ekipler mi, yoksa yazılım ekipleri de mi?
4. Rakiplerin ürün içi ekran görüntüleri (onboarding, Kanban, görev detayı) **UI/UX kıyası** için ayrıca toplanabilir; bu, Sprint 1'deki wireframe işine doğrudan girdi sağlar.
5. Fiyatlar PR öncesi resmî sayfalardan tekrar kontrol edilecek.

---

## 10. Kaynaklar

- Atlassian — Jira AI / Rovo: atlassian.com/software/jira/ai
- Atlassian — Rovo planları ve kredi sistemi: atlassian.com/licensing/rovo ve support.atlassian.com/rovo
- Jira fiyatları: resolution.de, ones.com, costbench.com, comparedge.com, saascrmreview.com
- Trello fiyatları ve AI: ones.com, usecarly.com, ai-cmo.net, costbench.com, automationatlas.io
- Asana fiyatları ve AI Studio: agiled.app, pagedog.app, appstackinsider.com, aivario.com, saasworthy.com
- ClickUp fiyatları ve Brain: agiled.app, hackceleration.com, usecarly.com, thickethq.com, aiproductivity.ai
