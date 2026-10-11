# LUNO – Kullanıcı Hikâyeleri (User Stories)

| | |
|---|---|
| **Kaynak doküman** | LUNO Gereksinim Dokümanı v4 (Fonksiyonel Gereksinimler) |
| **Kapsam** | 86 fonksiyonel gereksinim (FR-001 – FR-086) |
| **Story sayısı** | 54 |
| **Durum** | Taslak – PR incelemesi bekliyor |

## 1. Özet

| Öncelik | FR sayısı | Story sayısı | Story aralığı |
|---|---:|---:|---|
| Must | 46 | 26 | US-001 – US-026 |
| Should | 27 | 19 | US-027 – US-045 |
| Could | 13 | 9 | US-046 – US-054 |
| **Toplam** | **86** | **54** | |

## 2. Yazım kuralları ve varsayımlar

- Hikâye kalıbı: *Bir [Yönetici / Ekip Üyesi] olarak, [amaç] için [işlem] yapmak istiyorum.*
- İlişkili FR'ler tek story'de toplanmıştır. **Her story'nin tek bir önceliği vardır**; bu nedenle farklı önceliğe sahip FR'ler (örneğin FR-072, FR-074, FR-083) aynı konuya yakın olsalar da ayrı story'lerde tutulmuştur.
- Öncelikler gereksinim dokümanı v4'teki MoSCoW değerleriyle birebir aynıdır.
- Kabul kriterleri FR metinlerinden türetilmiştir; her kriterin sonunda dayandığı FR numarası yazılıdır. Gereksinim dokümanında olmayan sayı veya kural eklenmemiştir.
- Yönetici de oturum açan bir kullanıcıdır. **Ekip Üyesi** olarak yazılan genel kullanıcı story'leri Yönetici için de geçerlidir. Arka planda çalışan sistem davranışları (hatırlatma, LLM yedekleme vb.) o davranıştan yararlanan role bağlanmıştır.
- Fonksiyonel olmayan gereksinimler (NFR-001 – NFR-023) bu dokümanın kapsamı dışındadır.

## 3. Must öncelikli story'ler

### US-001 – Kullanıcı kaydı

**Hikâye:** Bir Ekip Üyesi olarak, sisteme erişebilmek için ad, e-posta ve şifremle kayıt olmak istiyorum.

**Kabul kriterleri:**
- [ ] Geçerli ad, e-posta ve en az 8 karakterli şifre girildiğinde yeni kullanıcı hesabı oluşturulur. *(FR-001)*
- [ ] Hesap başarıyla oluşturulduğunda kayıt işleminin başarılı olduğunu bildiren mesaj gösterilir. *(FR-002)*
- [ ] Sistemde zaten kayıtlı bir e-posta ile kayıt denendiğinde hesap oluşturulmaz ve e-postanın kullanımda olduğunu belirten hata mesajı gösterilir. *(FR-003)*
- [ ] Zorunlu bir alan boş bırakıldığında veya şifre 8 karakterden kısa girildiğinde hesap oluşturulmaz ve hatalı alanı belirten hata mesajı gösterilir. *(FR-004)*

**Karşıladığı FR'ler:** FR-001, FR-002, FR-003, FR-004  
**Öncelik:** Must

---

### US-002 – Kullanıcı girişi

**Hikâye:** Bir Ekip Üyesi olarak, projelerime ve görevlerime ulaşabilmek için e-posta ve şifremle giriş yapmak istiyorum.

**Kabul kriterleri:**
- [ ] Kayıtlı e-posta ve doğru şifre girildiğinde kullanıcı doğrulanır ve yetkilerine uygun ana sayfaya yönlendirilir. *(FR-005)*
- [ ] Geçersiz e-posta veya şifre girildiğinde giriş tamamlanmaz ve kullanıcıya hata mesajı gösterilir. *(FR-006)*

**Karşıladığı FR'ler:** FR-005, FR-006  
**Öncelik:** Must

---

### US-003 – Çıkış yapma

**Hikâye:** Bir Ekip Üyesi olarak, hesabımın güvenliğini sağlamak için oturumumu kapatmak istiyorum.

**Kabul kriterleri:**
- [ ] Oturum açmış kullanıcı çıkış yap seçeneğini seçtiğinde oturum sonlandırılır ve kullanıcı giriş sayfasına yönlendirilir. *(FR-007)*

**Karşıladığı FR'ler:** FR-007  
**Öncelik:** Must

---

### US-004 – Sistem rolü yönetimi

**Hikâye:** Bir Yönetici olarak, yetki dağılımını kontrol edebilmek için kullanıcıların sistem rolünü yönetmek istiyorum.

**Kabul kriterleri:**
- [ ] Yeni bir kullanıcı hesabı oluşturulduğunda kullanıcıya varsayılan olarak Ekip Üyesi rolü atanır. *(FR-010)*
- [ ] Yönetici bir kullanıcının sistem rolünü değiştirdiğinde rol seçilen değere (Yönetici veya Ekip Üyesi) güncellenir. *(FR-011)*

**Karşıladığı FR'ler:** FR-010, FR-011  
**Öncelik:** Must

---

### US-005 – Yetki ve proje erişim kısıtları

**Hikâye:** Bir Yönetici olarak, proje verilerini ve yönetim işlemlerini yetkisiz kullanımdan korumak için yetki ve erişim kısıtlarının uygulanmasını sağlamak istiyorum.

