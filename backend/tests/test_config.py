"""SECRET_KEY zorunluluğu: anahtar tanımlı değilse uygulama başlamamalı."""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_fails_without_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_fails_with_empty_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reads_secret_key_from_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "ortamdan-gelen-anahtar")
    assert Settings(_env_file=None).SECRET_KEY == "ortamdan-gelen-anahtar"
