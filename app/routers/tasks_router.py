from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from ..database import get_db
from ..models import User, Task
from ..schemas import TaskCreate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _get_user_by_tg(db: Session, telegram_id: int) -> User:
    from uuid import uuid4
    from datetime import datetime, timedelta
    tg_str = str(telegram_id)
    user = db.query(User).filter(User.telegram_id == tg_str).first()
    if user:
        return user
    user = User(
        id=uuid4(),
        telegram_id=tg_str,
        email=f"tg_{tg_str}@actor.neyrix.ai",
        hashed_password="telegram_only",
        name=f"Актёр {tg_str[-4:]}",
        subscription_tier="trial",
            subscription_expires_at=datetime.utcnow() + timedelta(days=7),
        )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=list[TaskResponse])
def list_tasks(telegram_id: int, db: Session = Depends(get_db)):
    user = _get_user_by_tg(db, telegram_id)
    if not user:
        return []
    return user.tasks


@router.post("/", response_model=TaskResponse)
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    user = _get_user_by_tg(db, data.telegram_id)
    task = Task(
        user_id=user.id,
        title=data.title,
        description=data.description,
        task_type=data.task_type,
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/", status_code=204)
def reset_tasks(telegram_id: int, db: Session = Depends(get_db)):
    """Удаляет все задачи пользователя."""
    user = _get_user_by_tg(db, telegram_id)
    db.query(Task).filter(Task.user_id == user.id).delete()
    db.commit()
    return None


@router.patch("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: UUID, telegram_id: int, db: Session = Depends(get_db)):
    user = _get_user_by_tg(db, telegram_id)
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.is_completed = True
    db.commit()
    db.refresh(task)
    return task
