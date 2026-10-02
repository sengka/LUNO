from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from app.models.project import Project
from app.models.task import Task, TaskStatus
from app.schemas.report import (
    ProjectProgressReport, UserTaskSummaryReport, PeriodStatPoint, PeriodicStatsReport
)
from app.schemas.calendar_gantt import (
    CalendarEventResponse, GanttTaskItem, GanttProjectItem, GanttTimelineResponse
)

class ReportService:
    @staticmethod
    def get_project_progress(db: Session, project_id: int) -> Optional[ProjectProgressReport]:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return None

        total_tasks = db.query(func.count(Task.id)).filter(Task.project_id == project_id).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(
            Task.project_id == project_id, Task.status == TaskStatus.DONE
        ).scalar() or 0
        in_progress_tasks = db.query(func.count(Task.id)).filter(
            Task.project_id == project_id, Task.status == TaskStatus.IN_PROGRESS
        ).scalar() or 0
        todo_tasks = db.query(func.count(Task.id)).filter(
            Task.project_id == project_id, Task.status == TaskStatus.TODO
        ).scalar() or 0

        progress_pct = round((completed_tasks / total_tasks * 100.0), 2) if total_tasks > 0 else 0.0

        return ProjectProgressReport(
            project_id=project.id,
            project_name=project.name,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            in_progress_tasks=in_progress_tasks,
            todo_tasks=todo_tasks,
            progress_percentage=progress_pct
        )

    @staticmethod
    def get_user_task_summary(db: Session, user_id: int) -> UserTaskSummaryReport:
        total_assigned = db.query(func.count(Task.id)).filter(Task.assigned_to_id == user_id).scalar() or 0
        completed = db.query(func.count(Task.id)).filter(
            Task.assigned_to_id == user_id, Task.status == TaskStatus.DONE
        ).scalar() or 0
        in_progress = db.query(func.count(Task.id)).filter(
            Task.assigned_to_id == user_id, Task.status == TaskStatus.IN_PROGRESS
        ).scalar() or 0
        todo = db.query(func.count(Task.id)).filter(
            Task.assigned_to_id == user_id, Task.status == TaskStatus.TODO
        ).scalar() or 0

        completion_rate = round((completed / total_assigned * 100.0), 2) if total_assigned > 0 else 0.0

        return UserTaskSummaryReport(
            user_id=user_id,
            total_assigned=total_assigned,
            completed_tasks=completed,
            in_progress_tasks=in_progress,
            todo_tasks=todo,
            completion_rate_percentage=completion_rate
        )

    @staticmethod
    def get_periodic_stats(
        db: Session,
        timeframe: str = "daily",  # "daily", "weekly", "monthly"
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> PeriodicStatsReport:
        if not end_date:
            end_date = date.today()
        if not start_date:
            if timeframe == "daily":
                start_date = end_date - timedelta(days=14)
            elif timeframe == "weekly":
                start_date = end_date - timedelta(weeks=8)
            else:
                start_date = end_date - timedelta(days=180)

        # Query all tasks created or completed in period
        tasks = db.query(Task).all()

        points_map: Dict[str, Dict[str, int]] = {}

        for task in tasks:
            # Check created date
            if task.created_at:
                c_date = task.created_at.date()
                if start_date <= c_date <= end_date:
                    label = ReportService._format_date_label(c_date, timeframe)
                    if label not in points_map:
                        points_map[label] = {"created": 0, "completed": 0}
                    points_map[label]["created"] += 1

            # Check completed date
            if task.completed_at:
                comp_date = task.completed_at.date()
                if start_date <= comp_date <= end_date:
                    label = ReportService._format_date_label(comp_date, timeframe)
                    if label not in points_map:
                        points_map[label] = {"created": 0, "completed": 0}
                    points_map[label]["completed"] += 1

        sorted_labels = sorted(points_map.keys())
        data_points = [
            PeriodStatPoint(
                label=lbl,
                created_tasks=points_map[lbl]["created"],
                completed_tasks=points_map[lbl]["completed"]
            )
            for lbl in sorted_labels
        ]

        total_created = sum(p.created_tasks for p in data_points)
        total_completed = sum(p.completed_tasks for p in data_points)

        return PeriodicStatsReport(
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
            total_created=total_created,
            total_completed=total_completed,
            data_points=data_points
        )

    @staticmethod
    def _format_date_label(d: date, timeframe: str) -> str:
        if timeframe == "daily":
            return d.strftime("%Y-%m-%d")
        elif timeframe == "weekly":
            year, week, _ = d.isocalendar()
            return f"{year}-W{week:02d}"
        elif timeframe == "monthly":
            return d.strftime("%Y-%m")
        return d.strftime("%Y-%m-%d")

    @staticmethod
    def get_calendar_events(
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        assigned_to_id: Optional[int] = None
    ) -> List[CalendarEventResponse]:
        events: List[CalendarEventResponse] = []

        # 1. Projects as calendar items
        proj_query = db.query(Project)
        projects = proj_query.all()
        for p in projects:
            p_status_str = p.status.value if hasattr(p.status, 'value') else str(p.status)
            if p.start_date or p.end_date:
                events.append(CalendarEventResponse(
                    id=p.id,
                    title=f"[Proje] {p.name}",
                    event_type="PROJECT",
                    start_date=p.start_date,
                    end_date=p.end_date,
                    status=p_status_str,
                    project_id=p.id,
                    project_name=p.name,
                    assigned_to_id=None
                ))

        # 2. Tasks as calendar items
        task_query = db.query(Task)
        if assigned_to_id:
            task_query = task_query.filter(Task.assigned_to_id == assigned_to_id)
        
        tasks = task_query.all()
        for t in tasks:
            t_status_str = t.status.value if hasattr(t.status, 'value') else str(t.status)
            if t.start_date or t.due_date:
                proj_name = t.project.name if t.project else None
                events.append(CalendarEventResponse(
                    id=t.id,
                    title=t.title,
                    event_type="TASK",
                    start_date=t.start_date or t.due_date,
                    end_date=t.due_date or t.start_date,
                    status=t_status_str,
                    project_id=t.project_id,
                    project_name=proj_name,
                    assigned_to_id=t.assigned_to_id
                ))

        # Filter by range if provided
        if start_date or end_date:
            filtered = []
            for ev in events:
                ev_start = ev.start_date or ev.end_date
                ev_end = ev.end_date or ev.start_date
                if not ev_start and not ev_end:
                    continue
                if start_date and ev_end and ev_end < start_date:
                    continue
                if end_date and ev_start and ev_start > end_date:
                    continue
                filtered.append(ev)
            return filtered

        return events

    @staticmethod
    def get_gantt_timeline(db: Session, project_id: Optional[int] = None) -> GanttTimelineResponse:
        proj_query = db.query(Project)
        if project_id:
            proj_query = proj_query.filter(Project.id == project_id)
        
        projects = proj_query.all()
        gantt_projects: List[GanttProjectItem] = []

        for p in projects:
            task_items: List[GanttTaskItem] = []
            p_status_str = p.status.value if hasattr(p.status, 'value') else str(p.status)
            for t in p.tasks:
                prog = 0.0
                if t.status == TaskStatus.DONE:
                    prog = 100.0
                elif t.status == TaskStatus.IN_PROGRESS:
                    prog = 50.0

                task_items.append(GanttTaskItem(
                    id=t.id,
                    title=t.title,
                    start_date=t.start_date or p.start_date,
                    due_date=t.due_date or p.end_date,
                    status=t.status,
                    priority=t.priority,
                    assigned_to_id=t.assigned_to_id,
                    progress_percent=prog
                ))

            gantt_projects.append(GanttProjectItem(
                project_id=p.id,
                project_name=p.name,
                status=p_status_str,
                start_date=p.start_date,
                end_date=p.end_date,
                tasks=task_items
            ))

        return GanttTimelineResponse(projects=gantt_projects)
