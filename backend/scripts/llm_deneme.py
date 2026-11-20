"""Groq ve Gemini'yi Türkçe demo örnekleriyle karşılaştırma betiği (#257).

Ne yapar?
  10 uydurma örneği (5 toplantı notu, 5 görev metni) iki modele AYRI AYRI gönderir.
  Her yanıt için şunlara bakar: süre, JSON şemaya uyuyor mu, sonuç beklenene uyuyor mu.
  Sonucu ekrana ve backend/llm_deneme_sonuc.md dosyasına yazar.

Neden LLMService değil de sağlayıcılar tek tek?
  LLMService Groq başarılıysa Gemini'yi hiç denemez (yedek mantığı). Karşılaştırma için
  ikisini de her örnekte ayrı çağırmamız gerekiyor. İstek atma ve JSON doğrulama için
  uygulamanın kendi kodu (GroqProvider, GeminiProvider, parse_json_response) kullanılır;
  böylece denediğimiz şey canlıda çalışacak kodun aynısıdır.

Güvenlik:
  - Anahtarlar backend/.env'den okunur, hiçbir yere yazdırılmaz.
  - Tüm örnekler uydurmadır; gerçek kullanıcı verisi yoktur (teknoloji kararları, bölüm 6).

Çalıştırma (backend klasöründe, sanal ortam açıkken):
  python -m scripts.llm_deneme
"""

import time
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, field_validator

from app.config import settings
from app.models.enums import STORY_POINT_VALUES
from app.services.llm import GeminiProvider, GroqProvider, parse_json_response
from app.services.llm.providers import LLMProviderError

# Göreli tarihlerin ("cuma", "yarın") doğru çözülüp çözülmediğini ölçebilmek için sabit bir "bugün".
BUGUN = date(2026, 11, 16)  # Pazartesi
UYELER = ["Ali Yılmaz", "Ayşe Kaya", "Can Demir", "Deniz Şahin", "Elif Arslan"]  # uydurma proje üyeleri

# Ücretsiz sürümlerin dakikalık istek sınırına takılmamak için iki istek arası bekleme (saniye).
BEKLEME = 6


# --- Modelden beklenen JSON şemaları (sözleşme 13.2 ve 13.4) ---------------------------------

class PuanOnerisi(BaseModel):
    story_points: int
    reason: str

    @field_validator("story_points")
    @classmethod
    def gecerli_puan(cls, v: int) -> int:
        # Sözleşme 13.4: story_points her zaman 1, 2, 3, 5, 8 veya 13'ten biri.
        if v not in STORY_POINT_VALUES:
            raise ValueError("geçersiz efor puanı")
        return v


class GorevOnerisi(BaseModel):
    title: str
    assignee_name: Optional[str] = None
    due_date: Optional[date] = None


class CikarilanGorevler(BaseModel):
    suggestions: list[GorevOnerisi]


# --- İstem (prompt) metinleri; #258'de efor istemi temel alınacak -----------------------------

PUAN_SISTEM = (
    "Sen bir Scrum ekibine yardım eden asistansın. Sana bir görevin başlığı ve açıklaması verilecek. "
    "Görevin eforunu yalnızca şu değerlerden biriyle tahmin et: 1, 2, 3, 5, 8, 13. "
    "1: birkaç dakikalık çok küçük değişiklik; 3: tek ekran veya tek API; "
    "8: birden fazla ekran ve API, testlerle birlikte; 13: çok büyük, bölünmesi gereken iş. "
    'Yalnızca şu biçimde JSON döndür: {"story_points": <sayı>, "reason": "<Türkçe tek cümle>"}'
)

CIKAR_SISTEM = (
    "Sen bir proje yönetimi asistanısın. Sana Türkçe bir toplantı notu verilecek. "
    "Nottaki yapılacak işleri görev olarak çıkar. Her görev için kısa bir Türkçe başlık, "
    "sorumlu kişinin notta geçen adı ve teslim tarihini (YYYY-MM-DD) yaz. "
    "Kişi veya tarih belirtilmemişse null yaz. Yapılacak iş yoksa boş liste döndür. "
    f"Bugünün tarihi {BUGUN.isoformat()} (Pazartesi). Proje üyeleri: {', '.join(UYELER)}. "
    'Yalnızca şu biçimde JSON döndür: {"suggestions": [{"title": "...", "assignee_name": "...", "due_date": "..."}]}'
)


