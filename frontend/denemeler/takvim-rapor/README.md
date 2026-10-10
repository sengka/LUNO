# LUNO — Takvim, Gantt ve Grafik Denemeleri

Görev: #83  
Hazırlayan: Havva Zülal Ertürk

Sprint 5–6 için kullanılacak kütüphaneler, ayrı bir React + Vite +
TypeScript deneme projesinde örnek verilerle çalıştırılmıştır.
Backend bağlantısı bulunmaz. Görev tarihleri, ilerleme oranları ve
kişi bazlı sayılar gerçek proje verisi değildir.

## Çalıştırma

LUNO deposunun kök klasöründen:

```bash
cd frontend/denemeler/takvim-rapor
npm ci
npm run dev
```

Tarayıcıda terminalin gösterdiği Local adresi açılır.
Windows PowerShell'de gerekirse `npm` yerine `npm.cmd` kullanılır.

## Kütüphane seçimi

| Alan | Denenen sürüm | Öneri ve gerekçe |
| --- | --- | --- |
| Takvim | FullCalendar 6.1.21 | Türkçe ay/hafta görünümü ve görev tıklama örneği çalıştığı için önerilir. FullCalendar paketleri aynı sürümde tutulmuştur. |
| Gantt | Frappe Gantt 1.2.2 | Tarih aralıkları, ilerleme dolguları ve bağımlılık okları gösterilebildiği için önerilir. |
| Grafik | Recharts 3.10.1 | Kişi bazlı görev sayılarını React bileşenleriyle göstermek için önerilir. |

Gantt için görevde sunulan iki alternatiften Frappe Gantt denenmiştir.
gantt-task-react denenmediği için iki kütüphane arasında kapsamlı
karşılaştırma yapılmamıştır.

## Örneklerin kapsamı

- FullCalendar: Türkçe takvim, örnek görev tarihleri, ay/hafta seçenekleri
  ve tıklanan görevin adını gösterme.
- Frappe Gantt: Üç örnek görev, tarih aralıkları, tamamlanma oranları ve
  görev bağımlılıkları. Çizelge salt okunurdur.
- Recharts: Dört örnek kişinin tamamlanan görev sayılarını gösteren
  sütun grafiği ve metin özeti.

## Kontroller

```bash
npm run build
npm run lint
```

Her iki komut da başarıyla tamamlanmıştır. Takvimde görev tıklama
davranışı tarayıcıda doğrulanmıştır. Gantt çubukları ve bağımlılık
okları ile grafikteki örnek değerler görsel olarak kontrol edilmiştir.

## Sınırlamalar ve sonraki adımlar

- Frappe Gantt'ın bazı kontrol metinleri İngilizce kalmaktadır.
- Frappe Gantt için kullanılan alanları kapsayan yerel TypeScript
  tanımları eklenmiştir.
- Üç kütüphane aynı sayfada yüklendiğinden build sırasında 500 kB
  üzerinde JavaScript parçası uyarısı oluşmaktadır. Ana uygulamada
  ekran bazlı yükleme değerlendirilmelidir.
- Ana uygulamaya aktarılırken API verileri, ortak tasarım sistemi,
  yetkiler, yüklenme/hata durumları ve farklı ekran boyutları ayrıca
  ele alınmalıdır.