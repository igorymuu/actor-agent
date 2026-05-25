import os
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SiteContent, Lead
from ..schemas import (
    AdminLogin,
    SiteContentUpdate,
    SiteContentVisibility,
    SiteContentReorder,
    SiteContentResponse,
    LeadResponse,
)
from ..config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/admin", tags=["admin"])

# Admin credentials from env
ADMIN_LOGIN = os.getenv("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
security = HTTPBearer(auto_error=False)


# --- JWT helpers for admin ---

def create_admin_token() -> str:
    expire = datetime.utcnow().timestamp() + ACCESS_TOKEN_EXPIRE_MINUTES * 60
    to_encode = {"sub": "admin", "role": "admin", "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin" or payload.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload


# --- Admin login ---

@router.post("/login")
def admin_login(data: AdminLogin):
    if data.login != ADMIN_LOGIN or data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    token = create_admin_token()
    return {"access_token": token, "token_type": "bearer"}


# --- Site content CRUD ---

@router.get("/content", response_model=list[SiteContentResponse])
def get_all_content(
    db: Session = Depends(get_db),
    _=Depends(verify_admin_token),
):
    blocks = db.query(SiteContent).order_by(SiteContent.sort_order).all()
    return blocks


@router.put("/content/{block_key}", response_model=SiteContentResponse)
def update_content(
    block_key: str,
    body: SiteContentUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_admin_token),
):
    block = db.query(SiteContent).filter(SiteContent.block_key == block_key).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    block.data = body.data
    block.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(block)
    return block


@router.put("/content/{block_key}/visibility", response_model=SiteContentResponse)
def toggle_visibility(
    block_key: str,
    body: SiteContentVisibility,
    db: Session = Depends(get_db),
    _=Depends(verify_admin_token),
):
    block = db.query(SiteContent).filter(SiteContent.block_key == block_key).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    block.is_visible = body.is_visible
    block.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(block)
    return block


@router.put("/content-reorder")
def reorder_content(
    body: dict,
    db: Session = Depends(get_db),
    _=Depends(verify_admin_token),
):
    order_list = body.get("block_order", [])
    blocks = {b.block_key: b for b in db.query(SiteContent).all()}
    for idx, key in enumerate(order_list):
        if key in blocks:
            blocks[key].sort_order = idx
    db.commit()
    return {"ok": True}


# --- Seed default content ---

DEFAULT_CONTENT = {
    "hero": {
        "title": 'Вы не получаете роли, потому что вас не <span class="bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">понимают</span>',
        "subtitle": "AI-анализ кастинга. Откройте свой архетип. Оптимизируйте портфолио.",
        "badge_text": "AI Casting System · v2.1",
        "button_text": "Запустить AI-анализ",
        "footer_text": "Бесплатный доступ · Карта не нужна",
        "stats": [
            {"value": "12K+", "label": "Актёров проанализировано"},
            {"value": "89%", "label": "Средний рост чёткости"},
            {"value": "47", "label": "Измерений анализа"},
        ],
    },
    "how_it_works": {
        "title": "Три шага к<span class='bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent'>ясность в кастинге</span>",
        "badge": "Как это работает",
        "steps": [
            {"num": "01", "title": "Загрузить материалы", "desc": "Загрузите ваше фото на роль и, при необходимости, видеопробу. Система принимает любой формат."},
            {"num": "02", "title": "AI Analysis", "desc": "47-мерное сканирование по архетипу, присутствию, чёткости и соответствию кастингу."},
            {"num": "03", "title": "Получить стратегию", "desc": "Получите полный аналитический отчёт с 90-дневным планом действий, адаптированным под ваш тип."},
        ],
    },
    "archetypes": {
        "badge": "Превью AI-анализа",
        "title": 'Узнайте, что AI обнаружит <span class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">в вашем профиле</span>',
        "description": "Это пример анализа. Когда вы запустите сканирование, Neyrix оценит вас по 47 измерениям и предоставит полный отчёт.",
    },
    "problem": {
        "title": "Вы теряете роли из-за:",
        "description": "AI выявил 3 критических пробела в вашем профиле",
        "problems": [
            {"title": "Нечёткий тип", "desc": "Кастинг-директоры не могут вас категоризировать за 3 секунды."},
            {"title": "Слабое портфолио", "desc": "Ваши материалы не отражают ваш истинный архетип или диапазон."},
            {"title": "Непоследовательный образ", "desc": "Ваши фото, шоурел и присутствие рассказывают 3 разные истории."},
        ],
    },
    "image_gap": {
        "title": 'Ваше текущее фото ≠ <span class="bg-gradient-to-r from-cyan-400 to-blue-500 bg-clip-text text-transparent">ваш кастинговый потенциал</span>',
        "description": "Ваши текущие фото снижают ваши шансы получить роль.",
    },
    "solution": {
        "badge": "Решение",
        "title": 'Интеллектуальная <span class="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">кастинговая стратегия</span>',
        "description": "Neyrix заменяет догадки данными. Каждое решение, каждая заявка, каждая самопроба — оптимизированы AI, который понимает индустрию кастинга.",
    },
    "pricing": {
        "badge": "Тарифы",
        "title": "Выберите уровень анализа",
        "tiers": [
            {"name": "FREE", "price": "0 ₽", "desc": "Сканирование профиля", "features": ["Превью архетипа", "3 базовых метрики", "Выявление проблем"]},
            {"name": "PRO", "price": "2 900 ₽", "desc": "Полный отчёт", "features": ["Анализ по 47 измерениям", "Полная расшифровка", "90-дневная стратегия", "Чеклист улучшений"]},
            {"name": "AI AGENT", "price": "7 900 ₽", "desc": "AI коуч в комплекте", "features": ["Все функции PRO", "Личный AI коуч", "Уведомления Telegram", "Кастинговые возможности"]},
        ],
    },
    "final_cta": {
        "badge": "Готовы?",
        "title": 'Хватит гадать. <span class="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">Начните получать роли.</span>',
        "description": "12 000+ актёров уже использовали Neyrix, чтобы прояснить своё позиционирование. Ваш анализ займёт 60 секунд. Карьера изменится сегодня.",
        "button_text": "Начать бесплатный анализ",
        "footer_text": "Бесплатно · Карта не нужна · 60 секунд",
    },
    "footer": {
        "brand": "NEYRIX",
        "tagline": "AI-система анализа кастинга",
        "links": [
            {"label": "Конфиденциальность", "href": "#"},
            {"label": "Условия", "href": "#"},
            {"label": "Контакты", "href": "#"},
        ],
        "copyright": "© 2025 Neyrix · Все права защищены",
    },
}


@router.post("/seed")
def seed_content(db: Session = Depends(get_db)):
    existing = db.query(SiteContent).count()
    if existing > 0:
        return {"message": "Content already seeded", "count": existing}

    for idx, (key, data) in enumerate(DEFAULT_CONTENT.items()):
        block = SiteContent(
            id=uuid4(),
            block_key=key,
            data=data,
            is_visible=True,
            sort_order=idx,
        )
        db.add(block)
    db.commit()
    return {"message": "Content seeded successfully", "count": len(DEFAULT_CONTENT)}


# --- Image management ---

UPLOAD_DIR = Path("/home/openclaw/.openclaw/workspace/actor-ai/public/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}


@router.post("/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    _=Depends(verify_admin_token),
):
    ext = Path(file.filename).suffix.lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Extension {ext} not allowed. Allowed: {ALLOWED_EXTENSIONS}")

    # Generate unique filename
    filename = f"{uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    return {"filename": filename, "url": f"/uploads/{filename}"}


@router.get("/images")
def list_images(_=Depends(verify_admin_token)):
    if not UPLOAD_DIR.exists():
        return {"images": []}
    files = []
    for p in sorted(UPLOAD_DIR.iterdir()):
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
            files.append({
                "filename": p.name,
                "url": f"/uploads/{p.name}",
                "size": p.stat().st_size,
                "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
            })
    return {"images": files}


@router.delete("/images/{filename}")
def delete_image(
    filename: str,
    _=Depends(verify_admin_token),
):
    filepath = UPLOAD_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    filepath.unlink()
    return {"ok": True, "filename": filename}


# --- Leads ---

@router.get("/leads", response_model=list[LeadResponse])
def get_leads(
    db: Session = Depends(get_db),
    _=Depends(verify_admin_token),
):
    return db.query(Lead).order_by(Lead.created_at.desc()).all()
