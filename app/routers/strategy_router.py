from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from ..database import get_db
from ..models import User, Strategy
from ..schemas import StrategyResponse
from ..auth import get_current_user

router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/", response_model=StrategyResponse)
def get_active_strategy(user: User = Depends(get_current_user)):
    if not user.strategies:
        raise HTTPException(status_code=404, detail="No strategy found. Generate one first.")

    active = [s for s in user.strategies if s.is_active]
    if not active:
        raise HTTPException(status_code=404, detail="No active strategy found.")

    # Return the most recently created active strategy
    return sorted(active, key=lambda s: s.created_at, reverse=True)[0]


@router.post("/generate", response_model=StrategyResponse)
def generate_strategy(
    period_days: int = 30,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Заглушка генерации стратегии. Позже заменится на AI."""
    if not user.profile:
        raise HTTPException(status_code=400, detail="Complete your profile and photo analysis first.")

    # Деактивируем старые стратегии
    for s in user.strategies:
        s.is_active = False

    # Тестовая стратегия
    content = {
        "period_days": period_days,
        "goals": [
            {"week": 1, "title": "Update headshot portfolio", "done": False},
            {"week": 2, "title": "Practice emotional range exercises", "done": False},
            {"week": 3, "title": "Submit to 5 casting calls", "done": False},
        ],
        "daily_routine": [
            "Morning: Voice warm-up (15 min)",
            "Afternoon: Scene study (30 min)",
            "Evening: Industry news & casting research (15 min)",
        ],
        "recommendations": [
            "Work on emotional vulnerability in dramatic scenes",
            "Expand your character repertoire beyond 'everyman' roles",
            "Build a demo reel with your strongest monologues",
        ],
    }

    strategy = Strategy(
        user_id=user.id,
        period_days=period_days,
        content=content,
        is_active=True,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy
