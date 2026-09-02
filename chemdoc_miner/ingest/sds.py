from __future__ import annotations

import re
from typing import Any

from chemdoc_miner.normalize import collapse_ws, grade_from_filename, normalize_grade, parse_date

_CAS = re.compile(r"\b(\d{2,7}-\d{2}-\d)\b")
_H_CODE = re.compile(r"\b(H\d{3}[A-Za-z]*)\b")
_P_CODE = re.compile(r"\b(P\d{3}(?:\+P\d{3})*)\b")
_SECTION = re.compile(
    r"(?im)(?:^|\n)\s*(\d{1,2})\.\s*"
    r"(CHEMICAL PRODUCT|HAZARD|COMPOSITION|FIRST AID|FIRE|ACCIDENTAL|HANDLING|"
    r"EXPOSURE|PHYSICAL|STABILITY|TOXICOLOG|ECOLOG|DISPOSAL|TRANSPORT|REGULAT|OTHER)"
)
_SIGNAL_WORDS = frozenset({"DANGER", "WARNING", "NONE", "NONE."})

_PICTOGRAM_RULES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    ("GHS06", "Skull and Crossbones", "骷髅", ("H300", "H301", "H310", "H311", "H330", "H331")),
    ("GHS05", "Corrosion", "腐蚀", ("H314", "H318")),
    (
        "GHS08",
        "Health Hazard",
        "健康危害",
        ("H334", "H340", "H341", "H350", "H351", "H360", "H361", "H370", "H371", "H372"),
    ),
    (
        "GHS07",
        "Exclamation Mark",
        "感叹号",
        ("H302", "H312", "H315", "H317", "H319", "H332", "H335", "H336"),
    ),
    ("GHS09", "Environment", "环境", ("H400", "H410", "H411", "H412", "H413")),
    ("GHS02", "Flame", "火焰", ("H224", "H225", "H226", "H228")),
    ("GHS03", "Flame Over Circle", "火焰圆圈", ("H240", "H241", "H242")),
    ("GHS04", "Gas Cylinder", "气瓶", ("H280", "H281")),
)


_FIELD_STOP = (
    r"Synonyms?\s*:|Company\s*:|Address\s*:|Telephone\s*:|Email\s*:|"
    r"Intended(?:/Recommended)?\s+Use\s*:|Limited Use\s*:|Business Emergency|"
    r"National Chemical|\d{1,2}\.\s*[A-Z]"
)


def parse_sds(text: str, filename: str = "") -> dict[str, Any]:
    body = _prep(text)
    sections = _split_sections(body)
    sec1 = sections.get(1, "")
    sec2 = sections.get(2, "")
    sec3 = sections.get(3, "")
    sec7 = sections.get(7, "")
    sec8 = sections.get(8, "")
    sec9 = sections.get(9, "")
    sec10 = sections.get(10, "")
    sec14 = sections.get(14, "")
    sec15 = sections.get(15, "")

    product = _field_until(sec1 or body, r"Product Name\s*:", _FIELD_STOP)
    company = _field_until(sec1 or body, r"Company\s*:", _FIELD_STOP) or _field(
        body, r"(POWERDREAM[^\n]+|Power\s*Dream[^\n]+)"
    )
    synonyms = _field_until(sec1, r"Synonyms?\s*:", _FIELD_STOP)
    intended_use = _extract_intended_use(sec1)
    emergency_phone = _field_until(sec1, r"(?:Business Emergency Telephone|Telephone)\s*:", _FIELD_STOP)

    ghs_categories = _ghs_categories(sec2)
    hazard_statements = _hazard_statements(sec2 or body)
    precautionary = _precautionary_statements(sec2 or body)
    signal = _signal_word(sec2 or body)
    label_elements = {
        "product_identifier": collapse_ws(product or ""),
        "pictograms": _derive_pictograms(hazard_statements, ghs_categories),
        "signal_word": signal,
        "hazard_statements": hazard_statements,
        "precautionary_statements": precautionary,
    }

    components = _components(sec3 or body)
    cas_list = [c["cas"] for c in components if c.get("cas")]
    if not cas_list:
        cas_list = list(dict.fromkeys(_CAS.findall(body)))

    transport = _parse_transport(sec14)
    regulatory = _parse_regulatory(sec15)
    handling, storage_sds = _parse_handling_storage(sec7)
    ppe = _parse_ppe(sec8)
    physical_safety = _parse_physical_safety(sec9)
    incompatibles, stability_notes = _parse_stability(sec10)
    hazard_flags = _hazard_flags(hazard_statements, ghs_categories)

    ghs = _legacy_ghs(ghs_categories, hazard_statements)
    sds_summary = {
        "label_elements": label_elements,
        "ghs_categories": ghs_categories,
        "hazard_flags": hazard_flags,
        "components": components,
        "synonyms": synonyms,
        "intended_use": intended_use,
        "emergency_phone": emergency_phone,
        "handling": handling,
        "storage_sds": storage_sds,
        "incompatibles": incompatibles,
        "stability_notes": stability_notes,
        "ppe": ppe,
        "physical_safety": physical_safety,
        "transport": transport,
        "regulatory": regulatory,
        "revised_date": parse_date(body),
    }

    grade = normalize_grade(product or grade_from_filename(filename))
    if len(grade) > 40:
        grade = normalize_grade(grade_from_filename(filename))
    chemical_name = synonyms if synonyms and synonyms.lower() != "none" else None
    if not chemical_name and components:
        chemical_name = components[0].get("name") or None

    return {
        "grade": grade,
        "product_name": collapse_ws(product or ""),
        "company": collapse_ws(company or "POWERDREAM AMERICA INC"),
        "chemical_name": chemical_name,
        "signal_word": signal,
        "ghs": ghs,
        "ghs_categories": ghs_categories,
        "label_elements": label_elements,
        "hazard_flags": hazard_flags,
        "components": components,
        "cas_list": cas_list,
        "synonyms": synonyms,
        "intended_use": intended_use,
        "emergency_phone": emergency_phone,
        "sds_summary": sds_summary,
        "revised_date": parse_date(body),
        "raw_text": text,
    }


