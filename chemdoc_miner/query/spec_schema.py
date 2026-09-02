from __future__ import annotations

from chemdoc_miner.glossary import FAMILY_EN, FAMILY_LABELS

# Numeric / range filters exposed per family (Phase 1).
FAMILY_FILTER_SPECS: dict[str, list[str]] = {
    "pua": ["viscosity", "hardness", "tg", "functionality", "acid_value"],
    "pea": ["viscosity", "hardness", "tg", "functionality", "acid_value"],
    "ea": ["viscosity", "hardness", "tg", "functionality", "acid_value"],
    "amine": ["viscosity", "hardness", "tg", "functionality"],
    "monomer": ["viscosity", "acid_value", "purity"],
    "photoinitiator": ["purity", "melting_point"],
    "thiol": ["viscosity", "functionality"],
    "led_uv": ["viscosity", "hardness"],
    "dispersant": ["viscosity"],
    "phosphate": ["viscosity", "acid_value"],
    "petroleum_resin": ["softening_point", "acid_value"],
    "other": ["viscosity", "hardness"],
}

SPEC_LABELS: dict[str, str] = {
    "viscosity": "Viscosity (cps)",
    "hardness": "Hardness (Shore D)",
    "tg": "Tg (°C)",
    "functionality": "Functionality",
    "acid_value": "Acid value",
    "purity": "Purity (%)",
    "melting_point": "Melting point (°C)",
    "softening_point": "Softening point (°C)",
}

# English performance tags mapped to search phrases in highlights/description/applications.
PERFORMANCE_TAGS: list[tuple[str, str]] = [
    ("low_yellowing", "non-yellowing low yellowing"),
    ("fast_curing", "fast curing quick cure"),
    ("flexible", "flexible flexibility"),
    ("high_hardness", "high hardness"),
    ("high_transparency", "transparent high transparency"),
    ("low_odor", "low odor"),
    ("adhesion", "adhesion"),
    ("weather_resistance", "weather resistance weathering"),
]

HAZARD_FLAGS: list[tuple[str, str]] = [
    ("reproductive_toxicity", "Reproductive toxicity"),
    ("carcinogen_suspect", "Suspected carcinogen"),
    ("aquatic_hazard", "Aquatic hazard"),
    ("skin_sensitization", "Skin sensitization"),
    ("respiratory_irritation", "Respiratory irritation"),
    ("eye_irritation", "Eye irritation"),
    ("skin_irritation", "Skin irritation"),
]

APPLICATION_SKIP = frozenset({"etc", "etc.", "and etc", "and etc."})


def normalize_application(app: str) -> str:
    return " ".join((app or "").lower().split())


def application_display(app: str) -> str:
    text = collapse_app(app)
    if not text:
        return ""
    return text[0].upper() + text[1:] if len(text) > 1 else text.upper()


def collapse_app(app: str) -> str:
    return " ".join((app or "").strip().split())


def family_options() -> list[dict[str, str]]:
    return [
        {"slug": slug, "label": FAMILY_EN.get(slug, slug), "label_zh": FAMILY_LABELS.get(slug, slug)}
        for slug in FAMILY_FILTER_SPECS
    ]
