"""Yapay zekâ (LLM) öneri uç noktaları (sözleşme 13).

Kurallar (13.1):
- Bu uç noktalar veritabanına yazmaz, yalnızca öneri döndürür (FR-078, FR-086).
- Groq/Gemini'ye doğrudan istek atılmaz; tüm çağrılar LLMService'ten geçer.
  Yedeğe geçiş (FR-083) ve ikisi de düşerse 503 LLM_UNAVAILABLE (FR-084) serviste yapılır.
- Kullanıcı başına dakikada en fazla 10 LLM isteği; aşılırsa 429 RATE_LIMITED (US-026, #259).
  Yalnızca yetki kontrolünden geçen, yani gerçekten modele gidecek istekler sayılır.
- Kullanıcı metni (görev başlığı/açıklaması) günlüğe yazılmaz.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.exceptions import ProjectAccessDeniedException, TaskNotFoundException
from app.database import get_db
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.ai import StoryPointsSuggestion, SuggestPointsResponse
from app.services.llm import LLMService, RateLimiter, get_llm_rate_limiter, get_llm_service

router = APIRouter(prefix="/ai", tags=["Yapay Zekâ"])

# #257 denemesinde Türkçe örneklerle 10/10 geçerli puan veren istem.
SUGGEST_POINTS_SYSTEM_PROMPT = (
    "Sen bir Scrum ekibine yardım eden asistansın. Sana bir görevin başlığı ve açıklaması verilecek. "
    "Görevin eforunu yalnızca şu değerlerden biriyle tahmin et: 1, 2, 3, 5, 8, 13. "
    "1: birkaç dakikalık çok küçük değişiklik; 3: tek ekran veya tek API; "
    "8: birden fazla ekran ve API, testlerle birlikte; 13: çok büyük, bölünmesi gereken iş. "
    'Yalnızca şu biçimde JSON döndür: {"story_points": <sayı>, "reason": "<Türkçe tek cümle>"}'
)


def _task_text(task: Task) -> str:
    description = (task.description or "").strip() or "(yok)"
    return f"Başlık: {task.title}\nAçıklama: {description}"


@router.post(
    "/tasks/{task_id}/suggest-points",
    response_model=SuggestPointsResponse,
    status_code=status.HTTP_200_OK,
    summary="Efor puanı önerisi (US-052 / 13.4)",
)
def suggest_story_points(
    task_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm_service),
    limiter: RateLimiter = Depends(get_llm_rate_limiter),
):
    """
    Görev başlığı ve açıklamasına göre efor puanı önerir (US-052, FR-080, sözleşme 13.4).
    Erişim: Yönetici = sistem rolü YONETICI ve görevin projesinin üyesi (1.2).
    - Yönetici değilse 403 FORBIDDEN
    - Görev yoksa 404 TASK_NOT_FOUND
    - Proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    - Dakikada 10 isteği aşarsa 429 RATE_LIMITED
    - İki LLM servisi de yanıt vermezse 503 LLM_UNAVAILABLE
    Öneri kaydedilmez; kullanıcı onaylarsa frontend görev güncelleme uç noktasını çağırır.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise TaskNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()

    limiter.check(current_user.id)
    result = llm.complete_json(SUGGEST_POINTS_SYSTEM_PROMPT, _task_text(task), StoryPointsSuggestion)
    return SuggestPointsResponse(
        provider=result.provider,
        story_points=result.data.story_points,
        reason=result.data.reason,
    )
