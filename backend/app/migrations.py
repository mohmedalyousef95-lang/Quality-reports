"""Lightweight additive migrations.

Base.metadata.create_all creates missing tables but never alters existing
ones. This adds any newly-introduced columns to already-created tables,
idempotently, on both SQLite (local) and Postgres (production).
"""
from sqlalchemy import inspect, text

from .database import engine

# (table, column, SQL column type with default)
NEW_COLUMNS = [
    ("reports", "updated_at", "TIMESTAMP"),
    ("reports", "status", "VARCHAR DEFAULT 'draft'"),
    ("reports", "completed_at", "TIMESTAMP"),
    ("reports", "contractor", "VARCHAR DEFAULT ''"),
    ("report_photos", "caption", "VARCHAR DEFAULT ''"),
    ("reports", "visit_type", "VARCHAR DEFAULT ''"),
    ("reports", "during_readiness_plan", "VARCHAR DEFAULT ''"),
    ("reports", "team_count", "INTEGER"),
    ("reports", "oversight_supervisor_present", "VARCHAR DEFAULT ''"),
    ("reports", "team_types", "VARCHAR DEFAULT ''"),
    ("reports", "important_notes", "TEXT DEFAULT ''"),
    ("report_notes", "status", "VARCHAR DEFAULT ''"),
]


def run_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, coltype in NEW_COLUMNS:
            if table not in existing_tables:
                continue  # create_all will build it fresh with all columns
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column in cols:
                continue
            conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {coltype}'))
