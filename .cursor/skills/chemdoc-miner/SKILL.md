---
name: chemdoc-miner
description: Query the iLENE / Power Dream UV raw-material catalog (TDS, SDS, competitive offsets). Use when the user asks about product grades, Allnex/Sartomer/IGM equivalents, or application/performance recommendations.
---

# ChemDoc Miner

Internal sales catalog for Power Dream / iLENE UV-curable materials.

## When to use

User asks about iLENE grades, competitor offsets (Allnex Ebecryl, Sartomer SR/CN, IGM Photomer, Miwon, Qualipoly, Eternal, RAHN), or “what resin for low yellowing / 3D printing / nail gel / ink”.

## How to query

Run from the project root. Do **not** invent viscosity, CAS, or offsets.

```bash
python -m chemdoc_miner ask "Allnex EB3700 对应什么"
python -m chemdoc_miner get HDDA
python -m chemdoc_miner eq Allnex EB3700
python -m chemdoc_miner recommend "低黄变 3D打印"
python -m chemdoc_miner list "Power Dream" --family ea
python -m chemdoc_miner search "nail gel"
```

If the database is missing (`data/derived/chemdoc.db`):

```bash
python -m chemdoc_miner ingest
```

## Answering rules

- Cite `tds_path` / `sds_path`. Offer to open the PDF.
- Treat equivalents as **sales offsets**, not lab-proven drop-ins. Say 需配方验证.
- Do not compare viscosities measured at different temperatures.
- If the catalog has no match, say so. Do not fallback to generic chemistry knowledge for a specific grade.

## Rebuild

New PDFs go in `doc/`. Then `python -m chemdoc_miner ingest`.
