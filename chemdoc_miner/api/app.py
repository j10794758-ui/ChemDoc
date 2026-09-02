from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chemdoc_miner.glossary import FAMILY_LABELS
from chemdoc_miner.paths import WEB_DIR, abs_from_rel
from chemdoc_miner.query.answer import ask
from chemdoc_miner.query.tools import (
    find_equivalents,
    get_product,
    list_by_company,
    recommend,
    search_products,
    stats,
)
from chemdoc_miner.query.xref import find_cross_refs

app = FastAPI(title="ChemDoc Miner", version="0.1.0")


class AskBody(BaseModel):
    question: str


class NeedBody(BaseModel):
    need: str


@app.get("/api/stats")
def api_stats():
    data = stats()
    data["family_labels"] = FAMILY_LABELS
    return data


@app.get("/api/search")
def api_search(q: str = Query(..., min_length=1), family: str | None = None, limit: int = 20):
    return {"query": q, "results": search_products(q, family=family, limit=limit)}


@app.get("/api/product/{grade}")
def api_product(grade: str):
    product = get_product(grade)
    if not product:
        raise HTTPException(404, f"Unknown grade {grade}")
    return product


@app.get("/api/list")
def api_list(company: str = "Power Dream", family: str | None = None, limit: int = 80):
    return list_by_company(company, family=family, limit=limit)


@app.get("/api/equivalents")
def api_eq(grade: str, company: str = ""):
    return {"company": company, "grade": grade, "equivalents": find_equivalents(company, grade)}


@app.get("/api/xref")
def api_xref(grade: str, company: str = ""):
    return find_cross_refs(company, grade)


@app.post("/api/recommend")
def api_recommend(body: NeedBody):
    return recommend(body.need)


@app.post("/api/ask")
def api_ask(body: AskBody):
    return ask(body.question)


@app.get("/api/file")
def api_file(path: str):
    if not path.startswith("doc/"):
        raise HTTPException(400, "path must be under doc/")
    try:
        target = abs_from_rel(path)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    if not target.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(target, filename=target.name, media_type="application/pdf")


if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
