from __future__ import annotations

import json
import sqlite3
from typing import Any

from chemdoc_miner.normalize import normalize_grade, restore_pdf_spaces
from chemdoc_miner.query.tools import _row_to_product


def export_catalog_json(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT * FROM products ORDER BY grade").fetchall()
    products: dict[str, dict[str, Any]] = {}
    grades: list[str] = []

    for row in rows:
        product = _row_to_product(row)
        if not product:
            continue
        grade = product["grade"]
        grades.append(grade)
        products[grade.upper()] = _slim_product(product)

    alias_rows = conn.execute(
        "SELECT alias, grade FROM aliases WHERE company = 'Power Dream'"
    ).fetchall()
    aliases: dict[str, str] = {}
    for alias_row in alias_rows:
        alias = normalize_grade(alias_row["alias"])
        grade = alias_row["grade"]
        if alias and grade:
            aliases[alias.upper()] = grade.upper()

    payload = {
        "count": len(products),
        "grades": grades,
        "aliases": aliases,
        "products": products,
    }
    return json.dumps(payload, ensure_ascii=False)


def _slim_product(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "grade": product.get("grade"),
        "grade_display": product.get("grade_display"),
        "family": product.get("family"),
        "family_label": product.get("family_label"),
        "cas": product.get("cas"),
        "chemical_name": product.get("chemical_name"),
        "description": restore_pdf_spaces(product.get("description")),
        "highlights": product.get("highlights") or [],
        "applications": product.get("applications") or [],
        "properties": product.get("properties") or {},
        "package": restore_pdf_spaces(product.get("package")),
        "storage": restore_pdf_spaces(product.get("storage")),
        "revised_date": product.get("revised_date"),
        "tds_path": product.get("tds_path"),
        "sds_path": product.get("sds_path"),
        "signal_word": product.get("signal_word"),
        "sds_summary": product.get("sds_summary") or {},
    }
