from __future__ import annotations

import json
import re
import sqlite3
from typing import Any

from chemdoc_miner.db import connect
from chemdoc_miner.ingest.equivalence import EqGroup, EqMember, load_equivalence_groups
from chemdoc_miner.normalize import canonical_company, canonical_grade, collapse_ws, grade_query_variants, normalize_grade


def member_key(company: str, grade: str) -> str:
    return f"{canonical_company(company) or company}|{normalize_grade(grade) or collapse_ws(grade).upper().replace(' ', '')}"


def build_union_lookup(groups: list[EqGroup] | None = None) -> dict[str, list[dict[str, str]]]:
    groups = groups or load_equivalence_groups()
    key_to_peers: dict[str, dict[str, dict[str, str]]] = {}
    for group in groups:
        if group.member_count < 2:
            continue
        for i, m in enumerate(group.members):
            self_key = member_key(m.company, m.grade)
            bucket = key_to_peers.setdefault(self_key, {})
            for j, other in enumerate(group.members):
                if i == j:
                    continue
                peer_key = member_key(other.company, other.grade)
                bucket[peer_key] = {"company": other.company, "grade": other.grade}
    lookup: dict[str, list[dict[str, str]]] = {}
    for key, peers in key_to_peers.items():
        lookup[key] = sorted(peers.values(), key=lambda p: (p["company"], p["grade"]))
    return lookup


def expand_peers_with_hops(
    lookup: dict[str, list[dict[str, str]]],
    start_keys: set[str],
    *,
    max_hops: int | None = None,
    hop_cap: int = 12,
) -> list[dict[str, Any]]:
    """BFS peer expansion. max_hops=None expands until the graph is stable."""
    visited = set(start_keys)
    out: dict[str, dict[str, Any]] = {}
    frontier = list(start_keys)
    hop = 0
    while frontier and (max_hops is None or hop < max_hops):
        hop += 1
        if hop > hop_cap:
            break
        next_frontier: list[str] = []
        for key in frontier:
            for p in lookup.get(key, []):
                pk = member_key(p["company"], p["grade"])
                if pk in visited:
                    continue
                visited.add(pk)
                out[pk] = {"company": p["company"], "grade": p["grade"], "hop": hop}
                next_frontier.append(pk)
        frontier = next_frontier
    return sorted(out.values(), key=lambda p: (p["hop"], p["company"], p["grade"]))


def find_cross_refs(
    company: str,
    grade: str,
    *,
    conn: sqlite3.Connection | None = None,
    max_hops: int | None = None,
) -> dict[str, Any]:
    own = conn is None
    close = conn or connect()
    try:
        from chemdoc_miner.query.tools import resolve_grade

        name = canonical_company(company) or company
        g = normalize_grade(grade) or collapse_ws(grade).upper().replace(" ", "")
        resolved = resolve_grade(grade, close)
        candidates: set[tuple[str, str]] = {(name, g)}
        for item in resolved:
            candidates.add((item["company"], item["grade"]))
        for variant in grade_query_variants(grade, name):
            candidates.add((name, variant))
        if name in {"AGI", "Covestro"} or re.search(r"(?i)agisyn", grade):
            for variant in grade_query_variants(grade, "AGI"):
                candidates.add(("AGI", variant))
            agi_grade = canonical_grade(grade, "AGI", domain="ecr")
            if agi_grade:
                candidates.add(("AGI", agi_grade))

        groups_out: list[dict[str, Any]] = []
        seen_gids: set[int] = set()

        for cname, cgrade in candidates:
            rows = close.execute(
                """
                SELECT g.group_id, g.eq_key, g.domain, g.chemistry, g.cas, g.chemistry_group,
                       g.source_file, g.member_count, g.quality
                FROM eq_members m
                JOIN eq_groups g ON g.group_id = m.group_id
                WHERE m.company = ? COLLATE NOCASE
                  AND (m.grade = ? COLLATE NOCASE OR replace(m.grade,' ','') = ? COLLATE NOCASE)
                ORDER BY g.member_count DESC, g.domain
                """,
                (cname, cgrade, cgrade.replace(" ", "")),
            ).fetchall()
            for row in rows:
                gid = row["group_id"]
                if gid in seen_gids:
                    continue
                seen_gids.add(gid)
                members = [
                    dict(r)
                    for r in close.execute(
                        """
                        SELECT company, grade, grade_raw, role
                        FROM eq_members WHERE group_id = ?
                        ORDER BY company, grade
                        """,
                        (gid,),
                    ).fetchall()
                ]
                groups_out.append(
                    {
                        "group_id": gid,
                        "eq_key": row["eq_key"],
                        "domain": row["domain"],
                        "chemistry": row["chemistry"],
                        "cas": row["cas"],
                        "chemistry_group": row["chemistry_group"],
                        "source_file": row["source_file"],
                        "member_count": row["member_count"],
                        "quality": row["quality"],
                        "members": members,
                    }
                )

        lookup = build_union_lookup_from_db(close)
        start_keys = {member_key(cname, cgrade) for cname, cgrade in candidates}
        peers = expand_peers_with_hops(lookup, start_keys, max_hops=max_hops)
        hop1 = sum(1 for p in peers if p["hop"] == 1)
        hop2 = sum(1 for p in peers if p["hop"] == 2)
        hop3plus = sum(1 for p in peers if p["hop"] >= 3)
        max_hop_reached = max((p["hop"] for p in peers), default=0)
        return {
            "query": {"company": name, "grade": g},
            "peers": peers,
            "peer_count": len(peers),
            "hop1_count": hop1,
            "hop2_count": hop2,
            "hop3plus_count": hop3plus,
            "max_hop_reached": max_hop_reached,
            "max_hops": max_hops,
            "groups": groups_out,
            "disclaimer": "销售/化学对标参考，需配方验证。",
        }
    finally:
        if own:
            close.close()


