#!/usr/bin/env python3
"""
Actor Worker — единый AI-агент для общения с актёрами.
Забирает сообщения из очереди MessageQueue, обрабатывает через LLM,
сохраняет ответ обратно в БД.
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from uuid import UUID

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WORKER] %(levelname)s %(message)s",
)
logger = logging.getLogger("actor-worker")

# --- Config ---
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://actor_admin:actor_pass_2026_secure@localhost:5434/actor_agent",
)
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "sk-71d6862512e54c649f02560b77e7e52b")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))  # секунд между проверками

# System prompt для единого AI-агента
SYSTEM_PROMPT = """ТЫ — NEYRIX ACTOR AI, единый AI-агент для актёров.

ТЫ ОТВЕЧАЕШЬ ВСЕМ АКТЁРАМ, КОТОРЫЕ К ТЕБЕ ОБРАЩАЮТСЯ.
Каждое обращение содержит профиль актёра (контекст).
Отвечай персонально каждому, с учётом его типажа, анализа и целей.

ТВОЯ РОЛЬ:
- Актерский агент
- Карьерный консультант
- Кастинг-директор аналитик

ПРАВИЛА ОТВЕТА:
1. Всегда обращайся к актёру по имени (если указано)
2. Отвечай развёрнуто, конкретно, без воды
3. Используй данные из профиля: архетип, типаж, оценку
4. Если актёр спрашивает про кастинг — давай конкретные роли
5. Если про стратегию — конкретные шаги на неделю/месяц
6. Будь прямолинейным, честным, без лести
7. Каждый ответ должен заканчиваться конкретным действием

СТРУКТУРА ОТВЕТА:
1. Обращение
2. Ответ на вопрос
3. Вывод/диагноз
4. Конкретный следующий шаг
"""


def create_worker():
    """Создание и запуск воркера."""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)

    logger.info("Actor Worker запущен")
    logger.info(f"LLM: {LLM_MODEL} via {LLM_BASE_URL}")
    logger.info(f"Проверка очереди каждые {POLL_INTERVAL}с")

    while True:
        try:
            db = SessionLocal()
            try:
                # Берём самое старое pending сообщение
                result = db.execute(
                    text("""
                        SELECT mq.id, mq.user_id, mq.message, mq.context,
                               u.name as user_name, u.email as user_email
                        FROM messages_queue mq
                        JOIN users u ON u.id = mq.user_id
                        WHERE mq.status = 'pending'
                        ORDER BY mq.created_at ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                    """)
                )
                row = result.fetchone()

                if row:
                    msg_id, user_id, message, context_raw, user_name, user_email = row
                    context = json.loads(context_raw) if context_raw else {}

                    logger.info(f"Обрабатываю сообщение {msg_id} от {user_name or user_email}")

                    # Помечаем как processing
                    db.execute(
                        text("UPDATE messages_queue SET status='processing', processed_at=NOW() WHERE id=:id"),
                        {"id": msg_id},
                    )
                    db.commit()

                    # Формируем промпт
                    profile_context = ""
                    if context:
                        profile_context = (
                            f"Профиль актёра:\n"
                            f"- Типаж: {context.get('actor_type', 'не указан')}\n"
                            f"- Архетип: {context.get('archetype', 'не указан')}\n"
                            f"- Сильные стороны: {', '.join(context.get('strengths', ['не указаны']))}\n"
                            f"- Слабые стороны: {', '.join(context.get('weaknesses', ['не указаны']))}\n"
                            f"- Уровень: {context.get('experience_level', 'не указан')}\n"
                            f"- Цели: {context.get('goals', 'не указаны')}\n"
                        )

                    user_prompt = (
                        f"Клиент: {user_name or user_email}\n"
                        f"{profile_context}\n"
                        f"Вопрос актёра: {message}\n\n"
                        f"Дай развёрнутый ответ."
                    )

                    # Вызов LLM
                    reply = call_llm(SYSTEM_PROMPT, user_prompt)

                    if reply:
                        # Сохраняем ответ
                        db.execute(
                            text("""
                                UPDATE messages_queue
                                SET status='done', reply=:reply, completed_at=NOW()
                                WHERE id=:id
                            """),
                            {"id": msg_id, "reply": reply},
                        )
                        logger.info(f"✅ Сообщение {msg_id} обработано")
                    else:
                        db.execute(
                            text("""
                                UPDATE messages_queue
                                SET status='error', error='LLM не вернул ответ', completed_at=NOW()
                                WHERE id=:id
                            """),
                            {"id": msg_id},
                        )
                        logger.error(f"❌ Сообщение {msg_id}: LLM не ответил")

                    db.commit()
                else:
                    # Нет сообщений — ждём
                    time.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"Ошибка обработки: {e}", exc_info=True)
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Критическая ошибка: {e}", exc_info=True)
            time.sleep(POLL_INTERVAL * 2)


def call_llm(system_prompt: str, user_prompt: str) -> str | None:
    """Вызов LLM через OpenAI-совместимый API."""
    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4096,
        "temperature": 0.7,
    }

    try:
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return None


if __name__ == "__main__":
    create_worker()
