from __future__ import annotations

import json
import os
from typing import Any


def maybe_llm_fill(parsed: dict[str, Any], text: str) -> dict[str, Any]:
    """Optional schema repair when regex confidence is low and an API key is set."""
    if (parsed.get("confidence") or 0) >= 0.55:
        return parsed
    api_key = os.environ.get("CHEMDOC_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return parsed
    base = os.environ.get("CHEMDOC_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    model = os.environ.get("CHEMDOC_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    payload = {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": "Extract TDS fields as JSON with keys grade, chemical_name, cas, description, highlights (array), applications (array), package. Do not invent numbers.",
            },
            {"role": "user", "content": text[:4000]},
        ],
    }
    try:
        import urllib.request

        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            body = json.loads(resp.read().decode())
        content = body["choices"][0]["message"]["content"]
        start, end = content.find("{"), content.rfind("}")
        filled = json.loads(content[start : end + 1])
    except Exception:
        return parsed
    for key in ("chemical_name", "cas", "description", "package"):
        if filled.get(key) and not parsed.get(key):
            parsed[key] = filled[key]
    for key in ("highlights", "applications"):
        if filled.get(key) and not parsed.get(key):
            parsed[key] = filled[key]
    parsed["confidence"] = min(1.0, (parsed.get("confidence") or 0) + 0.2)
    parsed["llm_filled"] = True
    return parsed
