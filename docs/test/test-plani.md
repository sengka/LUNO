# LUNO Test Planı

| Alan | Değer |
| --- | --- |
| Kimlik / sürüm | TP-001 / v1.0 |
| Görev | [#82 — Test planı](https://github.com/sengka/LUNO/issues/82) |
| Tarih | 19.10.2026 |
| Sorumlu | Hakan Aydın (QA), Codex yardımıyla hazırlanmıştır |
| Durum | Ekip incelemesine sunulan strateji; onaylanmış yayın kararı değildir |
| Temel sürüm | develop, 9fad8ab |
| Kapsam | 54 kullanıcı hikâyesi, 86 FR ve 23 NFR |

## 1. Amaç ve kaynaklar

Kabul kriterlerini doğrulamak, yetkisiz erişim ve veri kaybını erken bulmak,
hataları tekrar üretilebilir kanıtla raporlamak ve sprint/yayın kararına
ölçülmüş test sonuçları sağlamak. Bu plan tüm özelliklerin yapılmış veya
testlerden geçmiş olduğunu bildiren sonuç raporu değildir.

- [User story ve kabul kriterleri](../analiz/user-stories.md).
- [Gereksinim çalışma kitabı](../gereksinimler/LUNO_Gereksinim_Dokumani.xlsx):
  Yeni Gereksinim Şablonu sayfası FR-001–086; Fonks. Olmayan Gereksinimler sayfası NFR-001–023.
- [API sözleşmesi v1.1](../api/api-sozlesmesi.md): erişim, veri ve hata formatı.
- [README](../../README.md), [CI](../../.github/workflows/ci.yml),
  [backend testleri](../../backend/tests) ve [Hata Raporu şablonu](../../.github/ISSUE_TEMPLATE/hata-raporu.md).
- [İzlenebilirlik matrisi](test-izlenebilirlik.md) bu planın ayrılmaz ekidir.

Kaynak çelişkisi issue üzerinden gereksinim/sözleşme sahipleriyle çözülür;
karara kadar ilgili test Engelli kaydedilir. Kaynaksız sayısal eşik ürün
kuralı olarak eklenmez. Aşağıdaki süreç ve örneklem kuralları ekip incelemesine sunulur.

## 2. Kapsam ve öncelik

Must: US-001–026; Should: US-027–045; Could: US-046–054.
Önce kimlik/yetki, veri bütünlüğü ve ana iş akışları test edilir.
Should/Could seçilen sprint kapsamına girince aynı kabul disiplini uygulanır;
ertelenen kapsamın nedeni ve ekip kararı kaydedilir.

Her kriter için olumlu akış, olumsuz/boş veri, sınır değeri ve uygun rol/proje
üyeliği varyantı hazırlanır. Hatalı istekte mesajın yanında verinin değişmediği
de doğrulanır. Uygulanmamış uç noktadan gelen 404 başarılı yetki testi sayılmaz.

## 3. Hangi modül nasıl test edilecek?

Otomatik sütunu hedef yöntemdir; mevcut altyapı bölüm 5'te ayrılır.
54 story'nin FR ve kabul odağı eşlemesi matriste eksiksiz bulunur.

| Modül / story | Otomatik | Manuel / tarayıcı | Kritik kontroller |
| --- | --- | --- | --- |
| Kimlik/hesap/rol: 001–004, 027–029 | pytest API, parola/JWT, varsayılan rol, izinler; sahte posta servisi | Kayıt/giriş/çıkış, mesaj, rol ve şifre yenileme ekranı | 7/8 karakter, kayıtlı e-posta, 24 saat token, eski token, mevcut oturumda rol değişimi |
| Yetki: 005 ve tüm korumalı işlemler | Rol × proje üyeliği; başka proje/nesne ID'si | Gizli menü, doğrudan URL, geri düğmesi | 401/403 ayrımı; üye olmayan yöneticiye proje verisi yok |
| Proje/üye: 006–010, 029 | CRUD, tarih, cascade, davet süresi/tekrar kullanım, üyelik iptali | Silme/üye çıkarma onayı, davet akışı | Tarih öncesi/eşit/sonrası; iptal edilen silmede veri kalması |
| Görev/Kanban: 011–015, 030–034, 046–047 | Atama, durum/alt görev/dependency, arama/filtre | Sürükle-bırak, öneri onay/ret, düzenleme | Başkasının görevi, aktif/öneri ayrımı, Fibonacci efor, iş kuralı sınırları |
| Takvim/Gantt: 016–017 | Tarih/veri dönüşümü, görünüm sayımları | Ay/hafta ve zaman çizelgesi yerleşimi | Aynı gün, ay/yıl sınırı, UTC–Türkiye; aktif olmayan görevlerin dışlanması |
| Dosya/yorum: 018–020, 035 | multipart, MIME/uzantı/boyut, indirme ve izinler | Dosyanın açılması, mesajlar, yorum görünümü | İzinli tüm türler, 10 MB alt/eşit/üst, farklı projenin dosyası |
| Bildirim/posta/hatırlatma: 021, 036–038, 048 | Kontrollü saat, sahte posta, tercih/tekrar çalıştırma | Okundu, tercih, bildirim bağlantısı | Kapalı tercih, tarih sınırı, gereksiz yinelenen gönderim |
| Dashboard/rapor: 022–023, 039, 041 | Bilinen veriyle sayım/yüzde/dönem, PDF/XLSX içeriği | Grafik ve dışa aktarılan dosyanın okunabilirliği | Sıfır görev, Done/aktif kapsamı, gün/hafta/ay sınırı |
| Risk/kapasite/sprint: 024–025, 032–033, 040–044, 050 | İş kuralı ve API; alt/eşit/üst kapasite, Done istisnası | Uyarı ve onay, risk görünümü, sıralama | Geçmiş teslim, boş kapasite, alt görev/efor/sprint bağımlılıkları |
| LLM: 026, 045, 051–054 | Deterministik sahte servis, timeout/429/503/bozuk JSON, yedek servis | Türkçe çıktı, onay/red, öneri kontrolü | Onaysız kayıt yok, iki servis kapalı, projeler arası veri sızıntısı yok |
| Tema/ortak arayüz: 049 ve tüm ekranlar | Mevcut lint/build; kurulursa bileşen/E2E | Klavye, kontrast, responsive, açık/koyu tema | 768/1280/1920 px, uzun Türkçe metin, boş/yükleniyor/hata |
| Migration/yayın/operasyon | PostgreSQL migration ve veri koruma, sağlık kontrolü, CI | Demo linki, farklı cihaz, yedekten dönüş | SQLite sonucu PostgreSQL doğrulaması sayılmaz |

LLM metninde birebir eşitlik yerine şema, izin, onay ve beklenen içerik
kontrol edilir. Gerçek servis denemelerinde sentetik veri ve kontrollü istek
sayısı kullanılır. Gerçek kullanıcı verisi sağlayıcı koşulları doğrulanmadan gönderilmez.

## 4. Test seviyeleri ve sıra

1. Birim: iş kuralları, hesaplama, tarih, şifre/token.
2. API/entegrasyon: sözleşme, kimlik/yetki, veri değişimi, ilişkiler ve migration.
3. Arayüz/uçtan uca: kabul kriterinin ekranda yürütülmesi ve mesaj/yönlendirme.
4. NFR: matristeki 23 koşul için ölçüm veya inceleme kanıtı.
5. Düzeltme testi: hatanın aynı veri/adımlarla tekrarı; ilgili modül ve komşu
   akışların regresyonu. Sonuç düzeltme commit'i ve hata issue'suna bağlanır.

Tur sırası: sağlık/giriş smoke → yeni/değişen modül → olumsuz/yetki → entegrasyon
→ regresyon. Yayın öncesi zincir: kayıt → giriş → proje/üye → görev/atama →
Kanban → takvim/Gantt → dosya/yorum → bildirim/rapor → çıkış ve eski token reddi.
Hazır olmayan adım Engelli'dir; çalıştırılmış sayılmaz.

## 5. Mevcut altyapı ve planlanan otomasyon

| Kontrol | Mevcut kaynakta durum | Planlanan çalışma |
| --- | --- | --- |
| Backend | pytest/TestClient; conftest test başına bellek içi SQLite | Yeni API/iş kuralına regresyon |
| CI backend | Ubuntu, Python 3.12, PostgreSQL 16; migration ardından pytest | Gerçek PostgreSQL entegrasyon/veri koruma turu |
| DB ayrımı | Migration PostgreSQL'de, mevcut API fixture'ı SQLite'ta | PostgreSQL servisi var diye tüm API testleri PostgreSQL'de sayılmaz |
| Frontend | npm ci, lint, build; package.json'da test/E2E komutu yok | Ayrı görevde Vitest/Testing Library veya Playwright seçimi; henüz kurulu sayılmaz |
| Kapsam | pytest-cov requirements içinde yok; yüzde raporu doğrulanmadı | NFR-022 için araç/CI kararı ve en az %60 kapsam ölçümü |
| Yük/erişilebilirlik | Ölçüm raporu doğrulanmadı | NFR protokolleri, araç/sürüm/ortam kaydı |

Mevcut backend komutu (depo kökü):

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests
```

Frontend klasöründe `npm.cmd ci`, `npm.cmd run lint`, `npm.cmd run build`.
Kilidin değişmesi istenmiyorsa npm install yerine npm ci tercih edilir.
Kapsam aracı ayrı test bağımlılığı olarak eklendiğinde backend klasöründe hedef komut:

```powershell
python -m pytest --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=60
```

Bu komut pytest-cov gerektirir; mevcut CI bunu henüz zorunlu tutmaz.
Test sayısından kapsam yüzdesi hesaplanmaz.

## 6. Ortam ve test verisi

| Ortam | Kullanım / hazırlık | Kayıt ve sınır |
| --- | --- | --- |
| Yerel | README Python 3.11+, Node 22.22+ veya Docker; SQLite | SHA, .env sırları paylaşılmadan yapılandırma; özgün ayarları geri yükle |
| Otomatik API | conftest izole SQLite, her testte yeni şema | Uygulama DB'sini silme/seed reset yok |
| PostgreSQL entegrasyon | İzole PostgreSQL 16 + Alembic | Gerçek demo/üretim DB'si kullanılmaz; önce/sonra veri kontrolü |
| Staging/demo | DevOps'un paylaştığı SHA/URL, sentetik veri | Gerçek alıcıya posta yok; gerçek LLM için veri koşulları |
| Tarayıcı | Güncel Chrome/Firefox/Edge/Safari; 768/1280/1920 px | OS/sürüm/tarih yaz; erişilemeyen tarayıcı Engelli |

Her raporda commit, ortam/araç sürümü ve başlangıç verisi bulunur.
Performansta donanım, ağ, sunucu uyanıklığı ve örnek sayısı yazılır.
Yerel tek tarayıcı sonucu dört tarayıcı veya canlı performans doğrulaması değildir.
Proje içi Review & Testing görev durumu, GitHub panosunun Todo/In progress/Done sütunlarıyla karıştırılmaz.

| Veri kümesi | İçerik |
| --- | --- |
| TD-AUTH | Yönetici + iki üye; yeni/kayıtlı/geçersiz e-posta; boş ve 7/8 karakter şifre; geçerli/bozuk/geçmiş/iptal token |
| TD-ACCESS | Proje A/B; yalnız A, yalnız B, her ikisi, hiçbirinin üyesi olmayan yönetici/üye; başka nesne ID'leri |
| TD-TASK | Her durum; onay bekleyen/reddedilen/aktif ayrımı; boş/tek/tamamı Done; bugün/yarın/geçmiş ve ay/yıl sınırı |
| TD-CAPACITY | Efor 1/2/3/5/8/13; boş, sınır altı/eşit/üst kapasite; alt görev ve bağımlılıklar |
| TD-FILE | İzinli türler, izin dışı tür/MIME; 10 MB alt/eşit/üst; boş dosya/Unicode ad |
| TD-LOAD | 100 görev sayfa süresi; 200 görev ve 20 üye görünüm kapasitesi |
| TD-LLM | Sentetik Türkçe/boş/uzun metin; gecikme/hata/bozuk JSON; onay/red, başka proje verisi |

Kaynak yalnız 10 MB der; 10.000.000/10.485.760 byte yorumu sözleşme sahibiyle
netleştirilmeden tam boyut sınırı için beklenti uydurulmaz. Tarih/şifre gibi
net kaynak sınırları doğrudan kullanılır. Zaman testinde kontrollü saat veya
geçmiş exp tercih edilir; UI için süre değiştirilirse eski ayar geri yüklenir.

`python -m app.seed` boş yerel test DB'sinde örnek veri yükler; kullanıcı varsa
atlayabilir. `--reset` veriyi siler ve yalnız ayrılmış disposable test DB'sinde
kullanılır. Test yönetici hesabı hazırlığı sadece yeni QA hesabında yapılır,
rol API'sinin çalıştığına kanıt sayılmaz; geçici yetki sonunda geri alınır.
Gerçek ekip hesapları/üretim verisi/anahtarlar test verisi veya kanıta konmaz.

## 7. NFR ölçüm protokolleri

23 NFR'nin kaynak metni, önceliği ve doğrulama yöntemi matriste yer alır.
Aşağıdaki tekrar/örnek sayıları süreç önerisidir; ürün eşiklerini değiştirmez.

- NFR-008: Sunucu uyanık, 100 görev; sayfa 2 saniye içinde kullanılabilir.
  İlk açılışı ayrı kaydet; her görünümde önerilen 5 tekrar ve ham süreler.
- NFR-009: CRUD yanıtlarının en az %95'i 1 saniye içinde. Önerilen en az
  100 temsili istek; rol/işlem karışımı, ham süre ve hata oranı kaydedilir.
  Ortalama tek başına yeterli değildir; hata yanıtları başarı sayılmaz.
- NFR-010: 10 farklı LLM isteği; kullanıcıya yanıt 10 saniye içinde.
  Ağ/sağlayıcı ve yedek servis ayrılır.
- NFR-011: 200 görev/20 üye ile Kanban/takvim/Gantt hatasız; tutarlı sayım.
- NFR-012: Ekip dışından 3 kişi, eğitim almadan 5 dakikada proje ve görev atama.
  Sentetik hesap, izin, süre ve başarısız adım kaydedilir.
- NFR-014/016: Metin kontrastı en az 4.5:1; 768 px ve üzeri yatay taşma yok.
- NFR-018/019: Migration öncesi/sonrası kayıt/ilişki kontrolü; haftalık yedek
  kaydı ve izole ortama geri dönüş. Yedek varlığı geri yükleme kanıtı değildir.
- NFR-022: Backend kapsamı en az %60; SHA, araç ve kapsam raporu saklanır.

## 8. Sprint sırası ve sorumluluklar

Kullanıcının paylaştığı 4 Ekim 2026 sürüm planına göre taslak sıra aşağıdadır;
sprint kapsamı ve kapasite ekip planlamasında güncellenir.

| Sprint | Test odağı |
| --- | --- |
| 2 | Plan/ortam ve US-001–004 kimlik/rol |
| 3 | US-005–010 yetki/proje/üye; kimlik regresyonu |
| 4 | US-011–015, 032–033 görev/Kanban/efor/alt görev |
| 5 | US-016–020, 035 takvim/Gantt/dosya/yorum |
| 6 | US-021–023, 040–041 bildirim/dashboard/rapor/sprint |
| 7 | US-024–026, 042–044 risk/kapasite/LLM hata/onay; Must kontrolü |
| 8–9 | Kalan Should ve seçilmiş Could; bildirim/LLM/dışa aktarma |
| 10 | Regresyon/hata/NFR/demo/yayın; yeni isteğe bağlı kapsam sadece ekip kararıyla |

Risk/kapasite testleri efor, alt görev ve sprint hazır olmadan tamamlandı sayılmaz.
LLM onay/hata testi en az bir çalışır özellik veya sözleşmeye uygun sahte servis ister.

Hakan Aydın: plan/senaryo/yürütme/kanıt/hata tekrar testi.
İlgili geliştirici: birim testleri ve hata düzeltmesi. Salih Bilgin: ortam,
CI/yayın/yedekleme desteği. Gizem Tangel: UI/kullanılabilirlik beklentisi.
Sena Gül Kara ve Aybüke Turgun: PR/kapsam incelemesi ve sprint risk kararı.
QA'nın hatayı raporlaması, tüm geliştirici hatalarını kendisinin düzelteceği anlamına gelmez.

## 9. Başlama, durdurma ve tamamlanma koşulları

Teste giriş: SHA/kapsam belli; kriter/sözleşme erişilebilir; servis/migration
çalışır; bağımsız veri ve roller hazır; ekran/API veya onaylı sahte servis var.
Eksik bağımlılık Engelli kaydedilir.

Veri kaybı, yanlış ortama bağlanma, sır sızıntısı veya smoke akışı çalışmıyorsa
etkilenen tur durdurulur; ortam ve hata kaydı alınır. Neden giderilip ortam/veri
doğrulanınca tur yeniden başlatılır.

Story çıkışı: her kabul kriteri çalıştırılmış senaryo ve kanıta bağlı; ilgili
regresyon ve zorunlu CI başarılı; kritik yetki/veri kaybı hatası açık değil.
Kaldı/Engelli saklanmaz. Kalan düşük etkili bulgu için ekip kararı, gerekçe ve
takip issue'su yazılır; Must kriteri atlanarak Geçti denmez.

Yayın: seçilmiş sürümün Must ve Must NFR'leri, uçtan uca zincir, tarayıcı
matrisi, migration ve geri dönüş planı incelenir. Ertelenen Should/Could ve
kalan riskler açıkça karara sunulur. QA sonuç verir; yayın/PR onayı ekip
sorumlusundadır. PR açılması onaylandığı anlamına gelmez.

## 10. Hata raporlama ve tekrar test

1. Mevcut issue'larda belirti/FR/sürüm aranır; kopya yerine mevcut kayda kanıt
   eklenir. Örnek: proje listeleme 404 bulgusu #140.
2. GitHub Issues → New issue → Hata Raporu şablonu kullanılır.
3. Başlık/açıklama; ön koşul ve veri; numaralı tekrar adımları; beklenen ve
   gerçekleşen sonuç; ekran görüntüsü/log; OS/tarayıcı/URL/commit; FR/NFR ve
   senaryo ID'si yazılır. Tekrar oranı ve etki belirtilir; sırlar temizlenir.
4. bug etiketi ve önerilen önem yazılır; sorumlu/öncelik ekip triage'ında
   netleşir. Etkilenen test Kaldı veya Engelli olur.
5. Geliştirici düzeltme PR/commit'ini bağlar; QA eski adımları ve etkilenen
   regresyonu yeniden çalıştırır. Sonuç/SHA/kanıt issue'ya bağlanır.
6. Geçmezse yeniden açılır; düzeltme doğrulanmadan kapatılmaz. Panoda sadece
   Todo/In progress/Done varsa inceleme bekleyen kart In progress kalır;
   görev koşulları ve onay tamamlanınca Done yapılır.

Önerilen önem: Kritik = veri kaybı/yetki aşımı/sır sızıntısı veya tüm temel
akışın kapanması; Yüksek = önemli akış bozuk ve uygun geçici çözüm yok;
Orta = sınırlı etki/geçici çözüm var; Düşük = davranışı bozmayan metin/görsel.
Önem etkiyi, öncelik çözüm sırasını anlatır. Hata yoksa gözlenen kapsam için
“Hata bulunmadı; hata kaydı N/A” yazılır. npm audit uyarısı ayrı sürüm/bağımlılık/
etki incelemesi gerektirir; doğrulanmış açık veya yanlış pozitif varsayılmaz.

## 11. Senaryo kaydı, kanıt ve ölçüler

Rapor: docs/test/us-XXX-...md; kanıt: docs/test/kanitlar/us-XXX/.

| Alan | İçerik |
| --- | --- |
| ID ve kaynak | TC-US-XXX-01; US/FR/NFR ve issue |
| Sürüm/ortam | SHA, OS/tarayıcı, backend/frontend/DB ve araç sürümü |
| Ön koşul/veri | Rol/üyelik, başlangıç verisi, token/kayıt durumu |
| Adımlar | Başkasının tekrar edebileceği numaralı işlemler |
| Beklenen | Kaynağa dayanan mesaj/HTTP kodu/veri ve erişim sonucu |
| Gerçekleşen | Ölçülen/görülen sonuç; gerekirse önce/sonra karşılaştırması |
| Durum | Planlandı, Geçti, Kaldı, Engelli veya gerekçeli N/A |
| Kanıt/hata | Repo göreli görsel/log bağlantısı ve hata issue'su |
| Yürüten/tarih | İnsan manuel, tarayıcı otomasyonu veya API otomasyonu açıkça yazılır |

Geçiş oranı = Geçti / (Geçti + Kaldı); diğer durumlar ayrı raporlanır.
Kriter yürütme kapsamı = çalıştırılan kriter / seçilen sürümdeki kriter.
Dolu plan matrisi çalıştırma kanıtı değildir; kod kapsamı ayrı ölçülür.
Sprint raporu: durum sayıları, kritik açık hatalar, engeller, tekrar test ve ertelenen kapsam.

## 12. Başlangıç durumu, riskler ve bakım

19.10.2026 tarihinde önceki işler için incelemeye sunulan raporlar:

| Story | Kayıt | Tarihsel yerel sonuç |
| --- | --- | --- |
| US-001 | [PR #139](https://github.com/sengka/LUNO/pull/139) | 7 manuel senaryo ve mevcut 75 test |
| US-002 | [PR #141](https://github.com/sengka/LUNO/pull/141) | 77 test; tarayıcı oturum süresi ek kontrolü |
| US-003 | [PR #142](https://github.com/sengka/LUNO/pull/142) | 81 test |
| US-004 | [PR #143](https://github.com/sengka/LUNO/pull/143) | 83 test |

Sonuçlar farklı dalların tarihsel raporlarıdır; toplanmaz, tek güncel sürüm
sonucu sayılmaz. #82 yeni ürün test turu değildir. Bu plan hazırlanırken
raporlar develop'a birleşmediğinden bağlantılar PR'lara verilmiştir.

Bilinen takip: [#140 proje API'si 404](https://github.com/sengka/LUNO/issues/140);
önceki npm kurulumundaki 7 yüksek önem uyarısının ayrıntılı incelemesi;
PostgreSQL entegrasyon ayrımı; kapsam/E2E araç eksikliği; dört tarayıcıya
ve LLM/posta sağlayıcılarına erişim; uyuyan sunucunun süre ölçümünü etkilemesi.
Bunlar ürün/yayın doğrulama işleridir; planın yazılmasıyla yapılmış sayılmaz.

Her sprintte kapsam/öncelik/matris gözden geçirilir. Gereksinim değişince
kaynak ID, senaryo ve rapor bağlantısı aynı PR'da güncellenir. Kod değişince
ilgili testler yeniden çalıştırılır. v1.0 değişiklik kaydı: #82'nin dört maddesi,
tüm kaynak ID'lerinin yöntem eşlemesi, ortam/veri, NFR ölçümleri, hata akışı,
tamamlanma koşulları ve mevcut altyapı boşlukları belgelendi.