**Kabul kriterleri:**
- [ ] Ekip Üyesi yalnızca Yöneticiye tanımlı bir işlemi (proje oluşturma, proje silme, üye yönetimi, görev atama, rol değiştirme) denediğinde işlem gerçekleşmez ve yetkisiz işlem hata mesajı gösterilir. *(FR-012)*
- [ ] Kullanıcı üyesi olmadığı bir projeye erişmeye çalıştığında proje verileri gösterilmez ve erişim reddedildi mesajı gösterilir. *(FR-013)*

**Karşıladığı FR'ler:** FR-012, FR-013  
**Öncelik:** Must

---

### US-006 – Proje oluşturma

**Hikâye:** Bir Yönetici olarak, yeni bir çalışmayı takip edebilmek için proje adı, açıklama ve tarih bilgileriyle proje oluşturmak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici proje adı, açıklama, başlangıç tarihi ve bitiş tarihini girip kaydettiğinde proje oluşturulur. *(FR-015)*
- [ ] Bitiş tarihi başlangıç tarihinden önce olan proje kaydedilmeye çalışıldığında proje kaydedilmez ve tarih hatası mesajı gösterilir. *(FR-016)*

**Karşıladığı FR'ler:** FR-015, FR-016  
**Öncelik:** Must

---

### US-007 – Proje listeleme

**Hikâye:** Bir Ekip Üyesi olarak, çalışacağım projelere ulaşabilmek için projeler sayfasında üyesi olduğum projeleri görmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı projeler sayfasını açtığında yalnızca üyesi olduğu projeler listelenir. *(FR-017)*

**Karşıladığı FR'ler:** FR-017  
**Öncelik:** Must

---

### US-008 – Proje düzenleme

**Hikâye:** Bir Yönetici olarak, proje bilgilerini güncel tutabilmek için mevcut bir projenin bilgilerini düzenlemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici mevcut bir projenin adını, açıklamasını ve tarih bilgilerini düzenlediğinde bu bilgiler güncellenir. *(FR-018)*

**Karşıladığı FR'ler:** FR-018  
**Öncelik:** Must

---

### US-009 – Proje silme

**Hikâye:** Bir Yönetici olarak, artık gerekmeyen projeleri kaldırırken yanlışlıkla silmeyi önlemek için onay vererek projeyi silmek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici bir projeyi silmek istediğinde silme işleminden önce onay penceresi gösterilir. *(FR-019)*
- [ ] Yönetici onay penceresinde işlemi onayladığında proje ve projeye bağlı görevler silinir. *(FR-020)*

**Karşıladığı FR'ler:** FR-019, FR-020  
**Öncelik:** Must

---

### US-010 – Proje üyesi yönetimi

**Hikâye:** Bir Yönetici olarak, projede çalışacak ekibi belirleyebilmek için projeye ekip üyesi eklemek ve çıkarmak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici projeye üye eklemek istediğinde kullanıcı e-posta adresi veya davet bağlantısı ile projeye eklenebilir. *(FR-021)*
- [ ] Yönetici bir ekip üyesini projeden çıkarmayı onayladığında kullanıcı projeden çıkarılır. *(FR-022)*

**Karşıladığı FR'ler:** FR-021, FR-022  
**Öncelik:** Must

---

### US-011 – Görev oluşturma

**Hikâye:** Bir Yönetici olarak, yapılacak işleri tanımlayabilmek için görev bilgilerini girerek görev oluşturmak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici yeni görev oluşturmak istediğinde görev başlığı, açıklaması, sorumlu kişi, başlangıç tarihi ve teslim tarihi girilebilir. *(FR-024)*
- [ ] Görev başlığı boş bırakıldığında veya teslim tarihi başlangıç tarihinden önce seçildiğinde görev kaydedilmez ve hatalı alanı belirten mesaj gösterilir. *(FR-025)*

**Karşıladığı FR'ler:** FR-024, FR-025  
**Öncelik:** Must

---

### US-012 – Görev atama

**Hikâye:** Bir Yönetici olarak, işlerin sorumlularını belirleyebilmek için oluşturulmuş veya onaylanmış bir görevi ekip üyesine atamak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici görevi bir ekip üyesine atadığında görev seçilen ekip üyesinin görev listesine eklenir. *(FR-030)*

**Karşıladığı FR'ler:** FR-030  
**Öncelik:** Must

---

### US-013 – Görev düzenleme ve silme

**Hikâye:** Bir Yönetici olarak, görev bilgilerini güncel tutmak ve gereksiz görevleri kaldırmak için görevleri düzenlemek ve silmek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici bir görevin bilgilerini değiştirmek istediğinde görev bilgileri güncellenebilir. *(FR-031)*
- [ ] Yönetici görevi silmeyi onayladığında görev silinir. *(FR-032)*

**Karşıladığı FR'ler:** FR-031, FR-032  
**Öncelik:** Must

---

### US-014 – Görev durumu güncelleme

**Hikâye:** Bir Ekip Üyesi olarak, işin ilerleyişini yansıtabilmek için bana atanmış görevlerin durumunu değiştirmek istiyorum.

**Kabul kriterleri:**
- [ ] Ekip üyesi kendisine atanmış bir görevin durumunu To Do, In Progress, Review & Testing veya Done olarak güncelleyebilir. *(FR-033)*
- [ ] Ekip Üyesi kendisine atanmamış bir görevin durumunu değiştirmeye çalıştığında durum değişmez ve yetki hatası mesajı gösterilir. *(FR-034)*

**Karşıladığı FR'ler:** FR-033, FR-034  
**Öncelik:** Must

---

### US-015 – Kanban panosu

