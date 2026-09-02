from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from chemdoc_miner.db import connect
from chemdoc_miner.glossary import FAMILY_EN, FAMILY_LABELS, GLOSSARY, expand_query
from chemdoc_miner.normalize import canonical_company, collapse_ws, normalize_grade
from chemdoc_miner.query.xref import find_cross_refs, xref_stats

_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "used", "use", "product",
    "resin", "good", "high", "low", "can", "are", "our", "in", "of", "to", "a",
    "an", "or", "as", "on", "is", "be", "by", "it", "at",
}


def _conn() -> sqlite3.Connection:
    return connect()


def _row_to_product(row: sqlite3.Row | None, *, include_text: bool = False) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    for key in ("highlights", "applications", "properties", "ghs", "sds_summary"):
        raw = data.get(key)
        if isinstance(raw, str) and raw:
            try:
                data[key] = json.loads(raw)
            except json.JSONDecodeError:
                pass
        elif not raw:
            data[key] = [] if key not in {"properties", "sds_summary"} else {}
    if not include_text:
        data.pop("tds_text", None)
        data.pop("sds_text", None)
    data["family_label"] = FAMILY_LABELS.get(data.get("family") or "", data.get("family"))
    data["family_en"] = FAMILY_EN.get(data.get("family") or "", data.get("family"))
    return data


def resolve_grade(query: str, conn: sqlite3.Connection | None = None) -> list[dict[str, str]]:
    close = conn or _conn()
    q = collapse_ws(query)
    squeezed = normalize_grade(q)
    variants = {q, q.upper(), squeezed, squeezed.lower(), q.replace(" ", "")}
    found: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for alias in variants:
        if not alias:
            continue
        rows = close.execute(
            "SELECT alias, company, grade FROM aliases WHERE alias = ? COLLATE NOCASE LIMIT 20",
            (alias,),
        ).fetchall()
        if not rows:
            rows = close.execute(
                "SELECT alias, company, grade FROM aliases WHERE replace(alias,' ','') = ? COLLATE NOCASE LIMIT 20",
                (alias.replace(" ", ""),),
            ).fetchall()
        for row in rows:
            key = (row["company"], row["grade"])
            if key in seen:
                continue
            seen.add(key)
            found.append({"alias": row["alias"], "company": row["company"], "grade": row["grade"]})
    prod = close.execute(
        "SELECT grade, company FROM products WHERE grade = ? COLLATE NOCASE OR grade_display LIKE ?",
        (squeezed, f"%{q}%"),
    ).fetchall()
    for row in prod:
        key = (row["company"], row["grade"])
        if key not in seen:
            seen.add(key)
            found.append({"alias": row["grade"], "company": row["company"], "grade": row["grade"]})
    if conn is None:
        close.close()
    return found


def get_product(grade: str) -> dict[str, Any] | None:
    conn = _conn()
    try:
        resolved = resolve_grade(grade, conn)
        pd = next((r for r in resolved if r["company"] == "Power Dream"), resolved[0] if resolved else None)
        target = pd["grade"] if pd else normalize_grade(grade)
        row = conn.execute("SELECT * FROM products WHERE grade = ? COLLATE NOCASE", (target,)).fetchone()
        product = _row_to_product(row)
        if product:
            xref = find_cross_refs("Power Dream", product["grade"], conn=conn)
            product["equivalents"] = _peers_as_equivalents(
                "Power Dream", product["grade"], xref["peers"], xref.get("groups") or []
            )[:20]
            product["cross_refs"] = xref
        return product
    finally:
        conn.close()


