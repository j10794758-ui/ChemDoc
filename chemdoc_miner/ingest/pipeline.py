from __future__ import annotations

import json
import re
import sqlite3
from collections import defaultdict
from typing import Any

from chemdoc_miner.db import connect, rebuild
from chemdoc_miner.ingest.equivalence import iter_alias_hints, load_equivalence_groups, load_equivalence_rows
from chemdoc_miner.ingest.inventory import mark_canonical, scan_documents, write_inventory
from chemdoc_miner.normalize import normalize_grade


def run_ingest(*, rebuild_db: bool = True) -> dict[str, Any]:
    records = mark_canonical(scan_documents())
    write_inventory(records)
    conn = connect()
    if rebuild_db:
        rebuild(conn)
    _insert_documents(conn, records)
    _insert_products(conn, records)
    eq_groups = load_equivalence_groups()
    _insert_eq_groups(conn, eq_groups)
    eq_rows = load_equivalence_rows()
    _insert_equivalents(conn, eq_rows)
    _insert_aliases(conn, records, eq_groups)
    _rebuild_fts(conn)
    conn.commit()
    stats = {
        "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "eq_groups": conn.execute("SELECT COUNT(*) FROM eq_groups").fetchone()[0],
        "eq_members": conn.execute("SELECT COUNT(*) FROM eq_members").fetchone()[0],
        "equivalents": conn.execute("SELECT COUNT(*) FROM equivalents").fetchone()[0],
        "aliases": conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0],
        "unreadable": sum(1 for r in records if not r["extractable"]),
    }
    conn.close()
    return stats


