import json

from chemdoc_miner.db import connect
from chemdoc_miner.export.app_mobile import export_app_html
from chemdoc_miner.export.finder_mobile import export_finder_html
from chemdoc_miner.query.finder import build_finder_index, find_products


def test_finder_index_has_products():
    conn = connect()
    try:
        index = build_finder_index(conn)
    finally:
        conn.close()
    assert index["count"] >= 290
    assert "coatings" in {a["id"] for a in index["applications_vocab"]}
    assert "2230" in index["products"] or "2230" in {p["grade"].upper() for p in index["products"].values()}


def test_find_by_application_coatings():
    conn = connect()
    try:
        index = build_finder_index(conn)
    finally:
        conn.close()
    result = find_products({"applications": ["coatings"], "family": "all"}, index)
    assert result["count"] >= 5
    for item in result["results"]:
        apps_norm = {a.lower() for a in item.get("applications") or []}
        assert any("coating" in a for a in apps_norm)


def test_safety_excludes_reproductive_toxicity():
    conn = connect()
    try:
        index = build_finder_index(conn)
    finally:
        conn.close()
    open_result = find_products({"applications": ["nail gel"]}, index, limit=30)
    safe_result = find_products(
        {
            "applications": ["nail gel"],
            "safety": {"exclude_flags": ["reproductive_toxicity"], "require_sds": True},
        },
        index,
        limit=30,
    )
    open_grades = {item["grade"] for item in open_result["results"]}
    safe_grades = {item["grade"] for item in safe_result["results"]}
    assert len(safe_grades) <= len(open_grades)
    for item in safe_result["results"]:
        assert "reproductive_toxicity" not in (item.get("hazard_flags") or [])


def test_find_by_viscosity_range():
    conn = connect()
    try:
        index = build_finder_index(conn)
    finally:
        conn.close()
    result = find_products(
        {
            "family": "pua",
            "specs": {"viscosity": {"min": 1000, "max": 10000}},
        },
        index,
        limit=20,
    )
    assert result["count"] >= 1
    for item in result["results"]:
        assert item["family"] == "pua"


def test_export_finder_html(tmp_path):
    out = tmp_path / "ChemDoc.html"
    path = export_app_html(out_path=out)
    text = path.read_text(encoding="utf-8")
    assert "Product Finder" in text or "Finder" in text
    assert "__FINDER_JSON__" not in text
    assert "coatings" in text
    assert "openCatalog" in text
    assert "returnTo" in text and "finder" in text
