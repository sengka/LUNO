from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, TaskAssign, TaskStatusUpdate, TaskDatesUpdate

class TaskService:
    @staticmethod
    def create_task(db: Session, task_in: TaskCreate) -> Task:
        completed_at = datetime.utcnow() if task_in.status == TaskStatus.DONE else None
        db_task = Task(
            title=task_in.title,
            description=task_in.description,
            project_id=task_in.project_id,
            assigned_to_id=task_in.assigned_to_id,
            status=task_in.status,
            priority=task_in.priority,
            start_date=task_in.start_date,
            due_date=task_in.due_date,
            story_points=task_in.story_points,
            module_name=task_in.module_name,
            completed_at=completed_at
        )
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def get_task(db: Session, task_id: int) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_tasks(
        db: Session,
        project_id: Optional[int] = None,
        assigned_to_id: Optional[int] = None,
        status: Optional[TaskStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Task]:
        query = db.query(Task)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        if assigned_to_id:
            query = query.filter(Task.assigned_to_id == assigned_to_id)
        if status:
            query = query.filter(Task.status == status)
        
        return query.offset(skip).limit(limit).all()

    @staticmethod
    def update_task(db: Session, task_id: int, task_in: TaskUpdate) -> Optional[Task]:
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        update_data = task_in.model_dump(exclude_unset=True)
        if "status" in update_data:
            if update_data["status"] == TaskStatus.DONE and db_task.status != TaskStatus.DONE:
                db_task.completed_at = datetime.utcnow()
            elif update_data["status"] != TaskStatus.DONE:
                db_task.completed_at = None

        for field, value in update_data.items():
            setattr(db_task, field, value)

        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def assign_task(db: Session, task_id: int, assign_in: TaskAssign) -> Optional[Task]:
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        db_task.assigned_to_id = assign_in.assigned_to_id
        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def update_task_status(db: Session, task_id: int, status_in: TaskStatusUpdate) -> Optional[Task]:
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        db_task.status = status_in.status
        if status_in.status == TaskStatus.DONE:
            db_task.completed_at = datetime.utcnow()
        else:
            db_task.completed_at = None

        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def update_task_dates(db: Session, task_id: int, dates_in: TaskDatesUpdate) -> Optional[Task]:
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return None
        
        if dates_in.start_date is not None:
            db_task.start_date = dates_in.start_date
        if dates_in.due_date is not None:
            db_task.due_date = dates_in.due_date

        db.commit()
        db.refresh(db_task)
        return db_task

    @staticmethod
    def delete_task(db: Session, task_id: int) -> bool:
        db_task = TaskService.get_task(db, task_id)
        if not db_task:
            return False
        db.delete(db_task)
        db.commit()
        return True