# --- Demo örnekler ----------------------------------------------------------------------------

@dataclass
class Ornek:
    ad: str
    tur: str  # "puan" veya "cikar"
    metin: str
    # puan için: kabul edilen puanlar; cikar için: beklenen (kişi ilk adı, tarih) listesi
    beklenen: object = None


ORNEKLER = [
    Ornek("P1 Buton rengi", "puan",
          "Başlık: Profil sayfasındaki kaydet butonunun rengini değiştir\nAçıklama: Buton mavi yerine yeşil olacak.",
          {1, 2}),
    Ornek("P2 E-posta doğrulama", "puan",
          "Başlık: Kayıt formuna e-posta biçimi kontrolü ekle\nAçıklama: Hatalı e-postada alanın altında Türkçe uyarı çıksın.",
          {1, 2, 3}),
    Ornek("P3 Şifre sıfırlama", "puan",
          "Başlık: Şifre sıfırlama\nAçıklama: Şifremi unuttum ekranı, e-postayla tek kullanımlık bağlantı gönderen API, "
          "yeni şifre formu ve bunların testleri.",
          {5, 8}),
    Ornek("P4 Gantt sürükle-bırak", "puan",
          "Başlık: Gantt şemasında sürükle-bırak\nAçıklama: Görev çubukları sürüklenerek tarih değişsin, bağımlılık okları "
          "çizilsin, backend'de tarih güncelleme API'si ve çakışma kontrolü yazılsın, tüm parçalar test edilsin.",
          {8, 13}),
    Ornek("P5 Belirsiz kısa metin", "puan",
          "Başlık: rapor\nAçıklama: (yok)",
          set(STORY_POINT_VALUES)),  # tek beklenti: geçerli bir puan dönmesi
    Ornek("T1 Basit not", "cikar",
          "Can cumaya kadar giriş API'sini bitirecek. Ayşe de takvim ekranını tasarlayacak.",
          [("can", "2026-11-20"), ("ayse", None)]),
    Ornek("T2 Sorumlusuz iş", "cikar",
          "Toplantıda demo hazırlığını konuştuk. Elif sunumu çarşamba gününe hazırlayacak. "
          "Veritabanı yedeği de alınmalı ama kimin yapacağına karar verilmedi.",
          [("elif", "2026-11-18"), (None, None)]),
    Ornek("T3 Göreli tarihler", "cikar",
          "Deniz yarın bildirim ekranındaki hatayı düzeltecek. Ali haftaya salı rapor sayfasını bitirmiş olacak.",
          [("deniz", "2026-11-17"), ("ali", "2026-11-24")]),
    Ornek("T4 Yazım hatalı not", "cikar",
          "can kanban ekranindaki surukleme hatasini duzeltcek, ayse de persembeye kadar test yazsin",
          [("can", None), ("ayse", "2026-11-19")]),
    Ornek("T5 Görev içermeyen not", "cikar",
          "Bugün geçen sprintin retrosunu yaptık. Herkes iletişimin iyi olduğunu söyledi, yeni bir iş çıkmadı.",
          []),
]


# --- Değerlendirme ----------------------------------------------------------------------------

# "Ayşe" ile "Ayse" aynı kişi sayılsın: karşılaştırmada Türkçe harfler sadeleştirilir.
_SADE = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def _ilk_ad(ad: Optional[str]) -> Optional[str]:
    return ad.split()[0].translate(_SADE).casefold() if ad and ad.strip() else None


def beklenene_uygun(ornek: Ornek, veri) -> bool:
    if ornek.tur == "puan":
        return veri.story_points in ornek.beklenen
    # Çıkarma: görev sayısı ve her görevin kişi + tarih çifti beklenenle aynı mı (sıra önemsiz)?
    bulunan = sorted(
        ((_ilk_ad(g.assignee_name), g.due_date.isoformat() if g.due_date else None) for g in veri.suggestions),
        key=str,
    )
    return bulunan == sorted(ornek.beklenen, key=str)