**Hikâye:** Bir Ekip Üyesi olarak, görevlerin durumunu bir bakışta izleyebilmek için Kanban panosunda görevleri görmek ve sütunlar arasında taşımak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı erişim yetkisi olan bir projenin panosunu açtığında aktif görevler To Do, In Progress, Review & Testing ve Done sütunlarında gösterilir. *(FR-042)*
- [ ] Kullanıcı yetkili olduğu bir görevi başka bir sütuna sürüklediğinde görevin durumu yeni sütuna karşılık gelen durum olarak güncellenir. *(FR-043)*

**Karşıladığı FR'ler:** FR-042, FR-043  
**Öncelik:** Must

---

### US-016 – Takvim görünümü

**Hikâye:** Bir Ekip Üyesi olarak, görevleri tarih bazında planlayabilmek için görevlerin başlangıç ve teslim tarihlerini takvimde görmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı bir projedeki görevleri tarih bazında incelemek istediğinde görevlerin başlangıç ve teslim tarihleri takvim üzerinde gösterilir. *(FR-044)*

**Karşıladığı FR'ler:** FR-044  
**Öncelik:** Must

---

### US-017 – Gantt şeması

**Hikâye:** Bir Ekip Üyesi olarak, proje zaman çizelgesini takip edebilmek için görevleri Gantt şemasında görmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı proje zaman çizelgesini görüntülemek istediğinde görevlerin başlangıç ve bitiş tarihleri Gantt şemasında gösterilir. *(FR-045)*

**Karşıladığı FR'ler:** FR-045  
**Öncelik:** Must

---

### US-018 – Doküman yükleme

**Hikâye:** Bir Ekip Üyesi olarak, proje ve görevle ilgili dosyaları bir arada tutabilmek için projeye veya göreve dosya yüklemek istiyorum.

**Kabul kriterleri:**
- [ ] PDF, DOCX, XLSX, PPTX, PNG, JPG veya TXT formatında ve en fazla 10 MB boyutunda dosya yüklendiğinde dosya ilgili proje veya göreve eklenir. *(FR-046)*
- [ ] Desteklenmeyen formatta veya 10 MB'tan büyük dosya yüklenmeye çalışıldığında dosya kaydedilmez ve dosya formatı veya boyutu hatası mesajı gösterilir. *(FR-047)*

**Karşıladığı FR'ler:** FR-046, FR-047  
**Öncelik:** Must

---

### US-019 – Doküman indirme

**Hikâye:** Bir Ekip Üyesi olarak, ihtiyaç duyduğum dosyalara ulaşabilmek için erişim yetkim olan dokümanları indirmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı erişim yetkisi olan bir dokümanı indirmek istediğinde doküman indirilebilir. *(FR-048)*

**Karşıladığı FR'ler:** FR-048  
**Öncelik:** Must

---

### US-020 – Yorum ekleme

**Hikâye:** Bir Ekip Üyesi olarak, ekiple görev ve doküman üzerinden iletişim kurabilmek için görev veya doküman üzerine yorum yapmak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı erişim yetkisi olan bir görev veya doküman üzerinde yorum yapmak istediğinde yorum eklenebilir. *(FR-050)*

**Karşıladığı FR'ler:** FR-050  
**Öncelik:** Must

---

### US-021 – Uygulama içi bildirimler

**Hikâye:** Bir Ekip Üyesi olarak, beni ilgilendiren gelişmeleri kaçırmamak için uygulama içi bildirim almak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcıyı ilgilendiren bir görev, yorum, tarih veya onay olayı gerçekleştiğinde kullanıcıya uygulama içi bildirim gösterilir. *(FR-051)*
- [ ] Yönetici bir görevi kullanıcıya atadığında atanan kullanıcıya uygulama içi bildirim gösterilir. *(FR-052)*

**Karşıladığı FR'ler:** FR-051, FR-052  
**Öncelik:** Must

---

### US-022 – Dashboard ve proje ilerlemesi

**Hikâye:** Bir Ekip Üyesi olarak, çalışmamın genel durumunu görebilmek için ana sayfada özet bilgileri ve proje ilerleme yüzdesini görmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı giriş yaptıktan sonra ana sayfayı görüntülediğinde projeleri, görev durumları, yaklaşan teslim tarihleri ve okunmamış bildirimleri özetlenir. *(FR-060)*
- [ ] Kullanıcı bir projenin dashboardunu görüntülediğinde Done durumundaki görevlerin toplam görevlere oranı proje ilerleme yüzdesi olarak gösterilir. *(FR-061)*

**Karşıladığı FR'ler:** FR-060, FR-061  
**Öncelik:** Must

---

### US-023 – Kişi bazlı ve dönemsel raporlar

**Hikâye:** Bir Yönetici olarak, ekibin ve projenin ilerlemesini değerlendirebilmek için kişi bazlı ve dönemsel proje raporlarını görüntülemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici proje raporlarını görüntülediğinde her ekip üyesinin To Do, In Progress, Review & Testing ve Done durumundaki görev sayıları gösterilir. *(FR-062)*
- [ ] Yönetici günlük, haftalık veya aylık dönemlerden birini seçtiğinde seçilen dönemde tamamlanan ve yeni açılan görev sayılarını içeren ilerleme raporu oluşturulur. *(FR-063)*

**Karşıladığı FR'ler:** FR-062, FR-063  
**Öncelik:** Must

---

### US-024 – Gecikme risk seviyesi

**Hikâye:** Bir Yönetici olarak, gecikme riski taşıyan görevleri erken fark edebilmek için görevlerin gecikme risk seviyesini görmek istiyorum.

