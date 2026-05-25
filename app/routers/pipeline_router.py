from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, ActorProfile
from ..schemas import (
    PhotoAnalysisRequest,
    PhotoAnalysisResult,
    StrategyRequest,
    StrategyPlan,
    CastingRequest,
    CastingRecommendation,
    PipelineChatRequest,
    PipelineChatResponse,
    PipelinePhotoUploadResponse,
)
from ..auth import get_current_user
from ..services.photo_analysis import PhotoAnalysisService
from ..services.strategy import StrategyService
from ..services.casting import CastingService
from ..services.chat_router import ChatRouter

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

chat_router = ChatRouter()


@router.get("/health")
def pipeline_health():
    """Health check for pipeline subsystem."""
    return {"status": "ok", "services": ["photo_analysis", "strategy", "casting", "chat_router"]}


@router.post("/analyze-photo-url", response_model=PhotoAnalysisResult)
async def analyze_photo_url(
    data: PhotoAnalysisRequest,
    user: User = Depends(get_current_user),
):
    """Analyze actor photos from URLs. Requires auth. Returns structured analysis."""
    result = await PhotoAnalysisService.analyze_from_urls(data.urls, data.profile_id)
    return result


@router.post("/analyze-photo", response_model=PipelinePhotoUploadResponse)
async def analyze_photo_upload(
    files: list[UploadFile] = File(..., description="Up to 5 photo files"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload photos for analysis (multipart/form-data). Creates profile if needed."""
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 photos allowed")

    # Ensure profile exists
    if not user.profile:
        profile = ActorProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    else:
        profile = user.profile

    # Read file contents
    file_contents = []
    for f in files:
        content = await f.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"Empty file: {f.filename}")
        file_contents.append(content)

    analysis_id, result = await PhotoAnalysisService.analyze_from_files(
        file_contents, str(profile.id)
    )

    return PipelinePhotoUploadResponse(
        status="completed" if result else "error",
        result=result,
        analysis_id=analysis_id,
    )


@router.post("/generate-strategy", response_model=StrategyPlan)
async def generate_strategy(
    data: StrategyRequest,
    user: User = Depends(get_current_user),
):
    """Generate a 30-day strategy plan for the actor profile."""
    try:
        plan = await StrategyService.generate(
            profile_id=data.profile_id,
            goals=data.goals,
            user_id=str(user.id),
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/match-casting", response_model=CastingRecommendation)
def match_casting(
    data: CastingRequest,
    user: User = Depends(get_current_user),
):
    """Get casting recommendations for the actor profile."""
    try:
        return CastingService.get_recommendations(data.profile_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/chat", response_model=PipelineChatResponse)
async def pipeline_chat(
    data: PipelineChatRequest,
    user: User = Depends(get_current_user),
):
    """Route a message through the chat coordinator."""
    result = await chat_router.route(data.message, data.user_id)
    return PipelineChatResponse(
        response=result["response"],
        data=result.get("data"),
    )
