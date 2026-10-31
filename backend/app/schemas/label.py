"""Etiket şemaları (US-033, FR-037, sözleşme 6.11)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

DEFAULT_LABEL_COLOR = "#6B7280"


class LabelCreateRequest(BaseModel):
    """POST /projects/{project_id}/labels istek gövdesi."""

    name: str = Field(..., min_length=1, max_length=50, description="Etiket adı (1-50 karakter)")
    color: str = Field(
        DEFAULT_LABEL_COLOR,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="#RRGGBB biçiminde renk kodu. Gönderilmezse gri.",
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Etiket adı boş olamaz.")
        return value


class LabelResponse(BaseModel):
    """Sözleşme 2. bölüm: Label nesnesi."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str
