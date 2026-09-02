from __future__ import annotations

import re
from typing import Any

from chemdoc_miner.glossary import classify_family
from chemdoc_miner.ingest.llm_fill import maybe_llm_fill
from chemdoc_miner.normalize import collapse_ws, grade_from_filename, normalize_grade, parse_date, restore_pdf_spaces

_SECTION_A = re.compile(
    r"(?im)^(description|physical properties|specifications|performance highlights|"
    r"applications|package|chemical name|cas(?:\s*no\.?)?|storage(?:andhandling)?:?|"
    r"storage and handling)\s*$"
)
_DISCLAIMER = re.compile(r"(?im)^disclaimer[:：]")
_STAR_LINE = re.compile(r"^[☆★]\s*")
_KV = re.compile(
    r"^(?P<key>[A-Za-z][A-Za-z0-9 ,./%()°℃\-@]*)\s*[:：]\s*(?P<value>.+)$"
)
_CAS = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")

_STORAGE_MARKER = re.compile(r"(?i)\s*storage\s+and\s+handling\s*[:：]\s*")
_PKG_SPEC = re.compile(r"\d+\s*kg/(?:drum|pail|IBC|plastic\s+drum|carton)", re.I)

_STOP_HEADINGS = (
    "description",
    "physical properties",
    "specifications",
    "performance highlights",
    "applications",
    "package",
    "packaging",
    "storage",
    "storageandhandling",
    "storage and handling",
    "disclaimer",
    "chemical name",
    "cas no",
    "cas number",
    "technical data sheet",
    "introduction",
    "properties",
    "features",
    "application",
    "precautions",
    "name",
)


def parse_tds(text: str, filename: str = "") -> dict[str, Any]:
    cleaned = _prep(text)
    template = "bjtds" if re.search(r"TDS\s*No", cleaned, re.I) else "pda"
    parsed = _parse_bjtds(cleaned) if template == "bjtds" else _parse_pda(cleaned)
    grade = parsed.get("grade") or grade_from_filename(filename)
    parsed["grade"] = normalize_grade(grade)
    parsed["grade_display"] = _display_grade(parsed["grade"], cleaned)
    parsed["template"] = template
    parsed["revised_date"] = parsed.get("revised_date") or parse_date(cleaned)
    parsed["cas"] = parsed.get("cas") or (_CAS.search(cleaned).group(1) if _CAS.search(cleaned) else None)
    parsed["family"] = classify_family(
        parsed["grade"], parsed.get("description") or "", parsed.get("chemical_name") or ""
    )
    parsed["confidence"] = _confidence(parsed, cleaned)
    parsed["raw_text"] = text
    parsed = maybe_llm_fill(parsed, cleaned)
    return parsed


def _prep(text: str) -> str:
    text = (text or "").replace("\u3000", " ").replace("\xa0", " ")
    text = text.replace("：", ":")
    text = re.sub(r"Storageandhandling", "Storage and handling", text, flags=re.I)
    text = re.sub(r"Storageand handling", "Storage and handling", text, flags=re.I)
    return text


def _display_grade(grade: str, text: str) -> str:
    if not grade:
        return "iLENE"
    m = re.search(r"iLENE[®\s]*[A-Za-z0-9+\-/% ]{1,40}", text, re.I)
    if m:
        name = collapse_ws(m.group(0).replace("®", " "))
        name = re.split(r"\s+Revised|\s+TDS|\s+SDS", name, maxsplit=1, flags=re.I)[0]
        return collapse_ws(name)
    return f"iLENE {grade}"


def _parse_pda(text: str) -> dict[str, Any]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = _DISCLAIMER.split(text, maxsplit=1)[0]
    product_line = next((ln for ln in lines if re.search(r"ilene", ln, re.I)), lines[0] if lines else "")
    product_line = re.split(r"Revised", product_line, maxsplit=1, flags=re.I)[0]
    grade = normalize_grade(product_line)
    sections = _split_pda_sections(body)
    description = collapse_ws(sections.get("description", ""))
    chem = _first_kv(sections.get("chemical name", "") or body, ("chemical name",))
    props_block = sections.get("physical properties") or sections.get("specifications") or ""
    properties = _parse_properties(props_block)
    if chem:
        properties.setdefault("chemical_name_raw", chem)
    highlights = _bullet_lines(sections.get("performance highlights", ""))
    applications = _split_apps(sections.get("applications", ""))
    package, storage = _split_package_storage(
        sections.get("package", ""),
        sections.get("storage and handling", "") or sections.get("storage", ""),
    )
    return {
        "grade": grade,
        "chemical_name": chem,
        "description": description,
        "properties": properties,
        "highlights": highlights,
        "applications": applications,
        "package": package,
        "storage": storage,
        "revised_date": parse_date(text),
    }