**Kabul kriterleri:**
- [ ] Done durumunda olmayan bir görev görüntülendiğinde teslim tarihi, durumu, alt görevlerinin tamamlanma oranı, efor puanı ve atanan kişinin aktif görev yükü kullanılarak hesaplanan Düşük, Orta veya Yüksek gecikme risk seviyesi gösterilir. *(FR-070)*
- [ ] Teslim tarihi geçmiş ve Done durumunda olmayan görevin gecikme risk seviyesi Yüksek olarak gösterilir. *(FR-071)*

**Karşıladığı FR'ler:** FR-070, FR-071  
**Öncelik:** Must

---

### US-025 – Kapasite sınırı ve kapasite uyarısı

**Hikâye:** Bir Yönetici olarak, ekip üyelerinin aşırı yüklenmesini önlemek için kapasite sınırı tanımlamak ve atama sırasında kapasite uyarısı almak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici bir ekip üyesi veya sprint için kapasite sınırı girdiğinde girilen değer ilgili ekip üyesinin veya sprintin iş yükü hesaplamalarında kullanılır. *(FR-075)*
- [ ] Görev atanırken ekip üyesinin Done durumunda olmayan görevlerinin toplam Fibonacci puanı kapasite sınırını aşacaksa, atama tamamlanmadan önce ekip üyesinin adını ve toplam Fibonacci puanını içeren kapasite uyarısı gösterilir. *(FR-073)*

**Karşıladığı FR'ler:** FR-073, FR-075  
**Öncelik:** Must

---

### US-026 – LLM önerilerinin kontrolü ve hata durumu

**Hikâye:** Bir Yönetici olarak, yapay zekâ destekli özelliklerin kontrolümde ve öngörülebilir çalışmasını sağlamak için LLM önerilerini onaylamak ve servis kullanılamadığında bilgilendirilmek istiyorum.

**Kabul kriterleri:**
- [ ] LLM görev, alt görev veya efor önerisi ürettiğinde öneri Yönetici onaylamadan kaydedilmez. *(FR-078)*
- [ ] Birincil ve yedek LLM servislerinin ikisi de yanıt vermediğinde LLM özelliğinin şu an kullanılamadığını belirten mesaj gösterilir. *(FR-084)*

**Karşıladığı FR'ler:** FR-078, FR-084  
**Öncelik:** Must

---

## 4. Should öncelikli story'ler

### US-027 – Şifre sıfırlama

**Hikâye:** Bir Ekip Üyesi olarak, şifremi unuttuğumda hesabıma yeniden erişebilmek için e-postama gelen bağlantıyla şifremi yenilemek istiyorum.

**Kabul kriterleri:**
- [ ] Kayıtlı kullanıcı şifresini unuttuğunu bildirdiğinde e-posta adresine 30 dakika geçerli bir şifre yenileme bağlantısı gönderilir. *(FR-008)*

**Karşıladığı FR'ler:** FR-008  
**Öncelik:** Should

---

### US-028 – Profil düzenleme

**Hikâye:** Bir Ekip Üyesi olarak, profil bilgilerimi güncel tutabilmek için adımı ve profil fotoğrafımı güncellemek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı profil bilgilerini düzenlediğinde ad ve profil fotoğrafı bilgileri güncellenir. *(FR-009)*

**Karşıladığı FR'ler:** FR-009  
**Öncelik:** Should

---

### US-029 – Teknik rol atama ve rol görüntüleme

**Hikâye:** Bir Yönetici olarak, ekipteki iş dağılımını açık hale getirmek için üyelere teknik rol atamak ve rolleri görüntülemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici proje üyesine teknik rol (ör. frontend geliştirici, backend geliştirici, tasarımcı) atadığında atanan rol ekip bilgisinde gösterilir. *(FR-023)*
- [ ] Kullanıcı profilini veya ekip listesini görüntülediğinde kullanıcının sistem rolü ve proje içindeki teknik rolü gösterilir. *(FR-014)*

**Karşıladığı FR'ler:** FR-014, FR-023  
**Öncelik:** Should

---

### US-030 – Görev önerme

**Hikâye:** Bir Ekip Üyesi olarak, yapılması gereken işleri ekibe iletebilmek için yeni görev önermek istiyorum.

**Kabul kriterleri:**
- [ ] Ekip üyesi yeni bir görev oluşturduğunda görev Onay Bekliyor durumunda kaydedilir. *(FR-026)*

**Karşıladığı FR'ler:** FR-026  
**Öncelik:** Should

---

### US-031 – Önerilen görevlere karar verme

**Hikâye:** Bir Yönetici olarak, ekip üyelerinin önerdiği görevleri kontrol edebilmek için onay bekleyen görevleri onaylamak, reddetmek veya düzenlemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici Onay Bekliyor durumundaki bir ekip üyesi görevini açtığında görevi onaylayabilir, reddedebilir veya düzenleyebilir. *(FR-027)*
- [ ] Yönetici onay bekleyen görevi onayladığında görevin durumu To Do olarak güncellenir. *(FR-028)*
- [ ] Yönetici onay bekleyen görevi reddettiğinde görevin durumu Reddedildi olarak kaydedilir. *(FR-029)*

**Karşıladığı FR'ler:** FR-027, FR-028, FR-029  
**Öncelik:** Should

---

### US-032 – Görev önceliği ve efor puanı

**Hikâye:** Bir Yönetici olarak, görevlerin önemini ve büyüklüğünü belirleyebilmek için göreve öncelik ve Fibonacci efor puanı atamak istiyorum.

**Kabul kriterleri:**
- [ ] Görev oluşturulurken veya düzenlenirken Düşük, Orta veya Yüksek öncelik değeri atanabilir. *(FR-035)*
- [ ] Görev oluşturulurken veya düzenlenirken efor yalnızca 1, 2, 3, 5, 8 veya 13 değerlerinden biriyle puanlanabilir. *(FR-036)*

