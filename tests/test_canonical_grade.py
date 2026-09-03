from chemdoc_miner.normalize import (
    canonical_grade,
    grade_query_variants,
    related_grade_variants,
)


def test_igm_offset_ph_to_numeric():
    assert canonical_grade("PH3016", "IGM", domain="offsets") == "3016"
    assert canonical_grade("Photomer 3016 LT", "IGM", domain="ecr") == "3016LT"


def test_igm_query_variants():
    variants = grade_query_variants("Photomer 3016", "IGM")
    assert "3016" in variants
    variants = grade_query_variants("PH3016", "IGM")
    assert "3016" in variants


def test_pi_bch_keep_numeric():
    assert canonical_grade("1173", "BCH", domain="pi") == "1173"
    assert canonical_grade("Omnirad 1173", "IGM", domain="pi") == "1173"


def test_allnex_eb_variants():
    assert canonical_grade("EB3700", "Allnex") == "EB3700"
    assert canonical_grade("3700", "Allnex") == "EB3700"
    assert "EB3700" in grade_query_variants("3700", "Allnex")


def test_related_3016_variants():
    catalog = ["3016", "3016LT", "3016-25G", "4006"]
    rel = related_grade_variants("3016", catalog)
    assert "3016LT" in rel
    assert "3016-25G" in rel
    assert "4006" not in rel


def test_agi_agisyn_to_numeric():
    assert canonical_grade("AgiSyn 008", "AGI", domain="ecr") == "008"
    assert canonical_grade("008", "AGI", domain="ecr") == "008"
    assert canonical_grade("AGISYN008", "AGI", domain="offsets") == "008"
    assert "008" in grade_query_variants("AgiSyn 008", "AGI")
    assert "008" in grade_query_variants("AgiSyn 008", "Covestro")


def test_covestro_p50_variants():
    assert canonical_grade("P-50", "Covestro") == "COVESTROP-50"
    assert canonical_grade("Covestro P-50", "Covestro") == "COVESTROP-50"
    assert "COVESTROP-50" in grade_query_variants("P-50", "Covestro")
