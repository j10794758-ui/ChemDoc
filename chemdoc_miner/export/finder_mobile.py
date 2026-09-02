from __future__ import annotations

import json
from pathlib import Path

from chemdoc_miner.db import connect
from chemdoc_miner.paths import DATA_DIR
from chemdoc_miner.query.finder import build_finder_index

FINDER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>iLENE Product Finder</title>
<style>
:root{--bg:#0f1419;--card:#1a2332;--text:#e8eef5;--muted:#8fa3b8;--accent:#4db6ff;--warn:#f0a030;--danger:#ff6b6b;--line:#2a3544;--ok:#6bcb77}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);min-height:100dvh;padding:16px;padding-bottom:max(16px,env(safe-area-inset-bottom))}
h1{font-size:1.25rem;font-weight:700;margin-bottom:4px}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:14px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px;margin-bottom:12px}
.panel h2{font-size:.78rem;color:var(--accent);text-transform:uppercase;letter-spacing:.04em;margin-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{border:1px solid var(--line);background:#243044;border-radius:999px;padding:6px 11px;font-size:.78rem;cursor:pointer;color:var(--text)}
.chip.on{background:rgba(77,182,255,.18);border-color:var(--accent);color:var(--accent)}
.row{display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap}
.row label{font-size:.78rem;color:var(--muted);min-width:110px}
select,input[type=number],input[type=text]{background:#243044;border:1px solid var(--line);color:var(--text);border-radius:8px;padding:8px 10px;font-size:.88rem}
select{flex:1;min-width:140px}
.spec-grid{display:grid;grid-template-columns:minmax(120px,1fr) 1fr 1fr;gap:8px;align-items:center;margin-bottom:8px}
.spec-grid .name{font-size:.78rem;color:var(--muted)}
.checks{display:grid;gap:6px}
.checks label{font-size:.82rem;display:flex;gap:8px;align-items:flex-start;color:var(--text)}
button.primary{background:var(--accent);color:#111;border:none;border-radius:10px;padding:12px 16px;font-weight:700;font-size:16px;width:100%;margin-top:4px}
button.link{background:transparent;border:none;color:var(--accent);font-size:.82rem;padding:8px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:10px}
.card-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.title{font-size:1rem;font-weight:700}
.score{font-size:.82rem;color:var(--ok);font-weight:700;white-space:nowrap}
.meta{font-size:.78rem;color:var(--muted);margin-top:4px}
.reasons{margin-top:8px;font-size:.78rem;color:var(--text);line-height:1.4}
.reasons li{margin-left:16px;margin-bottom:2px}
.specs-row{font-size:.78rem;color:var(--muted);margin-top:6px}
.actions{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.actions a{font-size:.78rem;color:var(--accent);text-decoration:none;padding:6px 10px;border:1px solid var(--line);border-radius:8px}
.empty{padding:24px;text-align:center;color:var(--muted)}
.badge{display:inline-block;padding:2px 7px;border-radius:6px;font-size:.72rem;font-weight:700;margin-left:6px}
.badge-warn{background:rgba(240,160,48,.2);color:var(--warn)}
.badge-danger{background:rgba(255,107,107,.2);color:var(--danger)}
.hint{margin-top:12px;font-size:.76rem;color:var(--muted);line-height:1.4}
</style>
</head>
<body>
<h1>iLENE Product Finder</h1>
<p class="sub" id="meta">Offline product recommendation by application and specs</p>

<div class="panel">
<h2>Application</h2>
<div class="chips" id="apps"></div>
</div>

<div class="panel">
<h2>Product family</h2>
<div class="row">
<select id="family">
<option value="all">All families</option>
</select>
</div>
</div>

<div class="panel">
<h2>Performance</h2>
<div class="chips" id="tags"></div>
</div>

<div class="panel">
<h2>Specifications</h2>
<div id="specs"></div>
</div>

<div class="panel">
<h2>Safety filters</h2>
<div class="checks" id="safety"></div>
</div>

<div class="panel">
<h2>Additional keywords</h2>
<input type="text" id="text" placeholder="e.g. flexible, wood coating, low odor" style="width:100%"/>
</div>

<button class="primary" id="find">Find products</button>
<button class="link" id="reset" type="button">Clear filters</button>

<div id="out"></div>
<p class="hint">Recommendations are based on TDS data. Safety filters use SDS hazard flags when available. Products without SDS are excluded when safety filters are active. Open ChemDoc-products.html for full TDS/SDS details.</p>

<script>
const INDEX = __FINDER_JSON__;
const $ = (id) => document.getElementById(id);
const state = { applications: new Set(), tags: new Set(), specs: {}, safety: { exclude: new Set(), warningOnly: false } };

function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}
function normApp(s) { return String(s || "").trim().toLowerCase().replace(/\\s+/g, " "); }

function initApps() {
  const box = $("apps");
  (INDEX.applications_vocab || []).forEach(item => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = item.label;
    btn.dataset.id = item.id;
    btn.onclick = () => {
      btn.classList.toggle("on");
      if (state.applications.has(item.id)) state.applications.delete(item.id);
      else state.applications.add(item.id);
    };
    box.appendChild(btn);
  });
}

function initFamilies() {
  const sel = $("family");
  const seen = new Set();
  Object.values(INDEX.products || {}).forEach(p => {
    if (!p.family || seen.has(p.family)) return;
    seen.add(p.family);
    const opt = document.createElement("option");
    opt.value = p.family;
    opt.textContent = p.family_en || p.family;
    sel.appendChild(opt);
  });
  sel.onchange = renderSpecFields;
}

function initTags() {
  const box = $("tags");
  (INDEX.performance_tags || []).forEach(item => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = item.label;
    btn.dataset.id = item.id;
    btn.onclick = () => {
      btn.classList.toggle("on");
      if (state.tags.has(item.id)) state.tags.delete(item.id);
      else state.tags.add(item.id);
    };
    box.appendChild(btn);
  });
}

function initSafety() {
  const box = $("safety");
  const warn = document.createElement("label");
  warn.innerHTML = '<input type="checkbox" id="warning-only"/> Exclude DANGER (WARNING only, requires SDS)';
  box.appendChild(warn);
  (INDEX.hazard_flags || []).forEach(item => {
    const lab = document.createElement("label");
    lab.innerHTML = '<input type="checkbox" data-flag="' + esc(item.id) + '"/> Exclude: ' + esc(item.label);
    box.appendChild(lab);
  });
}

const TAG_PHRASES = {
  low_yellowing: ["non-yellowing", "low yellowing"],
  fast_curing: ["fast curing", "quick cure"],
  flexible: ["flexible", "flexibility"],
  high_hardness: ["high hardness"],
  high_transparency: ["transparent", "high transparency"],
  low_odor: ["low odor"],
  adhesion: ["adhesion"],
  weather_resistance: ["weather resistance", "weathering"]
};

function specKeysForFamily(family) {
  const map = INDEX.family_specs || {};
  if (family && family !== "all" && map[family]) return map[family];
  return ["viscosity", "hardness", "tg", "functionality", "purity"];
}

function renderSpecFields() {
  const family = $("family").value;
  const keys = specKeysForFamily(family);
  const labels = INDEX.spec_labels || {};
  const box = $("specs");
  box.innerHTML = "";
  keys.forEach(key => {
    const row = document.createElement("div");
    row.className = "spec-grid";
    row.innerHTML =
      '<div class="name">' + esc(labels[key] || key) + '</div>' +
      '<input type="number" step="any" placeholder="min" data-key="' + esc(key) + '" data-bound="min"/>' +
      '<input type="number" step="any" placeholder="max" data-key="' + esc(key) + '" data-bound="max"/>';
    box.appendChild(row);
  });
}

function readCriteria() {
  const specs = {};
  document.querySelectorAll("#specs input[data-key]").forEach(inp => {
    const key = inp.dataset.key;
    const bound = inp.dataset.bound;
    if (!specs[key]) specs[key] = { min: null, max: null };
    if (inp.value !== "") specs[key][bound] = Number(inp.value);
  });
  const exclude = [];
  document.querySelectorAll("#safety input[data-flag]").forEach(inp => {
    if (inp.checked) exclude.push(inp.dataset.flag);
  });
  return {
    family: $("family").value || "all",
    applications: Array.from(state.applications),
    performance_tags: Array.from(state.tags),
    specs,
    text: $("text").value.trim(),
    safety: {
      exclude_flags: exclude,
      warning_only: $("warning-only").checked,
      require_sds: exclude.length > 0 || $("warning-only").checked
    }
  };
}

function passesSafety(product, safety) {
  if ((safety.exclude_flags || []).length || safety.warning_only) {
    if (!product.has_sds) return false;
    const flags = new Set(product.hazard_flags || []);
    for (const f of safety.exclude_flags || []) if (flags.has(f)) return false;
    if (safety.warning_only && String(product.signal_word || "").toUpperCase() === "DANGER") return false;
  }
  return true;
}

function specInRange(productVal, reqMin, reqMax) {
  if (reqMin == null && reqMax == null) return { ok: true, partial: 1 };
  if (productVal == null) return { ok: false, partial: 0 };
  let lo, hi, target;
  if (typeof productVal === "object") {
    lo = productVal.min != null ? Number(productVal.min) : Number(productVal.max);
    hi = productVal.max != null ? Number(productVal.max) : lo;
    target = (lo + hi) / 2;
    if (reqMin != null && hi < reqMin) return { ok: false, partial: 0 };
    if (reqMax != null && lo > reqMax) return { ok: false, partial: 0 };
  } else {
    target = Number(productVal);
    if (reqMin != null && target < reqMin) return { ok: false, partial: 0 };
    if (reqMax != null && target > reqMax) return { ok: false, partial: 0 };
  }
  if (reqMin != null && reqMax != null && reqMax > reqMin) {
    const span = reqMax - reqMin;
    const dist = Math.abs(target - (reqMin + reqMax) / 2) / span;
    return { ok: true, partial: Math.max(0.2, 1 - dist) };
  }
  return { ok: true, partial: 1 };
}

function scoreProduct(product, criteria) {
  if (criteria.family !== "all" && product.family !== criteria.family) return null;
  if (!passesSafety(product, criteria.safety || {})) return null;

  let score = 0;
  const reasons = [];
  const specHits = [];

  const apps = criteria.applications || [];
  if (apps.length) {
    const wanted = new Set(apps.map(normApp));
    const matched = (product.applications_norm || []).filter(a => wanted.has(a));
    if (!matched.length) return null;
    score += 35 * matched.length / apps.length;
    matched.forEach(norm => {
      const display = (product.applications || []).find(a => normApp(a) === norm) || norm;
      reasons.push("Application: " + display);
    });
  }

  const tags = criteria.performance_tags || [];
  if (tags.length) {
    const blob = [product.description || "", ...(product.highlights || []), ...(product.applications || [])].join(" ").toLowerCase();
    let hit = 0;
    tags.forEach(tag => {
      const phrases = TAG_PHRASES[tag] || [tag.replace(/_/g, " ")];
      if (phrases.some(p => blob.includes(p))) {
        hit += 1;
        reasons.push("Performance: " + tag.replace(/_/g, " "));
      }
    });
    if (!hit && !apps.length && !criteria.text && !hasSpecCriteria(criteria)) return null;
    score += 18 * hit / tags.length;
  }

  const activeSpecs = Object.entries(criteria.specs || {}).filter(([, b]) => b.min != null || b.max != null);
  if (activeSpecs.length) {
    let specScore = 0;
    for (const [key, bounds] of activeSpecs) {
      const val = (product.specs || {})[key];
      const chk = specInRange(val, bounds.min, bounds.max);
      if (!chk.ok) return null;
      specScore += chk.partial;
      const label = (INDEX.spec_labels || {})[key] || key;
      const disp = (product.spec_display || {})[key] || "";
      specHits.push(label + (disp ? ": " + disp : ""));
      reasons.push("Spec " + label + " in range");
    }
    score += 30 * specScore / activeSpecs.length;
  }

  const text = (criteria.text || "").trim();
  if (text) {
    const tokens = text.toLowerCase().split(/[^a-z0-9+\\-]+/).filter(t => t.length > 1);
    const blob = [product.description || "", ...(product.highlights || []), ...(product.applications || []), product.family_en || ""].join(" ").toLowerCase();
    const hits = tokens.filter(t => blob.includes(t)).length;
    if (hits) {
      score += Math.min(15, hits * 3);
      reasons.push("Text match (" + hits + " terms)");
    } else if (!apps.length && !activeSpecs.length && !tags.length) return null;
  }

  if (!hasAnyCriteria(criteria)) {
    score = 1;
    reasons.push("Catalog browse");
  }
  return { score, reasons, specHits };
}

function hasSpecCriteria(criteria) {
  return Object.values(criteria.specs || {}).some(b => b.min != null || b.max != null);
}
function hasAnyCriteria(criteria) {
  return (criteria.applications || []).length || (criteria.performance_tags || []).length || hasSpecCriteria(criteria) ||
    (criteria.text || "").trim() || (criteria.safety.exclude_flags || []).length || criteria.safety.warning_only;
}

function findProducts(criteria) {
  const results = [];
  for (const product of Object.values(INDEX.products || {})) {
    const scored = scoreProduct(product, criteria);
    if (!scored) continue;
    if (scored.score <= 0 && hasAnyCriteria(criteria)) continue;
    results.push({ product, ...scored });
  }
  results.sort((a, b) => b.score - a.score || String(a.product.grade).localeCompare(String(b.product.grade)));
  return results.slice(0, 15);
}

function renderResults(results, criteria) {
  if (!results.length) {
    $("out").innerHTML = '<div class="empty">No matching products. Try fewer safety filters or broader application/spec ranges.</div>';
    return;
  }
  let html = '<div class="meta" style="margin-top:14px">' + results.length + ' recommendation(s)</div>';
  results.forEach(({ product, score, reasons, specHits }) => {
    const sw = product.signal_word;
    const badge = sw === "DANGER" ? '<span class="badge badge-danger">DANGER</span>' :
      sw === "WARNING" ? '<span class="badge badge-warn">WARNING</span>' : "";
    const specs = Object.values(product.spec_display || {}).slice(0, 4).join(" · ");
    html += '<div class="card">' +
      '<div class="card-head"><div><div class="title">' + esc(product.grade_display || product.grade) + badge + '</div>' +
      '<div class="meta">' + esc(product.family_en || product.family) + (product.has_sds ? "" : " · no SDS") + '</div></div>' +
      '<div class="score">' + Math.min(100, Math.round(score)) + '%</div></div>' +
      (specs ? '<div class="specs-row">' + esc(specs) + '</div>' : "") +
      '<ul class="reasons">' + reasons.slice(0, 4).map(r => '<li>' + esc(r) + '</li>').join("") + '</ul>' +
      '<div class="actions">' +
      '<a href="ChemDoc-products.html?q=' + encodeURIComponent(product.grade) + '">TDS / SDS details</a>' +
      '</div></div>';
  });
  $("out").innerHTML = html;
}

function resetForm() {
  state.applications.clear();
  state.tags.clear();
  document.querySelectorAll(".chip.on").forEach(el => el.classList.remove("on"));
  $("family").value = "all";
  $("text").value = "";
  $("warning-only").checked = false;
  document.querySelectorAll("#safety input[data-flag]").forEach(inp => { inp.checked = false; });
  renderSpecFields();
  $("out").innerHTML = "";
}

$("find").onclick = () => renderResults(findProducts(readCriteria()), readCriteria());
$("reset").onclick = resetForm;
$("meta").textContent = (INDEX.count || 0) + " products · offline finder";
initApps();
initFamilies();
initTags();
initSafety();
renderSpecFields();
</script>
</body>
</html>
"""


from chemdoc_miner.export.app_mobile import export_app_html


def export_finder_html(out_path: Path | None = None) -> Path:
    return export_app_html(out_path or (DATA_DIR / "ChemDoc.html"))