def xref_stats(conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    own = conn is None
    close = conn or connect()
    try:
        groups = close.execute("SELECT COUNT(*) AS n FROM eq_groups").fetchone()["n"]
        members = close.execute("SELECT COUNT(*) AS n FROM eq_members").fetchone()["n"]
        complete = close.execute("SELECT COUNT(*) AS n FROM eq_groups WHERE quality='complete'").fetchone()["n"]
        by_domain = {
            row["domain"]: row["n"]
            for row in close.execute("SELECT domain, COUNT(*) AS n FROM eq_groups GROUP BY domain")
        }
        lookup = build_union_lookup_from_db(close)
        return {
            "eq_groups": groups,
            "eq_members": members,
            "complete_groups": complete,
            "lookup_keys": len(lookup),
            "by_domain": by_domain,
        }
    finally:
        if own:
            close.close()


def build_union_lookup_from_db(conn: sqlite3.Connection) -> dict[str, list[dict[str, str]]]:
    groups: list[EqGroup] = []
    for grow in conn.execute(
        "SELECT group_id, eq_key, domain, chemistry, cas, chemistry_group, source_file FROM eq_groups WHERE member_count >= 2"
    ).fetchall():
        members_rows = conn.execute(
            "SELECT company, grade, grade_raw, role FROM eq_members WHERE group_id = ?",
            (grow["group_id"],),
        ).fetchall()
        members = [
            EqMember(r["company"], r["grade"], r["grade_raw"], r["role"] or "product_code") for r in members_rows
        ]
        groups.append(
            EqGroup(
                eq_key=grow["eq_key"],
                domain=grow["domain"],
                chemistry=grow["chemistry"],
                cas=grow["cas"],
                chemistry_group=grow["chemistry_group"],
                source_file=grow["source_file"],
                members=members,
            )
        )
    return build_union_lookup(groups)


def export_lookup_json(conn: sqlite3.Connection | None = None) -> str:
    own = conn is None
    close = conn or connect()
    try:
        lookup = build_union_lookup_from_db(close)
        grades_by_company: dict[str, list[str]] = {}
        for key in lookup:
            co, grade = key.split("|", 1)
            grades_by_company.setdefault(co, set()).add(grade)
        grades_by_company = {co: sorted(gs) for co, gs in grades_by_company.items()}
        companies = sorted(grades_by_company.keys())
        payload = {
            "version": 2,
            "lookup": lookup,
            "grades_by_company": grades_by_company,
            "companies": companies,
            "key_count": len(lookup),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    finally:
        if own:
            close.close()