def search_products(
    query: str,
    *,
    family: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    conn = _conn()
    try:
        expanded = expand_query(query)
        match = _fts_match(expanded)
        sql = """
            SELECT p.*
            FROM products_fts
            JOIN products p ON p.id = products_fts.rowid
            WHERE products_fts MATCH ?
        """
        params: list[Any] = [match]
        if family:
            sql += " AND p.family = ?"
            params.append(family)
        sql += " LIMIT ?"
        params.append(limit)
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.OperationalError:
            rows = []
        if not rows:
            like = f"%{query.strip()}%"
            extra_sql = """
                SELECT * FROM products
                WHERE grade LIKE ? OR grade_display LIKE ? OR description LIKE ?
                   OR applications LIKE ? OR highlights LIKE ? OR chemical_name LIKE ?
            """
            extra_params: list[Any] = [like, like, like, like, like, like]
            if family:
                extra_sql += " AND family = ?"
                extra_params.append(family)
            extra_sql += " LIMIT ?"
            extra_params.append(limit)
            rows = conn.execute(extra_sql, extra_params).fetchall()
        return [_row_to_product(r) for r in rows if r]
    finally:
        conn.close()


def list_by_company(company: str, *, family: str | None = None, limit: int = 80) -> dict[str, Any]:
    conn = _conn()
    try:
        name = canonical_company(company) or company
        if name in {"Power Dream", "iLENE", "Ilene"}:
            sql = "SELECT * FROM products"
            params: list[Any] = []
            if family:
                sql += " WHERE family = ?"
                params.append(family)
            sql += " ORDER BY family, grade LIMIT ?"
            params.append(limit)
            products = [_row_to_product(r) for r in conn.execute(sql, params).fetchall()]
            return {"company": "Power Dream", "count": len(products), "products": products}
        sql = """
            SELECT DISTINCT m.grade, g.chemistry, g.cas, g.source_file, g.domain
            FROM eq_members m
            JOIN eq_groups g ON g.group_id = m.group_id
            WHERE m.company = ? COLLATE NOCASE
        """
        params = [name]
        if family:
            sql += " AND g.chemistry LIKE ?"
            params.append(f"%{family}%")
        sql += " ORDER BY m.grade LIMIT ?"
        params.append(limit)
        grades = [dict(r) for r in conn.execute(sql, params).fetchall()]
        for item in grades:
            xref = find_cross_refs(name, item["grade"], conn=conn)
            item["power_dream"] = [
                p["grade"] for p in xref["peers"] if p["company"] == "Power Dream"
            ]
            item["peer_count"] = xref["peer_count"]
        return {"company": name, "count": len(grades), "grades": grades}
    finally:
        conn.close()


def find_equivalents(
    company: str,
    grade: str,
    *,
    conn: sqlite3.Connection | None = None,
    limit: int = 40,
) -> list[dict[str, Any]]:
    own = conn is None
    close = conn or _conn()
    try:
        xref = find_cross_refs(company, grade, conn=close)
        name = xref["query"]["company"]
        g = xref["query"]["grade"]
        rows = _peers_as_equivalents(name, g, xref["peers"], xref.get("groups") or [])
        return rows[:limit]
    finally:
        if own:
            close.close()


def _peers_as_equivalents(
    company: str,
    grade: str,
    peers: list[dict[str, str]],
    groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    meta = groups[0] if groups else {}
    out: list[dict[str, Any]] = []
    for peer in peers:
        out.append(
            {
                "src_company": company,
                "src_grade": grade,
                "dst_company": peer["company"],
                "dst_grade": peer["grade"],
                "eq_key": meta.get("eq_key"),
                "chemistry": meta.get("chemistry"),
                "cas": meta.get("cas"),
                "source_file": meta.get("source_file"),
                "eq_kind": meta.get("domain"),
                "priority": 1 if meta.get("domain") == "offsets" else 2,
            }
        )
    return out


def recommend(need_text: str, *, limit: int = 5) -> dict[str, Any]:
    hits = search_products(need_text, limit=24)
    expanded = expand_query(need_text).lower()
    phrases = [en.lower() for zh, en in GLOSSARY if zh in need_text.lower()]
    tokens = [t for t in re.findall(r"[a-z0-9\+\-]{2,}", expanded.lower()) if t not in _STOP]
    weak = {"ink", "inks", "print", "printing", "coat", "coating", "resin"}
    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    for product in hits:
        blob = " ".join(
            [
                product.get("description") or "",
                " ".join(product.get("highlights") or []),
                " ".join(product.get("applications") or []),
                product.get("family_en") or "",
            ]
        ).lower()
        reasons = []
        score = 0.0
        for phrase in phrases:
            if phrase in blob:
                score += 4.0
                reasons.append(phrase)
        for token in tokens:
            if token in blob:
                score += 0.4 if token in weak else 1.4
        for app in product.get("applications") or []:
            al = app.lower()
            if any(p in al for p in phrases) or any(token in al for token in tokens if token not in weak):
                score += 2.0
                reasons.append(f"Applications: {app}")
        for hi in product.get("highlights") or []:
            hl = hi.lower()
            if any(p in hl for p in phrases) or any(token in hl for token in tokens if token not in weak):
                score += 1.6
                reasons.append(f"Performance: {hi}")
        if product.get("family") and product["family"] in expanded:
            score += 0.8
        scored.append((score, product, _dedupe(reasons)[:4]))
    scored.sort(key=lambda x: x[0], reverse=True)
    picks = []
    for score, product, reasons in scored[:limit]:
        if score <= 0 and not picks:
            continue
        picks.append(
            {
                "grade": product["grade"],
                "grade_display": product.get("grade_display"),
                "family": product.get("family"),
                "family_label": product.get("family_label"),
                "description": product.get("description"),
                "applications": product.get("applications"),
                "highlights": product.get("highlights"),
                "properties": product.get("properties"),
                "cas": product.get("cas"),
                "tds_path": product.get("tds_path"),
                "sds_path": product.get("sds_path"),
                "score": round(score, 2),
                "reasons": reasons or ["Matched catalog text for this need."],
                "disclaimer": "推荐依据 TDS 原文，对标关系为销售对照，需配方验证。",
            }
        )
    if not picks and hits:
        for product in hits[:limit]:
            picks.append(
                {
                    "grade": product["grade"],
                    "grade_display": product.get("grade_display"),
                    "family": product.get("family"),
                    "family_label": product.get("family_label"),
                    "description": product.get("description"),
                    "applications": product.get("applications"),
                    "highlights": product.get("highlights"),
                    "tds_path": product.get("tds_path"),
                    "score": 0,
                    "reasons": ["Keyword fallback from catalog search."],
                    "disclaimer": "推荐依据 TDS 原文，对标关系为销售对照，需配方验证。",
                }
            )
    return {"need": need_text, "recommendations": picks}


def stats() -> dict[str, Any]:
    conn = _conn()
    try:
        families = {
            row["family"]: row["n"]
            for row in conn.execute("SELECT family, COUNT(*) AS n FROM products GROUP BY family")
        }
        xref = xref_stats(conn)
        return {
            "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
            "equivalents": conn.execute("SELECT COUNT(*) FROM equivalents").fetchone()[0],
            "eq_groups": xref["eq_groups"],
            "eq_members": xref["eq_members"],
            "lookup_keys": xref["lookup_keys"],
            "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
            "families": families,
            "xref_by_domain": xref["by_domain"],
        }
    finally:
        conn.close()


def _fts_match(text: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9\+\-]{2,}", text)
    cleaned = []
    for token in tokens[:16]:
        if token.lower() in _STOP:
            continue
        if re.search(r"[^\w]", token):
            cleaned.append(f'"{token}"')
        else:
            cleaned.append(f"{token}*")
    return " OR ".join(cleaned) or "ilene"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
