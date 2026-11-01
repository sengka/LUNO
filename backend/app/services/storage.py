"""Dosya depolama (US-018, US-019, US-035).

Uç noktalar dosyanın nerede durduğunu bilmez; `get_storage()` ile gelen nesnenin
`save`, `read` ve `delete` metotlarını kullanır. Hangi depolamanın kullanılacağı
`.env` içindeki STORAGE_BACKEND ayarıyla seçilir:

- "local"    : UPLOAD_DIR klasörü. Geliştirme ve testler için; ayar gerektirmez.
- "supabase" : Supabase Storage (Teknoloji Kararları 3. bölüm). Canlı ortam için;
               SUPABASE_URL, SUPABASE_SERVICE_KEY ve SUPABASE_BUCKET gerekir.
"""

from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import settings


class StorageError(Exception):
    """Depolama servisine ulaşılamadı veya işlem başarısız oldu."""


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Anahtar her zaman sunucuda üretilir; yine de klasör dışına çıkılmasını engelle.
        if self.root.resolve() not in path.parents:
            raise StorageError("Geçersiz dosya anahtarı.")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def read(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError("Dosya depoda bulunamadı.")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class SupabaseStorage:
    """Supabase Storage REST API'si (ayrı bir kütüphane gerektirmez, httpx kullanır)."""

    def __init__(self, url: str, service_key: str, bucket: str, timeout: float = 30.0):
        if not url or not service_key:
            raise StorageError("SUPABASE_URL ve SUPABASE_SERVICE_KEY tanımlı olmalı.")
        self.base = f"{url.rstrip('/')}/storage/v1/object/{bucket}"
        self.headers = {"Authorization": f"Bearer {service_key}", "apikey": service_key}
        self.timeout = timeout

    def _url(self, key: str) -> str:
        return f"{self.base}/{quote(key)}"

    def _request(self, method: str, key: str, **kwargs) -> httpx.Response:
        try:
            response = httpx.request(
                method,
                self._url(key),
                headers={**self.headers, **kwargs.pop("headers", {})},
                timeout=self.timeout,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise StorageError(f"Depolama servisine ulaşılamadı: {exc}") from exc
        return response

    def save(self, key: str, data: bytes, content_type: str) -> None:
        response = self._request("POST", key, content=data, headers={"Content-Type": content_type})
        if response.status_code >= 400:
            raise StorageError(f"Dosya kaydedilemedi ({response.status_code}).")

    def read(self, key: str) -> bytes:
        response = self._request("GET", key)
        if response.status_code >= 400:
            raise StorageError(f"Dosya okunamadı ({response.status_code}).")
        return response.content

    def delete(self, key: str) -> None:
        response = self._request("DELETE", key)
        # Depoda zaten yoksa silinmiş sayılır.
        if response.status_code >= 400 and response.status_code not in (400, 404):
            raise StorageError(f"Dosya silinemedi ({response.status_code}).")


def get_storage():
    """FastAPI bağımlılığı. Testlerde `app.dependency_overrides` ile değiştirilebilir."""
    if settings.STORAGE_BACKEND == "supabase":
        return SupabaseStorage(
            settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY, settings.SUPABASE_BUCKET
        )
    return LocalStorage(settings.UPLOAD_DIR)
