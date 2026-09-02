from __future__ import annotations

import json
import os
import re
from typing import Any

from chemdoc_miner.normalize import canonical_company, collapse_ws, normalize_grade
from chemdoc_miner.query import tools

_COMPANY_PAT = re.compile(
    r"(allnex|ebecryl|\beb\b|sartomer|\bsr\b|\bcn\b|igm|photomer|miwon|qualipoly|"
    r"eternal|rahn|genomer|covestro|basf|dsm|agi|dymax|ilene|power\s*dream)",
    re.I,
)


def ask(question: str) -> dict[str, Any]:
    q = collapse_ws(question)
    intent = classify_intent(q)
    payload: dict[str, Any]
    if intent == "equivalents":
        company, grade = _extract_company_grade(q)
        rows = tools.find_equivalents(company or "", grade or q)
        payload = {"intent": intent, "company": company, "grade": grade, "equivalents": rows}
        if not rows and grade:
            payload["product"] = tools.get_product(grade)
    elif intent == "list":
        company = _extract_company(q) or "Power Dream"
        family = _extract_family(q)
        payload = {"intent": intent, **tools.list_by_company(company, family=family)}
    elif intent == "product":
        grade = _extract_grade(q)
        payload = {"intent": intent, "product": tools.get_product(grade or q)}
    else:
        payload = {"intent": "recommend", **tools.recommend(q)}
    payload["answer"] = compose_answer(q, payload)
    payload["disclaimer"] = "对标为内部销售对照，不是实验室证明等价；指标以 TDS 原文为准。"
    return payload


def classify_intent(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ("对应", "对标", "等价", "替代", "equivalent", "offset", "match", "代替")):
        return "equivalents"
    if _COMPANY_PAT.search(q) and re.search(r"[a-z]*\d", q, re.I):
        if "power dream" not in q and "ilene" not in q:
            return "equivalents"
    if any(w in q for w in ("列出", "有哪些", "清单", "list", "哪些产品", "产品型号")):
        return "list"
    if re.fullmatch(r"[a-z]{0,8}\s*\d+[a-z0-9\-]*", q.strip(), re.I) or re.search(
        r"\bilene\s+\S+", q, re.I
    ):
        return "product"
    if any(w in q for w in ("推荐", "需要", "要低", "用于", "应用", "性能", "recommend", "need")):
        return "recommend"
    if _COMPANY_PAT.search(q) and not re.search(r"\d", q):
        return "list"
    return "recommend"


def compose_answer(question: str, payload: dict[str, Any]) -> str:
    composed = _compose_template(payload)
    llm = _maybe_llm(question, payload, composed)
    return llm or composed


def _compose_template(payload: dict[str, Any]) -> str:
    intent = payload.get("intent")
    if intent == "product":
        product = payload.get("product")
        if not product:
            return "目录里没有找到这个型号。可以换牌号、CAS，或问对标/推荐。"
        return _format_product(product)
    if intent == "list":
        if payload.get("products"):
            lines = [f"{payload['company']} 目录共 {payload['count']} 条（本页已列出）："]
            for item in payload["products"][:30]:
                apps = ", ".join((item.get("applications") or [])[:3])
                lines.append(f"- {item.get('grade_display') or item['grade']}  [{item.get('family_label')}]  {apps}")
            return "\n".join(lines)
        if payload.get("grades"):
            lines = [f"{payload['company']} 在对照表中出现 {payload['count']} 个牌号："]
            for item in payload["grades"][:30]:
                pd = ", ".join(item.get("power_dream") or []) or "—"
                lines.append(f"- {item['grade']}  → Power Dream {pd}")
            return "\n".join(lines)
        return "没有列出产品。试试公司名 Allnex / Sartomer / IGM，或 Power Dream。"
    if intent == "equivalents":
        rows = payload.get("equivalents") or []
        if not rows:
            product = payload.get("product")
            if product:
                return "没有找到跨厂牌对照，但目录里有这支自有产品：\n" + _format_product(product)
            return "对照表里没有这条。请确认厂牌和牌号（例如 Allnex EB3700）。"
        lines = ["销售对标（需配方验证）："]
        for row in rows[:20]:
            chem = f"  · {row['chemistry']}" if row.get("chemistry") else ""
            lines.append(
                f"- {row['src_company']} {row['src_grade']}  →  {row['dst_company']} {row['dst_grade']}"
                f"  [{row.get('eq_kind')}/{row.get('source_file')}]{chem}"
            )
        return "\n".join(lines)
    recs = payload.get("recommendations") or []
    if not recs:
        return "没有足够匹配的 TDS 依据可推荐。请补充应用（油墨/涂料/3D）或性能（低黄变、低气味）。"
    lines = ["按 TDS 原文匹配到的推荐："]
    for rec in recs:
        reason = rec["reasons"][0] if rec.get("reasons") else ""
        lines.append(f"- {rec.get('grade_display') or rec['grade']}  ({rec.get('family_label')})  {reason}")
    lines.append("数字与性能请以 TDS 为准；对标需配方验证。")
    return "\n".join(lines)


