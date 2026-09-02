from __future__ import annotations

import argparse
import json
import sys

from chemdoc_miner.ingest.pipeline import run_ingest
from chemdoc_miner.export.app_mobile import export_app_html
from chemdoc_miner.export.finder_mobile import export_finder_html
from chemdoc_miner.export.mobile import export_xref_html
from chemdoc_miner.export.products_mobile import export_products_html
from chemdoc_miner.query.answer import ask
from chemdoc_miner.query.tools import find_equivalents, get_product, list_by_company, recommend, search_products, stats
from chemdoc_miner.query.xref import find_cross_refs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chemdoc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("ingest", help="Parse TDS/SDS/xlsx into SQLite")
    sub.add_parser("stats")

    q = sub.add_parser("ask", help="Natural-language catalog question")
    q.add_argument("question", nargs="+")

    s = sub.add_parser("search")
    s.add_argument("query", nargs="+")
    s.add_argument("--family")

    g = sub.add_parser("get")
    g.add_argument("grade")

    e = sub.add_parser("eq")
    e.add_argument("company")
    e.add_argument("grade")

    x = sub.add_parser("xref", help="Union cross-reference lookup")
    x.add_argument("company")
    x.add_argument("grade")

    sub.add_parser("export-app-html", help="Unified offline ChemDoc HTML (Finder + Catalog + Xref)")
    sub.add_parser("export-xref-html", help="Alias for export-app-html")
    sub.add_parser("export-products-html", help="Alias for export-app-html")
    sub.add_parser("export-finder-html", help="Alias for export-app-html")

    ls = sub.add_parser("list")
    ls.add_argument("company")
    ls.add_argument("--family")

    r = sub.add_parser("recommend")
    r.add_argument("need", nargs="+")

    srv = sub.add_parser("serve")
    srv.add_argument("--host", default="127.0.0.1")
    srv.add_argument("--port", type=int, default=8765)

    args = parser.parse_args(argv)
    if args.cmd == "ingest":
        result = run_ingest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "stats":
        print(json.dumps(stats(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "ask":
        print(json.dumps(ask(" ".join(args.question)), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "search":
        print(json.dumps(search_products(" ".join(args.query), family=args.family), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "get":
        print(json.dumps(get_product(args.grade), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "eq":
        print(json.dumps(find_equivalents(args.company, args.grade), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "xref":
        print(json.dumps(find_cross_refs(args.company, args.grade), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "export-app-html":
        path = export_app_html()
        print(json.dumps({"path": str(path)}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "export-xref-html":
        path = export_xref_html()
        print(json.dumps({"path": str(path)}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "export-products-html":
        path = export_products_html()
        print(json.dumps({"path": str(path)}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "export-finder-html":
        path = export_finder_html()
        print(json.dumps({"path": str(path)}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "list":
        print(json.dumps(list_by_company(args.company, family=args.family), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "recommend":
        print(json.dumps(recommend(" ".join(args.need)), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "serve":
        import uvicorn
        from chemdoc_miner.api.app import app

        uvicorn.run(app, host=args.host, port=args.port)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
