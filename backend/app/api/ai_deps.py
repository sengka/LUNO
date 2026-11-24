"""AI uç noktalarının ortak koruması (US-026, sözleşme 13.1, #288).

Her AI uç noktası aynı kontrolleri aynı sırayla yapmalı. Bu kontroller burada tek yerde
toplanır; uç nokta yalnızca bir bağımlılık ekler:

    ctx: AITaskContext = Depends(admin_task_access)        # görev üzerinden, yalnız yönetici
    ctx: AIProjectContext = Depends(admin_project_access)  # proje üzerinden, yalnız yönetici
    ctx: AITaskContext = Depends(member_task_access)       # görev üzerinden, her proje üyesi (13.6)

Kontrol sırası:
1. Giriş yapılmış mı?                               → 401 UNAUTHORIZED
2. Yönetici gerekiyorsa sistem rolü YONETICI mi?    → 403 FORBIDDEN
3. Görev / proje var mı?                            → 404 TASK_NOT_FOUND / PROJECT_NOT_FOUND
4. Kullanıcı projenin üyesi mi? (1.2)               → 403 PROJECT_ACCESS_DENIED
5. Uç noktaya özel ön kontrol (varsa; ör. 13.6'da en az 5 yorum → 400 NOT_ENOUGH_COMMENTS)
6. Dakikada 10 istek sınırı aşıldı mı?              → 429 RATE_LIMITED

İstek sınırı en sona konur: yalnızca gerçekten modele gidecek istekler sayılır, yetki,
bulunamadı veya ön kontrol hatası alan istekler kullanıcının hakkından düşmez.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.core.exceptions import (
    ProjectAccessDeniedException,
    ProjectNotFoundException,
    TaskNotFoundException,
)
from app.database import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.services.llm import RateLimiter, get_llm_rate_limiter


@dataclass
class AITaskContext:
    user: User
    task: Task


@dataclass
class AIProjectContext:
    user: User
    project: Project


def _ensure_member(db: Session, project_id: int, user_id: int) -> None:
    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not is_member:
        raise ProjectAccessDeniedException()


TaskPrecheck = Callable[[Session, Task], None]


def ai_task_access(admin_only: bool, precheck: Optional[TaskPrecheck] = None) -> Callable[..., AITaskContext]:
    """Adreste {task_id} olan AI uç noktaları için koruma üretir.

    precheck: Modele gitmeden önce çalışan, uç noktaya özel kontrol. Hata yükseltirse istek
    sınırından düşülmez.
    """
    role_check = require_admin if admin_only else get_current_user

    def dependency(
        task_id: int,
        current_user: User = Depends(role_check),
        db: Session = Depends(get_db),
        limiter: RateLimiter = Depends(get_llm_rate_limiter),
    ) -> AITaskContext:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise TaskNotFoundException()
        _ensure_member(db, task.project_id, current_user.id)
        if precheck is not None:
            precheck(db, task)
        limiter.check(current_user.id)
        return AITaskContext(user=current_user, task=task)

    return dependency


def ai_project_access(admin_only: bool) -> Callable[..., AIProjectContext]:
    """Adreste {project_id} olan AI uç noktaları için koruma üretir."""
    role_check = require_admin if admin_only else get_current_user

    def dependency(
        project_id: int,
        current_user: User = Depends(role_check),
        db: Session = Depends(get_db),
        limiter: RateLimiter = Depends(get_llm_rate_limiter),
    ) -> AIProjectContext:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ProjectNotFoundException()
        _ensure_member(db, project.id, current_user.id)
        limiter.check(current_user.id)
        return AIProjectContext(user=current_user, project=project)

    return dependency


# Uç noktaların kullandığı hazır korumalar.
admin_task_access = ai_task_access(admin_only=True)
member_task_access = ai_task_access(admin_only=False)
admin_project_access = ai_project_access(admin_only=True)
member_project_access = ai_project_access(admin_only=False)
