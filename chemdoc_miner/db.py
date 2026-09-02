from __future__ import annotations

import sqlite3
from pathlib import Path

from chemdoc_miner.paths import DATA_DIR, DB_PATH

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS documents (
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  filename TEXT NOT NULL,
  kind TEXT NOT NULL,
  sha256 TEXT,
  page_count INTEGER,
  text_len INTEGER,
  extract_method TEXT,
  extractable INTEGER,
  grade TEXT,
  revised_date TEXT,
  is_canonical INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  grade TEXT NOT NULL UNIQUE,
  grade_display TEXT,
  brand TEXT DEFAULT 'iLENE',
  company TEXT DEFAULT 'Power Dream',
  family TEXT,
  chemical_name TEXT,
  cas TEXT,
  description TEXT,
  highlights TEXT,
  applications TEXT,
  properties TEXT,
  package TEXT,
  storage TEXT,
  revised_date TEXT,
  tds_path TEXT,
  sds_path TEXT,
  tds_text TEXT,
  sds_text TEXT,
  ghs TEXT,
  signal_word TEXT,
  sds_summary TEXT,
  confidence REAL
);

CREATE TABLE IF NOT EXISTS equivalents (
  id INTEGER PRIMARY KEY,
  src_company TEXT NOT NULL,
  src_grade TEXT NOT NULL,
  dst_company TEXT NOT NULL,
  dst_grade TEXT NOT NULL,
  eq_key TEXT,
  chemistry TEXT,
  cas TEXT,
  source_file TEXT,
  eq_kind TEXT,
  priority INTEGER DEFAULT 9,
  needs_review INTEGER DEFAULT 0,
  UNIQUE(src_company, src_grade, dst_company, dst_grade)
);

CREATE TABLE IF NOT EXISTS eq_groups (
  group_id INTEGER PRIMARY KEY,
  eq_key TEXT,
  domain TEXT NOT NULL,
  chemistry TEXT,
  cas TEXT,
  chemistry_group TEXT,
  source_file TEXT NOT NULL,
  member_count INTEGER DEFAULT 0,
  quality TEXT DEFAULT 'complete'
);

CREATE TABLE IF NOT EXISTS eq_members (
  id INTEGER PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES eq_groups(group_id) ON DELETE CASCADE,
  company TEXT NOT NULL,
  grade TEXT NOT NULL,
  grade_raw TEXT,
  role TEXT DEFAULT 'product_code',
  UNIQUE(group_id, company, grade)
);

CREATE INDEX IF NOT EXISTS idx_eq_members_lookup ON eq_members(company, grade);

CREATE TABLE IF NOT EXISTS product_aliases (
  id INTEGER PRIMARY KEY,
  alias TEXT NOT NULL,
  company TEXT,
  grade TEXT NOT NULL,
  UNIQUE(alias, company, grade)
);

CREATE TABLE IF NOT EXISTS aliases (
  id INTEGER PRIMARY KEY,
  alias TEXT NOT NULL,
  company TEXT,
  grade TEXT NOT NULL,
  UNIQUE(alias, company, grade)
);

CREATE VIRTUAL TABLE IF NOT EXISTS products_fts USING fts5(
  grade,
  grade_display,
  chemical_name,
  description,
  highlights,
  applications,
  tds_text,
  cas,
  family,
  content='products',
  content_rowid='id'
);
"""


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def rebuild(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS products_fts;
        DROP TABLE IF EXISTS product_aliases;
        DROP TABLE IF EXISTS eq_members;
        DROP TABLE IF EXISTS eq_groups;
        DROP TABLE IF EXISTS aliases;
        DROP TABLE IF EXISTS equivalents;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS documents;
        """
    )
    init_db(conn)


def ensure_data_dir() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR
