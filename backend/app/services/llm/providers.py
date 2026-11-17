"""LLM sağlayıcı istemcileri (Groq ana, Gemini yedek).

Her sağlayıcı tek bir iş yapar: sistem ve kullanıcı metnini alıp JSON metni döndürür.
Zaman aşımı, ağ hatası, 4xx/5xx ve bozuk yanıt gibi tüm hatalar LLMProviderError olarak
yükseltilir; hangi servise geçileceğine servis katmanı karar verir.
"""

from abc import ABC, abstractmethod
from typing import Optional

import httpx


class LLMProviderError(Exception):
    """Sağlayıcıdan kullanılabilir bir yanıt alınamadı."""


class LLMProvider(ABC):
    name: str

    def __init__(self, api_key: str, model: str, client: Optional[httpx.Client] = None):
        self.api_key = api_key
        self.model = model
        # Testlerde httpx.MockTransport'lu bir istemci verilir; canlıda her çağrıda yenisi açılır.
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    def generate_json(self, system: str, user: str, timeout: float) -> str:
        try:
            return self._generate(system, user, timeout)
        except LLMProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise LLMProviderError(f"{self.name}: zaman aşımı") from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError(f"{self.name}: bağlantı hatası ({type(exc).__name__})") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMProviderError(f"{self.name}: beklenmeyen yanıt biçimi") from exc

    def _post(self, url: str, timeout: float, **kwargs) -> dict:
        if self._client is not None:
            response = self._client.post(url, timeout=timeout, **kwargs)
        else:
            with httpx.Client() as client:
                response = client.post(url, timeout=timeout, **kwargs)
        if response.status_code != 200:
            # Yanıt gövdesi (kullanıcı verisi içerebilir) hataya eklenmez, yalnızca durum kodu.
            raise LLMProviderError(f"{self.name}: HTTP {response.status_code}")
        return response.json()

    @abstractmethod
    def _generate(self, system: str, user: str, timeout: float) -> str: ...


class GroqProvider(LLMProvider):
    name = "groq"
    url = "https://api.groq.com/openai/v1/chat/completions"

    def _generate(self, system: str, user: str, timeout: float) -> str:
        data = self._post(
            self.url,
            timeout,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
        )
        content = data["choices"][0]["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("groq: boş yanıt")
        return content


class GeminiProvider(LLMProvider):
    name = "gemini"
    url = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def _generate(self, system: str, user: str, timeout: float) -> str:
        data = self._post(
            self.url.format(model=self.model),
            timeout,
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                },
            },
        )
        content = data["candidates"][0]["content"]["parts"][0]["text"]
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("gemini: boş yanıt")
        return content
