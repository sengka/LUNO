"""Yüklenen dosyanın türünü doğrular (FR-046, FR-047, NFR-006).

Uzantı tek başına yeterli değildir; dosyanın içeriği de o türe ait olmalıdır.
Örneğin adı "rapor.pdf" olan bir .exe dosyası reddedilir. Tarayıcının gönderdiği
içerik türüne (Content-Type) güvenilmez; gerçek tür dosyanın baytlarından anlaşılır.
"""

import io
import zipfile
from pathlib import PurePath

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB (FR-046)

# Office dosyaları aslında ZIP arşividir; içlerinde türe özgü bir dosya bulunur.
_OFFICE_MARKERS = {
    ".docx": "word/document.xml",
    ".xlsx": "xl/workbook.xml",
    ".pptx": "ppt/presentation.xml",
}

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".txt": "text/plain",
}


def _is_office(data: bytes, marker: str) -> bool:
    if not data.startswith(b"PK\x03\x04"):
        return False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and marker in names


def _is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    for encoding in ("utf-8-sig", "cp1254"):  # cp1254: Windows Türkçe
        try:
            data.decode(encoding)
            return True
        except UnicodeDecodeError:
            continue
    return False


def detect_mime_type(filename: str, data: bytes) -> str | None:
    """Dosya izin verilen türlerdense standart MIME türünü, değilse None döner."""
    ext = PurePath(filename).suffix.lower()
    if ext not in MIME_TYPES:
        return None

    if ext == ".pdf":
        ok = data.startswith(b"%PDF-")
    elif ext == ".png":
        ok = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext in (".jpg", ".jpeg"):
        ok = data.startswith(b"\xff\xd8\xff")
    elif ext in _OFFICE_MARKERS:
        ok = _is_office(data, _OFFICE_MARKERS[ext])
    else:  # .txt
        ok = _is_text(data)

    return MIME_TYPES[ext] if ok else None


def clean_filename(filename: str | None) -> str:
    """Kullanıcının gönderdiği adı klasör yolundan ve kontrol karakterlerinden arındırır."""
    name = PurePath((filename or "").replace("\\", "/")).name
    name = "".join(ch for ch in name if ch.isprintable()).strip()
    return name[:255] or "dosya"
