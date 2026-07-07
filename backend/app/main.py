import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .services.excel_import import import_schools, seed_checklist_items
from .routers import auth_router, schools, checklist, reports

Base.metadata.create_all(bind=engine)
import_schools()
seed_checklist_items()

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

default_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
FRONTEND_DIST = Path(os.environ.get("FRONTEND_DIST_PATH", default_frontend_dist))
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