def _insert_documents(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> None:
    conn.executemany(
        """
        INSERT INTO documents(path, filename, kind, sha256, page_count, text_len,
            extract_method, extractable, grade, revised_date, is_canonical)
        VALUES (:path, :filename, :kind, :sha256, :page_count, :text_len,
            :extract_method, :extractable, :grade, :revised_date, :is_canonical)
        """,
        [
            {
                **{k: rec[k] for k in (
                    "path", "filename", "kind", "sha256", "page_count", "text_len",
                    "extract_method", "extractable", "grade", "revised_date",
                )},
                "is_canonical": 1 if rec.get("is_canonical") else 0,
                "extractable": 1 if rec.get("extractable") else 0,
            }
            for rec in records
        ],
    )


def _insert_products(conn: sqlite3.Connection, records: list[dict[str, Any]]) -> None:
    by_grade: dict[str, dict[str, Any]] = {}
    extras: dict[str, dict[str, Any]] = defaultdict(dict)
    for rec in records:
        grade = rec.get("grade")
        if not grade:
            continue
        parsed = rec.get("parsed") or {}
        bucket = extras[grade]
        if rec["kind"] == "tds" and rec.get("is_canonical"):
            by_grade[grade] = {
                "grade": grade,
                "grade_display": parsed.get("grade_display") or f"iLENE {grade}",
                "brand": "iLENE",
                "company": "Power Dream",
                "family": parsed.get("family") or "other",
                "chemical_name": parsed.get("chemical_name"),
                "cas": parsed.get("cas"),
                "description": parsed.get("description"),
                "highlights": json.dumps(parsed.get("highlights") or [], ensure_ascii=False),
                "applications": json.dumps(parsed.get("applications") or [], ensure_ascii=False),
                "properties": json.dumps(parsed.get("properties") or {}, ensure_ascii=False),
                "package": parsed.get("package"),
                "storage": parsed.get("storage"),
                "revised_date": rec.get("revised_date"),
                "tds_path": rec["path"],
                "tds_text": parsed.get("raw_text") or "",
                "confidence": parsed.get("confidence") or 0,
            }
        if rec["kind"] == "sds" and rec.get("is_canonical"):
            bucket["sds_path"] = rec["path"]
            bucket["sds_text"] = parsed.get("raw_text") or ""
            bucket["ghs"] = json.dumps(parsed.get("ghs") or [], ensure_ascii=False)
            bucket["signal_word"] = parsed.get("signal_word")
            bucket["sds_summary"] = json.dumps(parsed.get("sds_summary") or {}, ensure_ascii=False)
            bucket["sds_revised_date"] = rec.get("revised_date")
            if parsed.get("cas_list") and not by_grade.get(grade, {}).get("cas"):
                bucket["cas"] = parsed["cas_list"][0]
            if parsed.get("chemical_name") and not by_grade.get(grade, {}).get("chemical_name"):
                bucket["chemical_name"] = parsed["chemical_name"]
    rows = []
    for grade, product in by_grade.items():
        product.update({k: v for k, v in extras[grade].items() if v})
        product.setdefault("sds_path", None)
        product.setdefault("sds_text", None)
        product.setdefault("ghs", None)
        product.setdefault("signal_word", None)
        product.setdefault("sds_summary", None)
        rows.append(product)
    # SDS-only grades (no TDS)
    for grade, extra in extras.items():
        if grade in by_grade:
            continue
        if not extra.get("sds_path"):
            continue
        if len(grade) > 40:
            continue
        rows.append(
            {
                "grade": grade,
                "grade_display": f"iLENE {grade}",
                "brand": "iLENE",
                "company": "Power Dream",
                "family": "other",
                "chemical_name": None,
                "cas": extra.get("cas"),
                "description": None,
                "highlights": "[]",
                "applications": "[]",
                "properties": "{}",
                "package": None,
                "storage": None,
                "revised_date": None,
                "tds_path": None,
                "tds_text": None,
                "confidence": 0.3,
                **extra,
            }
        )
    conn.executemany(
        """
        INSERT INTO products(
          grade, grade_display, brand, company, family, chemical_name, cas,
          description, highlights, applications, properties, package, storage,
          revised_date, tds_path, sds_path, tds_text, sds_text, ghs, signal_word, sds_summary, confidence
        ) VALUES (
          :grade, :grade_display, :brand, :company, :family, :chemical_name, :cas,
          :description, :highlights, :applications, :properties, :package, :storage,
          :revised_date, :tds_path, :sds_path, :tds_text, :sds_text, :ghs, :signal_word, :sds_summary, :confidence
        )
        """,
        rows,
    )


def _insert_eq_groups(conn: sqlite3.Connection, groups: list[Any]) -> None:
    for group in groups:
        cur = conn.execute(
            """
            INSERT INTO eq_groups(eq_key, domain, chemistry, cas, chemistry_group, source_file, member_count, quality)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group.eq_key,
                group.domain,
                group.chemistry,
                group.cas,
                group.chemistry_group,
                group.source_file,
                group.member_count,
                group.quality,
            ),
        )
        gid = cur.lastrowid
        conn.executemany(
            """
            INSERT OR IGNORE INTO eq_members(group_id, company, grade, grade_raw, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(gid, m.company, m.grade, m.grade_raw, m.role) for m in group.members],
        )


def _insert_equivalents(conn: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO equivalents(
          src_company, src_grade, dst_company, dst_grade, eq_key, chemistry, cas,
          source_file, eq_kind, priority, needs_review
        ) VALUES (
          :src_company, :src_grade, :dst_company, :dst_grade, :eq_key, :chemistry, :cas,
          :source_file, :eq_kind, :priority, :needs_review
        )
        """,
        rows,
    )


def _insert_aliases(conn: sqlite3.Connection, records: list[dict[str, Any]], eq_groups: list[Any]) -> None:
    aliases: set[tuple[str, str, str]] = set()
    for rec in records:
        grade = rec.get("grade")
        if not grade:
            continue
        aliases.add((grade, "Power Dream", grade))
        aliases.add((grade.lower(), "Power Dream", grade))
        display = (rec.get("parsed") or {}).get("grade_display") or ""
        if display:
            aliases.add((display, "Power Dream", grade))
            aliases.add((normalize_grade(display), "Power Dream", grade))
    for item in iter_alias_hints(eq_groups):
        aliases.add(item)
        for extra in _competitor_aliases(item[0], item[1], item[2]):
            aliases.add(extra)
    conn.executemany(
        "INSERT OR IGNORE INTO aliases(alias, company, grade) VALUES (?, ?, ?)",
        list(aliases),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO product_aliases(alias, company, grade) VALUES (?, ?, ?)",
        list(aliases),
    )


def _competitor_aliases(alias: str, company: str, grade: str) -> list[tuple[str, str, str]]:
    token = re.sub(r"\s+", "", alias)
    match = re.match(r"^(EB|EBECRYL|SR|CN|PH|PHOTOMER)(\d.*)$", token, re.I)
    if not match:
        return []
    prefix, rest = match.group(1).upper(), match.group(2)
    out: list[tuple[str, str, str]] = []
    if prefix in {"EB", "EBECRYL"}:
        out.extend(
            [
                ("EB" + rest, company, grade),
                ("EBECRYL" + rest, company, grade),
                ("EB " + rest, company, grade),
            ]
        )
    if prefix in {"PH", "PHOTOMER"}:
        out.extend(
            [
                ("PH" + rest, company, grade),
                ("PHOTOMER" + rest, company, grade),
                ("PHOTOMER " + rest, company, grade),
            ]
        )
    return out


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO products_fts(products_fts) VALUES('rebuild')")
