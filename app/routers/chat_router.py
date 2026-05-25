from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json
from uuid import uuid4
from datetime import datetime

from datetime import datetime

from ..database import get_db
from ..models import User, MessageQueue, ActorProfile
from ..schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


def _check_subscription(user: User) -> None:
    """Проверяет подписку и блокирует агента если expired"""
    if user.subscription_tier == "free":
        raise HTTPException(status_code=403, detail="subscription_required")
    if user.subscription_tier == "trial" and user.subscription_expires_at:
        if datetime.utcnow() > user.subscription_expires_at:
            # Автоматически переводим на free при истечении триала
            user.subscription_tier = "free"
            user.subscription_expires_at = None
            raise HTTPException(status_code=403, detail="trial_expired")

def _get_or_create_user(db: Session, telegram_id: int | str):
    """Ищет пользователя по telegram_id. Если нет — создаёт."""
    tg_str = str(telegram_id)
    user = db.query(User).filter(User.telegram_id == tg_str).first()
    if user:
        return user

    # Создаём нового пользователя
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


@router.post("/", response_model=ChatResponse)
def chat(data: ChatRequest, db: Session = Depends(get_db)):
    """Отправляет сообщение в очередь единого AI-агента.
    Пользователь создаётся автоматически по telegram_id.
    """
    if not data.telegram_id:
        raise HTTPException(status_code=400, detail="telegram_id обязателен")

    user = _get_or_create_user(db, data.telegram_id)

    # Проверка подписки — агент только по подписке
    _check_subscription(user)

    # Собираем контекст пользователя
    context = {}
    if user.profile:
        context["actor_type"] = user.profile.actor_type
        context["archetype"] = user.profile.archetype
        context["archetypes_secondary"] = user.profile.archetypes_secondary
        context["strengths"] = user.profile.strengths
        context["weaknesses"] = user.profile.weaknesses
        context["experience_level"] = user.profile.experience_level
        context["goals"] = user.profile.goals
        context["analysis_summary"] = user.profile.analysis_summary

    # Кладём в очередь
    entry = MessageQueue(
        id=uuid4(),
        user_id=user.id,
        message=data.message,
        context=context,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(entry)
    db.commit()

    return ChatResponse(
        reply=f"✅ Сообщение принято в обработку (ID: {entry.id})",
        actions=[{"type": "queue", "queue_id": str(entry.id), "status": "pending"}]
    )


@router.get("/queue-status/{queue_id}")
def queue_status(queue_id: str, db: Session = Depends(get_db)):
    """Проверить статус сообщения в очереди."""
    entry = db.query(MessageQueue).filter(MessageQueue.id == queue_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Сообщение не найдено")
    return {
        "id": str(entry.id),
        "status": entry.status,
        "reply": entry.reply,
        "error": entry.error,
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
        "completed_at": entry.completed_at.isoformat() if entry.completed_at else None,
    }
