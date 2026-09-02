from chemdoc_miner.export.app_mobile import export_app_html
from chemdoc_miner.export.finder_mobile import export_finder_html
from chemdoc_miner.export.products_mobile import export_products_html
from chemdoc_miner.query.catalog import export_catalog_json
from chemdoc_miner.db import connect


def test_export_catalog_json_has_2150f():
    conn = connect()
    try:
        import json
        data = json.loads(export_catalog_json(conn))
    finally:
        conn.close()
    assert data["count"] >= 290
    p = data["products"]["2150F"]
    assert p["grade"] == "2150F"
    assert p.get("description")
    assert p.get("sds_summary", {}).get("label_elements", {}).get("signal_word") == "DANGER"


def test_export_app_html(tmp_path):
    out = tmp_path / "ChemDoc.html"
    path = export_app_html(out_path=out)
    text = path.read_text(encoding="utf-8")
    assert "ChemDoc" in text
    assert "Finder" in text and "Catalog" in text and "Xref" in text
    assert "__CATALOG_JSON__" not in text
    assert "__FINDER_JSON__" not in text
    assert "__LOOKUP_JSON__" not in text
    assert "openCatalog" in text
    assert "catalog-back" in text
    assert "data:image/svg+xml;base64," in text


def test_legacy_exports_use_unified_app(tmp_path):
    path = export_products_html(out_path=tmp_path / "ChemDoc.html")
    assert path.name == "ChemDoc.html"
    text = path.read_text(encoding="utf-8")
    assert "app-nav" in text
    path2 = export_finder_html(out_path=tmp_path / "ChemDoc2.html")
    assert "openCatalog" in path2.read_text(encoding="utf-8")
