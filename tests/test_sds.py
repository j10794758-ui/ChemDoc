from __future__ import annotations

from chemdoc_miner.ingest.sds import parse_sds

SDS_2150F = """
SAFETY DATA SHEET
Product: iLENE ACRYLATE 2150F
1.CHEMICAL PRODUCT ANDCOMPANY INFORMATION
Product Name: iLENE ACRYLATE 2150F
Synonyms: None
Company: POWERDREAM AMERICA INC
Telephone: +1 (678) 2137719
Rawmaterial ofcarving glue, model glue, adhesive,
Intended/Recommended Use:
nailgels.
Limited Use:
Business Emergency Telephone: +1 (678) 2137719
2.HAZARDSUMMARIZATION
GHS classification:
Skin corrosion/irritation -Category 2
Skin sensitization- Category 1
Reproductive toxicity Category 1B
Hazardous tothe aquatic environment, long-term hazard -Category 2
Label elements:
Signalword: DANGER
H315 -Causes skinirritation.
H317 -May cause an allergic skin reaction.
H319 -Causes serious eye irritation.
H335 -May cause respiratory irritation.
H360Fd -May damagefertility; Suspected ofdamaging theunborn child.
H411 -Toxicto aquaticlife with longlasting effects.
Precautionary statements:
●Prevention:
P280: Wearprotective gloves/protectiveclothing/eye protection/face protection.
P273: Avoid releaseto theenvironment.
●Storage:
P233: Store in awell-ventilated place. Keep container tightly closed.
●Disposal:
P501: Disposeofcontent and container in accordance with regulations.
3.COMPOSITION/INFORMATION ONINGREDIENTS
Chemical Components ConcentrationWT% CAS No.
Aliphaticurethane acrylate 68-71.7 -
Isobornyl acrylate 28-31.7 5888-33-5
Diphenyl(2,4,6-trimethylbenzoyl)phosphineoxide 0.3 75980-60-8
7.HANDLING AND STORAGE
Handling:
Providegood ventilation ofworking area.
Precautions forstorage:
Storesealed in acool,ventilated warehouse at 4-27℃.
10.STABILITYAND REACTIVITY
Incompatiblesubstances:
Oxidants, peroxides, initiators,active metals, alkaline andacidic substances.
14.TRANSPORT INFORMATION
United Nations Dangerous Goods Number (UN No.):
UN3082
United Nations Hazard Classification:
Class 9
Packing Category:
III
Marine Pollutants:
Applicable.
15.REGULATORY INFORMATION
United States (USA): All components ofthisproduct are designated as "Active" ontheTSCA
inventory or are not required to belisted.
European Economic Area (includingEU): All components ofthisproduct listed intheEINECS,
ELINCS, orNLP inventories.
"""


def test_2150f_label_elements():
    parsed = parse_sds(SDS_2150F, "iLENE 2150F SDS_.pdf")
    label = parsed["label_elements"]
    assert label["signal_word"] == "DANGER"
    assert len(label["hazard_statements"]) == 6
    assert any(item["code"].startswith("H360") for item in label["hazard_statements"])
    picto_codes = {item["code"] for item in label["pictograms"]}
    assert "GHS07" in picto_codes
    assert "GHS08" in picto_codes
    assert "GHS09" in picto_codes
    assert label["precautionary_statements"]["prevention"]
    assert parsed["intended_use"] and "nail" in parsed["intended_use"].lower()


def test_2150f_components_and_transport():
    parsed = parse_sds(SDS_2150F, "iLENE 2150F SDS_.pdf")
    assert len(parsed["components"]) == 3
    assert parsed["components"][1]["cas"] == "5888-33-5"
    assert parsed["sds_summary"]["transport"]["un_number"] == "UN3082"
    assert "reproductive_toxicity" in parsed["hazard_flags"]


def test_signal_word_not_un_number():
    text = """
2.HAZARD
Label elements:
Signal word: WARNING
United Nations Dangerous Goods Number (UN No.): UN3082
H315 - Causes skin irritation.
3.COMPOSITION
"""
    parsed = parse_sds(text)
    assert parsed["signal_word"] == "WARNING"


def test_product_name_without_newlines():
    text = """
1.CHEMICAL PRODUCT ANDCOMPANY INFORMATION
Product Name: iLENE ACRYLATE 2150FSynonyms: None
Company: POWERDREAM AMERICA INC
2.HAZARD
Label elements:
Signal word: DANGER
H315 - Causes skin irritation.
Precautionary statements:
●Prevention:
P280: Wear gloves.
3.COMPOSITION
"""
    parsed = parse_sds(text, "iLENE 2150F SDS_.pdf")
    assert parsed["grade"] == "2150F"
    assert parsed["product_name"] == "iLENE ACRYLATE 2150F"

    from chemdoc_miner.ingest.inventory import mark_canonical

    records = mark_canonical(
        [
            {
                "kind": "sds",
                "grade": "2150F",
                "filename": "iLENE 2150F SDS.pdf",
                "path": "a.pdf",
                "extractable": True,
                "revised_date": None,
                "text_len": 1000,
            },
            {
                "kind": "sds",
                "grade": "2150F",
                "filename": "iLENE 2150F SDS_.pdf",
                "path": "b.pdf",
                "extractable": True,
                "revised_date": "2023-07-06",
                "text_len": 1200,
            },
        ]
    )
    canonical = [r for r in records if r["is_canonical"]]
    assert len(canonical) == 1
    assert canonical[0]["path"] == "b.pdf"
