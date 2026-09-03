from __future__ import annotations

import re
from datetime import date

_GRADE_STRIP = re.compile(
    r"(?i)\b(ilene|acrylate|photoinitiator|petroleum\s+resins?|polythiol|tds|sds)\b"
)
_COPY_SUFFIX = re.compile(r"(?:\s+[12]|\s+_+$|_+$|\s+\(\d+\))$")

_COMPANY_ALIASES = {
    "allnex": "Allnex",
    "ebecryl": "Allnex",
    "eb": "Allnex",
    "ucecoat": "Allnex",
    "sartomer": "Sartomer",
    "arkema": "Sartomer",
    "igm": "IGM",
    "photomer": "IGM",
    "omnirad": "IGM",
    "miwon": "Miwon",
    "miramer": "Miwon",
    "qualipoly": "Qualipoly",
    "eternal": "Eternal",
    "rahn": "RAHN",
    "genomer": "RAHN",
    "covestro": "Covestro",
    "basf": "BASF",
    "laromer": "BASF",
    "dsm": "DSM",
    "dymax": "Dymax",
    "agi": "AGI",
    "agisyn": "AGI",
    "kowa": "Kowa",
    "akzo": "Akzo",
    "actilane": "Akzo",
    "soltech": "Soltech",
    "melrob": "Soltech",
    "litian": "Litian",
    "shin-nakamura": "Shin-Nakamura",
    "power dream": "Power Dream",
    "powerdream": "Power Dream",
    "ilene": "Power Dream",
    "dbc": "DBC",
    "iht": "IHT",
    "deuteron": "Deuteron",
    "dow": "Dow",
    "lambson": "Arkema Lambson",
    "synasia": "Synasia",
    "mitsubishi": "Mitsubishi",
    "jiuri": "Jiuri",
    "tronly": "Tronly",
    "bch": "BCH",
    "chitec": "Chitec",
    "gurun": "Gurun",
    "phichem": "Phichem",
    "uv chemkeys": "UV Chemkeys",
    "byk": "BYK",
    "tego": "Tego",
    "dowsil": "Dow",
    "additol": "Allnex",
    "omnivadd": "IGM",
}


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def restore_pdf_spaces(text: str | None) -> str | None:
    """Re-insert spaces lost when PDF text is extracted without word boundaries."""
    if not text:
        return text
    raw = (text or "").replace("\u3000", " ").replace("\xa0", " ")
    t = re.sub(r"\.([A-Za-z])", r". \1", raw)
    t = re.sub(r"([a-z])([A-Z])", r"\1 \2", t)
    t = _touch_up_partial_pdf_spaces(t)
    if _pdf_text_looks_spaced(t):
        return t
    phrases = sorted(
        [
            "Storage and handling",
            "Do not expose the product to high temperature conditions or to direct sunlight",
            "Do not expose the product to high temperature conditions",
            "Do not expose the product",
            "Store at room temperature",
            "high temperature conditions",
            "direct sunlight",
            "room temperature",
            "the product",
            "conditions or",
            "Storage and",
        ],
        key=len,
        reverse=True,
    )
    compact = t.replace(" ", "")
    for phrase in phrases:
        glued = phrase.replace(" ", "")
        if glued.lower() in compact.lower():
            t = re.sub(re.escape(glued), phrase, t, flags=re.I)
    t = _touch_up_partial_pdf_spaces(t)
    return collapse_ws(t)


def _pdf_text_looks_spaced(text: str) -> bool:
    words = text.split()
    if len(words) < 4:
        return True
    avg_len = sum(len(word) for word in words) / len(words)
    long_words = sum(1 for word in words if len(word) > 18)
    return avg_len < 11 and long_words == 0


