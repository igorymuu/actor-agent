"""
Pipeline: Actor Profile + Analysis → 30-Day Structured Strategy Plan

Takes an actor profile (with optional goals), builds structured weekly plan
via LLM or heuristic, persists to Strategy model.
"""

import json
import logging
import os
from datetime import datetime

import httpx
from sqlalchemy.orm import Session

from ..models import ActorProfile, Strategy, User
from ..database import SessionLocal
from ..schemas import StrategyPlan
from ..config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT
from ..instructions.prompts import CASTING_DIRECTOR_PROMPT

logger = logging.getLogger(__name__)

STRATEGY_PROMPT = """Based on the actor profile below, create a structured 30-day strategy plan following the CAREER STRATEGY SYSTEM and MONETIZATION SYSTEM rules.

Actor Profile:
- Archetypes: {archetypes}
- Strengths: {strengths}
- Weaknesses: {weaknesses}
- Experience level: {experience_level} (1=Entry, 2=Emerging, 3=Working, 4=Recognizable, 5=Leading)
- Goals: {goals}

Monthly targets for this level: 20 casting submissions, 4 self tapes, 8 actor videos, profile update, 1 new photo per month.

Return ONLY valid JSON with this exact structure:
{{
    "weekly_goals": [
        {{"week": 1, "focus": "Позиционирование и типаж", "tasks": ["task1", "task2", "task3"], "expected_outcome": "outcome"}},
        {{"week": 2, "focus": "Кастинговая активность", "tasks": [...], "expected_outcome": "..."}},
        {{"week": 3, "focus": "Продвижение и видимость", "tasks": [...], "expected_outcome": "..."}},
        {{"week": 4, "focus": "Анализ и коррекция", "tasks": [...], "expected_outcome": "..."}}
    ],
    "long_term_goals": ["goal1", "goal2", "goal3"],
    "recommended_actions": ["action1", "action2", "action3"],
    "metrics_to_track": ["metric1", "metric2", "metric3"],
    "monetization_strategy": ["income stream 1", "income stream 2", "income stream 3"],
    "current_career_level": "ENTRY/EMERGING/WORKING/RECOGNIZABLE/LEADING",
    "target_career_level": "next level"
}}"""


def _mock_strategy(goals: str | None = None) -> dict:
    """Mock plan when no API key is configured."""
    return {
        "weekly_goals": [
            {
                "week": 1,
                "focus": "Типаж и амплуа",
                "tasks": [
                    "Проанализировать свои архетипы и типажные роли",
                    "Составить список амплуа, подходящих под ваш типаж",
                    "Подготовить план расширения амплуа",
                ],
                "expected_outcome": "Чёткое понимание своего актёрского амплуа",
            },
            {
                "week": 2,
                "focus": "Портфолио",
                "tasks": [
                    "Отсортировать текущие фото по амплуа",
                    "Запланировать фотосессию для недостающих ролей",
                    "Обновить шоурил и демо-материалы",
                ],
                "expected_outcome": "Полный пакет профессиональных материалов",
            },
            {
                "week": 3,
                "focus": "Кастинги",
                "tasks": [
                    "Подобрать 5-10 открытых кастингов по типажу",
                    "Подготовить самопробы на целевые роли",
                    "Подать заявки с новыми материалами",
                ],
                "expected_outcome": "3-5 поданных заявок на кастинги",
            },
            {
                "week": 4,
                "focus": "Продвижение",
                "tasks": [
                    "Обновить профили на кастинг-платформах",
                    "Собрать и проанализировать отклики от кастинг-директоров",
                    "Скорректировать стратегию на основе полученной обратной связи",
                ],
                "expected_outcome": "Повышение видимости на рынке кастингов",
            },
        ],
        "long_term_goals": [
            "Закрепиться в целевом амплуа",
            "Наработать портфолио для крупных проектов",
            "Выйти на стабильный поток кастингов",
        ],
        "recommended_actions": [
            "Ежедневно практиковать актёрское мастерство 30 минут",
            "Раз в неделю снимать самопробу для анализа",
            "Подписаться на рассылки кастинг-платформ",
        ],
        "metrics_to_track": [
            "Количество поданных заявок в неделю",
            "Процент откликов на заявки",
            "Рост качества самопроб (оценка от AI)",
        ],
    }


async def _call_llm(profile: ActorProfile, goals: str | None = None) -> dict:
    """Call OpenAI-compatible LLM to generate strategy plan."""
    if not LLM_API_KEY:
        return _mock_strategy(goals)

    prompt = STRATEGY_PROMPT.format(
        archetypes=profile.archetypes or [profile.archetype or "Unknown"],
        strengths=profile.strengths or [],
        weaknesses=profile.weaknesses or [],
        experience_level=profile.experience_level or "unknown",
        goals=goals or profile.goals or "Not specified",
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": CASTING_DIRECTOR_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4096,
        "temperature": 0.3,
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            # Support both OpenAI and Anthropic formats
            if "choices" in data:
                content = data["choices"][0]["message"]["content"]
            elif "content" in data and isinstance(data["content"], list):
                content = " ".join([c["text"] for c in data["content"] if c.get("type") == "text"])
            else:
                content = str(data)
            if content.startswith("```"):
                content = content.split("\n", 1)[-1]
                content = content.rsplit("```", 1)[0]
            return json.loads(content.strip())
        except Exception as e:
            logger.error(f"Strategy LLM call failed: {e}", exc_info=True)
            return _mock_strategy(goals)


class StrategyService:
    """Pipeline: profile → LLM strategy → save → return structured plan."""

    @staticmethod
    async def generate(profile_id: str, goals: str | None = None, user_id: str | None = None) -> StrategyPlan:
        """Generate a 30-day strategy plan for the given profile."""
        db: Session = SessionLocal()
        try:
            profile = db.query(ActorProfile).filter(ActorProfile.id == profile_id).first()
            if not profile:
                raise ValueError(f"Profile {profile_id} not found")

            raw = await _call_llm(profile, goals)
            plan = StrategyPlan(**raw)

            # Persist as Strategy record
            uid = user_id or (profile.user_id and str(profile.user_id))
            if uid:
                # Deactivate old strategies
                for s in db.query(Strategy).filter(Strategy.user_id == uid).all():
                    s.is_active = False

                strategy = Strategy(
                    user_id=uid,
                    period_days=30,
                    content=raw,
                    is_active=True,
                )
                db.add(strategy)
                db.commit()

            return plan

        except Exception as e:
            db.rollback()
            logger.error(f"Strategy generation failed: {e}", exc_info=True)
            raise
        finally:
            db.close()