def ozet_metni(ornek: Ornek, veri) -> str:
    if ornek.tur == "puan":
        return f"{veri.story_points} puan · {veri.reason}"
    if not veri.suggestions:
        return "(görev yok)"
    return "; ".join(f"{g.title} → {g.assignee_name or '-'}, {g.due_date or '-'}" for g in veri.suggestions)


@dataclass
class Sonuc:
    ornek: str
    sure: float
    json_gecerli: bool
    uygun: bool
    aciklama: str


@dataclass
class ModelOzeti:
    ad: str
    sonuclar: list[Sonuc] = field(default_factory=list)


def dene(provider, ornek: Ornek) -> Sonuc:
    sistem, sema = (PUAN_SISTEM, PuanOnerisi) if ornek.tur == "puan" else (CIKAR_SISTEM, CikarilanGorevler)
    baslangic = time.perf_counter()
    try:
        ham = provider.generate_json(sistem, ornek.metin, settings.LLM_TIMEOUT_SECONDS)
        veri = parse_json_response(ham, sema)
    except LLMProviderError as exc:
        # Hata mesajı yalnızca servis adı ve durum kodunu içerir; anahtar veya yanıt gövdesi içermez.
        return Sonuc(ornek.ad, time.perf_counter() - baslangic, False, False, f"HATA: {exc}")
    sure = time.perf_counter() - baslangic
    return Sonuc(ornek.ad, sure, True, beklenene_uygun(ornek, veri), ozet_metni(ornek, veri))


def rapor(ozetler: list[ModelOzeti]) -> str:
    satirlar = ["# LLM deneme sonuçları (#257)", "", f"Tarih: {date.today().isoformat()} · Zaman aşımı: "
                f"{settings.LLM_TIMEOUT_SECONDS:g} sn · Groq: `{settings.GROQ_MODEL}` · Gemini: `{settings.GEMINI_MODEL}`", ""]
    satirlar += ["## Özet", "", "| Model | Geçerli JSON | Beklenene uygun | Ortalama süre | En uzun süre |",
                 "|---|---|---|---|---|"]
    for oz in ozetler:
        n = len(oz.sonuclar)
        if n == 0:
            satirlar.append(f"| {oz.ad} | anahtar yok, denenmedi | | | |")
            continue
        gecerli = sum(s.json_gecerli for s in oz.sonuclar)
        uygun = sum(s.uygun for s in oz.sonuclar)
        sureler = [s.sure for s in oz.sonuclar]
        satirlar.append(f"| {oz.ad} | {gecerli}/{n} | {uygun}/{n} | {sum(sureler) / n:.1f} sn | {max(sureler):.1f} sn |")
    for oz in ozetler:
        if not oz.sonuclar:
            continue
        satirlar += ["", f"## {oz.ad} ayrıntı", "", "| Örnek | Süre | JSON | Uygun | Yanıt |", "|---|---|---|---|---|"]
        for s in oz.sonuclar:
            yanit = s.aciklama.replace("|", "/")
            satirlar.append(f"| {s.ornek} | {s.sure:.1f} sn | {'✓' if s.json_gecerli else '✗'} | "
                            f"{'✓' if s.uygun else '✗'} | {yanit} |")
    return "\n".join(satirlar) + "\n"


def main() -> None:
    providers = [
        GroqProvider(settings.GROQ_API_KEY, settings.GROQ_MODEL),
        GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
    ]
    ozetler = []
    for provider in providers:
        ozet = ModelOzeti(provider.name)
        ozetler.append(ozet)
        if not provider.configured:
            print(f"{provider.name}: .env dosyasında anahtar yok, atlanıyor.")
            continue
        for i, ornek in enumerate(ORNEKLER, 1):
            sonuc = dene(provider, ornek)
            ozet.sonuclar.append(sonuc)
            print(f"{provider.name} [{i}/{len(ORNEKLER)}] {ornek.ad}: {sonuc.sure:.1f} sn, "
                  f"{'uygun' if sonuc.uygun else 'uygun değil'}")
            if i < len(ORNEKLER):
                time.sleep(BEKLEME)

    metin = rapor(ozetler)
    cikti = Path("llm_deneme_sonuc.md")
    cikti.write_text(metin, encoding="utf-8")
    print("\n" + metin)
    print(f"Sonuç dosyası: {cikti.resolve()}")


if __name__ == "__main__":
    main()
