from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from typing import Any

from chemdoc_miner.glossary import FAMILY_EN
from chemdoc_miner.query.spec_match import extract_product_specs, spec_in_range
from chemdoc_miner.query.spec_schema import (
    APPLICATION_SKIP,
    FAMILY_FILTER_SPECS,
    HAZARD_FLAGS,
    PERFORMANCE_TAGS,
    SPEC_LABELS,
    application_display,
    normalize_application,
)
from chemdoc_miner.query.tools import _row_to_product

_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "used", "use", "product",
    "resin", "good", "high", "low", "can", "are", "our", "in", "of", "to", "a",
    "an", "or", "as", "on", "is", "be", "by", "it", "at",
}


def build_finder_index(conn: sqlite3.Connection) -> dict[str, Any]:
    rows = conn.execute("SELECT * FROM products ORDER BY grade").fetchall()
    products: dict[str, dict[str, Any]] = {}
    app_counter: Counter[str] = Counter()

    for row in rows:
        product = _row_to_product(row)
        if not product:
            continue
        grade = product["grade"]
        apps = [a for a in (product.get("applications") or []) if collapse_app(a)]
        apps_norm = []
        for app in apps:
            norm = normalize_application(app)
            if norm in APPLICATION_SKIP or len(norm) < 3:
                continue
            apps_norm.append(norm)
            app_counter[norm] += 1

        parsed = extract_product_specs(product.get("properties") or {})
        sds = product.get("sds_summary") or {}
        products[grade.upper()] = {
            "grade": grade,
            "grade_display": product.get("grade_display"),
            "family": product.get("family") or "other",
            "family_en": product.get("family_en") or FAMILY_EN.get(product.get("family") or "", ""),
            "applications": apps,
            "applications_norm": sorted(set(apps_norm)),
            "highlights": product.get("highlights") or [],
            "description": (product.get("description") or "")[:280],
            "specs": parsed["specs"],
            "spec_display": parsed["spec_display"],
            "hazard_flags": sds.get("hazard_flags") or [],
            "signal_word": product.get("signal_word") or sds.get("label_elements", {}).get("signal_word"),
            "has_sds": bool(product.get("sds_path")),
            "has_tds": bool(product.get("tds_path")),
        }

    applications_vocab = _build_applications_vocab(app_counter)
    return {
        "count": len(products),
        "applications_vocab": applications_vocab,
        "family_specs": FAMILY_FILTER_SPECS,
        "spec_labels": SPEC_LABELS,
        "performance_tags": [
            {"id": tag_id, "label": tag_id.replace("_", " ").title()} for tag_id, _ in PERFORMANCE_TAGS
        ],
        "hazard_flags": [{"id": flag_id, "label": label} for flag_id, label in HAZARD_FLAGS],
        "products": products,
    }


def find_products(criteria: dict[str, Any], index: dict[str, Any] | None = None, *, limit: int = 15) -> dict[str, Any]:
    if index is None:
        from chemdoc_miner.db import connect

        conn = connect()
        try:
            index = build_finder_index(conn)
        finally:
            conn.close()

    results: list[dict[str, Any]] = []
    for grade, product in index["products"].items():
        scored = _score_product(product, criteria, index)
        if scored is None:
            continue
        score, reasons, spec_hits = scored
        if score <= 0 and _has_active_criteria(criteria):
            continue
        results.append(
            {
                "grade": product["grade"],
                "grade_display": product.get("grade_display"),
                "family": product.get("family"),
                "family_en": product.get("family_en"),
                "applications": product.get("applications") or [],
                "highlights": (product.get("highlights") or [])[:3],
                "spec_display": product.get("spec_display") or {},
                "signal_word": product.get("signal_word"),
                "hazard_flags": product.get("hazard_flags") or [],
                "has_sds": product.get("has_sds"),
                "score": round(score, 1),
                "match_pct": min(100, int(score)),
                "reasons": reasons[:5],
                "spec_hits": spec_hits,
            }
        )

    results.sort(key=lambda item: (item["score"], item["grade"]), reverse=True)
    return {"criteria": criteria, "count": len(results), "results": results[:limit]}


