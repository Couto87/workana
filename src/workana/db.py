"""SQLite helpers for Workana ingestion and OpenAI analysis."""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

DEFAULT_DB = os.environ.get("WORKANA_DB", "data/workana.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workana_id_hash TEXT UNIQUE,
    slug TEXT,
    url TEXT NOT NULL,
    titulo TEXT,
    descricao TEXT,
    budget TEXT,
    postedDate TEXT,
    country TEXT,
    skills TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    score INTEGER,
    analysis_status TEXT DEFAULT 'pending',
    analysis_model TEXT,
    analysis_checked INTEGER DEFAULT 0,
    scope_fit TEXT,
    worthiness INTEGER,
    worthiness_reason TEXT,
    proposal TEXT,
    analysis_tokens INTEGER,
    analysis_raw TEXT,
    analyzed_at TEXT
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(analysis_status);",
    "CREATE INDEX IF NOT EXISTS idx_projects_created ON projects(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);",
]


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    db = db_path or DEFAULT_DB
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    for sql in INDEXES:
        conn.execute(sql)
    conn.commit()
    conn.close()


def upsert_project(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    fields = [
        "workana_id_hash",
        "slug",
        "url",
        "titulo",
        "descricao",
        "budget",
        "postedDate",
        "country",
        "skills",
        "raw_json",
    ]
    placeholders = ", ".join([f":{f}" for f in fields])
    update_clause = ", ".join([f"{f}=excluded.{f}" for f in fields if f != "workana_id_hash"])
    sql = f"""
    INSERT INTO projects ({', '.join(fields)})
    VALUES ({placeholders})
    ON CONFLICT(workana_id_hash) DO UPDATE SET {update_clause}
    """
    conn.execute(sql, row)
    conn.commit()


def fetch_pending(conn: sqlite3.Connection, limit: int = 10) -> Iterable[sqlite3.Row]:
    sql = """
    SELECT * FROM projects
    WHERE analysis_status = 'pending'
    ORDER BY created_at DESC
    LIMIT ?
    """
    return conn.execute(sql, (limit,)).fetchall()


def save_analysis(
    conn: sqlite3.Connection,
    workana_id_hash: str,
    *,
    analysis_status: str,
    model: Optional[str] = None,
    scope_fit: Optional[str] = None,
    worthiness: Optional[int] = None,
    worthiness_reason: Optional[str] = None,
    proposal: Optional[str] = None,
    tokens: Optional[int] = None,
    analysis_raw: Optional[Dict[str, Any]] = None,
) -> None:
    score = None
    if worthiness is not None:
        score = max(0, worthiness)
        if (scope_fit or "").lower().startswith("yes"):
            score += 2
    sql = """
    UPDATE projects
    SET
        analysis_status = :analysis_status,
        analysis_model = :analysis_model,
        scope_fit = :scope_fit,
        worthiness = :worthiness,
        worthiness_reason = :worthiness_reason,
        proposal = :proposal,
        analysis_tokens = :analysis_tokens,
        analysis_raw = :analysis_raw,
        score = COALESCE(:score, score),
        analysis_checked = CASE WHEN :analysis_status = 'complete' THEN 1 ELSE analysis_checked END,
        analyzed_at = datetime('now')
    WHERE workana_id_hash = :hash
    """
    conn.execute(
        sql,
        {
            "analysis_status": analysis_status,
            "analysis_model": model,
            "scope_fit": scope_fit,
            "worthiness": worthiness,
            "worthiness_reason": worthiness_reason,
            "proposal": proposal,
            "analysis_tokens": tokens,
            "analysis_raw": json.dumps(analysis_raw or {}),
            "score": score,
            "hash": workana_id_hash,
        },
    )
    conn.commit()


__all__ = [
    "DEFAULT_DB",
    "connect",
    "init_db",
    "upsert_project",
    "fetch_pending",
    "save_analysis",
]
