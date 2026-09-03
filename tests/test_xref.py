from chemdoc_miner.ingest.equivalence import load_equivalence_groups
from chemdoc_miner.query.xref import build_union_lookup, member_key


def test_load_groups():
    groups = load_equivalence_groups()
    assert len(groups) > 500
    domains = {g.domain for g in groups}
    assert "offsets" in domains
    assert "ecr" in domains
    assert "pi" in domains
    assert "additives" in domains


def test_union_lookup_eb3700():
    groups = load_equivalence_groups()
    lookup = build_union_lookup(groups)
    peers = lookup.get(member_key("Allnex", "EB3700"), [])
    companies = {p["company"] for p in peers}
    assert "Power Dream" in companies
    pd = [p for p in peers if p["company"] == "Power Dream"]
    assert any(p["grade"] == "700" for p in pd)


def test_offset_igm_3016():
    groups = load_equivalence_groups()
    lookup = build_union_lookup(groups)
    assert member_key("IGM", "3016") in lookup or member_key("IGM", "PH3016") in lookup
    key = member_key("IGM", "3016") if member_key("IGM", "3016") in lookup else member_key("IGM", "PH3016")
    peers = lookup[key]
    assert any(p["company"] == "Power Dream" and p["grade"] == "700" for p in peers)


def test_union_lookup_sr351():
    groups = load_equivalence_groups()
    lookup = build_union_lookup(groups)
    peers = lookup.get(member_key("Sartomer", "SR351"), [])
    assert len(peers) >= 5
    companies = {p["company"] for p in peers}
    assert "IGM" in companies or "Allnex" in companies


def test_2hop_power_dream_8000():
    from chemdoc_miner.query.xref import find_cross_refs

    r1 = find_cross_refs("Power Dream", "8000", max_hops=1)
    r2 = find_cross_refs("Power Dream", "8000", max_hops=2)
    assert r2["hop1_count"] == len(r1["peers"])
    assert r2["hop2_count"] >= 1
    hop2 = {(p["company"], p["grade"]) for p in r2["peers"] if p["hop"] == 2}
    assert ("AGI", "008") in hop2 or ("Qualipoly", "GC1100Z") in hop2


def test_2hop_allnex_eb3700():
    from chemdoc_miner.query.xref import find_cross_refs

    r = find_cross_refs("Allnex", "EB3700", max_hops=2)
    hop1 = {(p["company"], p["grade"]) for p in r["peers"] if p["hop"] == 1}
    assert ("Power Dream", "700") in hop1
    assert r["peer_count"] >= len(hop1)


def test_covestro_p50_xref():
    from chemdoc_miner.query.xref import find_cross_refs

    r = find_cross_refs("Covestro", "P-50", max_hops=2)
    assert r["peer_count"] >= 1
    assert any(p["company"] == "Power Dream" and p["grade"] == "LJ03250" for p in r["peers"])
