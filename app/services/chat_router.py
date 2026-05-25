"""
Thin agent coordinator — routes user messages to the correct pipeline.

NOT an LLM agent. A plain Python router that:
1. Detects intent via keyword/LLM heuristic
2. Routes to the correct pipeline service
3. Returns structured result + LLM-formatted response
"""

import json
import logging
from typing import Callable

import httpx

from .photo_analysis import PhotoAnalysisService
from .strategy import StrategyService
from .casting import CastingService
from ..config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT

logger = logging.getLogger(__name__)

# Short, direct prompt for the routing LLM — not a personality, just an intent extractor
INTENT_CLASSIFIER_PROMPT = """Classify the user's message into exactly one intent from:
- analyze_photos (user wants photo analysis, scanning, archetype detection)
- get_strategy (user wants a career/development strategy or 30-day plan)
- match_casting (user wants casting recommendations, role matching, role suggestions)
- ask_question (general career question, advice, or anything else)

Return ONLY a single word: the intent name."""

AGENT_OUTPUT_PROMPT = """You are an AI actor career assistant.
Your role: support actors, explain clearly, use actor profile context.
Never hallucinate casting facts. Always use structured tool outputs.
Keep responses concise and actionable.

Context:
{context}

Tool Output:
{tool_output}

Write a concise, supportive response to the user."""


class ChatRouter:
    """Routes user messages to the correct pipeline service."""

    def __init__(self):
        self.intent_map = {
            "analyze_photos": PhotoAnalysisService.analyze_from_urls,
            "get_strategy": self._run_strategy,
            "match_casting": self._run_casting,
            "ask_question": self._run_general_question,
        }

    async def detect_intent(self, message: str) -> str:
        """Detect user intent via LLM (with keyword fallback)."""
        # Quick keyword heuristic first
        msg_lower = message.lower()
        keyword_map = {
            "анализ": "analyze_photos",
            "фото": "analyze_photos",
            "сканиру": "analyze_photos",
            "архетип": "analyze_photos",
            "стратеги": "get_strategy",
            "план": "get_strategy",
            "30": "get_strategy",
            "кастинг": "match_casting",
            "рол": "match_casting",
            "амплуа": "match_casting",
        }
        for kw, intent in keyword_map.items():
            if kw in msg_lower:
                return intent

        # Fallback to LLM classification
        if not LLM_API_KEY:
            return "ask_question"

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "user", "content": f"{INTENT_CLASSIFIER_PROMPT}\n\nMessage: {message}"}
                        ],
                        "max_tokens": 20,
                        "temperature": 0.0,
                    },
                )
                resp.raise_for_status()
                intent_data = resp.json()
                if "choices" in intent_data:
                    intent = intent_data["choices"][0]["message"]["content"].strip().lower()
                elif "content" in intent_data and isinstance(intent_data["content"], list):
                    intent = " ".join([c["text"] for c in intent_data["content"] if c.get("type") == "text"]).strip().lower()
                else:
                    intent = "ask_question"
                if intent in self.intent_map:
                    return intent
        except Exception as e:
            logger.warning(f"Intent classification failed: {e}")

        return "ask_question"

    async def route(self, message: str, user_id: str) -> dict:
        """Route message to pipeline and return result with response."""
        intent = await self.detect_intent(message)
        logger.info(f"Routing intent={intent} for user={user_id}")

        pipeline = self.intent_map[intent]
        tool_output = await pipeline(message=message, user_id=user_id)

        # Format response through LLM
        response = await self._format_response(intent, tool_output, user_id)
        return {
            "response": response,
            "data": tool_output,
            "intent": intent,
        }

    async def _run_strategy(self, message: str, user_id: str) -> dict:
        """Extract profile_id and goals from message, run StrategyService."""
        # In MVP: use a simple heuristic. In production, resolve user_id → profile.
        return {"note": "Strategy generation requires profile_id. Use /api/pipeline/generate-strategy endpoint."}

    async def _run_casting(self, message: str, user_id: str) -> dict:
        """Run casting matching."""
        return {"note": "Casting matching requires profile_id. Use /api/pipeline/chat with structured data."}

    async def _run_general_question(self, message: str, user_id: str) -> dict:
        """Handle general career questions via LLM."""
        if not LLM_API_KEY:
            return {
                "answer": "Я AI-ассистент актёра. Задайте вопрос о кастингах, стратегии развития или анализе фото.",
                "message": message,
            }

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "system", "content": CASTING_DIRECTOR_PROMPT},
                            {"role": "user", "content": message},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if "choices" in data:
                    answer = data["choices"][0]["message"]["content"]
                elif "content" in data and isinstance(data["content"], list):
                    answer = " ".join([c["text"] for c in data["content"] if c.get("type") == "text"])
                else:
                    answer = str(data)
                return {"answer": answer, "message": message}
        except Exception as e:
            logger.error(f"General question failed: {e}", exc_info=True)
            return {
                "answer": "Извините, временные проблемы с AI-модулем. Попробуйте позже.",
                "message": message,
            }

    async def _format_response(self, intent: str, tool_output: dict, user_id: str) -> str:
        """Optionally format tool output into a natural response via LLM."""
        if not LLM_API_KEY:
            return tool_output.get("answer", str(tool_output))

        context_summary = f"User intent detected: {intent}"

        try:
            async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
                resp = await client.post(
                    f"{LLM_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": LLM_MODEL,
                        "messages": [
                            {"role": "user", "content": AGENT_OUTPUT_PROMPT.format(
                                context=context_summary,
                                tool_output=json.dumps(tool_output, ensure_ascii=False, indent=2),
                            )},
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.3,
                    },
                )
                resp.raise_for_status()
                resp_data = resp.json()
                if "choices" in resp_data:
                    return resp_data["choices"][0]["message"]["content"]
                elif "content" in resp_data and isinstance(resp_data["content"], list):
                    return " ".join([c["text"] for c in resp_data["content"] if c.get("type") == "text"])
                else:
                    return str(resp_data)
        except Exception as e:
            logger.warning(f"Response formatting failed: {e}")
            return tool_output.get("answer", json.dumps(tool_output, ensure_ascii=False))
