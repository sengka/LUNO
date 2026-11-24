"""Yapay zekâ (LLM) öneri uç noktaları (sözleşme 13).

Kurallar (13.1):
- Bu uç noktalar veritabanına yazmaz, yalnızca öneri döndürür (FR-078, FR-086).
  tests/test_ai_no_db_writes.py her AI uç noktası için bunu doğrular; yeni uç nokta oraya eklenmelidir.
- Yetki, proje üyeliği ve dakikada 10 istek sınırı ortak korumadadır (app/api/ai_deps.py, #288).
- Groq/Gemini'ye doğrudan istek atılmaz; tüm çağrılar LLMService'ten geçer.
  Yedeğe geçiş (FR-083) ve ikisi de düşerse 503 LLM_UNAVAILABLE (FR-084) serviste yapılır.
- Kullanıcı metni ortak şablonla verilir: system_prompt(...) ve user_data(...) (istem enjeksiyonuna karşı).
- Kullanıcı metni (görev başlığı/açıklaması) günlüğe yazılmaz.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.ai_deps import (
    AIProjectContext,
    AITaskContext,
    admin_project_access,
    admin_task_access,
    ai_task_access,
)
from app.database import get_db
from app.models.task import Task
from app.schemas.ai import (
    CommentSummaryLLMOutput,
    CommentSummaryResponse,
    StoryPointsSuggestion,
    SuggestPointsResponse,
    WeeklySummaryLLMOutput,
    WeeklySummaryResponse,
)
from app.services.ai_summaries import comment_thread_text, require_enough_comments, weekly_summary_data
from app.services.llm import LLMService, get_llm_service, system_prompt, user_data
from app.services.sprints import today_utc

router = APIRouter(prefix="/ai", tags=["Yapay Zekâ"])

# #257 denemesinde Türkçe örneklerle 10/10 geçerli puan veren istem.
SUGGEST_POINTS_INSTRUCTIONS = (
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
    ctx: AITaskContext = Depends(admin_task_access),
    llm: LLMService = Depends(get_llm_service),
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
    result = llm.complete_json(
        system_prompt(SUGGEST_POINTS_INSTRUCTIONS),
        user_data(_task_text(ctx.task)),
        StoryPointsSuggestion,
    )
    return SuggestPointsResponse(
        provider=result.provider,
        story_points=result.data.story_points,
        reason=result.data.reason,
    )


# --- 13.5 Haftalık proje özeti (US-053, FR-081) -------------------------------------------------

WEEKLY_SUMMARY_INSTRUCTIONS = (
    "Sen bir proje yönetimi asistanısın. Sana bir projenin son 7 günlük görev ve ilerleme verileri "
    "verilecek. Yöneticinin bir dakikada okuyabileceği, 3-6 cümlelik Türkçe bir haftalık özet yaz: "
    "bu hafta ne tamamlandı, ne ilerledi, hangi işler gecikti veya risk taşıyor, önümüzdeki günlerde "
    "neye dikkat edilmeli. Yalnızca verilen veriyi kullan; veride olmayan bir bilgi, sayı veya kişi "
    "uydurma. Veri yoksa bunu açıkça söyle. "
    'Yalnızca şu biçimde JSON döndür: {"summary": "<Türkçe özet>"}'
)


@router.post(
    "/projects/{project_id}/weekly-summary",
    response_model=WeeklySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Haftalık proje özeti (US-053 / 13.5)",
)
def weekly_project_summary(
    ctx: AIProjectContext = Depends(admin_project_access),
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm_service),
):
    """
    Son 7 günün (bugün dahil) görev ve ilerleme verilerini özetler (FR-081, sözleşme 13.5).
    Tarih aralığını (from, to) backend belirler. Erişim: Yönetici ve proje üyesi (1.2).
    Hatalar: 403 FORBIDDEN, 404 PROJECT_NOT_FOUND, 403 PROJECT_ACCESS_DENIED, 429 RATE_LIMITED,
    503 LLM_UNAVAILABLE. Özet kaydedilmez.
    """
    week = weekly_summary_data(db, ctx.project, today_utc())
    result = llm.complete_json(
        system_prompt(WEEKLY_SUMMARY_INSTRUCTIONS),
        user_data(week.text),
        WeeklySummaryLLMOutput,
    )
    return WeeklySummaryResponse(
        provider=result.provider,
        from_date=week.from_date,
        to_date=week.to_date,
        summary=result.data.summary,
    )


# --- 13.6 Yorum zinciri özeti (US-053, FR-082) --------------------------------------------------

COMMENT_SUMMARY_INSTRUCTIONS = (
    "Sen bir proje yönetimi asistanısın. Sana bir görevin yorum zinciri tarih sırasıyla verilecek. "
    "Yorumlarda alınan kararları, hâlâ cevaplanmamış soruları ve açık konuları çıkar; ardından "
    "zinciri 2-4 cümleyle Türkçe özetle. Her madde kısa ve tek cümle olsun. Yalnızca yorumlarda "
    "yazanı kullan; karar veya açık konu yoksa ilgili listeyi boş bırak. "
    'Yalnızca şu biçimde JSON döndür: {"decisions": ["..."], "open_questions": ["..."], "summary": "..."}'
)

# Proje üyelerine açık (13.6); en az 5 yorum yoksa modele gitmeden 400 döner ve istek sınırından düşmez.
comment_summary_access = ai_task_access(admin_only=False, precheck=require_enough_comments)


@router.post(
    "/tasks/{task_id}/summarize-comments",
    response_model=CommentSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Yorum zinciri özeti (US-053 / 13.6)",
)
def summarize_task_comments(
    ctx: AITaskContext = Depends(comment_summary_access),
    db: Session = Depends(get_db),
    llm: LLMService = Depends(get_llm_service),
):
    """
    Görevin yorum zincirindeki kararları ve açık konuları özetler (FR-082, sözleşme 13.6).
    Erişim: Görevin projesinin üyesi (yönetici olması gerekmez).
    Hatalar: 404 TASK_NOT_FOUND, 403 PROJECT_ACCESS_DENIED, 400 NOT_ENOUGH_COMMENTS (5'ten az yorum),
    429 RATE_LIMITED, 503 LLM_UNAVAILABLE. Özet kaydedilmez.
    """
    result = llm.complete_json(
        system_prompt(COMMENT_SUMMARY_INSTRUCTIONS),
        user_data(comment_thread_text(db, ctx.task)),
        CommentSummaryLLMOutput,
    )
    return CommentSummaryResponse(
        provider=result.provider,
        decisions=result.data.decisions,
        open_questions=result.data.open_questions,
        summary=result.data.summary,
    )
