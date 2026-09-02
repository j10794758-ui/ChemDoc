const $ = (id) => document.getElementById(id);
const qEl = $("q");
const answerEl = $("answer");
const hitsEl = $("hits");
const sheetEl = $("sheet");
const chipsEl = $("chips");

let currentFamily = "";
let lastHits = [];

async function jget(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
async function jpost(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function fileUrl(path) {
  return "/api/file?path=" + encodeURIComponent(path);
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

async function boot() {
  const stats = await jget("/api/stats");
  $("stat-products").textContent = stats.products;
  $("stat-eq").textContent = stats.lookup_keys || stats.eq_groups || stats.equivalents;
  $("stat-docs").textContent = stats.documents;
  const labels = { "": "全部", ...(stats.family_labels || {}) };
  chipsEl.innerHTML = "";
  for (const [id, label] of Object.entries(labels)) {
    const btn = document.createElement("button");
    btn.className = "chip" + (id === currentFamily ? " active" : "");
    btn.textContent = label;
    btn.onclick = () => {
      currentFamily = id;
      [...chipsEl.children].forEach((c) => c.classList.remove("active"));
      btn.classList.add("active");
      browse();
    };
    chipsEl.appendChild(btn);
  }
  await browse();
}

async function browse() {
  const data = await jget("/api/list?company=Power Dream" + (currentFamily ? "&family=" + encodeURIComponent(currentFamily) : "") + "&limit=60");
  lastHits = (data.products || []).map((p) => ({ kind: "product", product: p }));
  renderHits(lastHits, `${data.company} · ${data.count} 个型号`);
}

function renderHits(items, headline) {
  hitsEl.innerHTML = "";
  if (headline) {
    answerEl.innerHTML = `<p>${escapeHtml(headline)}</p>`;
  }
  items.forEach((item, i) => {
    const li = document.createElement("li");
    const p = item.product || item;
    const title = p.grade_display || p.grade || item.dst_grade || "—";
    const meta = [p.family_label || p.family, p.cas, (p.applications || [])[0]].filter(Boolean).join(" · ");
    const why = (item.reasons && item.reasons[0]) || p.description || "";
    li.innerHTML = `<div class="g">${escapeHtml(title)}</div>
      <div class="meta">${escapeHtml(meta)}</div>
      <div class="why">${escapeHtml(why).slice(0, 160)}</div>`;
    li.onclick = () => select(i);
    hitsEl.appendChild(li);
  });
}

async function select(index) {
  [...hitsEl.children].forEach((n, i) => n.classList.toggle("active", i === index));
  const item = lastHits[index];
  if (!item) return;
  if (item.kind === "eq") {
    const grade = item.power_dream || item.dst_grade;
    if (item.dst_company === "Power Dream" || item.src_company === "Power Dream") {
      const g = item.dst_company === "Power Dream" ? item.dst_grade : item.src_grade;
      try {
        const product = await jget("/api/product/" + encodeURIComponent(g));
        renderSheet(product);
        return;
      } catch (_) {}
    }
    renderEqOnly(item);
    return;
  }
  const grade = item.product?.grade || item.grade;
  if (!grade) return;
  const product = item.product?.tds_path ? item.product : await jget("/api/product/" + encodeURIComponent(grade));
  renderSheet(product, item.reasons);
}

function renderSheet(p, reasons) {
  const props = p.properties || {};
  const apps = (p.applications || []).map((a) => `<span class="pill">${escapeHtml(a)}</span>`).join("");
  const highs = (p.highlights || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("");
  const eqs = (p.equivalents || [])
    .map(
      (e) =>
        `<tr><td>${escapeHtml(e.src_company)} ${escapeHtml(e.src_grade)}</td><td>${escapeHtml(e.dst_company)} ${escapeHtml(e.dst_grade)}</td><td>${escapeHtml(e.source_file || "")}</td></tr>`
    )
    .join("");
  const tds = p.tds_path ? `<a href="${fileUrl(p.tds_path)}" target="_blank" rel="noopener">打开 TDS</a>` : "";
  const sds = p.sds_path ? `<a class="ghost" href="${fileUrl(p.sds_path)}" target="_blank" rel="noopener">打开 SDS</a>` : "";
  const reasonBlock = reasons?.length
    ? `<dt>依据</dt><dd>${reasons.map((r) => escapeHtml(r)).join("<br/>")}</dd>`
    : "";
  sheetEl.innerHTML = `
    <div class="sheet-head">
      <div>
        <h2>${escapeHtml(p.grade_display || p.grade)}</h2>
        <span class="badge">${escapeHtml(p.family_label || p.family || "")}</span>
      </div>
      <div class="actions">${tds}${sds}</div>
    </div>
    <dl class="grid-kv">
      <dt>描述</dt><dd>${escapeHtml(p.description || "—")}</dd>
      <dt>化学名</dt><dd>${escapeHtml(p.chemical_name || "—")}</dd>
      <dt>CAS</dt><dd>${escapeHtml(p.cas || "—")}</dd>
      <dt>粘度</dt><dd>${escapeHtml(props.viscosity || "—")}</dd>
      <dt>官能度</dt><dd>${escapeHtml(props.functionality || "—")}</dd>
      <dt>外观</dt><dd>${escapeHtml(props.appearance || "—")}</dd>
      <dt>包装</dt><dd>${escapeHtml(p.package || "—")}</dd>
      ${reasonBlock}
    </dl>
    <h3 style="font-family:var(--cond);letter-spacing:.08em;color:var(--amber);font-weight:600;">APPLICATIONS</h3>
    <div class="pills">${apps || "—"}</div>
    <h3 style="font-family:var(--cond);letter-spacing:.08em;color:var(--amber);font-weight:600;">PERFORMANCE</h3>
    <ul>${highs || "<li>—</li>"}</ul>
    <h3 style="font-family:var(--cond);letter-spacing:.08em;color:var(--amber);font-weight:600;">OFFSETS</h3>
    <table class="eq">
      <thead><tr><th>FROM</th><th>TO</th><th>SOURCE</th></tr></thead>
      <tbody>${eqs || "<tr><td colspan=3>无对照</td></tr>"}</tbody>
    </table>
    <p class="warn">销售对标，需配方验证。勿跨温度比较粘度。</p>
  `;
}

function renderEqOnly(row) {
  sheetEl.innerHTML = `
    <div class="sheet-head"><div><h2>${escapeHtml(row.src_grade)}</h2>
    <span class="badge">${escapeHtml(row.src_company)}</span></div></div>
    <dl class="grid-kv">
      <dt>对应</dt><dd>${escapeHtml(row.dst_company)} ${escapeHtml(row.dst_grade)}</dd>
      <dt>化学描述</dt><dd>${escapeHtml(row.chemistry || "—")}</dd>
      <dt>来源</dt><dd>${escapeHtml(row.source_file || "")}</dd>
    </dl>
    <p class="warn">销售对标，需配方验证。</p>`;
}

async function runQuery() {
  const q = qEl.value.trim();
  if (!q) return;
  answerEl.textContent = "检索目录中…";
  const data = await jpost("/api/ask", { question: q });
  answerEl.textContent = data.answer || "";
  lastHits = [];
  if (data.intent === "product" && data.product) {
    lastHits = [{ kind: "product", product: data.product }];
    renderHits(lastHits);
    select(0);
  } else if (data.intent === "recommend") {
    lastHits = (data.recommendations || []).map((r) => ({ kind: "product", product: r, reasons: r.reasons }));
    renderHits(lastHits);
    if (lastHits.length) select(0);
  } else if (data.intent === "list" && data.products) {
    lastHits = data.products.map((p) => ({ kind: "product", product: p }));
    renderHits(lastHits);
  } else if (data.equivalents) {
    lastHits = data.equivalents.map((e) => ({ kind: "eq", ...e }));
    hitsEl.innerHTML = "";
    lastHits.forEach((e, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<div class="g">${escapeHtml(e.dst_company)} ${escapeHtml(e.dst_grade)}</div>
        <div class="meta">${escapeHtml(e.src_company)} ${escapeHtml(e.src_grade)} · ${escapeHtml(e.eq_kind || "")}</div>`;
      li.onclick = () => select(i);
      hitsEl.appendChild(li);
    });
    if (lastHits.length) select(0);
  }
}

$("go").onclick = runQuery;
qEl.addEventListener("keydown", (ev) => {
  if (ev.key === "Enter") runQuery();
});

boot().catch((err) => {
  answerEl.textContent = "目录尚未建好。请先运行 python -m chemdoc_miner ingest";
  console.error(err);
});
