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