def _score_product(
    product: dict[str, Any],
    criteria: dict[str, Any],
    index: dict[str, Any],
) -> tuple[float, list[str], list[str]] | None:
    family = criteria.get("family") or "all"
    if family != "all" and product.get("family") != family:
        return None

    if not _passes_safety(product, criteria.get("safety") or {}):
        return None

    score = 0.0
    reasons: list[str] = []
    spec_hits: list[str] = []

    apps = criteria.get("applications") or []
    if apps:
        wanted = {normalize_application(a) for a in apps}
        matched = [a for a in product.get("applications_norm") or [] if a in wanted]
        if not matched:
            return None
        score += 35.0 * len(matched) / len(wanted)
        for norm in matched:
            display = next(
                (application_display(a) for a in product.get("applications") or [] if normalize_application(a) == norm),
                norm,
            )
            reasons.append(f"Application: {display}")

    tags = criteria.get("performance_tags") or []
    if tags:
        blob = " ".join(
            [
                product.get("description") or "",
                " ".join(product.get("highlights") or []),
                " ".join(product.get("applications") or []),
            ]
        ).lower()
        tag_map = {tag_id: phrases for tag_id, phrases in PERFORMANCE_TAGS}
        hit = 0
        for tag_id in tags:
            phrases = tag_map.get(tag_id, "").split()
            if any(p in blob for p in phrases):
                hit += 1
                reasons.append(f"Performance: {tag_id.replace('_', ' ')}")
        if tags and hit == 0 and not apps and not criteria.get("specs") and not criteria.get("text"):
            return None
        score += 18.0 * hit / max(len(tags), 1)

    specs = criteria.get("specs") or {}
    active_specs = {k: v for k, v in specs.items() if v.get("min") is not None or v.get("max") is not None}
    if active_specs:
        spec_score = 0.0
        for key, bounds in active_specs.items():
            product_val = (product.get("specs") or {}).get(key)
            ok, partial, _ = spec_in_range(product_val, bounds.get("min"), bounds.get("max"))
            if not ok:
                return None
            spec_score += partial
            label = index.get("spec_labels", SPEC_LABELS).get(key, key)
            disp = (product.get("spec_display") or {}).get(key, "")
            spec_hits.append(f"{label}: {disp}" if disp else label)
            reasons.append(f"Spec {label} in range")
        score += 30.0 * spec_score / len(active_specs)

    text = (criteria.get("text") or "").strip()
    if text:
        tokens = [t for t in re.findall(r"[a-z0-9\+\-]{2,}", text.lower()) if t not in _STOP]
        blob = " ".join(
            [
                product.get("description") or "",
                " ".join(product.get("highlights") or []),
                " ".join(product.get("applications") or []),
                product.get("family_en") or "",
            ]
        ).lower()
        hits = sum(1 for token in tokens if token in blob)
        if hits:
            score += min(15.0, hits * 3.0)
            reasons.append(f"Text match ({hits} terms)")
        elif not apps and not active_specs and not tags:
            return None

    if not _has_active_criteria(criteria):
        score = 1.0
        reasons.append("Catalog browse")

    return score, _dedupe(reasons), spec_hits


def _passes_safety(product: dict[str, Any], safety: dict[str, Any]) -> bool:
    exclude_flags = safety.get("exclude_flags") or []
    if exclude_flags:
        if not product.get("has_sds"):
            return False
        flags = set(product.get("hazard_flags") or [])
        if flags.intersection(exclude_flags):
            return False

    if safety.get("warning_only"):
        if not product.get("has_sds"):
            return False
        if (product.get("signal_word") or "").upper() == "DANGER":
            return False

    if safety.get("require_sds") and not product.get("has_sds"):
        return False

    return True


def _has_active_criteria(criteria: dict[str, Any]) -> bool:
    if criteria.get("applications"):
        return True
    if criteria.get("performance_tags"):
        return True
    if criteria.get("text"):
        return True
    specs = criteria.get("specs") or {}
    for bounds in specs.values():
        if bounds.get("min") is not None or bounds.get("max") is not None:
            return True
    safety = criteria.get("safety") or {}
    if safety.get("exclude_flags") or safety.get("warning_only") or safety.get("require_sds"):
        return True
    return False


def _build_applications_vocab(app_counter: Counter[str]) -> list[dict[str, str]]:
    merged: dict[str, str] = {}
    for norm, _count in app_counter.most_common():
        if norm in APPLICATION_SKIP:
            continue
        key = norm
        merged[key] = application_display(norm)
    items = sorted(merged.items(), key=lambda pair: (-app_counter[pair[0]], pair[1].lower()))
    return [{"id": norm, "label": label} for norm, label in items[:45]]


def collapse_app(app: str) -> str:
    return " ".join((app or "").strip().split())


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def export_finder_json(conn: sqlite3.Connection) -> str:
    return json.dumps(build_finder_index(conn), ensure_ascii=False)
