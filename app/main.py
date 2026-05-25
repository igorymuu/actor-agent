from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import engine, Base
from .routers.auth_router import router as auth_router
from .routers.profile_router import router as profile_router
from .routers.strategy_router import router as strategy_router
from .routers.tasks_router import router as tasks_router
from .routers.casting_router import router as casting_router
from .routers.chat_router import router as chat_router
from .routers.documents_router import router as documents_router
from .routers.admin_router import router as admin_router
from .routers.pipeline_router import router as pipeline_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Acting Agent API",
    description="Digital acting agent platform",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
static_dir = Path(__file__).parent.parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# API routers (must be before the catch-all)
app.include_router(auth_router, prefix="/api")
app.include_router(profile_router, prefix="/api")
app.include_router(strategy_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(casting_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(documents_router, prefix="/api")

# Admin router
app.include_router(admin_router, prefix="/api")

# Pipeline router
app.include_router(pipeline_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.get("/")
def serve_index():
    return FileResponse(str(static_dir / "index.html"))
