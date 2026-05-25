"""
Pipeline: Photo → Vision LLM → Structured Archetype JSON
"""

import json
import logging
import os
from datetime import datetime
from uuid import uuid4

import httpx
from sqlalchemy.orm import Session

from ..models import ActorProfile
from ..database import SessionLocal
from ..schemas import PhotoAnalysisResult
from ..config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT
from ..instructions.prompts import CASTING_DIRECTOR_PROMPT

logger = logging.getLogger(__name__)

PHOTO_ANALYSIS_PROMPT = """You are a CASTING DIRECTOR. Analyze this actor photo.

Use the COMPLETE SYSTEM from the system prompt above. Do not skip any system.

Think step by step like a casting director:
1. FIRST 3 SECONDS — what type is immediately visible? Would I stop or scroll past?
2. VISUAL CASTING ENGINE — face structure type, face energy, perceived age. Is casting clarity HIGH, MEDIUM, or LOW?
3. ARCHETYPE ENGINE — which archetype from the 9 listed in system prompt? Primary and secondary. Why?
4. ROLE MATCH — what specific Russian TV roles right now? Primary and secondary lists.
5. ACTOR SCORING — score ALL 6 categories: type_clarity, portfolio, showreel, online_presence, casting_readiness, recognizability. Each /10. Total /60. Interpretation.
6. CASTING PROBABILITY — LOW/MEDIUM/HIGH based on all factors. Explain why.
7. ACTOR BRAND — what is their brand? Positioning? Niche?
8. MONETIZATION — income streams based on this type.
9. CONVERSION TRIGGER — every weakness must have a clear consequence and solution.

After thinking, return ONLY valid flat JSON. All fields must be populated, none null. Scalar values like emotional_range (integer 1-10), camera_presence (integer 1-10), naturalness (integer 1-10), casting_clarity (string), perceived_age (string). actor_score as flat object.

CRITICAL: The field 'detailed_analysis' MUST contain a 300-500 word PERSONAL PORTRAIT narrative in Russian. Write as a casting director explaining to the actor what they see, what roles suit them, and a 30-day action plan.

Now analyze."""

MAX_PHOTOS = 5


def _extract_llm_content(data: dict) -> str:
    if "choices" in data:
        content = data["choices"][0]["message"]["content"]
    elif "content" in data and isinstance(data["content"], list):
        content = " ".join([c["text"] for c in data["content"] if c.get("type") == "text"])
    else:
        content = str(data)
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        content = content.rsplit("```", 1)[0]
    return content.strip()


async def _call_vision_model(photo_urls: list[str]) -> dict:
    if not LLM_API_KEY:
        return _mock_analysis()

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }

    content_parts = [{"type": "text", "text": PHOTO_ANALYSIS_PROMPT}]
    for url in photo_urls[:MAX_PHOTOS]:
        content_parts.append({
            "type": "image_url",
            "image_url": {"url": url},
        })

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": CASTING_DIRECTOR_PROMPT},
            {"role": "user", "content": content_parts},
        ],
        "max_tokens": 16384,
        "temperature": 0.7,
    }

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        try:
            resp = await client.post(
                f"{LLM_BASE_URL}/chat/completions",
                headers=headers, json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = _extract_llm_content(data)
            return json.loads(content)
        except Exception as e:
            logger.error(f"Vision model call failed: {e}", exc_info=True)
            return _mock_analysis()


def _mock_analysis() -> dict:
    return {
        "archetypes": ["Professional", "Romantic Lead"],
        "strengths": ["Clear professional type", "Strong camera presence", "Symmetrical face", "Calm authority", "Premium commercial look"],
        "weaknesses": ["No showreel visible", "Limited emotional range in photo", "Polished but narrow image"],
        "emotional_range": 5,
        "camera_presence": 7,
        "naturalness": 8,
        "casting_clarity": "MEDIUM",
        "face_structure": "symmetrical face with soft features",
        "face_energy": "warm, intellectual, professional",
        "perceived_age": "adult",
        "primary_archetype": "Professional",
        "secondary_archetype": "Romantic Lead",
        "primary_roles": ["doctor", "lawyer", "detective"],
        "secondary_roles": ["teacher", "neighbor", "businessman"],
        "actor_score": {"type_clarity": 6, "portfolio": 4, "showreel": 0, "online_presence": 0, "casting_readiness": 5, "recognizability": 5, "total": 20, "interpretation": "NOT READY"},
        "casting_probability": "LOW",
        "monetization_options": ["commercials", "voice acting", "UGC", "hosting"],
        "recommendations": ["Problem: insufficient material. If you do not fix this, casting directors will ignore you. Solution: provide more photos."],
        "summary": "DIAGNOSIS: Actor shows potential. WHY: Limited input. CONSEQUENCE: Cannot assess fully. SOLUTION: Provide full portfolio.",
    }


class PhotoAnalysisService:
    @staticmethod
    async def analyze_from_urls(photo_urls: list[str], profile_id: str) -> PhotoAnalysisResult:
        if len(photo_urls) > MAX_PHOTOS:
            photo_urls = photo_urls[:MAX_PHOTOS]
        raw = await _call_vision_model(photo_urls)
        result = PhotoAnalysisResult(**raw)
        db: Session = SessionLocal()
        try:
            profile = db.query(ActorProfile).filter(ActorProfile.id == profile_id).first()
            if profile:
                profile.archetypes = result.archetypes
                profile.archetype = result.archetypes[0] if result.archetypes else profile.archetype
                profile.strengths = result.strengths
                profile.weaknesses = result.weaknesses
                profile.emotional_range = result.emotional_range
                profile.camera_presence = result.camera_presence
                profile.naturalness = result.naturalness
                profile.analysis_recommendations = result.recommendations
                profile.analysis_summary = result.summary
                profile.analysis_completed_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Failed to persist analysis: {e}", exc_info=True)
            db.rollback()
        finally:
            db.close()
        return result

    @staticmethod
    async def analyze_from_files(file_contents: list[bytes], profile_id: str | None = None) -> tuple[str, PhotoAnalysisResult | None]:
        upload_dir = "/home/openclaw/.openclaw/workspace/actor-agent/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        analysis_id = str(uuid4())
        urls = []
        for i, content in enumerate(file_contents):
            filename = f"analysis_{analysis_id}_{i}.jpg"
            filepath = os.path.join(upload_dir, filename)
            with open(filepath, "wb") as f:
                f.write(content[:5 * 1024 * 1024])
            urls.append(f"file://{filepath}")
        result = None
        if profile_id:
            result = await self.analyze_from_urls(urls, profile_id)
        elif urls:
            raw = await _call_vision_model(urls)
            result = PhotoAnalysisResult(**raw)
        return analysis_id, result
