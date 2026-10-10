from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import STORY_POINT_VALUES, Priority, TaskStatus

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User

_story_points_sql = ", ".join(str(v) for v in STORY_POINT_VALUES)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    """API sözleşmesi 2. bölüm: Task nesnesi.

    Tabloda tutulmayan, API katmanında hesaplanan alanlar:
      risk_level (FR-070 – FR-072), subtask_count, subtask_done_count,
      comment_count, file_count.
    Sonraki sprintlerde eklenecek tablolar: labels / task_labels (Sprint 4),
      task_dependencies (Sprint 9), sprints (Sprint 6; sprint_id'ye FK o zaman eklenir).
    """

    __tablename__ = "tasks"
    __table_args__ = (
        # Teslim tarihi başlangıçtan önce olamaz (FR-025).
        CheckConstraint(
            "start_date IS NULL OR due_date IS NULL OR due_date >= start_date",
            name="ck_tasks_due_after_start",
        ),
        # Efor puanı yalnızca 1, 2, 3, 5, 8, 13 (FR-036).
        CheckConstraint(
            f"story_points IS NULL OR story_points IN ({_story_points_sql})",
            name="ck_tasks_story_points_fibonacci",
        ),
        # Bir görev kendisinin alt görevi olamaz.
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="ck_tasks_parent_not_self"),
        Index("ix_tasks_project_id_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # Alt görevse ana görevin id'si (FR-038). Ana görev silinince alt görevler de silinir.
    # "Alt görevin alt görevi olamaz" kuralı API katmanında kontrol edilir (6.10).
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Değerler metin olarak saklanır (users.role gibi); izin verilmeyen değer CHECK kısıtıyla reddedilir.
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus, name="ck_tasks_status", native_enum=False, create_constraint=True, length=20
        ),
        nullable=False,
        default=TaskStatus.TODO,
        server_default=TaskStatus.TODO.value,
    )
    priority: Mapped[Priority | None] = mapped_column(
        Enum(
            Priority, name="ck_tasks_priority", native_enum=False, create_constraint=True, length=10
        ),
        nullable=True,
    )
    story_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Üye projeden çıkarılınca (5.10) veya kullanıcı silinince görev atamasız kalır.
    assignee_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    sprint_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    # Hatırlatma işi (FR-057) "4 gündür güncellenmeyen görev" için bu alanı kullanır.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="tasks")
    assignee: Mapped["User | None"] = relationship(foreign_keys=[assignee_id])
    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])
    parent: Mapped["Task | None"] = relationship(back_populates="subtasks", remote_side=[id])
    subtasks: Mapped[list["Task"]] = relationship(
        back_populates="parent", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title!r} status={self.status.value}>"
