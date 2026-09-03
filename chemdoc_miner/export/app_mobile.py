from __future__ import annotations

import json
from pathlib import Path

from chemdoc_miner.db import connect
from chemdoc_miner.export.ghs_assets import ghs_pictogram_json
from chemdoc_miner.paths import DATA_DIR, ROOT
from chemdoc_miner.query.catalog import export_catalog_json
from chemdoc_miner.query.finder import build_finder_index
from chemdoc_miner.query.xref import export_lookup_json, xref_stats

APP_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>ChemDoc — iLENE Offline</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#0D1219;
  --card:#182231;
  --card-elevated:#1C2838;
  --control:#202D40;
  --dropdown:#151E2B;
  --empty:#111923;
  --border:#2B4058;
  --border-dropdown:#31445D;
  --border-hover:#3B5875;
  --accent:#4DB3FF;
  --accent-hover:#66C0FF;
  --accent-active:#3DA3EF;
  --accent-tint:rgba(77,179,255,0.10);
  --accent-ring:rgba(77,179,255,0.12);
  --text:#E8EDF4;
  --text-secondary:#91A3BA;
  --text-muted:#64748B;
  --warn:#D4A054;
  --danger:#E07070;
  --ok:#7CB88A;
  --nav-h:56px;
  --radius-lg:20px;
  --radius-md:15px;
  --radius-sm:14px;
  --shadow-card:0 8px 30px rgba(0,0,0,0.20);
  --shadow-dropdown:0 12px 40px rgba(0,0,0,0.35);
}
*{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  background:var(--bg);
  color:var(--text);
  font-weight:400;
  min-height:100dvh;
  padding:16px 16px calc(var(--nav-h) + 16px);
  -webkit-font-smoothing:antialiased;
}
h1{font-size:1.15rem;font-weight:600;margin-bottom:4px;color:var(--text);letter-spacing:-0.01em}
.sub{color:var(--text-secondary);font-size:.82rem;font-weight:400;margin-bottom:14px;line-height:1.45}
.view{display:none}.view.on{display:block}
.app-nav{
  position:fixed;left:0;right:0;bottom:0;height:var(--nav-h);
  padding-bottom:env(safe-area-inset-bottom);
  display:flex;background:var(--card);
  border-top:1px solid var(--border);z-index:100;
}
.app-nav button{
  flex:1;border:none;background:transparent;
  color:var(--text-secondary);font-size:.78rem;font-weight:500;
  padding:10px 4px 8px;position:relative;
}
.app-nav button.on{color:var(--accent);font-weight:600}
.app-nav button.on::after{
  content:"";position:absolute;top:0;left:18%;right:18%;height:3px;
  background:var(--accent);border-radius:0 0 2px 2px;
}
.search{display:flex;gap:8px;margin-bottom:12px;align-items:stretch}
input,select{
  background:var(--control);
  border:1px solid var(--border);
  color:var(--text);
  border-radius:var(--radius-sm);
  padding:11px 12px;
  font-size:16px;font-family:inherit;font-weight:400;
  min-width:0;
  transition:border-color .15s ease,box-shadow .15s ease;
}
input::placeholder{color:var(--text-muted)}
input[type=text],input[type=number]{flex:1}
select{
  flex:1;
  appearance:none;
  -webkit-appearance:none;
  background-color:var(--control);
  border-color:var(--border-dropdown);
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' viewBox='0 0 12 8'%3E%3Cpath fill='%2391A3BA' d='M1 1.5 6 6.5 11 1.5'/%3E%3C/svg%3E");
  background-repeat:no-repeat;
  background-position:right 12px center;
  padding-right:34px;
  cursor:pointer;
}
select:hover:not(:focus){border-color:var(--border-hover)}
select option{background:var(--dropdown);color:var(--text)}
.panel select{background-color:var(--control)}
input:focus,select:focus{
  outline:none;border-color:var(--accent);
  box-shadow:0 0 0 2px var(--accent-ring);
}
button.action{
  background:var(--accent);color:var(--bg);
  border:none;border-radius:var(--radius-sm);
  padding:11px 16px;font-weight:600;font-size:16px;font-family:inherit;
  flex:0 0 auto;white-space:nowrap;cursor:pointer;
  transition:background .15s ease,transform .1s ease;
}
button.action:hover{background:var(--accent-hover)}
button.action:active{background:var(--accent-active);transform:scale(0.98)}
#view-xref .search{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,0.8fr) auto;gap:8px}
#view-xref .search select,#view-xref .search input,#view-xref .search button.action{width:100%}
#view-xref .search button.action{width:auto;padding:11px 14px}
#view-catalog .search,#view-xref .search{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:12px;margin-bottom:12px;
  box-shadow:var(--shadow-card);
}
button.primary{width:100%;margin-top:6px}
button.link{
  background:transparent;border:none;color:var(--text-secondary);
  font-size:.82rem;font-weight:500;padding:10px 0;cursor:pointer;
}
button.link:hover{color:var(--text)}
button.link-btn{
  background:var(--control);border:1px solid var(--border);
  color:var(--text);border-radius:var(--radius-sm);
  padding:7px 12px;font-size:.78rem;font-weight:500;cursor:pointer;
  transition:border-color .15s ease,background .15s ease;
}
button.link-btn:hover{border-color:var(--border-hover);background:var(--card-elevated)}
.panel{
  background:var(--card);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:16px;margin-bottom:12px;
  box-shadow:var(--shadow-card);
}
.panel h2{
  font-size:.72rem;color:var(--text-secondary);font-weight:600;
  text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;
}
.panel select{width:100%}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{
  border:1px solid var(--border);background:var(--control);
  border-radius:999px;padding:7px 12px;font-size:.78rem;font-weight:500;
  cursor:pointer;color:var(--text);
  transition:border-color .15s ease,background .15s ease,color .15s ease;
}
.chip:hover{border-color:var(--border-hover)}
.chip.on{background:var(--accent-tint);border-color:var(--accent);color:var(--accent)}
.spec-grid{display:grid;grid-template-columns:1fr 1fr;gap:6px 8px;margin-bottom:10px}
.spec-grid .name{grid-column:1/-1;font-size:.76rem;color:var(--text-secondary);line-height:1.35;font-weight:500}
.spec-grid input[type=number]{width:100%;min-width:0;padding:9px 10px;font-size:.88rem}
.checks{display:grid;gap:8px}
.checks label{font-size:.82rem;font-weight:400;display:flex;gap:8px;align-items:flex-start;color:var(--text);line-height:1.4}
.checks input[type=checkbox]{accent-color:var(--accent);margin-top:2px;flex-shrink:0}
.card{
  background:var(--card-elevated);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:14px 16px;margin-top:12px;overflow:hidden;
  box-shadow:var(--shadow-card);
}
.card-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.title{font-size:1rem;font-weight:600;color:var(--text)}
.score{font-size:.82rem;color:var(--ok);font-weight:600;white-space:nowrap}
.meta{font-size:.78rem;color:var(--text-secondary);margin-top:4px;font-weight:400;line-height:1.4}
.reasons{margin-top:10px;font-size:.78rem;line-height:1.45;color:var(--text)}
.reasons li{margin-left:16px;margin-bottom:3px}
.specs-row{font-size:.78rem;color:var(--text-muted);margin-top:6px}
.actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.empty{
  padding:28px 20px;text-align:center;color:var(--text-secondary);
  font-size:.88rem;font-weight:400;line-height:1.45;
  background:var(--empty);border:1px solid var(--border);
  border-radius:var(--radius-lg);
}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:.72rem;font-weight:600;margin-left:6px}
.badge-warn{background:rgba(212,160,84,.15);color:var(--warn)}
.badge-danger{background:rgba(224,112,112,.15);color:var(--danger)}
.back-bar{margin-bottom:12px}
.back-bar button{
  background:var(--control);border:1px solid var(--border);
  color:var(--text);border-radius:var(--radius-sm);
  padding:10px 14px;font-size:.85rem;font-weight:600;width:100%;text-align:left;
  cursor:pointer;transition:border-color .15s ease;
}
.back-bar button:hover{border-color:var(--border-hover)}
.tabs{display:flex;border-bottom:1px solid var(--border)}
.tab{
  flex:1;padding:12px;text-align:center;font-size:.86rem;
  color:var(--text-secondary);cursor:pointer;border:none;background:transparent;
  font-family:inherit;font-weight:500;
}
.tab.on{color:var(--accent);box-shadow:inset 0 -2px 0 var(--accent);font-weight:600}
.pane{display:none;padding:14px}.pane.on{display:block}
.section{margin-bottom:14px}
.section h3{
  font-size:.72rem;color:var(--text-secondary);font-weight:600;
  text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;
}
.section p,.section li{font-size:.88rem;line-height:1.5;color:var(--text);font-weight:400}
.section ul{padding-left:18px}
.kv{display:grid;grid-template-columns:minmax(110px,38%) 1fr;gap:6px 10px;font-size:.84rem}
.kv div:nth-child(odd){color:var(--text-secondary);font-weight:500}
.kv div:nth-child(even){color:var(--text);font-weight:400}
.pcode,.hcode{font-size:.82rem;padding:6px 0;border-bottom:1px solid rgba(43,64,88,.55)}
.code{font-family:ui-monospace,monospace;color:var(--text-secondary);margin-right:8px;font-weight:500}
.ghs-label{background:#fff;color:#111;border:2px solid #c8102e;border-radius:6px;padding:12px;margin-bottom:14px}
.ghs-pictos{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px}
.ghs-diamond{width:52px;height:52px;object-fit:contain}
.ghs-signal{font-size:1.05rem;font-weight:800;margin-bottom:8px}
.ghs-signal.danger{color:#c8102e}.ghs-signal.warning{color:#e87722}
.ghs-haz{font-size:.78rem;line-height:1.35;margin-bottom:4px}
.ghs-haz .code{color:#c8102e;font-weight:700;margin-right:6px}
.ghs-product{margin-top:10px;padding-top:8px;border-top:1px solid #ddd;font-size:.82rem;font-weight:600}
.ghs-caption{font-size:.72rem;color:var(--text-muted);margin:-6px 0 10px}
.hrow{display:flex;justify-content:space-between;padding:12px 16px;border-bottom:1px solid var(--border);gap:12px}
.results{
  background:var(--card-elevated);border:1px solid var(--border);
  border-radius:var(--radius-lg);overflow:hidden;
  box-shadow:var(--shadow-card);
}
.results .empty{
  border:none;border-radius:0;background:var(--empty);
  padding:20px;text-align:center;color:var(--text-secondary);
}
.results > .empty:only-child{
  min-height:min(36vh,260px);
  display:flex;align-items:center;justify-content:center;
  padding:36px 20px;
}
.results .note + .empty{
  min-height:auto;display:block;padding:18px 20px;
}
.row{
  display:flex;justify-content:space-between;padding:12px 16px;
  border-bottom:1px solid var(--border);align-items:center;gap:8px;
}
.row:last-child{border-bottom:none}
.row button.link-btn{flex-shrink:0}
.co{font-weight:600;color:var(--text)}
.grade{color:var(--text);font-family:ui-monospace,monospace;font-weight:500;font-size:.88rem}
.note{padding:10px 16px;font-size:.82rem;color:var(--text-secondary);border-bottom:1px solid var(--border);font-weight:400}
.section-hdr{
  padding:8px 16px;font-size:.75rem;color:var(--text-muted);
  background:rgba(255,255,255,.02);font-weight:500;
}
.hint{margin-top:14px;font-size:.76rem;color:var(--text-muted);line-height:1.5;font-weight:400}
#catalog-search-out .empty,#finder-out .empty{margin-top:12px;border:1px solid var(--border)}
.hidden{display:none!important}
@media (max-width:520px){
  body{padding:14px 14px calc(var(--nav-h) + 14px)}
  #view-xref .search{grid-template-columns:1fr}
  #view-xref .search button.action{width:100%;padding:11px 16px}
  .search{flex-wrap:nowrap}
  .search input[type=text],.search button.action{min-width:0}
  .search button.action{padding:11px 12px;font-size:15px}
  .card-head{flex-direction:column;align-items:flex-start}
  .row{flex-wrap:wrap}
  .row button.link-btn{margin-left:auto}
  .chip{max-width:100%;overflow:hidden;text-overflow:ellipsis}
}
</style>
</head>
<body>
<h1 id="app-title">iLENE ChemDoc</h1>
<p class="sub" id="app-meta">Offline · Finder · Catalog · Cross-reference</p>

<section id="view-finder" class="view on">
<div class="panel"><h2>Application</h2><div class="chips" id="finder-apps"></div></div>
<div class="panel"><h2>Product family</h2><select id="finder-family"><option value="all">All families</option></select></div>
<div class="panel"><h2>Performance</h2><div class="chips" id="finder-tags"></div></div>
<div class="panel"><h2>Specifications</h2><div id="finder-specs"></div></div>
<div class="panel"><h2>Safety filters</h2><div class="checks" id="finder-safety"></div></div>
<div class="panel"><h2>Additional keywords</h2><input type="text" id="finder-text" placeholder="e.g. flexible, wood coating, low odor" style="width:100%"/></div>
<button class="action primary" id="finder-go">Find products</button>
<button class="link" id="finder-reset" type="button">Clear filters</button>
<div id="finder-out"></div>
</section>

<section id="view-catalog" class="view">
<div id="catalog-search-wrap">
<div class="search">
<input id="catalog-q" placeholder="Grade: 2150F / 700 / TMPTA" enterkeyhint="search" list="grades-list"/>
<datalist id="grades-list"></datalist>
<button class="action" id="catalog-go">Search</button>
</div>
<div id="catalog-search-out"><div class="empty">Enter a product grade</div></div>
</div>
<div id="catalog-detail-wrap" class="hidden">
<div class="back-bar"><button type="button" id="catalog-back">← Back</button></div>
<div id="catalog-detail-out"></div>
</div>
</section>

<section id="view-xref" class="view">
<div class="search">
<select id="xref-company"></select>
<input id="xref-grade" placeholder="Grade: 3016 / PH3016 / EB230"/>
<button class="action" id="xref-go">Search</button>
</div>
<div class="results" id="xref-out"><div class="empty">Select company and enter a grade</div></div>
<p class="hint">Sales/chemical cross-reference only. Formulation validation required.</p>
</section>

<nav class="app-nav" aria-label="Main">
<button type="button" data-tab="finder" class="on">Finder</button>
<button type="button" data-tab="catalog">Catalog</button>
<button type="button" data-tab="xref">Xref</button>
</nav>

<script>
const CATALOG = __CATALOG_JSON__;
const FINDER = __FINDER_JSON__;
const XREF = __LOOKUP_JSON__;
const GHS_PICTO = __GHS_PICTO_JSON__;
const products = CATALOG.products || {};
const aliases = CATALOG.aliases || {};
const xrefLookup = XREF.lookup || {};
const gradesByCo = XREF.grades_by_company || {};
const companies = XREF.companies || [];

const App = {
  tab: "finder",
  catalogReturn: null,
  finderScroll: 0,
};

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function norm(g) { return String(g || "").trim().toUpperCase().replace(/\s+/g, ""); }
function normApp(s) { return String(s || "").trim().toLowerCase().replace(/\s+/g, " "); }

function switchTab(tab, pushHash) {
  App.tab = tab;
  document.querySelectorAll(".view").forEach(v => v.classList.remove("on"));
  $("view-" + tab).classList.add("on");
  document.querySelectorAll(".app-nav button").forEach(b => {
    b.classList.toggle("on", b.dataset.tab === tab);
  });
  const titles = { finder: "Product Finder", catalog: "Product Catalog", xref: "Cross-Reference" };
  $("app-title").textContent = "iLENE " + (titles[tab] || "ChemDoc");
  if (pushHash !== false) {
    const h = tab === "catalog" && !$("catalog-detail-wrap").classList.contains("hidden")
      ? "#catalog/" + encodeURIComponent($("catalog-q").value.trim())
      : "#" + tab;
    if (location.hash !== h) history.pushState(null, "", h);
  }
}

function openCatalog(grade, opts) {
  opts = opts || {};
  const g = norm(grade);
  const p = resolveProduct(g);
  if (!p) {
    switchTab("catalog");
    $("catalog-search-wrap").classList.remove("hidden");
    $("catalog-detail-wrap").classList.add("hidden");
    $("catalog-q").value = grade;
    $("catalog-search-out").innerHTML = '<div class="empty">No product for "' + esc(grade) + '"</div>';
    return;
  }
  App.catalogReturn = opts.returnTo || null;
  $("catalog-back").textContent = opts.returnLabel || (App.catalogReturn === "finder" ? "← Back to Finder" : App.catalogReturn === "xref" ? "← Back to Xref" : App.catalogReturn === "search" ? "← Back to search" : "← Back to search");
  $("catalog-q").value = p.grade;
  $("catalog-search-wrap").classList.add("hidden");
  $("catalog-detail-wrap").classList.remove("hidden");
  renderProductDetail(p);
  switchTab("catalog", false);
  history.pushState(null, "", "#catalog/" + encodeURIComponent(p.grade));
}

function catalogBack() {
  if (App.catalogReturn === "finder") {
    $("catalog-detail-wrap").classList.add("hidden");
    $("catalog-search-wrap").classList.remove("hidden");
    switchTab("finder", false);
    history.pushState(null, "", "#finder");
    window.scrollTo(0, App.finderScroll || 0);
    App.catalogReturn = null;
    return;
  }
  if (App.catalogReturn === "xref") {
    $("catalog-detail-wrap").classList.add("hidden");
    $("catalog-search-wrap").classList.remove("hidden");
    switchTab("xref", false);
    history.pushState(null, "", "#xref");
    App.catalogReturn = null;
    return;
  }
  $("catalog-detail-wrap").classList.add("hidden");
  $("catalog-search-wrap").classList.remove("hidden");
  App.catalogReturn = null;
  history.replaceState(null, "", "#catalog");
}

function catalogSearch() {
  const q = $("catalog-q").value.trim();
  if (!q) {
    $("catalog-detail-wrap").classList.add("hidden");
    $("catalog-search-wrap").classList.remove("hidden");
    $("catalog-search-out").innerHTML = '<div class="empty">Enter a product grade</div>';
    return;
  }
  const p = resolveProduct(q);
  if (!p) {
    $("catalog-detail-wrap").classList.add("hidden");
    $("catalog-search-wrap").classList.remove("hidden");
    $("catalog-search-out").innerHTML = '<div class="empty">No product for "' + esc(q) + '"</div>';
    return;
  }
  openCatalog(p.grade, { returnTo: "search", returnLabel: "← Back to search" });
}

function resolveProduct(q) {
  const n = norm(q);
  if (!n) return null;
  if (products[n]) return products[n];
  const via = aliases[n];
  return via ? products[via] : null;
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
  if (!src) return '<span class="chip">' + esc(c) + '</span>';
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
    html += '<p class="ghs-caption">GHS label (from SDS Section 2)</p><div class="ghs-label">';
    if (pictos.length) html += '<div class="ghs-pictos">' + pictos.map(p => ghsPictogramImg(p.code)).join("") + '</div>';
    if (sw) html += '<div class="ghs-signal ' + (sw === "DANGER" ? "danger" : "warning") + '">' + esc(sw) + '</div>';
    hs.forEach(h => { html += '<div class="ghs-haz"><span class="code">' + esc(h.code || "") + '</span>' + esc(h.text) + '</div>'; });
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
  let html = renderLabel(s.label_elements || {}, p.grade_display || p.grade || p.chemical_name);
  if (s.components && s.components.length) {
    html += '<div class="section"><h3>Components</h3><div class="kv">';
    s.components.forEach(c => { html += '<div>' + esc(c.name || "—") + '</div><div>' + esc((c.wt || "") + (c.cas ? " · CAS " + c.cas : "")) + '</div>'; });
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
function renderProductDetail(p) {
  const sw = p.signal_word || (p.sds_summary && p.sds_summary.label_elements && p.sds_summary.label_elements.signal_word);
  const meta = [p.family_en || p.family, p.cas ? "CAS " + p.cas : "", p.revised_date ? "TDS " + p.revised_date : ""].filter(Boolean).join(" · ");
  const uid = "pd" + Date.now();
  $("catalog-detail-out").innerHTML =
    '<div class="card"><div class="hrow"><div><div class="title">' + esc(p.grade_display || p.grade) + signalBadge(sw) + '</div><div class="meta">' + esc(meta) + '</div></div></div>' +
    '<div class="tabs"><button class="tab on" data-pane="tech">Technical (TDS)</button><button class="tab" data-pane="safe">Safety (SDS)</button></div>' +
    '<div class="pane on" id="' + uid + '-tech">' + renderTechnical(p) + '</div>' +
    '<div class="pane" id="' + uid + '-safe">' + renderSafety(p) + '</div></div>';
  $("catalog-detail-out").querySelectorAll(".tab").forEach(btn => {
    btn.onclick = () => {
      $("catalog-detail-out").querySelectorAll(".tab").forEach(t => t.classList.remove("on"));
      $("catalog-detail-out").querySelectorAll(".pane").forEach(t => t.classList.remove("on"));
      btn.classList.add("on");
      $(uid + "-" + btn.dataset.pane).classList.add("on");
    };
  });
}

/* ---- Finder ---- */
const finderState = { applications: new Set(), tags: new Set() };
const TAG_PHRASES = {
  low_yellowing: ["non-yellowing", "low yellowing"], fast_curing: ["fast curing", "quick cure"],
  flexible: ["flexible", "flexibility"], high_hardness: ["high hardness"],
  high_transparency: ["transparent", "high transparency"], low_odor: ["low odor"],
  adhesion: ["adhesion"], weather_resistance: ["weather resistance", "weathering"]
};

function initFinder() {
  (FINDER.applications_vocab || []).forEach(item => {
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "chip"; btn.textContent = item.label; btn.dataset.id = item.id;
    btn.onclick = () => { btn.classList.toggle("on"); if (finderState.applications.has(item.id)) finderState.applications.delete(item.id); else finderState.applications.add(item.id); };
    $("finder-apps").appendChild(btn);
  });
  const seen = new Set();
  Object.values(FINDER.products || {}).forEach(p => {
    if (!p.family || seen.has(p.family)) return;
    seen.add(p.family);
    const opt = document.createElement("option");
    opt.value = p.family; opt.textContent = p.family_en || p.family;
    $("finder-family").appendChild(opt);
  });
  (FINDER.performance_tags || []).forEach(item => {
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "chip"; btn.textContent = item.label; btn.dataset.id = item.id;
    btn.onclick = () => { btn.classList.toggle("on"); if (finderState.tags.has(item.id)) finderState.tags.delete(item.id); else finderState.tags.add(item.id); };
    $("finder-tags").appendChild(btn);
  });
  const sbox = $("finder-safety");
  sbox.innerHTML = '<label><input type="checkbox" id="finder-warning-only"/> Exclude DANGER (WARNING only, requires SDS)</label>';
  (FINDER.hazard_flags || []).forEach(item => {
    const lab = document.createElement("label");
    lab.innerHTML = '<input type="checkbox" data-flag="' + esc(item.id) + '"/> Exclude: ' + esc(item.label);
    sbox.appendChild(lab);
  });
  $("finder-family").onchange = renderFinderSpecs;
  renderFinderSpecs();
}

function renderFinderSpecs() {
  const family = $("finder-family").value;
  const map = FINDER.family_specs || {};
  const keys = (family !== "all" && map[family]) ? map[family] : ["viscosity", "hardness", "tg", "functionality", "purity"];
  const labels = FINDER.spec_labels || {};
  $("finder-specs").innerHTML = keys.map(key =>
    '<div class="spec-grid"><div class="name">' + esc(labels[key] || key) + '</div>' +
    '<input type="number" step="any" placeholder="min" data-key="' + esc(key) + '" data-bound="min"/>' +
    '<input type="number" step="any" placeholder="max" data-key="' + esc(key) + '" data-bound="max"/></div>'
  ).join("");
}

function readFinderCriteria() {
  const specs = {};
  document.querySelectorAll("#finder-specs input[data-key]").forEach(inp => {
    const key = inp.dataset.key, bound = inp.dataset.bound;
    if (!specs[key]) specs[key] = { min: null, max: null };
    if (inp.value !== "") specs[key][bound] = Number(inp.value);
  });
  const exclude = [];
  document.querySelectorAll("#finder-safety input[data-flag]").forEach(inp => { if (inp.checked) exclude.push(inp.dataset.flag); });
  return {
    family: $("finder-family").value || "all",
    applications: Array.from(finderState.applications),
    performance_tags: Array.from(finderState.tags),
    specs, text: $("finder-text").value.trim(),
    safety: { exclude_flags: exclude, warning_only: $("finder-warning-only").checked, require_sds: exclude.length > 0 || $("finder-warning-only").checked }
  };
}

function specInRange(productVal, reqMin, reqMax) {
  if (reqMin == null && reqMax == null) return { ok: true, partial: 1 };
  if (productVal == null) return { ok: false, partial: 0 };
  let target;
  if (typeof productVal === "object") {
    const lo = productVal.min != null ? Number(productVal.min) : Number(productVal.max);
    const hi = productVal.max != null ? Number(productVal.max) : lo;
    target = (lo + hi) / 2;
    if (reqMin != null && hi < reqMin) return { ok: false, partial: 0 };
    if (reqMax != null && lo > reqMax) return { ok: false, partial: 0 };
  } else {
    target = Number(productVal);
    if (reqMin != null && target < reqMin) return { ok: false, partial: 0 };
    if (reqMax != null && target > reqMax) return { ok: false, partial: 0 };
  }
  if (reqMin != null && reqMax != null && reqMax > reqMin) {
    return { ok: true, partial: Math.max(0.2, 1 - Math.abs(target - (reqMin + reqMax) / 2) / (reqMax - reqMin)) };
  }
  return { ok: true, partial: 1 };
}

function scoreFinderProduct(product, criteria) {
  if (criteria.family !== "all" && product.family !== criteria.family) return null;
  const safety = criteria.safety || {};
  if ((safety.exclude_flags || []).length || safety.warning_only) {
    if (!product.has_sds) return null;
    const flags = new Set(product.hazard_flags || []);
    for (const f of safety.exclude_flags || []) if (flags.has(f)) return null;
    if (safety.warning_only && String(product.signal_word || "").toUpperCase() === "DANGER") return null;
  }
  let score = 0; const reasons = [];
  const apps = criteria.applications || [];
  if (apps.length) {
    const wanted = new Set(apps.map(normApp));
    const matched = (product.applications_norm || []).filter(a => wanted.has(a));
    if (!matched.length) return null;
    score += 35 * matched.length / apps.length;
    matched.forEach(norm => reasons.push("Application: " + ((product.applications || []).find(a => normApp(a) === norm) || norm)));
  }
  const tags = criteria.performance_tags || [];
  if (tags.length) {
    const blob = [product.description || "", ...(product.highlights || []), ...(product.applications || [])].join(" ").toLowerCase();
    let hit = 0;
    tags.forEach(tag => { if ((TAG_PHRASES[tag] || [tag.replace(/_/g, " ")]).some(p => blob.includes(p))) { hit++; reasons.push("Performance: " + tag.replace(/_/g, " ")); } });
    if (!hit && !apps.length && !criteria.text && !Object.values(criteria.specs || {}).some(b => b.min != null || b.max != null)) return null;
    score += 18 * hit / tags.length;
  }
  const activeSpecs = Object.entries(criteria.specs || {}).filter(([, b]) => b.min != null || b.max != null);
  if (activeSpecs.length) {
    let specScore = 0;
    for (const [key, bounds] of activeSpecs) {
      const chk = specInRange((product.specs || {})[key], bounds.min, bounds.max);
      if (!chk.ok) return null;
      specScore += chk.partial;
      reasons.push("Spec " + ((FINDER.spec_labels || {})[key] || key) + " in range");
    }
    score += 30 * specScore / activeSpecs.length;
  }
  const text = (criteria.text || "").trim();
  if (text) {
    const tokens = text.toLowerCase().split(/[^a-z0-9+\-]+/).filter(t => t.length > 1);
    const blob = [product.description || "", ...(product.highlights || []), ...(product.applications || []), product.family_en || ""].join(" ").toLowerCase();
    const hits = tokens.filter(t => blob.includes(t)).length;
    if (hits) { score += Math.min(15, hits * 3); reasons.push("Text match (" + hits + " terms)"); }
    else if (!apps.length && !activeSpecs.length && !tags.length) return null;
  }
  return { score: score || 1, reasons: reasons.length ? reasons : ["Catalog browse"] };
}

function runFinder() {
  App.finderScroll = window.scrollY;
  const criteria = readFinderCriteria();
  const results = [];
  for (const product of Object.values(FINDER.products || {})) {
    const scored = scoreFinderProduct(product, criteria);
    if (scored) results.push({ product, ...scored });
  }
  results.sort((a, b) => b.score - a.score || String(a.product.grade).localeCompare(String(b.product.grade)));
  renderFinderResults(results.slice(0, 15));
}

function renderFinderResults(results) {
  if (!results.length) {
    $("finder-out").innerHTML = '<div class="empty">No matching products. Try fewer safety filters or broader ranges.</div>';
    return;
  }
  let html = '<div class="meta" style="margin-top:14px">' + results.length + ' recommendation(s)</div>';
  results.forEach(({ product, score, reasons }) => {
    const sw = product.signal_word;
    const badge = sw === "DANGER" ? '<span class="badge badge-danger">DANGER</span>' : sw === "WARNING" ? '<span class="badge badge-warn">WARNING</span>' : "";
    const specs = Object.values(product.spec_display || {}).slice(0, 4).join(" · ");
    const gradeJs = esc(product.grade).replace(/'/g, "\\'");
    html += '<div class="card"><div class="card-head"><div><div class="title">' + esc(product.grade_display || product.grade) + badge +
      '</div><div class="meta">' + esc(product.family_en || product.family) + '</div></div><div class="score">' + Math.min(100, Math.round(score)) + '%</div></div>' +
      (specs ? '<div class="specs-row">' + esc(specs) + '</div>' : '') +
      '<ul class="reasons">' + reasons.slice(0, 4).map(r => '<li>' + esc(r) + '</li>').join("") + '</ul>' +
      '<div class="actions"><button type="button" class="link-btn" onclick="openCatalog(\'' + gradeJs + '\', {returnTo:\'finder\'})">TDS / SDS details</button></div></div>';
  });
  $("finder-out").innerHTML = html;
}

function resetFinder() {
  finderState.applications.clear(); finderState.tags.clear();
  document.querySelectorAll("#view-finder .chip.on").forEach(el => el.classList.remove("on"));
  $("finder-family").value = "all"; $("finder-text").value = "";
  $("finder-warning-only").checked = false;
  document.querySelectorAll("#finder-safety input[data-flag]").forEach(inp => { inp.checked = false; });
  renderFinderSpecs(); $("finder-out").innerHTML = "";
}

/* ---- Xref ---- */
function mkKey(co, g) { return co + "|" + String(g).toUpperCase().replace(/\s+/g, ""); }
function stripPrefixes(co, q) {
  let text = q.trim();
  const patterns = { IGM: [/^(?:photomer|ph|omnirad|esacure)\s*/i], Allnex: [/^(?:ebecryl|eb|additol)\s*/i], Sartomer: [/^(?:sr|cn|mcure|m-cure)\s*/i] };
  (patterns[co] || []).forEach(re => { text = text.replace(re, ""); });
  return text.trim();
}
function queryVariants(co, input) {
  const q = input.trim(); if (!q) return [];
  const seen = new Set(), out = [];
  function add(g) { const n = norm(g); if (n && !seen.has(n)) { seen.add(n); out.push(n); } }
  add(q); add(stripPrefixes(co, q));
  if (co === "Allnex" && /^\d+[A-Z0-9\-]*$/i.test(norm(q))) add("EB" + norm(q));
  return out;
}
function findXrefMatches(co, input) {
  const variants = queryVariants(co, input);
  const matchedKeys = [], peerMap = {};
  for (const v of variants) {
    const key = mkKey(co, v);
    if (xrefLookup[key]) matchedKeys.push({ grade: v, kind: "exact" });
  }
  const exact = matchedKeys.filter(m => m.kind === "exact");
  const seenKey = new Set();
  for (const item of exact) {
    const key = mkKey(co, item.grade);
    if (seenKey.has(key)) continue;
    seenKey.add(key);
    for (const p of xrefLookup[key] || []) peerMap[p.company + "|" + p.grade] = p;
  }
  for (const v of variants) delete peerMap[mkKey(co, v)];
  return { matchedKeys, peers: Object.values(peerMap).sort((a,b) => a.company.localeCompare(b.company) || a.grade.localeCompare(b.grade)) };
}
function renderXref() {
  const co = $("xref-company").value;
  const grade = $("xref-grade").value.trim();
  const box = $("xref-out");
  if (!grade) { box.innerHTML = '<div class="empty">Enter a grade code</div>'; return; }
  const { matchedKeys, peers } = findXrefMatches(co, grade);
  if (!matchedKeys.length) { box.innerHTML = '<div class="empty">No match for ' + esc(co) + ' ' + esc(grade) + '</div>'; return; }
  let html = '<div class="note">Matched: ' + matchedKeys.map(m => m.grade).join(", ") + '</div>';
  if (!peers.length) html += '<div class="empty">No cross-references</div>';
  else html += peers.map(p => {
    const pd = p.company === "Power Dream";
    const right = pd
      ? '<button type="button" class="link-btn" onclick="openCatalog(\'' + esc(p.grade).replace(/'/g, "\\'") + '\', {returnTo:\'xref\'})">' + esc(p.grade) + '</button>'
      : '<span class="grade">' + esc(p.grade) + '</span>';
    return '<div class="row"><span class="co">' + esc(p.company) + '</span>' + right + '</div>';
  }).join("");
  box.innerHTML = html;
}

function initXref() {
  companies.forEach(c => {
    const o = document.createElement("option"); o.value = c; o.textContent = c;
    $("xref-company").appendChild(o);
  });
  if (companies.includes("IGM")) $("xref-company").value = "IGM";
}

function routeFromHash() {
  const h = (location.hash || "#finder").replace(/^#/, "");
  if (h.startsWith("catalog/")) {
    openCatalog(decodeURIComponent(h.slice(8)), {});
    return;
  }
  if (h === "catalog") { switchTab("catalog", false); return; }
  if (h === "xref") { switchTab("xref", false); return; }
  switchTab("finder", false);
}

document.querySelectorAll(".app-nav button").forEach(btn => {
  btn.onclick = () => {
    if (btn.dataset.tab === "catalog") {
      $("catalog-detail-wrap").classList.add("hidden");
      $("catalog-search-wrap").classList.remove("hidden");
      App.catalogReturn = null;
    }
    switchTab(btn.dataset.tab);
  };
});
$("finder-go").onclick = runFinder;
$("finder-reset").onclick = resetFinder;
$("catalog-go").onclick = catalogSearch;
$("catalog-q").addEventListener("keydown", e => { if (e.key === "Enter") catalogSearch(); });
$("catalog-back").onclick = catalogBack;
$("xref-go").onclick = renderXref;
$("xref-grade").addEventListener("keydown", e => { if (e.key === "Enter") renderXref(); });
window.addEventListener("popstate", routeFromHash);

(CATALOG.grades || []).forEach(g => {
  const o = document.createElement("option"); o.value = g; $("grades-list").appendChild(o);
});
$("app-meta").textContent = (CATALOG.count || 0) + " products · " + (XREF.key_count || 0) + " xref keys · offline";
initFinder();
initXref();
routeFromHash();
</script>
</body>
</html>
"""


def export_app_html(out_path: Path | None = None) -> Path:
    conn = connect()
    try:
        catalog = export_catalog_json(conn)
        finder = json.dumps(build_finder_index(conn), ensure_ascii=False)
        xref = export_lookup_json(conn)
        stats = xref_stats(conn)
    finally:
        conn.close()

    html = (
        APP_HTML.replace("__CATALOG_JSON__", catalog)
        .replace("__FINDER_JSON__", finder)
        .replace("__LOOKUP_JSON__", xref)
        .replace("__GHS_PICTO_JSON__", ghs_pictogram_json())
    )
    target = out_path or (DATA_DIR / "ChemDoc.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")

    if out_path is None:
        (ROOT / "index.html").write_text(html, encoding="utf-8")

    meta_path = DATA_DIR / "xref_stats.json"
    meta_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    return target
