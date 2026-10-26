# US-011 Görev oluşturma testleri

Görev: [#151](https://github.com/sengka/LUNO/issues/151) · Story: [#21](https://github.com/sengka/LUNO/issues/21) · FR-024, FR-025.
Tarih: **24.10.2026** · Hakan Aydın, Codex ile test hazırlığı ve API otomasyonu.
Güncel temel: develop **3237fc8b5c69cfb580404a90ff2e8f0877aa1aad**.
Kaynaklar: [user story](../analiz/user-stories.md), [API sözleşmesi 6.2](../api/api-sozlesmesi.md), [güncel backend görevi #149](https://github.com/sengka/LUNO/issues/149), [form görevi #150](https://github.com/sengka/LUNO/issues/150).

## Sonuç: tam kabul engelli

Güncel router'da görev durumu değiştirme `PATCH /tasks/{task_id}/status` var; **görev oluşturma POST /projects/{project_id}/tasks yok**. Frontend App, proje detay bileşeni ve features kaynaklarında görev oluşturma formu/API çağrısı yok. #149 ve #150 açık. Bu yüzden oluşturma, doğrulama ve yetki kriterleri geçti denemez.

- Yeni dosya: **2 geçti, 18 Engelli/skip**. Geçen ikisi yalnız model/veri saklama testidir, görev oluşturma API'sinin kabulü değildir.
- Tam backend: **178 geçti, 19 skip, 10 uyarı** (55.44 s). 19 skip = 18 US-011 + mevcut US-005 görev atama bağımlılığı. Mevcut 176 test + 2 model testi geçmiştir.
- Son rol beklentisi #149'a göre düzeltildikten sonra yeni dosya yeniden doğrulandı: 2 geçti/18 skip. API eklenmediği için rol senaryosu çalıştırılmış sayılmaz.
- [API kanıtı](us-011-api-kaniti.json): aynı izole gerçek uygulamada mevcut proje detayı 200; altı görev oluşturma denemesi 404; görev sayısı 0. Bu 404'ler doğrulama/yetki başarısı değildir.

## Sprint kapsamı ve rol kuralı

Genel sözleşme 6.2, ileride Ekip Üyesinin `ONAY_BEKLIYOR` önerisi oluşturmasını tanımlar. Ancak proje sahibinin #149 görevinde **bu sprintte yalnız proje üyesi yönetici oluşturur; ekip üyesi 403 FORBIDDEN alır; öneri akışı US-030 / Sprint 8'de eklenecek** açıklaması vardır. #151'in rol beklentisi bu güncel kapsamla uyumludur. Test şimdilik 403 ve hiç kayıt oluşmamasını bekler; Sprint 8'de kapsam değişince bu senaryo aynı PR'da güncellenmelidir. 403 veya 201'i rastgele kabul eden gevşek kontrol kullanılmadı.

## Ortam ve izolasyon

Windows, **Python 3.12.14**, pytest 9.1.1, FastAPI 0.162.0, SQLAlchemy 2.1.6, httpx 0.28.1, Pydantic 2.14.1. requirements.txt değiştirilmeden ayrı sanal ortam kuruldu. Gerçek FastAPI/TestClient rotaları kullanıldı; yalnız get_db izole bellek içi SQLite'a yönlendirildi. Yetki/oluşturma fonksiyonu mock edilmedi. PostgreSQL veya tarayıcıda form kabulü bu sonuçlardan çıkarılamaz.

Eski Desktop/LUNO deposunun .git yazımı engelli olduğundan güncel develop çalışma klasöründeki ayrı checkout'tan alındı. Kullanıcının mevcut package-lock.json/.vscode değişiklikleri, .env ve geliştirme veritabanı değiştirilmedi. Sentetik yönetici/üye/dış kullanıcı ve proje yalnız test belleğinde oluşturuldu. Login yerine test anahtarıyla sentetik token kuruldu; gerçek token/anahtar kanıta yazılmadı.

10 uyarı mevcut Starlette/httpx ve HTTP_422 adlandırma deprecation uyarılarıdır. Bunlar test başarısızlığı değildir. Test sayısı kod kapsamı yüzdesi değildir.

## Tekrar çalıştırma

Depo kökünden, backend sanal ortamı hazırlanmışken:

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend/tests/test_task_creation.py -q -r s
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -q -r s
```

Bu Windows oturumunda tam tur için ayrılmış yazılabilir --basetemp dizini kullanıldı. Pytest bu dizini temizleyebilir; gerçek dosya/veri klasörü seçilmez.

## Otomatik kabul senaryoları

Kaynak: [test_task_creation.py](../../backend/tests/test_task_creation.py).

| ID | Ön koşul / adımlar | Beklenen ve veri kontrolü | Sonuç |
| --- | --- | --- | --- |
| TC01 | Proje üyesi yönetici; Türkçe başlık, açıklama, proje üyesi sorumlu, başlangıç/teslim tarihi | 201; TODO, doğru created_by/assignee, alanlar DB'de birebir, yalnız bir kayıt | Engelli |
| TC02–03 | Başlık tam 2 / 200 karakter; TC02'de tarihler eşit | 201; eşit tarih kabul, alanlar kalıcı | 2 Engelli |
| TC04–08 | Başlık gönderilmemiş, boş, yalnız boşluk, 1 veya 201 karakter | 422 VALIDATION_ERROR, title alanı belirtilir; kayıt oluşmaz | 5 Engelli |
| TC09 | Teslim tarihi başlangıçtan bir gün önce | 400 INVALID_DATE_RANGE, tarih mesajı; mevcut sentinel görev değişmez, yeni görev yok | Engelli |
| TC10–11 | Proje dışındaki / sistemde olmayan kişiye atama | 400 ASSIGNEE_NOT_MEMBER; mevcut görev/veri değişmez | 2 Engelli |
| TC12–15 | Oturumsuz, bozuk token, proje dışındaki üye/yönetici | 401 UNAUTHORIZED veya 403 PROJECT_ACCESS_DENIED; görev yok | 4 Engelli |
| TC16 | Var olmayan proje ID'sinde oluşturma | 404 PROJECT_NOT_FOUND; görev yok; rotasız genel 404 kabul edilmez | Engelli |
| TC17 | Yönetici yalnız geçerli başlık gönderir | 201 TODO; isteğe bağlı alanlar zorunlu tutulmaz, atama yok | Engelli |
| TC18 | Proje üyesi EKIP_UYESI görev oluşturmayı dener | #149 güncel kapsamına göre 403 FORBIDDEN; görev oluşmaz | Engelli |
| M01–02 | Task modeliyle Türkçe alanları ve eşit/bir gün sonraki tarihleri sakla/yeniden oku | Başlık/açıklama/sorumlu/tarihler aynı; varsayılan TODO | 2 Geçti; yalnız model düzeyi |

18 skip yalnız gerçek POST metodunun OpenAPI'de bulunmaması koşuluna bağlıdır. API eklendiğinde otomatik kalkar; gerçek HTTP/mesaj/veri kontrolleri yürütülür. Testler 404'ü başarı saymak veya sahte ürün rotası eklemek için yazılmadı. Mevcut ters tarih DB constraint regresyonu da tam backend turundadır; SQL constraint olması kullanıcıya uygun API mesajı verildiği anlamına gelmez.

## Ön koşul API kanıtı

İzole TestClient kurulumu: mevcut proje, projeye üye yönetici ve ekip üyesi; proje dışındaki sentetik kişi.

| Deneme | Beklenti | Gerçek |
| --- | --- | --- |
| GET mevcut proje, aynı yönetici | 200 pozitif kimlik/proje kontrolü | 200 |
| Geçerli yönetici oluşturma | 201 TODO | 404, rota yok |
| Boş başlık | 422 ve alan mesajı | 404, rota yok |
| Ters tarih | 400 INVALID_DATE_RANGE | 404, rota yok |
| Dış kullanıcıya atama | 400 ASSIGNEE_NOT_MEMBER | 404, rota yok |
| Üye oluşturma | 403 FORBIDDEN | 404, rota yok |
| Oturumsuz oluşturma | 401 UNAUTHORIZED | 404, rota yok |

Son görev sayısı 0; bu, engelin veri yazmadığını gösterir, oluşturma/validation mantığının doğru olduğunu kanıtlamaz.

## Form kabul senaryoları: API/form sonrası yürütülecek

1. Üye yönetici formu açar; başlık/açıklama/sorumlu/başlangıç/teslim alanları girilip kaydedilir; başarı, listede tek kayıt ve API/DB alanları karşılaştırılır.
2. Boş/boşluk başlık ve ters tarihte hatalı alan mesajı görülür; kayıt yok; düzelttikten sonra aynı formda başarı doğrulanır. Başlık 1/2/200/201, eşit/önce/sonra tarih sınırları ayrı denenir.
3. Proje dışı kullanıcı seçimde listelenmemeli; elle API isteğinde de ASSIGNEE_NOT_MEMBER alınmalı.
4. Ekip üyesi oluşturma menüsünü/URL'yi denediğinde aktif görev oluşturamaz; bu sprintte gerçek API 403, UI'de uygun yetki geri bildirimi beklenir.
5. İptalde POST/veri değişimi yok; kaydetme sırasında tekrar tıklamada mükerrer görev oluşmaması gözlenir.

Bu turda form mevcut olmadığı için bu tarayıcı senaryoları **çalıştırılmadı**. Kaynak incelemesi veya önceki görevlere ait ekranlar UI kabul kanıtı yerine kullanılmadı.

## Bulgular, tekrar test ve kapanış

Bağımsız yeni bir çalışan özellik hatası doğrulanmadı; oluşturma özelliğinin eksikliği zaten açık #149 / #150 ile takip edilir. Kopya hata açılmadı; bu engeller ve kanıtlar #151/PR açıklamasına eklenir. Hata Raporu maddesi için bu tur N/A (yeni bağımsız hata yok); uygulanmış davranışta hata bulunursa şablonla açılır.

**#149 ve #150 tamamlanıp develop'a birleştirildiğinde** TC01–18, form adımları ve ilgili regresyon yeniden çalıştırılır. O turda validation mesajı/veri yokluğu, kullanıcı ataması ve rol engeli gerçek uygulamada kanıtlanmadan kabul tikleri işaretlenmez. Başarısızlıklar gizlenmez; gerekirse yeni hata issue'su ve yeniden test kanıtı eklenir.

#151 In progress kalır. Test kodu çalışıyor, tüm story geçti anlamına gelmez. PR inceleme/onayı ve kabulün tamamlanması farklı adımlardır; bu PR'da Closes kullanılmaz. API/form yokken Done veya tamamen bitti denmez.
