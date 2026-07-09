import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PHOTOS_DIR = DATA_DIR / "photos"
DB_PATH = DATA_DIR / "app.db"
TEMPLATE_PATH = Path(__file__).resolve().parent / "assets" / "template.pptx"
SEED_XLSX_PATH = Path(__file__).resolve().parent / "assets" / "schools_seed.xlsx"

# Best-effort local dirs (only needed for the SQLite/local-disk fallback).
# On read-only or restricted-user hosts these may fail; that's fine when
# DATABASE_URL + R2 are configured, so don't crash startup over it.
for _d in (DATA_DIR, PHOTOS_DIR):
    try:
        _d.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

APP_PASSWORD = os.environ.get("APP_PASSWORD", "changeme")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Set AUTH_DISABLED=true to open the app without a login step (no password).
AUTH_DISABLED = os.environ.get("AUTH_DISABLED", "").strip().lower() in ("1", "true", "yes")

# Database: use DATABASE_URL (Neon Postgres) in production, fall back to local SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH}")

# Photo storage: use Cloudflare R2 (S3-compatible) when configured, else local disk.
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")

USE_R2 = bool(R2_ENDPOINT_URL and R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY and R2_BUCKET)
