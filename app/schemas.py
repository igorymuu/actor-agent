from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


# --- Auth ---
class UserRegister(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: Optional[int] = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    subscription_tier: str
    subscription_expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Profile ---
class ActorProfileCreate(BaseModel):
    photo_url: Optional[str] = None
    goals: Optional[str] = None
    experience_level: Optional[str] = None
    bio: Optional[str] = None


class ActorProfileResponse(BaseModel):
    id: UUID
    archetype: Optional[str]
    archetypes_secondary: List[str] = []
    age_range: Optional[str]
    strengths: List[str] = []
    weaknesses: List[str] = []
    actor_type: Optional[str]
    goals: Optional[str]
    experience_level: Optional[str]
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisResponse(BaseModel):
    """Result of photo analysis"""
    archetype: str
    archetypes_secondary: List[str]
    age_range: str
    strengths: List[str]
    weaknesses: List[str]
    actor_type: str
    analysis_text: str


class StrategyResponse(BaseModel):
    id: UUID
    period_days: int
    content: dict
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    task_type: str = "development"
    due_date: Optional[date] = None
    telegram_id: int = 0


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    task_type: str
    due_date: Optional[date]
    is_completed: bool
    created_at: datetime

    class Config:
        from_attributes = True


# --- Admin ---
class AdminLogin(BaseModel):
    login: str
    password: str


class SiteContentUpdate(BaseModel):
    data: dict


class SiteContentVisibility(BaseModel):
    is_visible: bool


class SiteContentReorder(BaseModel):
    block_order: list[str]  # list of block_keys in new order


class SiteContentResponse(BaseModel):
    id: UUID
    block_key: str
    data: dict
    is_visible: bool
    sort_order: int
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadResponse(BaseModel):
    id: UUID
    name: Optional[str]
    phone: Optional[str]
    source: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    telegram_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    actions: list[dict] = []


# --- Pipeline schemas ---

class PhotoAnalysisRequest(BaseModel):
    urls: list[str]
    profile_id: str


class PhotoAnalysisResult(BaseModel):
    archetypes: list[str]
    strengths: list[str]
    weaknesses: list[str]
    emotional_range: int
    camera_presence: int
    naturalness: int
    casting_clarity: str  # LOW / MEDIUM / HIGH
    face_structure: str
    face_energy: str
    perceived_age: str
    primary_archetype: str
    secondary_archetype: str
    primary_roles: list[str]
    secondary_roles: list[str]
    actor_score: dict
    casting_probability: str
    monetization_options: list[str]
    recommendations: list[str]
    summary: str
    detailed_analysis: str = ""  # Развёрнутый PERSONAL PORTRAIT 300-500 слов


class StrategyRequest(BaseModel):
    profile_id: str
    goals: str | None = None


class StrategyPlan(BaseModel):
    weekly_goals: list[dict]
    long_term_goals: list[str]
    recommended_actions: list[str]
    metrics_to_track: list[str]


class CastingRequest(BaseModel):
    profile_id: str


class CastingCreate(BaseModel):
    title: str
    event_date: str = ""
    event_time: str = ""
    location: str = ""
    notes: str = ""
    description: str = ""
    telegram_id: int


class CastingOut(BaseModel):
    id: UUID
    title: str
    event_date: str = ""
    event_time: str = ""
    location: str = ""
    notes: str = ""
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class CastingRecommendation(BaseModel):
    role_types: list[str]
    recommended_casting_types: list[str]
    compatibility_score: float
    suggestions: list[str]


class PipelineChatRequest(BaseModel):
    message: str
    user_id: str


class PipelineChatResponse(BaseModel):
    response: str
    data: dict | None = None


class PipelinePhotoUploadResponse(BaseModel):
    status: str
    result: PhotoAnalysisResult | None = None
    analysis_id: str | None = None