def _touch_up_partial_pdf_spaces(text: str) -> str:
    t = text
    replacements = [
        (r"Donotexpose", "Do not expose"),
        (r"donotexpose", "do not expose"),
        (r"theproduct", "the product"),
        (r"productto", "product to"),
        (r"tohigh", "to high"),
        (r"hightemperatureconditions", "high temperature conditions"),
        (r"hightemperature", "high temperature"),
        (r"conditionsor", "conditions or"),
        (r"ortodirect", "or to direct"),
        (r"orto", "or to"),
        (r"todirect", "to direct"),
        (r"directsunlight", "direct sunlight"),
        (r"Storeatroomtemperature", "Store at room temperature"),
        (r"Storeat", "Store at"),
        (r"roomtemperature", "room temperature"),
        (r"Storageandhandling", "Storage and handling"),
        (r"exposetheproduct", "expose the product"),
        (r"exposethe", "expose the"),
    ]
    for pattern, repl in replacements:
        t = re.sub(pattern, repl, t, flags=re.I)
    return collapse_ws(t)


def normalize_grade(raw: str | None) -> str:
    if not raw:
        return ""
    text = str(raw).replace("®", " ").replace("＋", "+").replace("–", "-").replace("—", "-")
    text = _GRADE_STRIP.sub(" ", text)
    text = collapse_ws(text.replace("_", " ")).strip(" -_,.")
    letter_suffix = re.fullmatch(r"(\d+)\s+([A-Za-z]\d*)", text)
    if letter_suffix:
        return (letter_suffix.group(1) + letter_suffix.group(2)).upper()
    text = text.upper()
    if "+" not in text and "/" not in text and "%" not in text and "," not in text:
        text = re.sub(r"\s+", "", text)
    else:
        text = re.sub(r"\s+", "", text)
    return text


def grade_from_filename(filename: str) -> str:
    stem = filename.rsplit("/", 1)[-1]
    stem = re.sub(r"\.pdf$", "", stem, flags=re.I)
    stem = re.sub(r"(?i)^tds[_\s\-]*", "", stem)
    stem = re.sub(r"(?i)^sds[_\s\-]*", "", stem)
    stem = re.sub(r"(?i)[_\s]*tds.*$", "", stem)
    stem = re.sub(r"(?i)[_\s]*sds.*$", "", stem)
    stem = re.sub(r"(?i)_en$", "", stem)
    stem = re.sub(r"\s+\d{2}$", "", stem)
    stem = _COPY_SUFFIX.sub("", stem)
    stem = collapse_ws(stem.replace("_", " "))
    if "," in stem:
        stem = stem.split(",", 1)[0]
    return normalize_grade(stem)


def split_combo_grades(grade: str) -> list[str]:
    if not grade:
        return []
    parts = re.split(r"[/,]", grade)
    out: list[str] = []
    for part in parts:
        cleaned = normalize_grade(part)
        if cleaned and cleaned not in out:
            out.append(cleaned)
    return out


def parse_date(text: str | None) -> str | None:
    if not text:
        return None
    t = text.replace("：", ":")
    m = re.search(
        r"(?:revision\s*date|revisiondate|revised\s*date|date of\s*issue)\s*:\s*(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})",
        t,
        re.I,
    )
    if m:
        return _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.search(
        r"(?:revision\s*date|revised\s*date)\s*:\s*(\d{1,2})\s*/\s*(\d{1,2})\s*/\s*(\d{4})",
        t,
        re.I,
    )
    if m:
        return _iso(int(m.group(3)), int(m.group(1)), int(m.group(2)))
    return None