def _prep(text: str) -> str:
    text = (text or "").replace("\u3000", " ").replace("\xa0", " ")
    text = text.replace("：", ":")
    text = re.sub(r"Signalword", "Signal word", text, flags=re.I)
    text = re.sub(r"Precautionary statement[s]?", "Precautionary statements", text, flags=re.I)
    return text


def _split_sections(text: str) -> dict[int, str]:
    markers = list(_SECTION.finditer(text))
    sections: dict[int, str] = {}
    for index, match in enumerate(markers):
        number = int(match.group(1))
        start = match.end()
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        sections[number] = text[start:end].strip()
    return sections


def _field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.I)
    if not match:
        return None
    value = collapse_ws(match.group(1).split("SDS")[0])
    return value or None


def _field_until(text: str, start_pat: str, stop_pat: str) -> str | None:
    match = re.search(rf"{start_pat}\s*(.+?)(?={stop_pat}|$)", text, re.I | re.S)
    if not match:
        return None
    value = collapse_ws(match.group(1).split("SDS")[0])
    return value or None


def _extract_intended_use(sec1: str) -> str | None:
    match = re.search(
        r"Intended/Recommended Use\s*:\s*(.+?)(?:Limited Use|Business Emergency|Telephone|\d+\.)",
        sec1,
        re.I | re.S,
    )
    if match:
        value = collapse_ws(match.group(1))
        if value:
            return value
    match = re.search(
        r"(?:Intended|Recommended)\s+Use\s*:\s*(.+?)(?:Limited Use|Business Emergency|Telephone|\d+\.)",
        sec1,
        re.I | re.S,
    )
    if match:
        value = collapse_ws(match.group(1))
        if value:
            return value
    match = re.search(
        r"([^\n]+(?:,\s*[^\n]+)*)\s*\n\s*Intended/Recommended Use\s*:\s*\n?\s*([^\n.]+)",
        sec1,
        re.I,
    )
    if match:
        return collapse_ws(f"{match.group(1)} {match.group(2)}")
    return None


def _ghs_categories(sec2: str) -> list[str]:
    match = re.search(
        r"GHS classification:\s*(.+?)(?:Label elements:|Precautionary|Signal word)",
        sec2,
        re.I | re.S,
    )
    if not match:
        return []
    items: list[str] = []
    for line in match.group(1).splitlines():
        line = collapse_ws(line)
        if not line or line.lower().startswith("ghs"):
            continue
        if _H_CODE.search(line):
            continue
        items.append(line)
    return _dedupe(items)


def _signal_word(sec2: str) -> str | None:
    match = re.search(
        r"Label elements:\s*Signal word\s*:\s*([A-Za-z.]+)",
        sec2,
        re.I | re.S,
    )
    if match:
        word = collapse_ws(match.group(1)).upper().rstrip(".")
        if word in _SIGNAL_WORDS or word in {"DANGER", "WARNING"}:
            return "DANGER" if word.startswith("DANGER") else "WARNING" if word.startswith("WARNING") else None
    match = re.search(r"Signal word\s*:\s*(DANGER|WARNING)\b", sec2, re.I)
    if match:
        return match.group(1).upper()
    return None