**Karşıladığı FR'ler:** FR-035, FR-036  
**Öncelik:** Should

---

### US-033 – Görev etiketi ve alt görevler

**Hikâye:** Bir Ekip Üyesi olarak, görevleri sınıflandırıp parçalara ayırabilmek için göreve etiket eklemek ve alt görev tanımlamak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı görev oluştururken veya düzenlerken göreve bir veya birden fazla etiket ekleyebilir. *(FR-037)*
- [ ] Kullanıcı bir görevin alt görevlerini tanımlamak istediğinde ana göreve bağlı alt görevler oluşturulabilir. *(FR-038)*

**Karşıladığı FR'ler:** FR-037, FR-038  
**Öncelik:** Should

---

### US-034 – Görev arama ve filtreleme

**Hikâye:** Bir Ekip Üyesi olarak, aradığım göreve ulaşabilmek için görevleri filtrelemek ve görev adına göre aramak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı görev listesini incelediğinde görevler kişi, durum, öncelik ve etiket bilgilerine göre filtrelenebilir ve görev adına göre aranabilir. *(FR-041)*

**Karşıladığı FR'ler:** FR-041  
**Öncelik:** Should

---

### US-035 – Doküman silme

**Hikâye:** Bir Ekip Üyesi olarak, yanlış veya eski dosyaları kaldırabilmek için yüklenmiş dokümanları silmek istiyorum.

**Kabul kriterleri:**
- [ ] Dosyayı yükleyen kullanıcı veya Yönetici dosyayı silmeyi onayladığında dosya silinir. *(FR-049)*

**Karşıladığı FR'ler:** FR-049  
**Öncelik:** Should

---

### US-036 – E-posta bildirimi ve bildirim tercihleri

**Hikâye:** Bir Ekip Üyesi olarak, bildirimleri istediğim kanaldan alabilmek için görev atama e-postası almak ve bildirim tercihlerimi yönetmek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici bir görevi kullanıcıya atadığında ve kullanıcının e-posta bildirimleri açıksa atanan kullanıcıya görev atama e-postası gönderilir. *(FR-053)*
- [ ] Kullanıcı bildirim ayarlarında e-posta bildirimlerini ve uygulama içi bildirimleri ayrı ayrı etkinleştirebilir veya devre dışı bırakabilir. *(FR-058)*

**Karşıladığı FR'ler:** FR-053, FR-058  
**Öncelik:** Should

---

### US-037 – Yorum bildirimi

**Hikâye:** Bir Ekip Üyesi olarak, görevlerimdeki tartışmaları takip edebilmek için yeni yorumlar için uygulama içi bildirim almak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcının görevine veya dahil olduğu yorum zincirine yeni yorum eklendiğinde ilgili kullanıcıya uygulama içi bildirim gösterilir. *(FR-054)*

**Karşıladığı FR'ler:** FR-054  
**Öncelik:** Should

---

### US-038 – Teslim ve güncelleme hatırlatmaları

**Hikâye:** Bir Ekip Üyesi olarak, görevlerimi zamanında tamamlayabilmek için teslim tarihi ve güncellenmeyen görevler için hatırlatma almak istiyorum.

**Kabul kriterleri:**
- [ ] Teslim tarihine 2 gün veya daha az kalmış ve Done durumunda olmayan görevin sahibine teslim tarihi yaklaşma bildirimi gönderilir. *(FR-056)*
- [ ] Done durumunda olmayan bir görev 4 gün boyunca güncellenmezse görev sahibine görevi güncellemesi için hatırlatma gönderilir. *(FR-057)*

**Karşıladığı FR'ler:** FR-056, FR-057  
**Öncelik:** Should

---

### US-039 – Rapor dışa aktarma

**Hikâye:** Bir Yönetici olarak, raporları ekip dışıyla paylaşabilmek için raporları PDF veya Excel olarak dışa aktarmak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici oluşturulan raporu dışa aktarmak istediğinde rapor PDF veya Excel formatında dışa aktarılır. *(FR-064)*

**Karşıladığı FR'ler:** FR-064  
**Öncelik:** Should

---

### US-040 – Sprint oluşturma ve planlama

**Hikâye:** Bir Yönetici olarak, çalışmayı sprintler halinde organize edebilmek için sprint oluşturmak ve görevleri sprinte bağlamak istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici sprint oluşturduğunda sprint başlangıç ve bitiş tarihleri ile sprint hedefi tanımlanabilir. *(FR-066)*
- [ ] Yönetici sprinti planladığında mevcut görevler seçilen sprint ile ilişkilendirilebilir. *(FR-067)*

**Karşıladığı FR'ler:** FR-066, FR-067  
**Öncelik:** Should

---

### US-041 – Sprint ilerlemesi

**Hikâye:** Bir Yönetici olarak, sprintin gidişatını değerlendirebilmek için aktif sprintin ilerlemesini görmek istiyorum.

**Kabul kriterleri:**
- [ ] Aktif bir sprint bulunduğunda sprintteki Done durumundaki görevlerin efor puanı toplamının sprintin toplam efor puanına oranı gösterilir. *(FR-068)*

**Karşıladığı FR'ler:** FR-068  
**Öncelik:** Should

---

### US-042 – Bugün ne yapmalıyım listesi

**Hikâye:** Bir Ekip Üyesi olarak, önceliklendirme yapabilmek için giriş yaptığımda acil görevlerimi sıralı görmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı giriş yaptığında kendisine atanmış, Done durumunda olmayan ve teslim tarihine 3 gün veya daha az kalan ya da teslim tarihi geçmiş görevler önce teslim tarihine, sonra önceliğe göre sıralanarak listelenir. *(FR-069)*

