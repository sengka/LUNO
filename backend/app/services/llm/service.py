"""Tüm LLM çağrılarının geçtiği tek servis katmanı (teknoloji kararları, bölüm 6).

- Önce ana servis (Groq), hata veya zaman aşımında yedek servis (Gemini) denenir (FR-083).
- Yanıt JSON olarak istenir ve Pydantic şemasıyla doğrulanır; bozuk yanıt da yedeğe geçirir.
- İki servis de başarısız olursa LLMUnavailableException (503, LLM_UNAVAILABLE) yükselir (FR-084).
- Bu katman veritabanına yazmaz; yalnızca öneri döndürür (FR-078, FR-086).
"""

import json
import logging
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Generic, Optional, Sequence, Type, TypeVar

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.core.exceptions import LLMUnavailableException, RateLimitedException
from app.services.llm.providers import (
    GeminiProvider,
    GroqProvider,
    LLMProvider,
    LLMProviderError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


@dataclass
class LLMResult(Generic[T]):
    provider: str  # Yanıtlarda "provider": "groq" | "gemini" olarak döner (sözleşme 13.1)
    data: T


def parse_json_response(text: str, schema: Type[T]) -> T:
    """Model çıktısını (varsa ```json çitini sıyırıp) şemaya göre doğrular."""
    cleaned = text.strip()
    match = _FENCE.match(cleaned)
    if match:
        cleaned = match.group(1)
    try:
        return schema.model_validate(json.loads(cleaned))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LLMProviderError("yanıt beklenen JSON şemasına uymuyor") from exc


class LLMService:
    def __init__(self, providers: Sequence[LLMProvider], timeout: float):
        # Anahtarı olmayan servis kullanılmaz.
        self.providers = [p for p in providers if p.configured]
        self.timeout = timeout

    def complete_json(self, system: str, user: str, schema: Type[T]) -> LLMResult[T]:
        for provider in self.providers:
            try:
                raw = provider.generate_json(system, user, self.timeout)
                return LLMResult(provider=provider.name, data=parse_json_response(raw, schema))
            except LLMProviderError as exc:
                # Kullanıcı metni günlüğe yazılmaz; yalnızca hangi servisin neden düştüğü.
                logger.warning("LLM servisi başarısız, yedeğe geçiliyor: %s", exc)
        raise LLMUnavailableException()


class RateLimiter:
    """Kullanıcı başına kayan 60 saniyelik pencere (sözleşme 13.1). Tek backend örneği için bellek içi."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[int, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, user_id: int, now: Optional[float] = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[user_id]
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                raise RateLimitedException()
            hits.append(now)


def build_llm_service() -> LLMService:
    return LLMService(
        providers=[
            GroqProvider(settings.GROQ_API_KEY, settings.GROQ_MODEL),
            GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
        ],
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )


_rate_limiter = RateLimiter(settings.LLM_RATE_LIMIT_PER_MINUTE)


def get_llm_service() -> LLMService:
    """FastAPI bağımlılığı: Depends(get_llm_service). Testlerde dependency_overrides ile sahtesi verilir."""
    return build_llm_service()


def get_llm_rate_limiter() -> RateLimiter:
    return _rate_limiter
