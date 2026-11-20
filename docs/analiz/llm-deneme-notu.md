# LLM model denemesi: Groq ve Gemini (#257)

> **Tarih:** 20 Kasım 2026 · **Hazırlayan:** Aybüke Turgun · **İlgili:** teknoloji kararları bölüm 6, API sözleşmesi bölüm 13, US-026, US-045, US-052

## Amaç

Teknoloji kararlarında "modeller seçilmeden önce Türkçe örneklerle denenir" kuralı var. Bu denemede iki soruya cevap aradık:

1. `config.py`'deki modeller (Groq `llama-3.3-70b-versatile`, Gemini `gemini-2.5-flash`) bugün çalışıyor mu?
2. Çalışmıyorlarsa ana ve yedek servis için hangi modelleri kullanmalıyız?

## Yöntem

- Betik: `backend/scripts/llm_deneme.py` (çalıştırma: `python -m scripts.llm_deneme`).
- İstekler uygulamanın kendi `GroqProvider` ve `GeminiProvider` sınıflarıyla atıldı, yanıtlar `parse_json_response` ile Pydantic şemasına göre doğrulandı. Yani denenen kod, canlıda çalışacak kodun aynısı.
- 10 uydurma örnek kullanıldı, gerçek kullanıcı verisi kullanılmadı:
  - 5 görev metni, efor puanı için (sözleşme 13.4).
  - 5 toplantı notu, görev çıkarma için (sözleşme 13.2). Notlarda göreli tarih, Türkçe karakter kullanılmadan yazılmış bir not ve görev içermeyen bir not da var.
- Her örneğin beklenen sonucu önceden yazıldı. Göreli tarihleri ölçebilmek için "bugün" 16 Kasım 2026 Pazartesi olarak sabitlendi.
- Zaman aşımı canlıdaki gibi 10 saniye (FR-083).

## Sonuçlar

**1. deneme: `config.py`'deki modeller.** İki servis de her istekte `HTTP 404` döndü.

- Groq, `llama-3.3-70b-versatile` modelini ücretsiz ve geliştirici planlarında 16 Ağustos 2026'da kapattı. Anahtarla alınan model listesinde de bu model yok.
- `gemini-2.5-flash` model listesinde görünüyor ama yeni anahtarla istek atılınca 404 dönüyor. Google'ın kullanımdan kaldırma sayfası yeni projeler için 3.x modellerini öneriyor.

**2. ve 3. deneme: önerilen yeni modeller**

| Model | Geçerli JSON | Beklenene uygun | Ortalama süre | En uzun süre |
|---|---|---|---|---|
| Groq `openai/gpt-oss-120b` (2. deneme) | 10/10 | 9/10 | 1,2 sn | 1,8 sn |
| Groq `openai/gpt-oss-120b` (3. deneme) | 10/10 | 8/10 | 1,4 sn | 2,0 sn |
| Gemini `gemini-3.5-flash` | 2/10 | 2/10 | 9,5 sn | 10,5 sn |
| Gemini `gemini-3.5-flash-lite` | 10/10 | 10/10 | 1,4 sn | 2,0 sn |

Gözlemler:

- **Efor puanında** (#258'i ilgilendiren kısım) `gpt-oss-120b` ve `gemini-3.5-flash-lite` 10 örneğin 10'unda geçerli bir puan (1, 2, 3, 5, 8, 13) ve anlaşılır, tek cümlelik Türkçe bir gerekçe döndürdü.
- **Açıklaması olmayan görevde** ("rapor") iki model çok farklı puan verdi: Groq 1–2, Gemini 13. Frontend bu öneriyi kullanıcı onayına sunduğu için bu bir hata değil. Yine de açıklaması boş görevlerde önerinin güvenilir olmadığını gösteriyor.
- **Göreli tarihler** Groq'un tek zayıf noktası oldu: "haftaya salı" iki denemede de yanlış tarihe çevrildi, "cuma" da bir denemede yanlış çevrildi. Aynı istem iki denemede farklı sonuç verdi.
- `gemini-3.5-flash`, 10 isteğin 8'inde 10 saniye sınırını aştı. Muhtemel sebep, modelin yanıt vermeden önce "düşünme" adımı çalıştırması. Bu haliyle yedek servis olarak kullanılamaz.
- Yazım hatalı ve Türkçe karakter kullanılmadan yazılmış not, iki modelde de doğru anlaşıldı. Görev içermeyen notta iki model de boş liste döndürdü.

## Seçilen modeller

| Rol | Model | Neden |
|---|---|---|
| Ana servis (Groq) | `openai/gpt-oss-120b` | Groq'un `llama-3.3-70b-versatile` yerine önerdiği model. 10/10 geçerli JSON verdi, yanıt süresi 2 saniyenin altında. |
| Yedek servis (Gemini) | `gemini-3.5-flash-lite` | Hızlı (ortalama 1,4 sn) ve 10/10 doğru sonuç verdi. `gemini-3.5-flash` ise 10 saniye sınırına sığmadı. |

Groq'un ana servis olarak kalması teknoloji kararlarıyla uyumlu: Gemini'nin ücretsiz sürümüne yalnızca demo verisi gönderilmesi kuralı nedeniyle gerçek veriyle çalışan ana servis Groq olmalı.

## Alınan kararlar (Sena, 20 Kasım 2026)

1. **Model değişikliği onaylandı:** `GROQ_MODEL=openai/gpt-oss-120b`, `GEMINI_MODEL=gemini-3.5-flash-lite`. `config.py`'deki varsayılanlar ve kök dizindeki `.env.example`'daki model satırları #258 PR'ında güncellenecek. Bu güncelleme yapılmazsa LLM özellikleri her istekte 503 `LLM_UNAVAILABLE` döner.
2. **Canlıda Gemini kullanılmayacak:** Canlı ortamda `GEMINI_API_KEY` boş bırakılır. Groq yanıt vermezse istek Gemini'ye gitmez, doğrudan 503 döner; böylece gerçek kullanıcı verisi Gemini'nin ücretsiz sürümüne hiç gönderilmez (teknoloji kararları, bölüm 6; `config.py`'deki yorum). Yerelde ve demoda iki anahtar da girilir, yedeğe geçiş orada gösterilir. Render ayarı için Salih'e haber verildi.
3. **Göreli tarihler LLM'e bırakılmayacak:** US-051 görevine not edildi. Türkçe tarih ifadeleri teknoloji kararlarında seçilen `dateparser` ile çözülecek. Model yalnızca metindeki ifadeyi ("haftaya salı") döndürecek, tarihe çevirmeyi backend yapacak.

## Riskler

- **Modeller değişebilir:** Bu denemede iki modelin de birkaç ay içinde kapatıldığını gördük. Model adları kodda sabit yazılmamalı, ortam değişkeniyle değiştirilebilir kalmalı (şu anki yapı böyle). Demodan önce betik bir kez daha çalıştırılmalı.
- **Canlıda yedek yok:** 2. karar nedeniyle canlıda Groq düşerse LLM özellikleri geçici olarak kullanılamaz. Uygulamanın geri kalanı bundan etkilenmez (FR-084).

## Kaynaklar

- Groq model kullanımdan kaldırma sayfası: https://console.groq.com/docs/deprecations
- Gemini kullanımdan kaldırma sayfası: https://ai.google.dev/gemini-api/docs/deprecations
- Ham sonuçlar: `python -m scripts.llm_deneme` çıktısı (`backend/llm_deneme_sonuc.md`, repoya eklenmedi)
