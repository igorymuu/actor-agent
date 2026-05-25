"""
Pipeline: Actor Profile → Casting Compatibility Scoring

MVP stage — generates role-type recommendations and casting suggestions
based on the actor's profile attributes (archetypes, strengths, weaknesses).
"""

import logging
from sqlalchemy.orm import Session

from ..models import ActorProfile
from ..database import SessionLocal
from ..schemas import CastingRecommendation

logger = logging.getLogger(__name__)

# Basic mapping: archetype → recommended role types
ARCHETYPE_ROLE_MAP = {
    "Hero": ["Боевик", "Приключения", "Драма"],
    "Rebel": ["Криминальная драма", "Триллер", "Драма"],
    "Sage": ["Интеллектуальное кино", "Научная фантастика", "Документальное"],
    "Innocent": ["Комедия", "Мелодрама", "Семейное кино"],
    "Explorer": ["Приключения", "Фэнтези", "Научная фантастика"],
    "Creator": ["Арт-хаус", "Авторское кино", "Творческие проекты"],
    "Caregiver": ["Мелодрама", "Семейное кино", "Драма"],
    "Magician": ["Фэнтези", "Мистика", "Сказки"],
    "Ruler": ["Историческое кино", "Политическая драма", "Биографический фильм"],
    "Lover": ["Мелодрама", "Романтическая комедия", "Драма"],
    "Jester": ["Комедия", "Ситком", "Импровизация"],
    "Everyman": ["Универсальные роли", "Комедия", "Социальная драма"],
}


def _score_compatibility(profile: ActorProfile) -> tuple[float, list[str]]:
    """Calculate compatibility score (0-1) and list of compatible archetypes."""
    profile_archetypes = (profile.archetypes or []) + ([profile.archetype] if profile.archetype else [])

    if not profile_archetypes:
        return 0.3, list(ARCHETYPE_ROLE_MAP.keys())

    compatible = []
    score = 0.5  # base

    for arch in profile_archetypes:
        if arch in ARCHETYPE_ROLE_MAP:
            compatible.append(arch)
            score += 0.1

    for s in (profile.strengths or []):
        if any(kw in s.lower() for kw in ["универсаль", "гибк", "разноплан"]):
            score += 0.05

    score = min(score, 1.0)
    return round(score, 2), compatible or list(ARCHETYPE_ROLE_MAP.keys())[:3]


class CastingService:
    """Pipeline: profile → casting recommendations. Currently rule-based MVP."""

    @staticmethod
    def get_recommendations(profile_id: str) -> CastingRecommendation:
        """Get role type and casting recommendations for a profile."""
        db: Session = SessionLocal()
        try:
            profile = db.query(ActorProfile).filter(ActorProfile.id == profile_id).first()
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")

            score, compatible_archetypes = _score_compatibility(profile)
            role_types = set()
            recommended_casting = []

            for arch in compatible_archetypes:
                if arch in ARCHETYPE_ROLE_MAP:
                    role_types.update(ARCHETYPE_ROLE_MAP[arch])

            # Build suggestions based on profile
            suggestions = [
                "Ищите кастинги, где требуется ваш доминирующий архетип",
                "Подготовьте самопробы для каждого типа роли из рекомендаций",
                "Следите за открытыми кастингами на профильных платформах",
            ]
            if profile.weaknesses:
                suggestions.append(
                    f"Уделите внимание слабым сторонам: {', '.join(profile.weaknesses[:2])}"
                )

            return CastingRecommendation(
                role_types=sorted(role_types),
                recommended_casting_types=sorted([
                    f"Кастинг под архетип: {a}" for a in compatible_archetypes
                ]),
                compatibility_score=score,
                suggestions=suggestions,
            )
        finally:
            db.close()
