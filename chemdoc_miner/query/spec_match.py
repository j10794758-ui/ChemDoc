from __future__ import annotations

import re
from typing import Any

_NUM = re.compile(r"(-?\d+(?:\.\d+)?)")
_RANGE = re.compile(r"(-?\d+(?:\.\d+)?)\s*[-–~to]+\s*(-?\d+(?:\.\d+)?)", re.I)


def first_number(text: str | None) -> float | None:
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    match = _NUM.search(str(text))
    return float(match.group(1)) if match else None


def parse_range(text: str | None) -> tuple[float | None, float | None]:
    if text is None:
        return None, None
    if isinstance(text, dict):
        lo = text.get("min")
        hi = text.get("max")
        if lo is not None or hi is not None:
            return (
                float(lo) if lo is not None else None,
                float(hi) if hi is not None else None,
            )
    raw = str(text)
    match = _RANGE.search(raw)
    if match:
        return float(match.group(1)), float(match.group(2))
    val = first_number(raw)
    return (val, val) if val is not None else (None, None)


def extract_product_specs(properties: dict[str, Any] | None) -> dict[str, Any]:
    props = properties or {}
    specs: dict[str, Any] = {}
    display: dict[str, str] = {}

    vis = props.get("viscosity_struct")
    if isinstance(vis, dict) and (vis.get("min") is not None or vis.get("max") is not None):
        specs["viscosity"] = {
            "min": vis.get("min"),
            "max": vis.get("max"),
            "unit": vis.get("unit") or "cps",
            "temp_c": vis.get("temp_c"),
        }
        lo, hi = vis.get("min"), vis.get("max")
        temp = vis.get("temp_c")
        if lo is not None and hi is not None and lo != hi:
            display["viscosity"] = f"{lo}–{hi} cps" + (f" @{temp}°C" if temp else "")
        elif lo is not None:
            display["viscosity"] = f"{lo} cps" + (f" @{temp}°C" if temp else "")
    elif props.get("viscosity"):
        lo, hi = parse_range(str(props["viscosity"]))
        if lo is not None:
            specs["viscosity"] = {"min": lo, "max": hi or lo, "unit": "cps", "temp_c": None}
            display["viscosity"] = str(props["viscosity"])

    if props.get("functionality_num") is not None:
        val = float(props["functionality_num"])
        specs["functionality"] = val
        display["functionality"] = str(val)
    elif props.get("functionality"):
        val = first_number(str(props["functionality"]))
        if val is not None:
            specs["functionality"] = val
            display["functionality"] = str(props["functionality"])

    for key, out_key in (
        ("hardness", "hardness"),
        ("tg", "tg"),
        ("acid_value", "acid_value"),
        ("purity", "purity"),
        ("melting_point", "melting_point"),
        ("softening_point", "softening_point"),
    ):
        raw = props.get(key)
        if raw is None:
            continue
        val = first_number(str(raw))
        if val is not None:
            specs[out_key] = val
            display[out_key] = str(raw)

    return {"specs": specs, "spec_display": display}


def spec_in_range(
    product_value: Any,
    req_min: float | None,
    req_max: float | None,
) -> tuple[bool, float, str | None]:
    """Return (matches, partial_score_0_1, reason)."""
    if req_min is None and req_max is None:
        return True, 1.0, None
    if product_value is None:
        return False, 0.0, None

    if isinstance(product_value, dict):
        lo = product_value.get("min")
        hi = product_value.get("max")
        if lo is None and hi is None:
            return False, 0.0, None
        lo = float(lo) if lo is not None else float(hi)
        hi = float(hi) if hi is not None else float(lo)
        mid = (lo + hi) / 2
        if req_min is not None and hi < req_min:
            return False, 0.0, None
        if req_max is not None and lo > req_max:
            return False, 0.0, None
        target = mid
    else:
        target = float(product_value)
        if req_min is not None and target < req_min:
            return False, 0.0, None
        if req_max is not None and target > req_max:
            return False, 0.0, None

    if req_min is not None and req_max is not None and req_max > req_min:
        span = req_max - req_min
        dist = abs(target - (req_min + req_max) / 2) / span
        partial = max(0.2, 1.0 - dist)
    else:
        partial = 1.0
    return True, partial, None
