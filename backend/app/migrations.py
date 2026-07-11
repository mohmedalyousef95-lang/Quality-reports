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