def _hazard_statements(sec2: str) -> list[dict[str, str]]:
    match = re.search(
        r"Label elements:\s*(.+?)(?:Precautionary statements|Precautionary statement)",
        sec2,
        re.I | re.S,
    )
    block = match.group(1) if match else sec2
    block = re.sub(r"\b\d{1,2}/\d{1,2}\b", " ", block)
    block = re.split(r"SAFETY DATA SHEET", block, maxsplit=1, flags=re.I)[0]
    statements = _parse_h_code_lines(block)
    if not statements:
        plain_block = re.sub(r"Signal word\s*:\s*(?:DANGER|WARNING)\.?\s*", "", block, flags=re.I)
        for line in re.split(r"\n+", plain_block):
            line = collapse_ws(line.rstrip("."))
            if len(line) < 12:
                continue
            if re.match(
                r"^(Causes|May cause|Harmful|Toxic|Suspected|Fatal|Flammable|Combustible)",
                line,
                re.I,
            ):
                statements.append({"code": "", "text": f"{line}."})
    if not statements:
        statements = _parse_h_code_lines(sec2)
    return _dedupe_h_statements(statements)


def _parse_h_code_lines(block: str) -> list[dict[str, str]]:
    statements: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in re.finditer(r"\b(H\d{3}[A-Za-z]*)\s*[-–:]\s*([^\n]+)", block, re.I):
        code = match.group(1).upper()
        if code in seen:
            continue
        seen.add(code)
        statements.append({"code": code, "text": collapse_ws(match.group(2))})
    return statements


