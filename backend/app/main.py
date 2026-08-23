import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .migrations import run_migrations
from .services.excel_import import import_schools, seed_checklist_items, seed_note_suggestions
from .routers import auth_router, schools, checklist, reports, reviews

Base.metadata.create_all(bind=engine)
run_migrations()
import_schools()
seed_checklist_items()
seed_note_suggestions()

app = FastAPI(title="تقارير الجودة")

frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(schools.router)
app.include_router(checklist.router)
app.include_router(reports.router)
app.include_router(reviews.router)

default_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST_PATH", default_frontend_dist))

if FRONTEND_DIST.exists():
    # Serve built static assets (hashed JS/CSS) under /assets.
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_file = FRONTEND_DIST / "index.html"

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Serve a real file when it exists (favicon, manifest, sw.js, icons…),
        # otherwise fall back to index.html so client-side routes work on a
        # full page load / refresh (SPA fallback).
        candidate = FRONTEND_DIST / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_file)