**Karşıladığı FR'ler:** FR-069  
**Öncelik:** Should

---

### US-043 – Tamamlanan görevde risk göstermeme

**Hikâye:** Bir Yönetici olarak, tamamlanmış işlerin gereksiz risk uyarılarıyla karışmasını önlemek için Done görevlerde gecikme riskinin gösterilmemesini sağlamak istiyorum.

**Kabul kriterleri:**
- [ ] Görev Done durumundaysa görev için gecikme risk seviyesi gösterilmez. *(FR-072)*

**Karşıladığı FR'ler:** FR-072  
**Öncelik:** Should

---

### US-044 – Kapasite tanımsız durumu

**Hikâye:** Bir Yönetici olarak, kapasite tanımlamadığım durumlarda gereksiz uyarı almamak için kapasite sınırı tanımsızken uyarı gösterilmemesini sağlamak istiyorum.

**Kabul kriterleri:**
- [ ] Ekip üyesi veya sprint için kapasite sınırı tanımlanmamışsa kapasite uyarısı gösterilmez. *(FR-074)*

**Karşıladığı FR'ler:** FR-074  
**Öncelik:** Should

---

### US-045 – Yedek LLM servisi

**Hikâye:** Bir Yönetici olarak, LLM özelliklerinin kesintiye uğramadan çalışmasını sağlamak için birincil servis yanıt vermediğinde isteğin yedek servise yönlendirilmesini istemek istiyorum.

**Kabul kriterleri:**
- [ ] Birincil LLM servisi 10 saniye içinde yanıt vermezse istek yedek LLM servisine yönlendirilir. *(FR-083)*

**Karşıladığı FR'ler:** FR-083  
**Öncelik:** Should

---

## 5. Could öncelikli story'ler

### US-046 – Alt görev önceliği

**Hikâye:** Bir Ekip Üyesi olarak, alt görevleri sıralayabilmek için alt göreve öncelik atamak istiyorum.

**Kabul kriterleri:**
- [ ] Alt görev oluşturulduğunda alt göreve Düşük, Orta veya Yüksek öncelik değeri atanabilir. *(FR-039)*

**Karşıladığı FR'ler:** FR-039  
**Öncelik:** Could

---

### US-047 – Görev bağımlılığı

**Hikâye:** Bir Ekip Üyesi olarak, görevler arasındaki sıralamayı netleştirmek için görevler arasında bağımlılık tanımlamak istiyorum.

**Kabul kriterleri:**
- [ ] Bir görev başka bir görevin tamamlanmasına bağlıysa görevler arasında bağımlılık tanımlanabilir. *(FR-040)*

**Karşıladığı FR'ler:** FR-040  
**Öncelik:** Could

---

### US-048 – Yorum e-postası ve haftalık özet e-postası

**Hikâye:** Bir Ekip Üyesi olarak, e-postamdan projedeki gelişmelerden haberdar olmak için yorum e-postası ve haftalık özet e-postası almak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcının görevine yeni yorum eklendiğinde ve kullanıcının e-posta bildirimleri açıksa ilgili kullanıcıya yorum bildirimi e-postası gönderilir. *(FR-055)*
- [ ] Pazartesi saat 09:00 olduğunda ve kullanıcı haftalık özet bildirimini etkinleştirmişse proje ilerlemesi ve görev durumlarını içeren haftalık özet e-posta ile gönderilir. *(FR-059)*

**Karşıladığı FR'ler:** FR-055, FR-059  
**Öncelik:** Could

---

### US-049 – Aydınlık/karanlık tema

**Hikâye:** Bir Ekip Üyesi olarak, arayüzü göz konforuma göre kullanabilmek için aydınlık veya karanlık tema seçmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı tema ayarından aydınlık veya karanlık temayı seçtiğinde seçilen tema uygulanır. *(FR-065)*

**Karşıladığı FR'ler:** FR-065  
**Öncelik:** Could

---

### US-050 – İş yükü dağılım önerisi

**Hikâye:** Bir Yönetici olarak, aşırı yüklenen üyelerin işlerini dengeleyebilmek için alternatif iş yükü dağılımı önerisi almak istiyorum.

**Kabul kriterleri:**
- [ ] Ekip üyesinin aktif sprintteki toplam efor puanı kapasite sınırını aştığında kapasitesi uygun ekip üyelerini içeren alternatif dağılım önerisi oluşturulur. *(FR-076)*

**Karşıladığı FR'ler:** FR-076  
**Öncelik:** Could

---

### US-051 – Toplantı notundan görev çıkarma

**Hikâye:** Bir Yönetici olarak, toplantı kararlarını görevlere dönüştürmek için toplantı notundan LLM ile görev önerileri üretmek istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı toplantı notunu LLM destekli görev çıkarma alanına girdiğinde metinden görev başlığı, sorumlu kişi ve tarih bilgilerini içeren görev önerileri üretilir. *(FR-077)*

**Karşıladığı FR'ler:** FR-077  
**Öncelik:** Could

---

### US-052 – LLM ile alt görev ve efor önerisi

**Hikâye:** Bir Yönetici olarak, görev planlamasını hızlandırmak için LLM'den alt görev ve efor puanı önerisi istemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici görevin alt görevlere bölünmesini istediğinde görev açıklaması analiz edilerek alt görev önerileri üretilir. *(FR-079)*
- [ ] Yönetici efor önerisi istediğinde görev açıklaması analiz edilerek 1, 2, 3, 5, 8 veya 13 değerlerinden biri efor puanı olarak önerilir. *(FR-080)*