def _dedupe_h_statements(statements: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for item in statements:
        key = (item.get("code") or "") + "|" + item["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _precautionary_statements(sec2: str) -> dict[str, list[dict[str, str]]]:
    match = re.search(r"Precautionary statements\s*:?\s*(.+)", sec2, re.I | re.S)
    groups = {"prevention": [], "response": [], "storage": [], "disposal": []}
    if not match:
        return groups
    blob = re.split(
        r"(?:Other hazards|Environmental hazards|Health hazard:|\n\d{1,2}\.\s*[A-Z]|SAFETY DATA SHEET)",
        match.group(1),
        maxsplit=1,
        flags=re.I,
    )[0]
    group_aliases = {
        "prevention": ("prevention",),
        "response": ("response", "responds"),
        "storage": ("storage",),
        "disposal": ("disposal",),
    }
    for group_name, aliases in group_aliases.items():
        alias_pat = "|".join(aliases)
        group_match = re.search(
            rf"●?\s*(?:{alias_pat})\s*:\s*(.+?)(?=●?\s*(?:prevention|response|responds|storage|disposal)\s*:|$)",
            blob,
            re.I | re.S,
        )
        if not group_match:
            continue
        chunk = group_match.group(1)
        seen: set[str] = set()
        for code_match in re.finditer(r"\b(P\d{3}(?:\+P\d{3})*)\s*[:：]\s*", chunk, re.I):
            code = code_match.group(1).upper()
            if code in seen:
                continue
            seen.add(code)
            start = code_match.end()
            next_code = re.search(r"\bP\d{3}", chunk[start:])
            end = start + next_code.start() if next_code else len(chunk)
            text = collapse_ws(chunk[start:end])
            groups[group_name].append({"code": code, "text": text})
        if not groups[group_name]:
            for sentence in re.split(r"(?<=[.;])\s+", collapse_ws(chunk)):
                sentence = collapse_ws(sentence)
                if len(sentence) >= 12:
                    groups[group_name].append({"code": "", "text": sentence})
    return groups


def _derive_pictograms(
    hazard_statements: list[dict[str, str]], ghs_categories: list[str]
) -> list[dict[str, Any]]:
    codes = {item["code"] for item in hazard_statements if item.get("code")}
    categories = " ".join(ghs_categories).lower()
    texts = " ".join(item["text"] for item in hazard_statements).lower()
    found: list[dict[str, Any]] = []
    seen_pictos: set[str] = set()

    def add(code: str, name: str, name_zh: str, derived_from: list[str]) -> None:
        if code in seen_pictos:
            return
        seen_pictos.add(code)
        found.append(
            {
                "code": code,
                "name": name,
                "name_zh": name_zh,
                "derived_from": derived_from,
                "source": "inferred_from_h_codes",
            }
        )

    for picto, name, name_zh, prefixes in _PICTOGRAM_RULES:
        matched = sorted(
            h for h in codes if any(h.startswith(prefix) for prefix in prefixes)
        )
        if matched:
            add(picto, name, name_zh, matched)

    if re.search(r"aquatic|environment", categories + " " + texts) and "GHS09" not in seen_pictos:
        add("GHS09", "Environment", "环境", ["category"])
    if re.search(r"reproductive|carcinogen|mutagen|respiratory sensit", categories + " " + texts):
        if "GHS08" not in seen_pictos:
            add("GHS08", "Health Hazard", "健康危害", ["category"])
    if re.search(r"skin irrit|eye irrit|allergic|respiratory irrit", texts) and "GHS07" not in seen_pictos:
        add("GHS07", "Exclamation Mark", "感叹号", ["text"])

    order = [rule[0] for rule in _PICTOGRAM_RULES]
    found.sort(key=lambda item: order.index(item["code"]) if item["code"] in order else 99)
    return found


def _components(sec3: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in sec3.splitlines():
        line = collapse_ws(line)
        if not line:
            continue
        lower = line.lower()
        if "chemical component" in lower or "concentration" in lower and "cas" in lower:
            continue
        match = re.match(
            r"^(.+?)\s+([\d.<>\-]+(?:-[\d.]+)?%?|≥[\d.]+%?|-)\s+(\d{2,7}-\d{2}-\d|-)\s*$",
            line,
            re.I,
        )
        if match:
            name, wt, cas = match.groups()
            rows.append(
                {
                    "name": collapse_ws(name),
                    "wt": collapse_ws(wt),
                    "cas": cas if cas != "-" else "",
                }
            )
            continue
        for cas in dict.fromkeys(_CAS.findall(line)):
            rows.append({"cas": cas, "name": "", "wt": ""})
    return _dedupe_components(rows)


def _parse_handling_storage(sec7: str) -> tuple[list[str], str | None]:
    if not sec7:
        return [], None
    handling_block = _slice_between(sec7, r"(?i)^Handling\s*:", r"(?i)^Precautions for storage")
    storage_block = _slice_between(sec7, r"(?i)^Precautions for storage\s*:", r"$")
    handling = _bulletize(handling_block)
    storage = collapse_ws(storage_block) or None
    return handling, storage


def _parse_ppe(sec8: str) -> dict[str, str | None]:
    if not sec8:
        return {}
    fields = {
        "respiratory": _slice_between(sec8, r"(?i)Respiratory protection\s*:", r"(?i)Hand protection|Skin protection|$"),
        "gloves": _slice_between(sec8, r"(?i)(?:Hand protection|Skin protection)\s*:", r"(?i)Eye protection|Body protection|$"),
        "eye": _slice_between(sec8, r"(?i)Eye protection\s*:", r"(?i)Body protection|Other protection|$"),
        "ventilation": _slice_between(sec8, r"(?i)Engineering measures\s*:", r"(?i)Personal protective equipment|$"),
    }
    return {key: collapse_ws(value) if value else None for key, value in fields.items()}


def _parse_physical_safety(sec9: str) -> dict[str, str | None]:
    if not sec9:
        return {}
    props: dict[str, str | None] = {}
    for key, pattern in {
        "flash_point": r"Flash point\s*[:：]?\s*([^\n]+)",
        "density": r"Relative density(?:\(water=1\))?\s*[:：]?\s*([^\n]+)",
        "water_solubility": r"Solubility\s*[:：]?\s*([^\n]+)",
        "appearance": r"Color/Appearance\s*[:：]?\s*([^\n]+)",
        "flammability": r"Flammability\s*[:：]?\s*([^\n]+)",
    }.items():
        match = re.search(pattern, sec9, re.I)
        props[key] = collapse_ws(match.group(1)) if match else None
    return props


def _parse_stability(sec10: str) -> tuple[list[str], str | None]:
    if not sec10:
        return [], None
    incompat = _slice_between(sec10, r"(?i)Incompatible substances\s*:", r"(?i)Decomposition products|$")
    incompatibles = [
        collapse_ws(part)
        for part in re.split(r",|;", incompat or "")
        if collapse_ws(part)
    ]
    stability = _slice_between(sec10, r"(?i)^Stability\s*:", r"(?i)^Reactivity\s*:")
    reactivity = _slice_between(sec10, r"(?i)^Reactivity\s*:", r"(?i)^Avoid contact conditions\s*:")
    notes = collapse_ws(" ".join(filter(None, [stability, reactivity]))) or None
    return incompatibles, notes


def _parse_transport(sec14: str) -> dict[str, Any]:
    if not sec14:
        return {}
    un_match = re.search(r"UN\s*(?:No\.?|Number)?\s*[:：]?\s*(?:UN\s*)?(\d{4})", sec14, re.I)
    not_regulated = bool(
        re.search(r"not (?:classified|regulated|a dangerous|restricted)", sec14, re.I)
    )
    shipping = _field_until(sec14, r"(?:Normal Shipping name|Proper shipping name)\s*:", _FIELD_STOP)
    hazard_class = _field_until(sec14, r"(?:Hazard Classification|Transport hazard class)\s*:", _FIELD_STOP)
    packing = _field_until(sec14, r"Packing Category\s*:", _FIELD_STOP)
    marine = re.search(r"Marine Pollutants?\s*:\s*(.+)", sec14, re.I)
    marine_val = collapse_ws(marine.group(1)).lower() if marine else ""
    return {
        "un_number": f"UN{un_match.group(1)}" if un_match else None,
        "proper_shipping_name": shipping,
        "hazard_class": hazard_class,
        "packing_group": packing,
        "marine_pollutant": "applicable" in marine_val or "yes" in marine_val,
        "not_regulated": not_regulated and not un_match,
    }


def _parse_regulatory(sec15: str) -> dict[str, Any]:
    if not sec15:
        return {"summary_flags": []}
    flags: list[str] = []
    checks = [
        ("tsca_active", r"United States.*?TSCA.*?Active"),
        ("iecsc_ok", r"China.*?IECSC|Chinese inventory"),
        ("dsl_ok", r"Canada.*?DSL"),
        ("einecs_ok", r"European.*?EINECS|ELINCS|NLP"),
        ("aiic_ok", r"Australia.*?AIIC"),
        ("encs_ok", r"Japan.*?ENCS"),
        ("reach_ok", r"United Kingdom.*?REACH|REACH Regulation"),
    ]
    summary: dict[str, str | None] = {}
    for key, pattern in checks:
        match = re.search(pattern, sec15, re.I | re.S)
        if match:
            flags.append(key)
            summary[key.replace("_ok", "").replace("_active", "")] = collapse_ws(match.group(0))[:200]
    return {"summary_flags": flags, **summary}


def _hazard_flags(
    hazard_statements: list[dict[str, str]], ghs_categories: list[str]
) -> list[str]:
    codes = {item["code"] for item in hazard_statements}
    cats = " ".join(ghs_categories).lower()
    flags: list[str] = []
    mapping = [
        ("skin_irritation", lambda: any(c.startswith("H315") for c in codes)),
        ("skin_sensitization", lambda: any(c.startswith("H317") for c in codes) or "sensitization" in cats),
        ("eye_irritation", lambda: any(c.startswith("H319") for c in codes) or "eye" in cats),
        ("respiratory_irritation", lambda: any(c.startswith("H335") for c in codes)),
        ("reproductive_toxicity", lambda: any(c.startswith("H360") or c.startswith("H361") for c in codes) or "reproductive" in cats),
        ("aquatic_hazard", lambda: any(c.startswith("H4") for c in codes) or "aquatic" in cats),
        ("carcinogen_suspect", lambda: any(c.startswith("H351") for c in codes) or "carcinogen" in cats),
    ]
    for name, check in mapping:
        if check():
            flags.append(name)
    return flags


def _legacy_ghs(categories: list[str], hazard_statements: list[dict[str, str]]) -> list[str]:
    items = list(categories)
    for stmt in hazard_statements:
        items.append(f"{stmt['code']} - {stmt['text']}")
    return _dedupe(items)[:20]


def _slice_between(text: str, start_pat: str, end_pat: str) -> str:
    start = re.search(start_pat, text, re.I | re.S)
    if not start:
        return ""
    rest = text[start.end() :]
    end = re.search(end_pat, rest, re.I | re.S)
    return (rest[: end.start()] if end else rest).strip()


def _bulletize(block: str) -> list[str]:
    if not block:
        return []
    parts = re.split(r"(?<=[.;])\s+", collapse_ws(block))
    return [collapse_ws(part) for part in parts if len(collapse_ws(part)) > 8]


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


def _dedupe_components(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    out: list[dict[str, str]] = []
    for row in rows:
        key = (row.get("name", ""), row.get("wt", ""), row.get("cas", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out
