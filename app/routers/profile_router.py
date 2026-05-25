from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import json

from datetime import datetime

from ..database import get_db
from ..models import User, ActorProfile
from uuid import uuid4
from datetime import datetime, timedelta
from ..schemas import ActorProfileCreate, ActorProfileResponse, AnalysisResponse
# Авторизация по telegram_id
from ..services.photo_analysis import PhotoAnalysisService
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/")
def get_profile(telegram_id: int, db: Session = Depends(get_db)):
    tg_str = str(telegram_id)
    user = db.query(User).filter(User.telegram_id == tg_str).first()
    if not user:
        # Автоматически создаём пользователя по telegram_id
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
    profile = user.profile
    
    # Определяем статус подписки
    sub_status = user.subscription_tier or "free"
    days_left = None
    if user.subscription_expires_at:
        delta = user.subscription_expires_at - datetime.utcnow()
        days_left = max(0, delta.days)
    if sub_status == "trial" and days_left is not None and days_left == 0:
        sub_status = "expired"
    
    if not profile:
        return {
            "user": {
                "id": str(user.id),
                "name": user.name,
                "telegram_id": user.telegram_id,
            },
            "profile": None,
            "subscription": {"tier": sub_status, "days_left": days_left}
        }
    
    return {
        "user": {
            "id": str(user.id),
            "name": user.name,
            "telegram_id": user.telegram_id,
        },
        "profile": {
            "id": str(profile.id),
            "archetype": profile.archetype,
            "archetypes_secondary": profile.archetypes_secondary or [],
            "age_range": profile.age_range,
            "strengths": profile.strengths or [],
            "weaknesses": profile.weaknesses or [],
            "actor_type": profile.actor_type,
            "goals": profile.goals,
            "experience_level": profile.experience_level,
            "bio": profile.bio,
            "created_at": profile.created_at.isoformat() if profile.created_at else None,
        },
        "subscription": {"tier": sub_status, "days_left": days_left}
    }


@router.put("/", response_model=ActorProfileResponse)
def update_profile(data: ActorProfileCreate, telegram_id: int, db: Session = Depends(get_db)):
    if not user.profile:
        profile = ActorProfile(user_id=user.id)
        db.add(profile)
    else:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user or not user.profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = user.profile

    if data.photo_url is not None:
        profile.photo_url = data.photo_url
    if data.goals is not None:
        profile.goals = data.goals
    if data.experience_level is not None:
        profile.experience_level = data.experience_level
    if data.bio is not None:
        profile.bio = data.bio

    db.commit()
    db.refresh(profile)
    return profile


@router.post("/analyze-photo", response_model=AnalysisResponse)
async def analyze_photo(
    file: UploadFile = File(...),
    user: User = Depends(),
    db: Session = Depends(get_db),
):
    """Анализ фото актёра через AI Vision. Возвращает развёрнутую персональную картину."""
    import os
    from uuid import uuid4
    
    # Сохраняем фото
    upload_dir = "/home/openclaw/.openclaw/workspace/actor-agent/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    file_name = f"{user.id}_{uuid4()}.{file_ext}"
    file_path = os.path.join(upload_dir, file_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Создаем/обновляем профиль
    if not user.profile:
        profile = ActorProfile(user_id=user.id, photo_url=file_path)
        db.add(profile)
    else:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
    if not user or not user.profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = user.profile
    profile.photo_url = file_path
    
    # Вызываем реальный AI-анализ через PhotoAnalysisService
    try:
        result = await PhotoAnalysisService.analyze_from_files(
            file_contents=[content],
            profile_id=str(profile.id) if profile else None
        )
        analysis_id, analysis_result = result
        
        if analysis_result:
            profile.archetype = analysis_result.primary_archetype
            profile.archetypes_secondary = [analysis_result.primary_archetype, analysis_result.secondary_archetype] if analysis_result.secondary_archetype else []
            profile.strengths = analysis_result.strengths
            profile.weaknesses = analysis_result.weaknesses
            profile.actor_type = analysis_result.primary_archetype
            
            return AnalysisResponse(
                archetype=analysis_result.primary_archetype or "Не определён",
                archetypes_secondary=[analysis_result.secondary_archetype] if analysis_result.secondary_archetype else [],
                age_range=analysis_result.perceived_age or "Не определён",
                strengths=analysis_result.strengths or [],
                weaknesses=analysis_result.weaknesses or [],
                actor_type=analysis_result.primary_archetype or "Не определён",
                analysis_text=(
                    f"Анализ завершён. Архетип: {analysis_result.primary_archetype}. "
                    f"Чёткость: {analysis_result.casting_clarity}. "
                    f"Энергия лица: {analysis_result.face_energy}. "
                    f"Структура лица: {analysis_result.face_structure}. "
                    f"Оценка: {analysis_result.actor_score.get('total', 'N/A')}/60. "
                    f"Статус: {analysis_result.actor_score.get('interpretation', 'N/A')}."
                )
            )
    except Exception as e:
        logger.error(f"Photo analysis failed: {e}")
        return AnalysisResponse(
            archetype="Ошибка анализа",
            archetypes_secondary=[],
            age_range="",
            strengths=["Повторите попытку"],
            weaknesses=[],
            actor_type="",
            analysis_text=f"Не удалось выполнить анализ. Ошибка: {str(e)}"
        )
    
    db.commit()
    return result
