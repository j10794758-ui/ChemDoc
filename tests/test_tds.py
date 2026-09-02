from chemdoc_miner.ingest.tds import parse_tds

PDA = """
iLENE ACRYLATE 2201
Revised date: 3/25/2025
Technical data sheet
Description
iLENE ACRYLATE 2201 is a polyurethane acrylate.
Physical Properties
Appearance : Transparent viscous liquid
Color, Gardner : ≤1
Viscosity, cPs@60℃ : 6000
Functionality (theoretical) : 2
Performance Highlights
Low yellowing
Low odor
Fast curing
Applications
3D printing
Package
220kg/drum, 20kg/pail Storage and handling: Do not expose the product to high temperature conditions.
"""

BJ = """
TDS No：BJTDS-1011 VersionNo：A/1 RevisionDate：2025-5-6
Name iLENE HDDA
Chemical name: Hexamethylene diacrylate
Introduction
CASnumber: 13048-33-4
☆ Appearance: Transparent liquid
☆ Viscosity, CPS@25℃: 5-10
Features ☆Excellentdilution
Application ☆UVcoating, UVink and synthesis ofpolyurethane acrylate.
Packaging 200kg/drum
Avoid direct contact with skin and eyes. The storage stability of this
Precautions product should be at least 6 months, stored away from light in a properly sealed container at 0-35℃.
Disclaimer: test
"""


def test_pda_template():
    parsed = parse_tds(PDA, "iLENE 2201 TDS.pdf")
    assert parsed["grade"] == "2201"
    assert parsed["family"] == "pua"
    assert parsed["revised_date"] == "2025-03-25"
    assert any("3D" in a for a in parsed["applications"])
    assert parsed["properties"].get("viscosity")
    assert parsed["confidence"] >= 0.7
    assert parsed["package"] == "220kg/drum, 20kg/pail"
    assert parsed["storage"] == "Do not expose the product to high temperature conditions."


def test_bjtds_template():
    parsed = parse_tds(BJ, "iLENE HDDA TDS 1.pdf")
    assert parsed["grade"] == "HDDA"
    assert parsed["cas"] == "13048-33-4"
    assert parsed["family"] == "monomer"
    assert parsed["template"] == "bjtds"
    assert parsed["package"] == "200kg/drum"
    assert "storage stability" in (parsed["storage"] or "")
    assert "6 months" in (parsed["storage"] or "")