def _split_pda_sections(text: str) -> dict[str, str]:
    headings = [
        "description",
        "physical properties",
        "specifications",
        "performance highlights",
        "applications",
        "package",
        "chemical name",
        "storage and handling",
        "storage",
    ]
    pattern = re.compile(
        rf"(?im)^({'|'.join(re.escape(h) for h in headings)})\s*$"
    )
    found = list(pattern.finditer(text))
    sections: dict[str, str] = {}
    for i, match in enumerate(found):
        start = match.end()
        end = found[i + 1].start() if i + 1 < len(found) else len(text)
        sections[match.group(1).lower()] = text[start:end].strip()
    # Inline Chemical Name : value on same line as heading
    inline = re.search(r"(?im)^chemical name\s*[:：]\s*(.+)$", text)
    if inline and "chemical name" not in sections:
        sections["chemical name"] = inline.group(1).strip()
    cas_inline = re.search(r"(?im)^cas\s*(?:no\.?|number)\s*[:：]\s*(.+)$", text)
    if cas_inline:
        sections["cas"] = cas_inline.group(1).strip()
    return sections


def _parse_bjtds(text: str) -> dict[str, Any]:
    name = ""
    m = re.search(r"(?im)^name\s+(.+)$", text)
    if m:
        name = m.group(1).strip()
    chem = None
    cm = re.search(r"(?im)^chemical\s*name\s*[:：]?\s*(.+)$", text)
    if cm:
        chem = collapse_ws(cm.group(1))
    intro = _slice_between(text, r"(?im)^introduction\b", r"(?im)^(properties|features|application|packaging|precautions)\b")
    if intro:
        intro = re.sub(r"(?im)^cas\s*(?:no\.?|number)?\s*[:：]?\s*.+$", "", intro).strip()
        features = _bullet_lines(_slice_between(text, r"(?im)^features\b", r"(?im)^(application|packaging|precautions)\b") or "")
    apps_block = _slice_between(text, r"(?im)^application\b", r"(?im)^(packaging|precautions)\b") or ""
    applications = _split_apps(re.sub(r"[☆★]", " ", apps_block))
    props_block = _slice_between(text, r"(?im)^properties\b", r"(?im)^(features|application|packaging)\b") or ""
    properties = _parse_properties(re.sub(r"[☆★]", "\n", props_block))
    # stars on same lines as section titles
    for line in text.splitlines():
        if "☆" in line or "★" in line:
            bit = _STAR_LINE.sub("", line.split("☆", 1)[-1] if "☆" in line else line)
            parsed = _parse_properties(bit)
            for key, value in parsed.items():
                properties.setdefault(key, value)
            if ":" not in line and "☆" in line:
                feat = collapse_ws(_STAR_LINE.sub("", line.split("☆")[-1]))
                if feat and feat.lower() not in {h.lower() for h in features}:
                    if not re.match(r"(?i)(appearance|color|viscosity|solid|acid|water|cas)", feat):
                        if len(feat) > 8:
                            features.append(feat)
    package, storage = _split_package_storage(
        _slice_between(text, r"(?im)^packaging\b", r"(?im)^(precautions|disclaimer)\b") or "",
        _slice_between(text, r"(?im)^precautions\b", r"(?im)^disclaimer\b") or "",
    )
    description = collapse_ws(intro) if intro else ""
    return {
        "grade": normalize_grade(name),
        "chemical_name": chem,
        "description": description,
        "properties": properties,
        "highlights": _dedupe(features),
        "applications": applications,
        "package": package,
        "storage": storage,
        "revised_date": parse_date(text),
    }


def _split_package_storage(
    package: str | None, storage: str | None
) -> tuple[str | None, str | None]:
    pkg = collapse_ws(package or "")
    stor = collapse_ws(storage or "")

    marker = _STORAGE_MARKER.search(pkg)
    if marker:
        stor_part = collapse_ws(pkg[marker.end() :])
        pkg = collapse_ws(pkg[: marker.start()])
        stor = collapse_ws(f"{stor_part} {stor}".strip()) if stor_part and stor else (stor_part or stor)
        return _nullable(restore_pdf_spaces(pkg)), _nullable(restore_pdf_spaces(stor))

    if pkg and _PKG_SPEC.search(pkg):
        spec, rest = _extract_packaging_specs(pkg)
        if rest:
            pkg = spec
            stor = collapse_ws(f"{rest} {stor}".strip())

    return _nullable(restore_pdf_spaces(pkg)), _nullable(restore_pdf_spaces(stor))


def _extract_packaging_specs(text: str) -> tuple[str, str]:
    text = collapse_ws(text)
    matches = list(_PKG_SPEC.finditer(text))
    if not matches:
        return text, ""
    end = matches[-1].end()
    while end < len(text) and text[end] in ", ":
        end += 1
    return collapse_ws(text[:end]), collapse_ws(text[end:])


def _nullable(text: str) -> str | None:
    return text or None


def _slice_between(text: str, start_pat: str, end_pat: str) -> str:
    start = re.search(start_pat, text)
    if not start:
        return ""
    rest = text[start.end() :]
    end = re.search(end_pat, rest)
    return (rest[: end.start()] if end else rest).strip()


