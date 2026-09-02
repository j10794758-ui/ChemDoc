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
