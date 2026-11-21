from datetime import date
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReportUserSummary(BaseModel):
    id: int
    full_name: str
    avatar_url: Optional[str] = None


class MemberReportItem(BaseModel):
    user: ReportUserSummary
    counts: Dict[str, int]
    done_points: int = 0


class MemberReportResponse(BaseModel):
    """Sözleşme 10.2: Kişi bazlı rapor yanıtı (US-023, FR-062)."""

    members: List[MemberReportItem]


class PeriodSeriesItem(BaseModel):
    date: date
    completed: int = 0
    created: int = 0


class PeriodReportResponse(BaseModel):
    """Sözleşme 10.3: Dönemsel rapor yanıtı (US-023, FR-063)."""

    model_config = ConfigDict(populate_by_name=True)

    period: Literal["DAILY", "WEEKLY", "MONTHLY"]
    from_date: date = Field(..., alias="from")
    to: date
    completed_count: int = 0
    created_count: int = 0
    series: List[PeriodSeriesItem]
