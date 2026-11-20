"""Görev tablolarında kullanılan sabit değerler (API sözleşmesi bölüm 1.3).

Sistem rolü (SystemRole) app/models/user.py içinde tanımlıdır.
"""

import enum


class TaskStatus(str, enum.Enum):
    ONAY_BEKLIYOR = "ONAY_BEKLIYOR"
    REDDEDILDI = "REDDEDILDI"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    REVIEW_TESTING = "REVIEW_TESTING"
    DONE = "DONE"


# Kanban, takvim, Gantt ve raporlarda gösterilen durumlar (bölüm 1.3, "Aktif görev").
ACTIVE_TASK_STATUSES = (
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.REVIEW_TESTING,
    TaskStatus.DONE,
)


class Priority(str, enum.Enum):
    DUSUK = "DUSUK"
    ORTA = "ORTA"
    YUKSEK = "YUKSEK"


class NotificationType(str, enum.Enum):
    """Bildirim türleri (sözleşme 2. bölüm, Notification nesnesi)."""

    TASK_ASSIGNED = "TASK_ASSIGNED"  # FR-052
    COMMENT_ADDED = "COMMENT_ADDED"  # FR-054
    DUE_DATE_SOON = "DUE_DATE_SOON"  # FR-056
    TASK_STALE = "TASK_STALE"  # FR-057
    TASK_PENDING_APPROVAL = "TASK_PENDING_APPROVAL"  # FR-051
    TASK_APPROVED = "TASK_APPROVED"  # FR-051
    TASK_REJECTED = "TASK_REJECTED"  # FR-051


# Efor puanı yalnızca Fibonacci değerleri olabilir (FR-036).
STORY_POINT_VALUES = (1, 2, 3, 5, 8, 13)
