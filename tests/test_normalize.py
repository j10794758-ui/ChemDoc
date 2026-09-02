from chemdoc_miner.normalize import canonical_company, grade_from_filename, normalize_grade, parse_date


def test_normalize_numeric_suffix():
    assert normalize_grade("708 B") == "708B"
    assert normalize_grade("iLENE ACRYLATE 2201") == "2201"
    assert normalize_grade("iLENE HDDA") == "HDDA"


def test_filename_grades():
    assert grade_from_filename("iLENE 2201 TDS.pdf") == "2201"
    assert grade_from_filename("TDS_iLENE Photoinitiator 1173.pdf") == "1173"
    assert grade_from_filename("iLENE HDDA TDS 1.pdf") == "HDDA"
    assert grade_from_filename("SDS_iLENE ACRYLATE 2230 04_EN.pdf") == "2230"


def test_restore_pdf_spaces_glued():
    from chemdoc_miner.normalize import restore_pdf_spaces

    raw = "Donotexposetheproducttohightemperatureconditionsortodirectsunlight.Storeatroomtemperature."
    assert restore_pdf_spaces(raw) == (
        "Do not expose the product to high temperature conditions or to direct sunlight. "
        "Store at room temperature."
    )


def test_restore_pdf_spaces_partial():
    from chemdoc_miner.normalize import restore_pdf_spaces

    raw = "Do not exposetheproduct tohightemperatureconditionsor todirect sunlight. Storeat room temperature."
    assert "Store at room temperature" in (restore_pdf_spaces(raw) or "")
    assert "temperature" in (restore_pdf_spaces(raw) or "")


def test_dates():
    assert parse_date("Revised date: 3/25/2025") == "2025-03-25"
    assert parse_date("RevisionDate：2025-12-8") == "2025-12-08"


def test_company():
    assert canonical_company("Allnex") == "Allnex"
    assert canonical_company("PHOTOMER") == "IGM"
    assert canonical_company("Power Dream America Inc") == "Power Dream"
    assert canonical_company("RAHN                       Genomer") == "RAHN"