def _parse_properties(block: str) -> dict[str, Any]:
    props: dict[str, Any] = {}
    blob = block.replace("☆", "\n").replace("★", "\n")
    for raw_line in blob.splitlines():
        line = collapse_ws(raw_line)
        if not line or line.lower() in _STOP_HEADINGS:
            continue
        match = _KV.match(line)
        if not match:
            continue
        key = _norm_prop_key(match.group("key"))
        value = collapse_ws(match.group("value"))
        if not key or not value:
            continue
        props[key] = value
        if key == "viscosity":
            parsed_visc = _parse_viscosity(line + " " + value, value)
            if parsed_visc:
                props["viscosity_struct"] = parsed_visc
        if key == "functionality":
            num = re.search(r"(\d+(?:\.\d+)?)", value)
            if num:
                props["functionality_num"] = float(num.group(1))
    return props


def _norm_prop_key(key: str) -> str:
    k = collapse_ws(key).lower()
    k = k.replace(",", " ").replace(".", " ")
    k = re.sub(r"\s+", " ", k)
    mapping = {
        "appearance": "appearance",
        "color gardner": "color_gardner",
        "color apha": "color_apha",
        "color": "color",
        "molecular weight": "molecular_weight",
        "molecular weight mn": "molecular_weight",
        "viscosity": "viscosity",
        "hardness": "hardness",
        "shore hardness": "hardness",
        "solid content": "solid_content",
        "solidcontent": "solid_content",
        "oligomer": "oligomer",
        "functionality theoretical": "functionality",
        "functionality": "functionality",
        "purity": "purity",
        "water": "water",
        "water content": "water",
        "acid value": "acid_value",
        "acidity as maa": "acid_value",
        "active constituent": "active_constituent",
        "melting point": "melting_point",
        "density": "density",
        "softening point": "softening_point",
        "mehq content": "mehq",
        "insoluble matter": "insoluble_matter",
        "transmittance": "transmittance",
    }
    if k in mapping:
        return mapping[k]
    if k.startswith("viscosity"):
        return "viscosity"
    if k.startswith("color") and "gardner" in k:
        return "color_gardner"
    if k.startswith("color") and "apha" in k:
        return "color_apha"
    if k.startswith("molecular weight"):
        return "molecular_weight"
    if k.startswith("solid"):
        return "solid_content"
    if k.startswith("functionality"):
        return "functionality"
    if k.startswith("acid"):
        return "acid_value"
    if k.startswith("water"):
        return "water"
    if k.startswith("purity"):
        return "purity"
    slug = re.sub(r"[^a-z0-9]+", "_", k).strip("_")
    return slug[:40]


def _parse_viscosity(line: str, value: str) -> dict[str, Any] | None:
    temp = None
    tm = re.search(r"[@/]\s*(\d+)\s*[℃°C]?", line, re.I)
    if not tm:
        tm = re.search(r"(\d+)\s*[℃°C]", line)
    if tm:
        temp = int(tm.group(1))
    unit = "cPs"
    if re.search(r"mPa", line, re.I):
        unit = "mPa.s"
    nums = re.findall(r"(\d+(?:,\d{3})*(?:\.\d+)?)", value.replace(",", ""))
    if not nums:
        return None
    values = [float(n.replace(",", "")) for n in nums[:2]]
    return {
        "raw": collapse_ws(value),
        "min": values[0],
        "max": values[-1],
        "unit": unit,
        "temp_c": temp,
    }


def _bullet_lines(block: str) -> list[str]:
    items: list[str] = []
    for line in (block or "").splitlines():
        line = collapse_ws(_STAR_LINE.sub("", line))
        if not line:
            continue
        if _KV.match(line):
            continue
        items.append(line)
    return _dedupe(items)


def _split_apps(block: str) -> list[str]:
    text = collapse_ws(re.sub(r"[☆★]", " ", block or ""))
    text = re.sub(r"(?i)^used as\s+", "", text)
    text = re.sub(r"(?i)^recommended (?:for use in|for|addition[^.]*:)\s+", "", text)
    if not text:
        return []
    parts = re.split(r",|;|/|\band\b", text)
    return _dedupe([collapse_ws(p).rstrip(".") for p in parts if len(collapse_ws(p)) > 2])


def _first_kv(block: str, keys: tuple[str, ...]) -> str | None:
    for line in (block or "").splitlines():
        match = _KV.match(collapse_ws(line))
        if match and match.group("key").lower().strip() in keys:
            return collapse_ws(match.group("value"))
    match = re.search(r"(?im)chemical name\s*[:：]\s*(.+)$", block)
    return collapse_ws(match.group(1)) if match else None


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _confidence(parsed: dict[str, Any], text: str) -> float:
    score = 0.4
    if parsed.get("grade"):
        score += 0.15
    if parsed.get("description"):
        score += 0.15
    if parsed.get("applications"):
        score += 0.15
    if parsed.get("properties"):
        score += 0.1
    if parsed.get("highlights"):
        score += 0.05
    if len(text) < 80:
        score -= 0.3
    return round(min(max(score, 0.0), 1.0), 2)