def _iso(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def date_sort_key(iso: str | None) -> str:
    return iso or "0000-00-00"


def canonical_company(raw: str | None) -> str:
    if not raw:
        return ""
    key = collapse_ws(str(raw)).lower()
    if "power" in key and "dream" in key:
        return "Power Dream"
    if "ilene" in key:
        return "Power Dream"
    # AgiSyn / DSM-AGI UV resins: keep ECR-aligned company key even when header says Covestro (AGI).
    if "agi" in key and ("covestro" in key or "agisyn" in key):
        return "AGI"
    for alias, name in sorted(_COMPANY_ALIASES.items(), key=lambda kv: -len(kv[0])):
        if alias in key:
            return name
    first = re.split(r"\s{2,}|\(|/", key)[0].strip()
    return _COMPANY_ALIASES.get(first, collapse_ws(str(raw)).title())


def xref_member_company(header: str | None, raw_cell: str | None) -> str:
    """Resolve xref member company from sheet column header and cell text."""
    company = canonical_company(header)
    raw = collapse_ws(str(raw_cell or ""))
    if not raw:
        return company
    low = raw.lower()
    if company == "AGI":
        # German Covestro SKUs (e.g. Covestro P-50) are not AgiSyn / DSM-AGI products.
        if re.match(r"covestro\s+p[\-\s]?\d", low):
            return "Covestro"
        if low.startswith("covestro") and "agisyn" not in low:
            return "Covestro"
    return company


def looks_like_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    text = collapse_ws(str(value))
    if not text:
        return True
    low = text.lower()
    return low.startswith("x-not yet") or low in {"tbd", "n/a", "na", "-", "?", "x"}


def canonical_grade(raw: str | None, company: str | None = None, *, domain: str | None = None) -> str:
    """Map Excel/raw text to one standard SKU per (company, product)."""
    if not raw or looks_like_placeholder(raw):
        return ""
    name = canonical_company(company) if company else ""
    text = collapse_ws(str(raw)).strip("*").strip()
    text = re.sub(r"\s*\([^)]*\)\s*", " ", text).strip()

    if name == "Power Dream":
        first = re.split(r"[/,]", text)[0].strip()
        return normalize_grade(first)

    if name == "IGM":
        if domain == "additives":
            core = re.sub(r"(?i)^omnivadd\s*", "", text).strip()
            return normalize_grade(core.replace(" ", "")) or normalize_grade(text)
        if domain == "pi":
            for pat in (
                r"(?i)(?:omnirad|esacure|omnipol|photomer|ph)\s*[-]?\s*(\d+[a-z0-9\-]*)",
                r"(?i)^(\d+[a-z0-9\-]*)$",
            ):
                m = re.search(pat, text.replace(" ", " ") if pat.endswith("$") else text)
                if m:
                    return normalize_grade(m.group(1))
            return normalize_grade(text)
        m = re.match(r"(?i)(?:photomer|ph)\s*[-]?\s*(.+)", text)
        if m:
            core = re.sub(r"\s+", "", m.group(1)).upper()
            if domain == "offsets":
                mnum = re.match(r"(\d+)(.*)", core)
                if mnum:
                    suffix = mnum.group(2)
                    return mnum.group(1) + suffix if suffix else mnum.group(1)
            return normalize_grade(core)
        return normalize_grade(re.sub(r"\s+", "", text))

    if name == "Allnex":
        m = re.match(r"(?i)(?:ebecryl|eb|additol)\s*[-]?\s*(.+)", text)
        token = re.sub(r"\s+", "", (m.group(1) if m else text)).upper()
        if re.fullmatch(r"\d+[A-Z0-9\-]*", token):
            token = "EB" + token
        elif re.fullmatch(r"\d+[A-Z0-9\-]*", token.lstrip("EB")):
            token = "EB" + token.lstrip("EB")
        return normalize_grade(token)

    if name == "Sartomer":
        m = re.match(r"(?i)(?:sr|cn|mcure|m-cure)\s*[-]?\s*(.+)", re.sub(r"\s+", "", text))
        if m:
            prefix = "SR" if text.upper().lstrip().startswith("SR") else "CN"
            if "MCURE" in text.upper().replace(" ", ""):
                prefix = "MCURE"
            body = re.sub(r"\s+", "", m.group(1)).upper()
            return normalize_grade(prefix + body)
        return normalize_grade(re.sub(r"\s+", "", text))

    if name == "BCH" and domain == "pi":
        m = re.search(r"(\d+[A-Z]?)", text.replace(" ", ""))
        if m:
            return m.group(1).upper()

    if name == "Tronly" and domain == "pi":
        m = re.search(r"(?i)TR[-]?(\d+[A-Z0-9]*)", text)
        if m:
            return f"TR-{m.group(1).upper()}"

    if name == "Jiuri" and domain == "pi":
        m = re.search(r"(?i)JR\s*CURE\s*(\d+)", text)
        if m:
            return f"JRCURE{m.group(1)}"

    if name == "AGI":
        m = re.match(r"(?i)(?:agisyn|agi[-\s]?syn)\s*[-]?\s*(\d+[a-z0-9]*)", text)
        if m:
            return normalize_grade(m.group(1))
        compact = re.sub(r"\s+", "", text).upper()
        m = re.match(r"(?i)AGISYN(\d+[A-Z0-9]*)", compact)
        if m:
            return normalize_grade(m.group(1))
        if re.fullmatch(r"\d+[A-Z0-9]*", compact):
            return normalize_grade(compact)

    if name == "Covestro":
        m = re.match(r"(?i)(?:covestro\s*)?p[\-\s]?(\d+)\s*$", collapse_ws(text))
        if m:
            return f"COVESTROP-{m.group(1)}"

    token = re.sub(r"\s+", "", text).upper()
    return normalize_grade(token) or token


def grade_query_variants(query: str, company: str | None = None, *, domain: str | None = None) -> list[str]:
    """Expand user input into canonical grade candidates for lookup."""
    name = canonical_company(company) if company else ""
    q = collapse_ws(query)
    if not q:
        return []
    seen: set[str] = set()
    out: list[str] = []

    def add(raw: str, dom: str | None = domain) -> None:
        for candidate in (
            canonical_grade(raw, name, domain=dom),
            normalize_grade(raw),
            normalize_grade(re.sub(r"\s+", "", raw)),
        ):
            if candidate and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)

    add(q, domain)
    if name == "IGM":
        for dom in ("offsets", "ecr", "pi", "additives"):
            if dom != domain:
                add(q, dom)
    if name == "AGI":
        for pat in (
            r"(?i)^agisyn\s*[-]?\s*(.+)$",
            r"(?i)^agi\s*syn\s*[-]?\s*(.+)$",
        ):
            m = re.match(pat, q)
            if m:
                add(m.group(1), domain)
    stripped = q
    for prefix in (
        r"(?i)^photomer\s*",
        r"(?i)^ph\s*",
        r"(?i)^ebecryl\s*",
        r"(?i)^eb\s*",
        r"(?i)^omnirad\s*",
        r"(?i)^esacure\s*",
        r"(?i)^sr\s*",
        r"(?i)^cn\s*",
        r"(?i)^additol\s*",
    ):
        if re.match(prefix, stripped):
            rest = re.sub(prefix, "", stripped).strip()
            add(rest, domain)
            if name == "IGM":
                for dom in ("offsets", "ecr", "pi"):
                    add(rest, dom)
            stripped = rest
    if name == "Allnex" and re.fullmatch(r"\d+[A-Z0-9\-]*", re.sub(r"\s+", "", q), re.I):
        add("EB" + re.sub(r"\s+", "", q), domain)
    if name == "Covestro" and re.search(r"(?i)agisyn", q):
        for ag in grade_query_variants(q, "AGI", domain=domain):
            if ag not in seen:
                seen.add(ag)
                out.append(ag)
    if name == "Covestro":
        m = re.match(r"(?i)(?:covestro\s*)?p[\-\s]?(\d+)\s*$", q)
        if m:
            add(f"COVESTROP-{m.group(1)}", domain)
            add(f"P-{m.group(1)}", domain)
    return out


def related_grade_variants(base: str, catalog: list[str]) -> list[str]:
    """For query 3016, also surface 3016LT / 3016-25G siblings in catalog."""
    base = normalize_grade(base)
    if not base or not re.fullmatch(r"\d+[A-Z]?", base):
        return []
    siblings: list[str] = []
    for grade in catalog:
        if grade == base:
            continue
        if not grade.startswith(base):
            continue
        tail = grade[len(base) :]
        if not tail or tail[0] in "-LTGHRABCDEF":
            siblings.append(grade)
    return sorted(siblings)
