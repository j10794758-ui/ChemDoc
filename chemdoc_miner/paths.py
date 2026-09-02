from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_DIR = ROOT / "doc"
TDS_DIR = DOC_DIR / "02 TDS-20260824T012836Z-1-001" / "02 TDS" / "Power Dream America TDS"
SDS_DIR = DOC_DIR / "01 SDS-20260824T012835Z-1-001" / "01 SDS"
XLS_DIR = DOC_DIR / "Competitive Landscape-20260824T012835Z-1-001" / "Competitive Landscape"
DATA_DIR = ROOT / "data" / "derived"
DB_PATH = DATA_DIR / "chemdoc.db"
INVENTORY_PATH = DATA_DIR / "inventory.json"
WEB_DIR = ROOT / "web"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def abs_from_rel(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    if not str(candidate).startswith(str(ROOT.resolve())):
        raise ValueError("path escapes project root")
    return candidate
