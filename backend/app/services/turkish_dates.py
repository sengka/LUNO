"""Toplantı notundaki Türkçe tarih ifadelerini tarihe çevirme (US-051, sözleşme 13.2, #302).

Karar (Sena, 20 Kasım 2026): Model tarihi hesaplamaz; yalnızca metindeki ifadeyi ("cumaya kadar",
"haftaya salı") döndürür. Tarihe çevirmeyi backend yapar. #257 denemesinde model "haftaya salı"
ifadesini iki kez yanlış tarihe çevirmişti.

dateparser "yarın", "cuma", "2 gün sonra", "25.11.2026" gibi ifadeleri anlıyor, ama toplantı
notlarında sık geçen şu biçimleri anlamıyor (24 Kasım 2026'da denendi, dateparser 1.5.1):
"cumaya kadar", "perşembeye kadar", "çarşamba günü", "haftaya salı", "gelecek hafta salı".
Bu yüzden ifade önce sadeleştirilir, "haftaya <gün>" ise burada hesaplanır.

Kurallar:
- "<gün>" (salı, cumaya kadar): bugünden sonraki ilk o gün. Bugün o günse bir sonraki hafta
  (pazartesi söylenen "pazartesiye kadar" bugün değil, gelecek pazartesidir; dateparser da böyle yorumlar).
- "haftaya / gelecek hafta / önümüzdeki hafta <gün>": bir sonraki haftanın (pazartesi başlar) o günü.
- Çözülemeyen ifade None döner; uç nokta hata vermez, due_date null olur.
"""

import re
from datetime import date, datetime, timedelta
from typing import Optional

import dateparser

WEEKDAYS = {
    "pazartesi": 0,
    "salı": 1,
    "çarşamba": 2,
    "perşembe": 3,
    "cuma": 4,
    "cumartesi": 5,
    "pazar": 6,
}

# Türkçe karakter kullanılmadan yazılan gün adları ("persembe", "sali").
_ASCII = str.maketrans("çğıöşü", "cgiosu")
_WEEKDAY_BY_ASCII = {name.translate(_ASCII): name for name in WEEKDAYS}

_NEXT_WEEK = re.compile(r"^(haftaya|gelecek hafta|önümüzdeki hafta|onumuzdeki hafta)\s+(\S+)$")
# Gün adının sonundaki yönelme ve diğer ekler: cumaya, perşembeye, salıya, pazara, cuma'ya ...
_SUFFIX = re.compile(r"['’]?(ya|ye|a|e|yı|yi|ı|i|da|de|ta|te|nın|nin|ın|in)$")
_FILLER_WORDS = {"kadar"}
# "günü / gününe / gününden", "akşamı / akşamına", "sabahı / sabahına" ve Türkçe karaktersiz halleri.
# Yalın "gün" atılmaz: "2 gün sonra" ifadesinde gereklidir. (#302 gerçek model denemesi: "çarşamba gününe")
_FILLER = re.compile(r"^(günü|gunu|akşamı|aksami|sabahı|sabahi)(na|ne|nda|nde|ndan|nden)?$")


def _lower(text: str) -> str:
    # Türkçe büyük İ ve I harfleri doğru küçültülsün.
    return text.replace("İ", "i").replace("I", "ı").lower()


def _weekday_of(word: str) -> Optional[int]:
    """'cumaya', "Perşembe'ye", 'persembe' gibi bir sözcükten haftanın gününü bulur."""
    candidates = [word, _SUFFIX.sub("", word)]
    for candidate in candidates:
        candidate = candidate.strip("'’")
        if candidate in WEEKDAYS:
            return WEEKDAYS[candidate]
        if candidate in _WEEKDAY_BY_ASCII:
            return WEEKDAYS[_WEEKDAY_BY_ASCII[candidate]]
    return None


def _clean(expression: str) -> str:
    words = [
        w for w in _lower(expression).replace(",", " ").split()
        if w not in _FILLER_WORDS and not _FILLER.match(w.replace("'", "").replace("’", ""))
    ]
    return " ".join(words)


def resolve_due_date(expression: Optional[str], today: date) -> Optional[date]:
    """Türkçe tarih ifadesini tarihe çevirir; çözemezse None döner."""
    if not expression or not expression.strip():
        return None
    text = _clean(expression)
    if not text:
        return None

    next_week = _NEXT_WEEK.match(text)
    if next_week:
        weekday = _weekday_of(next_week.group(2))
        if weekday is None:
            return None
        next_monday = today + timedelta(days=7 - today.weekday())
        return next_monday + timedelta(days=weekday)

    if " " not in text:
        weekday = _weekday_of(text)
        if weekday is not None:
            return today + timedelta(days=(weekday - today.weekday() - 1) % 7 + 1)

    settings = {
        "RELATIVE_BASE": datetime(today.year, today.month, today.day, 12),
        "PREFER_DATES_FROM": "future",
        "DATE_ORDER": "DMY",
    }
    parsed = dateparser.parse(text, languages=["tr"], settings=settings)
    if parsed is None:
        # "20 kasıma" gibi eklerle çözülemediyse ekleri atıp bir kez daha dene.
        # Ünsüz yumuşaması: "aralığa" → "aralığ" → "aralık".
        without_suffixes = " ".join(re.sub(r"ğ$", "k", _SUFFIX.sub("", w)) for w in text.split())
        if without_suffixes != text:
            parsed = dateparser.parse(without_suffixes, languages=["tr"], settings=settings)
    return parsed.date() if parsed else None
