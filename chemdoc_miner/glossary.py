from __future__ import annotations

# Chinese / informal sales language -> English TDS terms used in FTS.
GLOSSARY: list[tuple[str, str]] = [
    ("低黄变", "low yellowing non-yellowing"),
    ("耐黄变", "low yellowing non-yellowing"),
    ("不黄变", "non-yellowing"),
    ("低气味", "low odor"),
    ("快固化", "fast curing"),
    ("快速固化", "fast curing"),
    ("柔韧性", "flexibility flexible"),
    ("柔软", "flexible flexibility"),
    ("高硬度", "high hardness"),
    ("硬度", "hardness"),
    ("耐热", "thermal resistance high-temperature"),
    ("耐候", "weather resistance weathering"),
    ("低收缩", "low shrinkage"),
    ("高透明", "high transparency transparent"),
    ("附着力", "adhesion"),
    ("稀释", "diluent dilution"),
    ("活性稀释剂", "diluent"),
    ("3d打印", "3d printing"),
    ("3d 打印", "3d printing"),
    ("三维打印", "3d printing"),
    ("指甲胶", "nail gel"),
    ("美甲", "nail gel"),
    ("真空镀膜", "vacuum metallization"),
    ("镀膜", "metallization"),
    ("油墨", "ink"),
    ("胶印", "offset lithographic ink"),
    ("丝印", "screen printing ink"),
    ("涂料", "coating"),
    ("木器", "wood coatings"),
    ("塑料", "plastic coatings"),
    ("胶粘剂", "adhesive adhesives"),
    ("热熔胶", "hot melt adhesives"),
    ("压敏胶", "pressure-sensitive adhesives"),
    ("光引发剂", "photoinitiator"),
    ("聚氨酯丙烯酸酯", "urethane acrylate polyurethane"),
    ("聚氨酯", "urethane acrylate polyurethane"),
    ("环氧丙烯酸酯", "epoxy acrylate"),
    ("环氧", "epoxy acrylate"),
    ("聚酯丙烯酸酯", "polyester acrylate"),
    ("聚酯", "polyester acrylate"),
    ("氨改性", "amine modified"),
    ("单体", "monomer diluent"),
    ("低聚物", "oligomer acrylate"),
    ("石油树脂", "petroleum resin"),
    ("硫醇", "thiol mercaptan polythiol"),
    ("分散剂", "dispersant"),
    ("对应", "equivalent offset"),
    ("对标", "equivalent offset"),
    ("等价", "equivalent"),
    ("替代", "offset equivalent replacement"),
    ("推荐", "recommend"),
]

FAMILY_LABELS = {
    "pua": "聚氨酯丙烯酸酯",
    "pea": "聚酯丙烯酸酯",
    "ea": "环氧丙烯酸酯",
    "amine": "氨改性丙烯酸酯",
    "monomer": "单体 / 活性稀释剂",
    "photoinitiator": "光引发剂",
    "petroleum_resin": "石油树脂",
    "thiol": "硫醇 / 聚硫醇",
    "dispersant": "分散剂",
    "phosphate": "磷酸酯",
    "led_uv": "LED / 滴胶树脂",
    "other": "其他",
}

FAMILY_EN = {
    "pua": "Polyurethane acrylate",
    "pea": "Polyester acrylate",
    "ea": "Epoxy acrylate",
    "amine": "Amine-modified acrylate",
    "monomer": "Monomer / diluent",
    "photoinitiator": "Photoinitiator",
    "petroleum_resin": "Petroleum resin",
    "thiol": "Thiol / polythiol",
    "dispersant": "Dispersant",
    "phosphate": "Phosphate ester",
    "led_uv": "LED / doming resin",
    "other": "Other",
}

MONOMER_GRADES = {
    "HDDA",
    "TPGDA",
    "DPGDA",
    "TMPTA",
    "PETIA",
    "DPHA",
    "HEA",
    "HEMA",
    "HPA",
    "HPMA",
    "IBOA",
    "IBOMA",
    "CTFA",
    "THFA",
    "EOEOEA",
    "PPTTA",
    "TMPEOTA",
    "PETMP",
    "SA",
    "NVP",
    "4EOTMPTA",
    "9EO-TMPTA",
    "TMCHMA",
    "TMP(EO)9TA",
}

PI_HINTS = ("PHOTOINITIATOR", "1173", "184", "907", "EDB", "EHA", "KIP-150", "KIP150")


def expand_query(text: str) -> str:
    if not text:
        return ""
    lowered = text.lower()
    extra: list[str] = []
    for zh, en in GLOSSARY:
        if zh in lowered:
            extra.append(en)
    return (text + " " + " ".join(extra)).strip()


def classify_family(grade: str, description: str = "", chemical_name: str = "") -> str:
    g = (grade or "").upper().replace(" ", "")
    blob = f"{description} {chemical_name} {grade}".lower()
    if g in MONOMER_GRADES:
        return "monomer"
    if (
        "photoinitiator" in blob
        or g in {"1173", "184", "907", "EDB", "EHA", "KIP150", "KIP-150"}
        or "KIP" in g
    ):
        return "photoinitiator"
    if "petroleum resin" in blob or g in {"J2090", "G100"}:
        return "petroleum_resin"
    if "thiol" in blob or "mercapt" in blob or g in {"PETMP", "M249", "M539", "9301S"}:
        return "thiol"
    if g.startswith("A381") or g.startswith("381") or "dispers" in blob:
        return "dispersant"
    if g.startswith("107"):
        return "phosphate"
    if "led" in g.lower() or "doming" in blob:
        return "led_uv"
    if g in MONOMER_GRADES or any(
        k in blob for k in ("diacrylate", "triacrylate", "methacrylate", "monoacrylate")
    ):
        if "urethane" not in blob and "epoxy acrylate" not in blob and "polyester acrylate" not in blob:
            if g in MONOMER_GRADES or "chemical name" in blob or "purity" in blob:
                return "monomer"
    m = __import__("re").match(r"^(\d)", g)
    if m:
        d = m.group(1)
        if d == "2":
            return "pua"
        if d == "6":
            return "pea"
        if d == "7":
            return "ea"
        if d == "8":
            return "amine"
    if "urethane acrylate" in blob or "polyurethane" in blob:
        return "pua"
    if "epoxy acrylate" in blob or "bisphenol" in blob:
        return "ea"
    if "polyester acrylate" in blob:
        return "pea"
    if "amine" in blob:
        return "amine"
    if g in MONOMER_GRADES:
        return "monomer"
    return "other"