**Karşıladığı FR'ler:** FR-079, FR-080  
**Öncelik:** Could

---

### US-053 – LLM ile haftalık ve yorum özeti

**Hikâye:** Bir Yönetici olarak, uzun bilgileri kısa sürede kavrayabilmek için haftalık proje özeti ve yorum zinciri özeti istemek istiyorum.

**Kabul kriterleri:**
- [ ] Yönetici haftalık proje özeti istediğinde son 7 günün görev ve ilerleme verilerini özetleyen metin üretilir. *(FR-081)*
- [ ] Görevde en az 5 yorum varsa ve kullanıcı özet isterse yorum zincirindeki kararlar ve açık konular özetlenir. *(FR-082)*

**Karşıladığı FR'ler:** FR-081, FR-082  
**Öncelik:** Could

---

### US-054 – Proje chatbotu

**Hikâye:** Bir Ekip Üyesi olarak, proje bilgilerine soru sorarak ulaşabilmek için proje chatbotuna soru sormak ve önerilen işlemleri onaylamak istiyorum.

**Kabul kriterleri:**
- [ ] Kullanıcı chatbota proje yönetimi sorusu gönderdiğinde yanıt yalnızca kullanıcının erişim yetkisi olan proje verilerine dayanarak üretilir. *(FR-085)*
- [ ] Chatbot veri değiştiren bir işlem önerdiğinde işlem kullanıcı onayı olmadan gerçekleştirilmez. *(FR-086)*

**Karşıladığı FR'ler:** FR-085, FR-086  
**Öncelik:** Could

---

## 6. FR → US eşleme tablosu

| FR No | FR Başlığı | Öncelik | Story |
|---|---|---|---|
| FR-001 | Kullanıcı Kaydı | Must | US-001 |
| FR-002 | Kayıt Başarı Mesajı | Must | US-001 |
| FR-003 | Kayıtlı E-posta Hatası | Must | US-001 |
| FR-004 | Geçersiz Kayıt Bilgisi | Must | US-001 |
| FR-005 | Kullanıcı Girişi | Must | US-002 |
| FR-006 | Hatalı Giriş | Must | US-002 |
| FR-007 | Çıkış Yapma | Must | US-003 |
| FR-008 | Şifre Sıfırlama | Should | US-027 |
| FR-009 | Profil Düzenleme | Should | US-028 |
| FR-010 | Varsayılan Sistem Rolü | Must | US-004 |
| FR-011 | Sistem Rolü Değiştirme | Must | US-004 |
| FR-012 | Yetkisiz İşlem Engeli | Must | US-005 |
| FR-013 | Proje Erişim Kısıtı | Must | US-005 |
| FR-014 | Rol Görüntüleme | Should | US-029 |
| FR-015 | Proje Oluşturma | Must | US-006 |
| FR-016 | Geçersiz Proje Tarihi | Must | US-006 |
| FR-017 | Proje Listeleme | Must | US-007 |
| FR-018 | Proje Düzenleme | Must | US-008 |
| FR-019 | Proje Silme Onayı | Must | US-009 |
| FR-020 | Proje Silme | Must | US-009 |
| FR-021 | Proje Üyesi Ekleme | Must | US-010 |
| FR-022 | Proje Üyesi Çıkarma | Must | US-010 |
| FR-023 | Teknik Rol Tanımlama | Should | US-029 |
| FR-024 | Görev Oluşturma | Must | US-011 |
| FR-025 | Geçersiz Görev Bilgisi | Must | US-011 |
| FR-026 | Ekip Üyesi Görev Önerisi | Should | US-030 |
| FR-027 | Görev Önerisi Yönetici Kararı | Should | US-031 |
| FR-028 | Görev Önerisi Onayı | Should | US-031 |
| FR-029 | Görev Önerisi Reddi | Should | US-031 |
| FR-030 | Görev Atama | Must | US-012 |
| FR-031 | Görev Düzenleme | Must | US-013 |
| FR-032 | Görev Silme | Must | US-013 |
| FR-033 | Görev Durumu Değiştirme | Must | US-014 |
| FR-034 | Başkasının Görevini Değiştirme Engeli | Must | US-014 |
| FR-035 | Görev Önceliği | Should | US-032 |
| FR-036 | Fibonacci Efor Puanı | Should | US-032 |
| FR-037 | Görev Etiketi | Should | US-033 |
| FR-038 | Alt Görev Oluşturma | Should | US-033 |
| FR-039 | Alt Görev Önceliği | Could | US-046 |
| FR-040 | Görev Bağımlılığı | Could | US-047 |
| FR-041 | Arama ve Filtreleme | Should | US-034 |
| FR-042 | Kanban Panosu | Must | US-015 |
| FR-043 | Kanban Sürükle-Bırak | Must | US-015 |
| FR-044 | Takvim Görünümü | Must | US-016 |
| FR-045 | Gantt Şeması | Must | US-017 |
| FR-046 | Doküman Yükleme | Must | US-018 |
| FR-047 | Geçersiz Dosya | Must | US-018 |
| FR-048 | Doküman İndirme | Must | US-019 |
| FR-049 | Doküman Silme | Should | US-035 |
| FR-050 | Yorum Ekleme | Must | US-020 |
| FR-051 | Uygulama İçi Bildirimler | Must | US-021 |
| FR-052 | Görev Atama Bildirimi | Must | US-021 |
| FR-053 | Görev Atama E-postası | Should | US-036 |
| FR-054 | Yorum Bildirimi | Should | US-037 |
| FR-055 | Yorum E-postası | Could | US-048 |
| FR-056 | Teslim Tarihi Hatırlatması | Should | US-038 |
| FR-057 | Güncellenmeyen Görev Hatırlatması | Should | US-038 |
| FR-058 | Bildirim Tercihleri | Should | US-036 |
| FR-059 | Otomatik Haftalık Özet E-postası | Could | US-048 |
| FR-060 | Dashboard | Must | US-022 |
| FR-061 | Proje İlerleme Yüzdesi | Must | US-022 |
| FR-062 | Kişi Bazlı Rapor | Must | US-023 |
| FR-063 | Dönemsel Rapor | Must | US-023 |
| FR-064 | Rapor Dışa Aktarma | Should | US-039 |
| FR-065 | Aydınlık/Karanlık Tema | Could | US-049 |
| FR-066 | Sprint Oluşturma | Should | US-040 |
| FR-067 | Sprint Görevleri | Should | US-040 |
| FR-068 | Sprint İlerlemesi | Should | US-041 |
| FR-069 | Bugün Ne Yapmalıyım | Should | US-042 |
| FR-070 | Gecikme Risk Seviyesi | Must | US-024 |
| FR-071 | Süresi Geçmiş Görev Riski | Must | US-024 |
| FR-072 | Tamamlanan Görev Riski | Should | US-043 |
| FR-073 | Kapasite Uyarısı | Must | US-025 |
| FR-074 | Kapasite Tanımsız Durumu | Should | US-044 |
| FR-075 | Kapasite Sınırı Ayarı | Must | US-025 |
| FR-076 | İş Yükü Dağılım Önerisi | Could | US-050 |
| FR-077 | Toplantı Notundan Görev Çıkarma | Could | US-051 |
| FR-078 | LLM Önerisi Onayı | Must | US-026 |
| FR-079 | LLM Görevi Alt Görevlere Bölme | Could | US-052 |
| FR-080 | LLM Efor Puanı Önerisi | Could | US-052 |
| FR-081 | LLM Haftalık Özet | Could | US-053 |
| FR-082 | LLM Yorum Özeti | Could | US-053 |
| FR-083 | Yedek LLM Servisi | Should | US-045 |
| FR-084 | LLM Servisi Kullanılamıyor | Must | US-026 |
| FR-085 | LLM Chatbot Yanıtı | Could | US-054 |
| FR-086 | Chatbot İşlem Onayı | Could | US-054 |

