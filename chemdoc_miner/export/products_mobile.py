from __future__ import annotations

import base64
import json
from pathlib import Path

from chemdoc_miner.db import connect
from chemdoc_miner.export.app_mobile import export_app_html
from chemdoc_miner.export.ghs_assets import ghs_pictogram_json
from chemdoc_miner.paths import DATA_DIR
from chemdoc_miner.query.catalog import export_catalog_json

PRODUCTS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>ChemDoc Product Catalog</title>
<style>
:root{--bg:#0f1419;--card:#1a2332;--text:#e8eef5;--muted:#8fa3b8;--accent:#4db6ff;--warn:#f0a030;--danger:#ff6b6b;--line:#2a3544;--ok:#6bcb77}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);min-height:100dvh;padding:16px;padding-bottom:max(16px,env(safe-area-inset-bottom))}
h1{font-size:1.25rem;font-weight:700;margin-bottom:4px}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:16px}
.search{display:flex;gap:8px;margin-bottom:12px}
input{flex:1;background:var(--card);border:1px solid var(--line);color:var(--text);border-radius:10px;padding:12px;font-size:16px}
button{background:var(--accent);color:#111;border:none;border-radius:10px;padding:12px 16px;font-weight:700;font-size:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin-top:12px}
.empty{padding:24px;text-align:center;color:var(--muted)}
.tabs{display:flex;border-bottom:1px solid var(--line)}
.tab{flex:1;padding:12px;text-align:center;font-size:.9rem;color:var(--muted);cursor:pointer;border:none;background:transparent}
.tab.on{color:var(--accent);box-shadow:inset 0 -2px 0 var(--accent);font-weight:600}
.panel{display:none;padding:14px}
.panel.on{display:block}
.hrow{display:flex;justify-content:space-between;align-items:flex-start;padding:12px 14px;border-bottom:1px solid var(--line);gap:12px}
.title{font-size:1.05rem;font-weight:700}
.meta{font-size:.8rem;color:var(--muted);margin-top:4px}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.75rem;font-weight:700;margin-left:6px}
.badge-warn{background:rgba(240,160,48,.2);color:var(--warn)}
.badge-danger{background:rgba(255,107,107,.2);color:var(--danger)}
.section{margin-bottom:14px}
.section h3{font-size:.78rem;color:var(--accent);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.section p,.section li{font-size:.88rem;line-height:1.45;color:var(--text)}
.section ul{padding-left:18px}
.kv{display:grid;grid-template-columns:minmax(110px,38%) 1fr;gap:6px 10px;font-size:.84rem}
.kv div:nth-child(odd){color:var(--muted)}
.pictos{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0}
.picto{background:#243044;border:1px solid var(--line);border-radius:8px;padding:6px 10px;font-size:.75rem;font-family:ui-monospace,monospace}
.hcode,.pcode{font-size:.82rem;padding:6px 0;border-bottom:1px solid rgba(42,53,68,.6)}
.hcode:last-child,.pcode:last-child{border-bottom:none}
.code{font-family:ui-monospace,monospace;color:var(--warn);margin-right:8px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{background:#243044;border-radius:999px;padding:4px 10px;font-size:.78rem}
.ghs-label{background:#fff;color:#111;border:2px solid #c8102e;border-radius:4px;padding:12px;margin-bottom:14px;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.ghs-label .ghs-pictos{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.ghs-diamond{width:52px;height:52px;flex:0 0 52px;display:block;object-fit:contain}
.ghs-signal{font-size:1.05rem;font-weight:800;letter-spacing:.06em;margin-bottom:8px}
.ghs-signal.danger{color:#c8102e}
.ghs-signal.warning{color:#e87722}
.ghs-haz{font-size:.78rem;line-height:1.35;margin-bottom:4px}
.ghs-haz .code{color:#c8102e;font-weight:700;margin-right:6px;font-family:ui-monospace,monospace}
.ghs-product{margin-top:10px;padding-top:8px;border-top:1px solid #ddd;font-size:.82rem;font-weight:600}
.ghs-caption{font-size:.72rem;color:var(--muted);margin:-6px 0 10px}
.hint{margin-top:12px;font-size:.78rem;color:var(--muted);line-height:1.4}
</style>
</head>
<body>
<h1>iLENE Product Catalog</h1>
<p class="sub" id="meta">Offline TDS + SDS lookup</p>
<div class="search">
<input id="q" placeholder="Grade: 2150F / 700 / TMPTA" enterkeyhint="search" list="grades-list"/>
<datalist id="grades-list"></datalist>
<button id="go">Search</button>
</div>
<div id="out"><div class="empty">Enter a product grade</div></div>
<p class="hint">Technical data from TDS. Safety, label elements, and transport from SDS. PDF paths shown for reference; open originals on desktop if needed.</p>
<script>
const DATA = __CATALOG_JSON__;
const GHS_PICTO = __GHS_PICTO_JSON__;
const products = DATA.products || {};
const aliases = DATA.aliases || {};
const $ = (id) => document.getElementById(id);

function norm(g) {
  return String(g || "").trim().toUpperCase().replace(/\\s+/g, "");
}
function resolve(q) {
  const n = norm(q);
  if (!n) return null;
  if (products[n]) return products[n];
  const via = aliases[n];
  return via ? products[via] : null;
}
function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function list(items) {
  if (!items || !items.length) return '<p class="meta">—</p>';
  return "<ul>" + items.map(i => "<li>" + esc(i) + "</li>").join("") + "</ul>";
}
function props(obj) {
  const keys = Object.keys(obj || {});
  if (!keys.length) return '<p class="meta">—</p>';
  return '<div class="kv">' + keys.map(k => '<div>' + esc(k) + '</div><div>' + esc(obj[k]) + '</div>').join("") + '</div>';
}
function signalBadge(sw) {
  if (!sw) return "";
  const cls = sw === "DANGER" ? "badge-danger" : "badge-warn";
  return '<span class="badge ' + cls + '">' + esc(sw) + '</span>';
}
function ghsPictogramImg(code) {
  const c = String(code || "").toUpperCase();
  const src = GHS_PICTO[c];
  if (!src) return '<span class="picto">' + esc(c) + '</span>';
  return '<img class="ghs-diamond" src="' + src + '" alt="' + esc(c) + '" loading="lazy"/>';
}
function renderLabel(label, productName) {
  if (!label || !Object.keys(label).length) return '<p class="meta">No SDS label data</p>';
  let html = "";
  const pictos = label.pictograms || [];
  const sw = label.signal_word || "";
  const hs = label.hazard_statements || [];
  const pid = label.product_identifier || productName || "";
  if (pictos.length || sw || hs.length) {
    html += '<p class="ghs-caption">GHS label (from SDS Section 2)</p>';
    html += '<div class="ghs-label" role="img" aria-label="GHS hazard label">';
    if (pictos.length) {
      html += '<div class="ghs-pictos">' + pictos.map(p => ghsPictogramImg(p.code)).join("") + '</div>';
    }
    if (sw) {
      const cls = sw === "DANGER" ? "danger" : "warning";
      html += '<div class="ghs-signal ' + cls + '">' + esc(sw) + '</div>';
    }
    hs.forEach(h => {
      html += '<div class="ghs-haz"><span class="code">' + esc(h.code || "") + '</span>' + esc(h.text) + '</div>';
    });
    if (pid) html += '<div class="ghs-product">' + esc(pid) + '</div>';
    html += '</div>';
  }
  const ps = label.precautionary_statements || {};
  for (const grp of ["prevention","response","storage","disposal"]) {
    const items = ps[grp] || [];
    if (!items.length) continue;
    html += '<div class="section"><h3>Precautionary — ' + grp + '</h3>';
    html += items.map(p => '<div class="pcode"><span class="code">' + esc(p.code || "—") + '</span>' + esc(p.text) + '</div>').join("");
    html += '</div>';
  }
  return html;
}
function renderSafety(p) {
  const s = p.sds_summary || {};
  const label = s.label_elements || {};
  let html = renderLabel(label, p.grade_display || p.grade || p.chemical_name);
  if (s.components && s.components.length) {
    html += '<div class="section"><h3>Components</h3><div class="kv">';
    s.components.forEach(c => {
      html += '<div>' + esc(c.name || "—") + '</div><div>' + esc((c.wt || "") + (c.cas ? " · CAS " + c.cas : "")) + '</div>';
    });
    html += '</div></div>';
  }
  const t = s.transport || {};
  if (Object.keys(t).length) {
    html += '<div class="section"><h3>Transport</h3><div class="kv">';
    ["un_number","proper_shipping_name","hazard_class","packing_group","marine_pollutant","not_regulated"].forEach(k => {
      if (t[k] !== undefined && t[k] !== null && t[k] !== "") html += '<div>' + esc(k) + '</div><div>' + esc(String(t[k])) + '</div>';
    });
    html += '</div></div>';
  }
  const r = s.regulatory || {};
  if (r.summary_flags && r.summary_flags.length) {
    html += '<div class="section"><h3>Regulatory</h3><div class="chips">' + r.summary_flags.map(f => '<span class="chip">' + esc(f) + '</span>').join("") + '</div></div>';
  }
  if (s.handling && s.handling.length) html += '<div class="section"><h3>Handling</h3>' + list(s.handling) + '</div>';
  if (s.storage_sds) html += '<div class="section"><h3>Storage (SDS)</h3><p>' + esc(s.storage_sds) + '</p></div>';
  const ppe = s.physical_safety || {};
  if (s.physical_safety && Object.keys(s.physical_safety).length) {
    html += '<div class="section"><h3>Physical (safety)</h3>' + props(s.physical_safety) + '</div>';
  }
  if (!p.sds_path) html = '<p class="meta">No SDS on file</p>';
  return html;
}
function renderTechnical(p) {
  if (!p.tds_path) return '<p class="meta">No TDS on file</p>';
  let html = "";
  if (p.description) html += '<div class="section"><h3>Description</h3><p>' + esc(p.description) + '</p></div>';
  if (p.highlights && p.highlights.length) html += '<div class="section"><h3>Highlights</h3>' + list(p.highlights) + '</div>';
  if (p.applications && p.applications.length) html += '<div class="section"><h3>Applications</h3>' + list(p.applications) + '</div>';
  html += '<div class="section"><h3>Properties</h3>' + props(p.properties) + '</div>';
  if (p.package) html += '<div class="section"><h3>Package</h3><p>' + esc(p.package) + '</p></div>';
  if (p.storage) html += '<div class="section"><h3>Storage</h3><p>' + esc(p.storage) + '</p></div>';
  return html;
}
function renderProduct(p) {
  const sw = p.signal_word || (p.sds_summary && p.sds_summary.label_elements && p.sds_summary.label_elements.signal_word);
  const meta = [p.family_label || p.family, p.cas ? "CAS " + p.cas : "", p.revised_date ? "TDS " + p.revised_date : ""].filter(Boolean).join(" · ");
  const html = '<div class="card">' +
    '<div class="hrow"><div><div class="title">' + esc(p.grade_display || p.grade) + signalBadge(sw) + '</div>' +
    '<div class="meta">' + esc(meta) + '</div></div></div>' +
    '<div class="tabs"><button class="tab on" data-tab="tech">Technical (TDS)</button><button class="tab" data-tab="safe">Safety (SDS)</button></div>' +
    '<div class="panel on" id="panel-tech">' + renderTechnical(p) + '</div>' +
    '<div class="panel" id="panel-safe">' + renderSafety(p) + '</div></div>';
  $("out").innerHTML = html;
  $("out").querySelectorAll(".tab").forEach(btn => {
    btn.onclick = () => {
      $("out").querySelectorAll(".tab").forEach(t => t.classList.remove("on"));
      $("out").querySelectorAll(".panel").forEach(t => t.classList.remove("on"));
      btn.classList.add("on");
      $("panel-" + btn.dataset.tab).classList.add("on");
    };
  });
}
function search() {
  const q = $("q").value.trim();
  if (!q) { $("out").innerHTML = '<div class="empty">Enter a product grade</div>'; return; }
  const p = resolve(q);
  if (!p) { $("out").innerHTML = '<div class="empty">No product for "' + esc(q) + '"</div>'; return; }
  renderProduct(p);
}
$("meta").textContent = (DATA.count || 0) + " products · offline";
const dl = $("grades-list");
(DATA.grades || []).forEach(g => {
  const o = document.createElement("option");
  o.value = g;
  dl.appendChild(o);
});
$("go").onclick = search;
$("q").addEventListener("keydown", e => { if (e.key === "Enter") search(); });
const _qp = new URLSearchParams(location.search).get("q");
if (_qp) { $("q").value = _qp; search(); }
</script>
</body>
</html>
"""


def export_products_html(out_path: Path | None = None) -> Path:
    return export_app_html(out_path or (DATA_DIR / "ChemDoc.html"))
