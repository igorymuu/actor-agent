from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from ..database import get_db
from ..models import User, Document
from ..schemas import StrategyResponse
from ..auth import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/")
def list_documents(user: User = Depends(get_current_user)):
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "title": d.title,
            "file_url": d.file_url,
            "created_at": d.created_at.isoformat(),
        }
        for d in user.documents
    ]


@router.post("/generate")
def generate_document(
    doc_type: str = "contract",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Заглушка генерации документов. Позже — шаблоны + LLM."""
    if user.subscription_tier not in ("premium",):
        raise HTTPException(
            status_code=403,
            detail="Document generation requires Premium subscription",
        )

    doc = Document(
        user_id=user.id,
        doc_type=doc_type,
        title=f"Template {doc_type} - {user.name or user.email}",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {
        "id": str(doc.id),
        "doc_type": doc.doc_type,
        "title": doc.title,
        "status": "generated (template placeholder)",
    }