## 7. Kontrol listesi (Bitti tanımı)

- [x] Dokümandaki FR sayısı (86) = eşleme tablosundaki FR sayısı (86); story'siz FR yok
- [x] Hiçbir FR birden fazla story'ye atanmamış (tekrar yok)
- [x] Her story'de numara, hikâye, kabul kriterleri, FR numaraları ve öncelik var (US-001 – US-054, sıralı ve tekrarsız)
- [x] Her story'nin önceliği, içerdiği tüm FR'lerin önceliğiyle aynı
- [x] Sıralama: önce Must, sonra Should, sonra Could
- [ ] PR açıldı ve onaylandı
- [ ] Board'daki kart güncellendi

## 8. Gözden geçirenlerin dikkatine: gereksinimlerde fark edilen noktalar

Story'ler yazılırken gereksinim dokümanında şu tutarsızlıklar/boşluklar görüldü. Story'lerde bunlara dair varsayım yapılmamış, olduğu gibi aktarılmıştır; karar için ekip ile netleştirilmelidir.

1. **Öncelik bağımlılığı (Must → Should):** Must olan FR-070 (gecikme riski) ve FR-073 (kapasite uyarısı) efor puanını kullanır; efor puanı FR-036 ise Should'dur. FR-070 ayrıca alt görev tamamlanma oranını kullanır; alt görevler FR-038 ile Should'dur. FR-075 (Must) sprint kapasitesinden söz eder, sprint FR-066 ile Should'dur. Bu Must story'lerinin (US-024, US-025) tam test edilebilmesi için ilgili Should story'leri (US-032, US-033, US-040) de aynı iterasyonda planlanmalı ya da öncelikler yeniden değerlendirilmelidir.
2. **LLM guard-rail'leri Must, LLM özellikleri Could/Should:** FR-078 ve FR-084 Must, ancak onay verilecek öneriler (FR-077, 079, 080) Could, yedek servis (FR-083) Should. LLM özelliği yapılmazsa US-026 test edilemez.
3. **Bildirim bağımlılığı:** FR-051 (Must) "tarih" ve "onay" olaylarında bildirim ister; bu olayların kaynağı olan hatırlatmalar (FR-056, FR-057) ve onay akışı (FR-026–029) Should'dur.
4. **Hesaplama kuralı tanımsız:** FR-070'te gecikme risk seviyesinin (Düşük/Orta/Yüksek) girdileri sayılmış fakat eşikler/formül verilmemiştir. FR-073'te "tanımlanan kapasite sınırı" için varsayılan bir değer yoktur (FR-074 sınır yoksa uyarı verilmeyeceğini söyler). Kabul kriterleri bu değerler netleşince sayısallaştırılmalıdır.
5. **Eşik değerleri farklı:** FR-056 teslim hatırlatması için 2 gün, FR-069 "Bugün Ne Yapmalıyım" listesi için 3 gün kullanır. Bilinçli bir fark mı, kontrol edilmelidir.
6. **Rol belirsizliği:** FR-026 "ekip üyesi", FR-037/FR-038 "kullanıcı" ifadesini kullanır; Yöneticinin de bu işlemleri yapıp yapamayacağı açık yazılmamıştır. Story'lerde Yönetici'nin de yapabildiği varsayılmıştır.
