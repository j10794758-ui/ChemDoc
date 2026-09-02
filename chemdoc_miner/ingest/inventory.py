from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from chemdoc_miner.ingest.pdf_text import extract_pdf_text
from chemdoc_miner.ingest.sds import parse_sds
from chemdoc_miner.ingest.tds import parse_tds
from chemdoc_miner.normalize import date_sort_key, grade_from_filename, normalize_grade, parse_date
from chemdoc_miner.paths import DATA_DIR, INVENTORY_PATH, SDS_DIR, TDS_DIR, rel


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def kind_from_path(path: Path) -> str:
    name = path.name.lower()
    if "sds" in name:
        return "sds"
    if "tds" in str(path).lower() or "tds" in name:
        return "tds"
    parent = str(path.parent).lower()
    if "sds" in parent:
        return "sds"
    return "tds"


def scan_documents() -> list[dict[str, Any]]:
    files = sorted(TDS_DIR.glob("*.pdf")) + sorted(SDS_DIR.glob("*.pdf"))
    records: list[dict[str, Any]] = []
    for path in files:
        kind = kind_from_path(path)
        text, pages, method = extract_pdf_text(path)
        if kind == "sds":
            parsed = parse_sds(text, path.name)
        else:
            parsed = parse_tds(text, path.name)
        grade = parsed.get("grade") or grade_from_filename(path.name)
        grade = normalize_grade(grade)
        records.append(
            {
                "path": rel(path),
                "filename": path.name,
                "kind": kind,
                "sha256": sha256_file(path),
                "page_count": pages,
                "text_len": len(text),
                "extract_method": method,
                "extractable": len(text) >= 40,
                "grade": grade,
                "revised_date": parsed.get("revised_date") or parse_date(text),
                "parsed": parsed,
            }
        )
    return records


def mark_canonical(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pick one canonical document per (kind, grade); newest revised_date wins."""
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for rec in records:
        grouped.setdefault((rec["kind"], rec["grade"] or rec["filename"]), []).append(rec)
    for group in grouped.values():
        ranked = sorted(
            group,
            key=lambda r: (
                1 if r["extractable"] else 0,
                date_sort_key(r.get("revised_date")),
                r.get("text_len") or 0,
                -len(r["filename"]),
            ),
            reverse=True,
        )
        for index, rec in enumerate(ranked):
            rec["is_canonical"] = index == 0
            rec["duplicate_of"] = ranked[0]["path"] if index else None
    return records


def write_inventory(records: list[dict[str, Any]]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    slim = []
    for rec in records:
        slim.append({k: rec[k] for k in rec if k != "parsed"})
    INVENTORY_PATH.write_text(json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8")
    report = DATA_DIR / "ingest_report.md"
    tds = [r for r in records if r["kind"] == "tds"]
    sds = [r for r in records if r["kind"] == "sds"]
    empty = [r for r in records if not r["extractable"]]
    tds_canon = [r for r in tds if r["is_canonical"]]
    lines = [
        "# Ingest report",
        "",
        f"- TDS files: {len(tds)} (canonical grades: {len(tds_canon)})",
        f"- SDS files: {len(sds)} (canonical: {sum(1 for r in sds if r['is_canonical'])})",
        f"- Unreadable: {len(empty)}",
        "",
        "## Unreadable files",
    ]
    for rec in empty:
        lines.append(f"- `{rec['filename']}` ({rec['kind']}, {rec['page_count']} pages)")
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return INVENTORY_PATH