def _format_product(product: dict[str, Any]) -> str:
    apps = ", ".join((product.get("applications") or [])[:6])
    highs = "; ".join((product.get("highlights") or [])[:5])
    props = product.get("properties") or {}
    visc = props.get("viscosity") or ""
    parts = [
        f"{product.get('grade_display') or product['grade']}  ·  {product.get('family_label')}",
        product.get("description") or "",
        f"CAS: {product.get('cas') or '—'}",
        f"粘度: {visc or '—'}",
        f"应用: {apps or '—'}",
        f"性能: {highs or '—'}",
    ]
    eqs = product.get("equivalents") or []
    if eqs:
        bits = [f"{e['dst_company']} {e['dst_grade']}" for e in eqs[:8]]
        parts.append("对标: " + "; ".join(bits))
    return "\n".join(p for p in parts if p)


def _extract_company(text: str) -> str | None:
    match = _COMPANY_PAT.search(text)
    if not match:
        return None
    return canonical_company(match.group(0))


def _extract_grade(text: str) -> str | None:
    m = re.search(r"ilene\s+([A-Za-z0-9+\-/%]+)", text, re.I)
    if m:
        return normalize_grade(m.group(1))
    m = re.search(
        r"\b(photomer|ebecryl|eb|sr|cn|ph|ucecoat)\s*[-]?\s*(\d[A-Za-z0-9\-]*)\b",
        text,
        re.I,
    )
    if m:
        return (m.group(1) + m.group(2)).upper().replace(" ", "")
    m = re.search(r"\b((?:EB|SR|CN|PH|UC)[A-Za-z]{0,8}\d[A-Za-z0-9\-]*)\b", text, re.I)
    if m:
        return m.group(1)
    m = re.search(r"\b([A-Za-z]{0,8}\d[A-Za-z0-9\-]*)\b", text, re.I)
    if m:
        return m.group(1)
    return None


def _extract_company_grade(text: str) -> tuple[str | None, str | None]:
    return _extract_company(text), _extract_grade(text)


def _extract_family(text: str) -> str | None:
    mapping = {
        "聚氨酯": "pua",
        "pua": "pua",
        "urethane": "pua",
        "聚酯": "pea",
        "polyester": "pea",
        "环氧": "ea",
        "epoxy": "ea",
        "氨改性": "amine",
        "amine": "amine",
        "单体": "monomer",
        "稀释剂": "monomer",
        "光引发剂": "photoinitiator",
        "photoinitiator": "photoinitiator",
    }
    low = text.lower()
    for key, family in mapping.items():
        if key in low:
            return family
    return None


def _maybe_llm(question: str, payload: dict[str, Any], fallback: str) -> str | None:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("CHEMDOC_LLM_API_KEY")
    base = os.environ.get("CHEMDOC_LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL")
    model = os.environ.get("CHEMDOC_LLM_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    if not api_key:
        return None
    try:
        import urllib.request

        url = (base or "https://api.openai.com/v1").rstrip("/") + "/chat/completions"
        slim = json.dumps(payload, ensure_ascii=False)[:8000]
        body = {
            "model": model,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是化工原材料销售助手。只能根据提供的 JSON 目录数据回答，"
                        "禁止编造未出现的粘度、CAS、对标。中文回答，引用 TDS 原句。"
                        "对标必须注明需配方验证。"
                    ),
                },
                {"role": "user", "content": f"问题：{question}\n数据：{slim}"},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None
