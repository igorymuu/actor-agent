from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from ..database import get_db
from ..models import User, CastingEvent
from ..schemas import CastingCreate, CastingOut

router = APIRouter(prefix="/castings", tags=["castings"])


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


@router.get("/", response_model=list[CastingOut])
def list_castings(telegram_id: int, db: Session = Depends(get_db)):
    user = _get_user_by_tg(db, telegram_id)
    if not user:
        return []
    castings = db.query(CastingEvent).filter(CastingEvent.user_id == user.id).order_by(CastingEvent.event_date.desc()).all()
    return [CastingOut(
        id=c.id,
        title=c.title,
        event_date=c.event_date.isoformat() if c.event_date else "",
        event_time=c.event_date.strftime("%H:%M") if c.event_date else "",
        location=c.location or "",
        notes=c.description or "",
        created_at=c.created_at,
    ) for c in castings]


@router.get("/upcoming/{days}", response_model=list[dict])
def get_upcoming_castings(days: int, db: Session = Depends(get_db)):
    """Возвращает все съёмки на ближайшие N дней с telegram_id пользователя."""
    from datetime import timedelta, timezone
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    castings = db.query(CastingEvent).filter(
        CastingEvent.event_date >= now,
        CastingEvent.event_date <= end,
        CastingEvent.is_reminded == False,
    ).order_by(CastingEvent.event_date.asc()).all()

    result = []
    for c in castings:
        user = db.query(User).filter(User.id == c.user_id).first()
        if user and user.telegram_id:
            result.append({
                "casting_id": str(c.id),
                "user_id": str(c.user_id),
                "telegram_id": int(user.telegram_id),
                "title": c.title,
                "event_date": c.event_date.isoformat(),
                "notes": c.description or "",
            })
    return result


@router.patch("/{casting_id}/reminded", status_code=200)
def mark_reminded(casting_id: UUID, db: Session = Depends(get_db)):
    """Пометить съёмку как уведомлённую."""
    casting = db.query(CastingEvent).filter(CastingEvent.id == casting_id).first()
    if not casting:
        raise HTTPException(status_code=404, detail="Not found")
    casting.is_reminded = True
    db.commit()
    return {"status": "ok"}


@router.post("/", response_model=CastingOut)
def create_casting(
    data: CastingCreate,
    db: Session = Depends(get_db),
):
    user = _get_user_by_tg(db, data.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Парсим дату (ДД.ММ.ГГГГ или ISO)
    from datetime import date
    import re
    ed = data.event_date
    if ed and re.match(r"\d{2}\.\d{2}\.\d{4}", ed):
        parts = ed.split(".")
        event_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
    elif ed:
        event_date = date.fromisoformat(ed[:10])
    else:
        event_date = date.today()
    event_datetime = datetime.combine(event_date, datetime.min.time())

    casting = CastingEvent(
        user_id=user.id,
        title=data.title,
        description=data.notes or data.description or "",
        location=data.location or "",
        event_date=event_datetime,
    )
    db.add(casting)
    db.commit()
    db.refresh(casting)

    return CastingOut(
        id=casting.id,
        title=casting.title,
        event_date=casting.event_date.isoformat() if casting.event_date else "",
        event_time=casting.event_date.strftime("%H:%M") if casting.event_date else "",
        location=casting.location or "",
        notes=casting.description or "",
        created_at=casting.created_at,
    )


@router.delete("/", status_code=204)
def reset_castings(telegram_id: int, db: Session = Depends(get_db)):
    """Удаляет все кастинги пользователя."""
    user = _get_user_by_tg(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.query(CastingEvent).filter(CastingEvent.user_id == user.id).delete()
    db.commit()
    return None


@router.delete("/{casting_id}", status_code=204)
def delete_casting(
    casting_id: UUID,
    telegram_id: int,
    db: Session = Depends(get_db),
):
    user = _get_user_by_tg(db, telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    casting = (
        db.query(CastingEvent)
        .filter(CastingEvent.id == casting_id, CastingEvent.user_id == user.id)
        .first()
    )
    if not casting:
        raise HTTPException(status_code=404, detail="Casting not found")
    db.delete(casting)
    db.commit()
    return None
