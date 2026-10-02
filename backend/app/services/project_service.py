from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.project import Project
from app.models.task import Task
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse

class ProjectService:
    @staticmethod
    def create_project(db: Session, project_in: ProjectCreate) -> Project:
        db_project = Project(
            name=project_in.name,
            description=project_in.description,
            status=project_in.status,
            start_date=project_in.start_date,
            end_date=project_in.end_date,
            created_by_id=project_in.created_by_id
        )
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        return db_project

    @staticmethod
    def get_project(db: Session, project_id: int) -> Optional[Project]:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def get_projects(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[ProjectResponse]:
        query = db.query(Project)
        if status:
            query = query.filter(Project.status == status)
        
        projects = query.offset(skip).limit(limit).all()
        result = []
        for p in projects:
            task_count = db.query(func.count(Task.id)).filter(Task.project_id == p.id).scalar() or 0
            p_dict = ProjectResponse.model_validate(p)
            p_dict.task_count = task_count
            result.append(p_dict)
        return result

    @staticmethod
    def update_project(db: Session, project_id: int, project_in: ProjectUpdate) -> Optional[Project]:
        db_project = ProjectService.get_project(db, project_id)
        if not db_project:
            return None
        
        update_data = project_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)

        db.commit()
        db.refresh(db_project)
        return db_project

    @staticmethod
    def delete_project(db: Session, project_id: int) -> bool:
        db_project = ProjectService.get_project(db, project_id)
        if not db_project:
            return False
        db.delete(db_project)
        db.commit()
        return True
