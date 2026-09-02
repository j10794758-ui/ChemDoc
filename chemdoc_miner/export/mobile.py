from __future__ import annotations

from pathlib import Path

from chemdoc_miner.db import connect
from chemdoc_miner.paths import DATA_DIR
from chemdoc_miner.query.xref import export_lookup_json, xref_stats

MOBILE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>ChemDoc Cross-Reference</title>
<style>
:root{--bg:#0f1419;--card:#1a2332;--text:#e8eef5;--muted:#8fa3b8;--accent:#f0a030;--line:#2a3544}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);min-height:100dvh;padding:16px;padding-bottom:max(16px,env(safe-area-inset-bottom))}
h1{font-size:1.25rem;font-weight:700;margin-bottom:4px}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:16px}
.search{display:flex;gap:8px;margin-bottom:12px}
input,select{flex:1;background:var(--card);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:12px;font-size:16px}
button{background:var(--accent);color:#111;border:none;border-radius:10px;padding:12px 16px;font-weight:700;font-size:16px}
.results{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.row{display:flex;justify-content:space-between;padding:12px 14px;border-bottom:1px solid var(--line)}
.row:last-child{border-bottom:none}
.co{font-weight:600}
.grade{color:var(--accent);font-family:ui-monospace,monospace}
.empty{padding:24px;text-align:center;color:var(--muted)}
.warn{margin-top:12px;font-size:.8rem;color:var(--muted);line-height:1.4}
.note{padding:10px 14px;font-size:.82rem;color:var(--muted);border-bottom:1px solid var(--line)}
.section{padding:8px 14px;font-size:.75rem;color:var(--accent);background:rgba(240,160,48,.08)}
</style>
</head>
<body>
<h1>Product Cross-Reference</h1>
<p class="sub" id="meta">Offline lookup</p>
<div class="search">
<select id="company"></select>
<input id="grade" placeholder="Grade: 3016 / PH3016 / Photomer 3016" enterkeyhint="search"/>
<button id="go">Search</button>
</div>
<div class="results" id="results"><div class="empty">Select company and enter a grade</div></div>
<p class="warn">Sales/chemical cross-reference only. Formulation validation required. Offsets and equivalence groups merged.</p>
<script>
const DATA = __LOOKUP_JSON__;
const lookup = DATA.lookup || {};
const gradesByCo = DATA.grades_by_company || {};
const companies = DATA.companies || [];
const $ = (id) => document.getElementById(id);

function mkKey(co, g) {
  return co + "|" + String(g).toUpperCase().replace(/\\s+/g, "");
}
function norm(g) {
  return String(g).trim().toUpperCase().replace(/\\s+/g, "");
}
function stripPrefixes(co, q) {
  let text = q.trim();
  const patterns = {
    IGM: [/^(?:photomer|ph|omnirad|esacure)\\s*/i],
    Allnex: [/^(?:ebecryl|eb|additol)\\s*/i],
    Sartomer: [/^(?:sr|cn|mcure|m-cure)\\s*/i],
  };
  (patterns[co] || []).forEach((re) => { text = text.replace(re, ""); });
  return text.trim();
}
function queryVariants(co, input) {
  const q = input.trim();
  if (!q) return [];
  const seen = new Set();
  const out = [];
  function add(g) {
    const n = norm(g);
    if (n && !seen.has(n)) { seen.add(n); out.push(n); }
  }
  add(q);
  add(stripPrefixes(co, q));
  if (co === "Allnex" && /^\\d+[A-Z0-9\\-]*$/i.test(norm(q))) add("EB" + norm(q));
  if (co === "IGM") {
    const bare = norm(stripPrefixes(co, q));
    if (/^\\d+[A-Z0-9\\-]*$/i.test(bare)) add(bare);
  }
  return out;
}
function relatedVariants(co, base) {
  const catalog = gradesByCo[co] || [];
  if (!/^\\d+[A-Z]?$/.test(base)) return [];
  return catalog.filter((g) => g !== base && g.startsWith(base) && (!g[base.length] || /[^0-9]/.test(g[base.length])));
}
function findMatches(co, input) {
  const variants = queryVariants(co, input);
  const matchedKeys = [];
  const peerMap = {};
  for (const v of variants) {
    const key = mkKey(co, v);
    if (lookup[key]) matchedKeys.push({ grade: v, kind: "exact" });
  }
  const base = variants.find((v) => /^\\d+[A-Z]?$/.test(v));
  const related = base ? relatedVariants(co, base).filter((g) => lookup[mkKey(co, g)]) : [];
  for (const sib of related) {
    matchedKeys.push({ grade: sib, kind: "related" });
  }
  const exact = matchedKeys.filter(m => m.kind === "exact");
  const seenKey = new Set();
  for (const item of exact) {
    const key = mkKey(co, item.grade);
    if (seenKey.has(key)) continue;
    seenKey.add(key);
    for (const p of lookup[key] || []) {
      peerMap[p.company + "|" + p.grade] = p;
    }
  }
  for (const v of variants) {
    delete peerMap[mkKey(co, v)];
  }
  return {
    matchedKeys,
    related,
    peers: Object.values(peerMap).sort((a,b)=>a.company.localeCompare(b.company)||a.grade.localeCompare(b.grade))
  };
}
function render() {
  const co = $("company").value;
  const grade = $("grade").value.trim();
  const box = $("results");
  if (!grade) { box.innerHTML = '<div class="empty">Enter a grade code</div>'; return; }
  const { matchedKeys, related, peers } = findMatches(co, grade);
  if (!matchedKeys.length) {
    box.innerHTML = '<div class="empty">No match for ' + co + ' ' + grade + '</div>';
    return;
  }
  let html = "";
  const exact = matchedKeys.filter(m => m.kind === "exact").map(m => m.grade);
  if (exact.length) html += '<div class="note">Matched: ' + exact.join(", ") + '</div>';
  if (related.length) {
    html += '<div class="section">Related grades (search separately): ' + related.slice(0,8).join(", ");
    if (related.length > 8) html += ' …+' + (related.length - 8);
    html += '</div>';
  }
  if (!peers.length) {
    html += '<div class="empty">No cross-references for this grade</div>';
  } else {
    html += peers.map(p => '<div class="row"><span class="co">' + p.company + '</span><span class="grade">' + p.grade + '</span></div>').join("");
  }
  box.innerHTML = html;
}
$("meta").textContent = (DATA.key_count || 0) + " grades · offline";
const sel = $("company");
companies.forEach(c => {
  const o = document.createElement("option");
  o.value = c; o.textContent = c; sel.appendChild(o);
});
if (companies.includes("IGM")) sel.value = "IGM";
else if (companies.includes("Allnex")) sel.value = "Allnex";
$("go").onclick = render;
$("grade").addEventListener("keydown", e => { if (e.key === "Enter") render(); });
</script>
</body>
</html>
"""


from chemdoc_miner.export.app_mobile import export_app_html


def export_xref_html(out_path: Path | None = None) -> Path:
    return export_app_html(out_path or (DATA_DIR / "ChemDoc.html"))
