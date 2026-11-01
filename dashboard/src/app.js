const D = __DATA__;
const $ = s => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt = {
  int: v => Math.round(v).toLocaleString("en-US"),
  pct: (v, d = 1) => (v * 100).toFixed(d) + "%",
  usd: v => { const a = Math.abs(v); const s = v < 0 ? "−" : ""; return a >= 1e6 ? s + "$" + (a / 1e6).toFixed(2) + "M" : a >= 1e3 ? s + "$" + (a / 1e3).toFixed(0) + "k" : s + "$" + a.toFixed(0); },
  d2: v => v.toFixed(2),
};
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const mLabel = m => MONTHS[+m.slice(5) - 1] + " " + m.slice(0, 4);

/* ---------- cube helpers ---------- */
function cube(c) {
  const idx = {}; c.cols.forEach((k, i) => idx[k] = i);
  return { ...c, idx, val: (r, k) => r[idx[k]], dim: (r, k) => c.dims[k][r[idx[k]]] };
}
const A = cube(D.A), B = cube(D.B), S = cube(D.S);
const F = { yr: "all", market: "all", mode: "all", seg: "all" };
const MEAS_A = ["lines","on_time","within_tol","breach","slip_sum","real_sum","sched_sum","sales","discount","net","profit","save5","save10","save15","loss_lines","loss_amt","margin_breach"];
const MEAS_B = ["lines","on_time","sales","discount","net","profit","save10","loss_lines","loss_amt","margin_breach"];

function rowsA(opts = {}) {
  return A.rows.filter(r => {
    const m = A.dim(r, "month");
    if (opts.month ? m !== opts.month : (F.yr !== "all" && !m.startsWith(F.yr))) return false;
    if (F.market !== "all" && A.dim(r, "market") !== F.market) return false;
    if (F.mode !== "all" && A.dim(r, "shipping_mode") !== F.mode) return false;
    if (F.seg !== "all" && A.dim(r, "customer_segment") !== F.seg) return false;
    return true;
  });
}
function rowsB() {
  return B.rows.filter(r => (F.yr === "all" || B.dim(r, "yr") === F.yr) &&
    (F.market === "all" || B.dim(r, "market") === F.market) &&
    (F.mode === "all" || B.dim(r, "shipping_mode") === F.mode) &&
    (F.seg === "all" || B.dim(r, "customer_segment") === F.seg));
}
function sum(c, rows, meas) {
  const t = {}; meas.forEach(k => t[k] = 0);
  rows.forEach(r => meas.forEach(k => t[k] += c.val(r, k)));
  return t;
}
function group(c, rows, keyFn, meas) {
  const g = new Map();
  rows.forEach(r => { const k = keyFn(r); if (!g.has(k)) g.set(k, []); g.get(k).push(r); });
  return new Map([...g].map(([k, rs]) => [k, sum(c, rs, meas)]));
}
const kpi = t => ({
  lines: t.lines, onTime: t.on_time / t.lines, withinTol: t.within_tol / t.lines, breach: t.breach / t.lines,
  slip: t.slip_sum / t.lines, margin: t.profit / t.net, discShare: t.discount / t.sales,
  discVsProfit: t.discount / t.profit, lossShare: t.loss_lines / t.lines, marginBreach: t.margin_breach / t.lines,
});

/* ---------- targets (also used by the Excel report) ---------- */
const TARGETS = [
  { key: "onTime", name: "On-time delivery", op: ">=", target: 0.45, f: v => fmt.pct(v) },
  { key: "withinTol", name: "Within 1-day tolerance", op: ">=", target: 0.80, f: v => fmt.pct(v) },
  { key: "slip", name: "Average slippage (days)", op: "<=", target: 0.50, f: v => fmt.d2(v) },
  { key: "margin", name: "Profit margin", op: ">=", target: 0.12, f: v => fmt.pct(v) },
  { key: "discShare", name: "Discount as % of gross sales", op: "<=", target: 0.10, f: v => fmt.pct(v) },
  { key: "lossShare", name: "Loss-making order lines", op: "<=", target: 0.15, f: v => fmt.pct(v) },
];
const round3 = v => Math.round(v * 1000) / 1000;
const passes = (t, v) => t.op === ">=" ? round3(v) >= t.target : round3(v) <= t.target;

/* ---------- tooltip ---------- */
const tip = $("#tip");
function showTip(e, html) { tip.innerHTML = html; tip.hidden = false; const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8); tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px"; }
function hideTip() { tip.hidden = true; }
function hover(el, html) { el.addEventListener("mousemove", e => showTip(e, html)); el.addEventListener("mouseleave", hideTip); el.style.cursor = "default"; }

/* ---------- svg helpers ---------- */
function svg(host, h) {
  const w = Math.max(300, host.clientWidth || 560);
  host.innerHTML = "";
  const s = document.createElementNS(NS, "svg"); s.setAttribute("viewBox", `0 0 ${w} ${h}`); s.setAttribute("role", "img");
  host.appendChild(s); return { s, w, h };
}
function el(parent, tag, attrs = {}, text) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (text !== undefined) e.textContent = text;
  parent.appendChild(e); return e;
}
let gid = 0;
function grad(s, color, o1 = 0.32, o2 = 0, vertical = true) {
  let defs = s.querySelector("defs"); if (!defs) defs = el(s, "defs");
  const id = "g" + (++gid), g = el(defs, "linearGradient", { id, x1: 0, y1: 0, x2: vertical ? 0 : 1, y2: vertical ? 1 : 0 });
  el(g, "stop", { offset: "0%", "stop-color": color, "stop-opacity": o1 }); el(g, "stop", { offset: "100%", "stop-color": color, "stop-opacity": o2 });
  return `url(#${id})`;
}
function niceTicks(lo, hi, n = 4) {
  const span = hi - lo || 1, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(x => x * mag).find(x => span / x <= n) || step0;
  const a = Math.floor(lo / step) * step, out = [];
  for (let v = a; ; v += step) { out.push(+v.toFixed(10)); if (v >= hi - step * 0.001) break; }
  return out;
}

/* line chart: series [{name, pts:[{x(label), y}], color, dash, width}] over shared x labels */
function lineChart(host, labels, series, opt = {}) {
  const { s, w } = svg(host, opt.h || 230), h = opt.h || 230;
  const L = 48, R = 12, T = 12, Bm = 28;
  const ys = series.flatMap(se => se.pts.map(p => p.y)).concat(opt.ref != null ? [opt.ref] : []);
  let lo = Math.min(...ys), hi = Math.max(...ys); const pad = (hi - lo) * 0.15 || 0.01; lo -= pad; hi += pad;
  if (opt.zero) lo = 0;
  const ticks = niceTicks(lo, hi, 4); lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
  const X = i => L + (w - L - R) * (labels.length === 1 ? 0.5 : i / (labels.length - 1));
  const Y = v => T + (h - T - Bm) * (1 - (v - lo) / (hi - lo));
  ticks.forEach(t => { el(s, "line", { x1: L, x2: w - R, y1: Y(t), y2: Y(t), stroke: css("--line"), "stroke-width": 1 }); el(s, "text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, opt.yf ? opt.yf(t) : t); });
  const every = Math.max(1, Math.ceil(labels.length / Math.max(2, Math.floor((w - L) / 70))));
  labels.forEach((lb, i) => { if (i % every === 0) el(s, "text", { x: X(i), y: h - 8, "text-anchor": "middle" }, opt.xf ? opt.xf(lb) : lb); });
  if (opt.band) el(s, "rect", { x: X(opt.band[0]) , y: T, width: X(opt.band[1]) - X(opt.band[0]), height: h - T - Bm, fill: css("--warn"), opacity: 0.09 });
  series.forEach((se, k) => {
    const d = se.pts.map((p, j) => (j ? "L" : "M") + X(p.i).toFixed(1) + "," + Y(p.y).toFixed(1)).join("");
    if (k === 0 && opt.area !== false) el(s, "path", { d: d + `L${X(se.pts[se.pts.length - 1].i).toFixed(1)},${h - Bm}L${X(se.pts[0].i).toFixed(1)},${h - Bm}Z`, fill: grad(s, se.color, 0.28, 0) });
    el(s, "path", { d, fill: "none", stroke: se.color, "stroke-width": se.width || 2.5, "stroke-dasharray": se.dash || "", "stroke-linejoin": "round", "stroke-linecap": "round" });
    if (se.dots) se.pts.forEach(p => el(s, "circle", { cx: X(p.i), cy: Y(p.y), r: 4, fill: se.color, stroke: css("--surface"), "stroke-width": 2 }));
    if (opt.endLabel && k === 0) { const p = se.pts[se.pts.length - 1]; el(s, "circle", { cx: X(p.i), cy: Y(p.y), r: 5, fill: se.color, stroke: css("--surface"), "stroke-width": 2.5 }); }
  });
  if (opt.ref != null) {
    el(s, "line", { x1: L, x2: w - R, y1: Y(opt.ref), y2: Y(opt.ref), stroke: css("--ink"), opacity: 0.55, "stroke-dasharray": "5 5", "stroke-width": 1.3 });
    const lt = opt.refLabel || "Target"; const bx = w - R - (lt.length * 6.4 + 14);
    el(s, "rect", { x: bx, y: Y(opt.ref) - 20, width: lt.length * 6.4 + 14, height: 17, rx: 8.5, fill: css("--ink") });
    el(s, "text", { x: bx + 7, y: Y(opt.ref) - 8, style: "fill:var(--surface);font-size:10.5px;font-weight:700" }, lt);
  }
  // hover layer
  const cross = el(s, "line", { y1: T, y2: h - Bm, stroke: css("--muted"), "stroke-width": 1, opacity: 0 });
  const hit = el(s, "rect", { x: L, y: T, width: w - L - R, height: h - T - Bm, fill: "transparent" });
  hit.addEventListener("mousemove", e => {
    const r = s.getBoundingClientRect(), px = (e.clientX - r.left) * (w / r.width);
    const i = Math.max(0, Math.min(labels.length - 1, Math.round((px - L) / (w - L - R) * (labels.length - 1))));
    cross.setAttribute("x1", X(i)); cross.setAttribute("x2", X(i)); cross.setAttribute("opacity", 0.6);
    const rows = series.map(se => { const p = se.pts.find(q => q.i === i); return p ? `<div>${se.name}: <b>${opt.yf ? opt.yf(p.y, true) : p.y}</b></div>` : ""; }).join("");
    showTip(e, `<b>${opt.xf ? opt.xf(labels[i]) : labels[i]}</b>${rows}`);
  });
  hit.addEventListener("mouseleave", () => { cross.setAttribute("opacity", 0); hideTip(); });
}

/* horizontal 100% stacked bars */
function stackBars(host, items, parts) {
  const rowH = 38, { s, w } = svg(host, items.length * rowH + 8);
  const L = 112, R = 8;
  items.forEach((it, j) => {
    const y = 4 + j * rowH; let x = L;
    el(s, "text", { x: L - 10, y: y + 19, "text-anchor": "end", class: "lbl" }, it.label);
    parts.forEach(p => {
      const v = it[p.key], wd = (w - L - R) * v;
      if (wd <= 0) return;
      const r = el(s, "rect", { x: x + 1, y: y + 2, width: Math.max(0, wd - 2), height: rowH - 12, rx: 7, fill: p.color });
      hover(r, `<b>${it.label}</b><div>${p.name}: ${fmt.pct(v)}</div><div>${fmt.int(it.lines)} order lines</div>`);
      if (wd > 40) el(s, "text", { x: x + wd / 2, y: y + 19, "text-anchor": "middle", style: "fill:#fff;font-weight:700;font-size:11.5px" }, fmt.pct(v, 0));
      x += wd;
    });
  });
}

/* vertical columns */
function columns(host, items, opt = {}) {
  const h = opt.h || 220, { s, w } = svg(host, h);
  const L = 46, R = 8, T = 14, Bm = 30;
  const max = Math.max(...items.map(i => i.v)) * 1.1, min = Math.min(0, ...items.map(i => i.v));
  const ticks = niceTicks(min, max, 4); const hi = Math.max(max, ticks[ticks.length - 1]), lo = Math.min(min, ticks[0]);
  const Y = v => T + (h - T - Bm) * (1 - (v - lo) / (hi - lo));
  ticks.forEach(t => { el(s, "line", { x1: L, x2: w - R, y1: Y(t), y2: Y(t), stroke: css("--line") }); el(s, "text", { x: L - 6, y: Y(t) + 4, "text-anchor": "end" }, opt.yf ? opt.yf(t) : t); });
  const bw = (w - L - R) / items.length;
  items.forEach((it, j) => {
    const x = L + j * bw + bw * 0.15, y0 = Y(Math.max(0, it.v)), y1 = Y(Math.min(0, it.v));
    const c = it.color || css("--accent");
    const r = el(s, "rect", { x, y: y0, width: bw * 0.7, height: Math.max(1, y1 - y0), rx: Math.min(6, bw * 0.2), fill: grad(s, c, 1, 0.55) });
    hover(r, it.tip || `<b>${it.label}</b><div>${opt.yf ? opt.yf(it.v) : it.v}</div>`);
    el(s, "text", { x: x + bw * 0.35, y: h - 10, "text-anchor": "middle" }, it.label);
    if (opt.labels) el(s, "text", { x: x + bw * 0.35, y: y0 - 4, "text-anchor": "middle", class: "lbl" }, opt.yf ? opt.yf(it.v) : it.v);
  });
}

/* ---------- filters ---------- */
function fillSelect(id, values, label) {
  const sel = $(id); sel.innerHTML = `<option value="all">All ${label}</option>` + values.map(v => `<option value="${v}">${v}</option>`).join("");
}
fillSelect("#f-yr", ["2015", "2016", "2017"], "years");
fillSelect("#f-mk", A.dims.market, "markets");
fillSelect("#f-md", A.dims.shipping_mode, "modes");
fillSelect("#f-sg", A.dims.customer_segment, "segments");
[["#f-yr", "yr"], ["#f-mk", "market"], ["#f-md", "mode"], ["#f-sg", "seg"]].forEach(([id, k]) => $(id).addEventListener("change", e => { F[k] = e.target.value; drillMarket = null; render(); }));
$("#f-reset").addEventListener("click", () => { Object.keys(F).forEach(k => F[k] = "all"); ["#f-yr", "#f-mk", "#f-md", "#f-sg"].forEach(id => $(id).value = "all"); drillMarket = null; render(); });

/* ---------- views ---------- */
const VIEWS = ["project", "overview", "delivery", "profit", "forecast", "report", "method"];
let current = "project", drillMarket = null, cap = 10;
function route() {
  const h = location.hash.slice(1); current = VIEWS.includes(h) ? h : "project";
  VIEWS.forEach(v => $("#v-" + v).hidden = v !== current);
  document.querySelectorAll("nav.tabs a").forEach(a => { if (a.getAttribute("href") === "#" + current) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
  render();
}
addEventListener("hashchange", route);

const MODE_ORDER = ["Same Day", "First Class", "Second Class", "Standard Class"];

function renderOverview() {
  const t = sum(A, rowsA(), MEAS_A), k = kpi(t);
  const tiles = [
    { k: "Order lines", v: fmt.int(k.lines), t: `${F.yr === "all" ? "33 months" : F.yr}` },
    ...TARGETS.slice(0, 4).map(tg => ({ k: tg.name, v: tg.f(k[tg.key]), tg })),
    { k: "Discount given vs profit", alt: true, v: fmt.pct(k.discVsProfit, 0), t: `${fmt.usd(t.discount)} discount · ${fmt.usd(t.profit)} profit` },
  ];
  $("#kpis").innerHTML = tiles.map(x => {
    const chip = x.tg ? (passes(x.tg, k[x.tg.key]) ? '<span class="chip pass">on target</span>' : '<span class="chip fail">off target</span>') : "";
    const tl = x.tg ? `${chip}<span>target ${x.tg.op === ">=" ? "≥" : "≤"} ${x.tg.key === "slip" ? x.tg.target.toFixed(2) : fmt.pct(x.tg.target, 0)}</span>` : `<span>${x.t}</span>`;
    let cls = "info", meter = "";
    if (x.tg) {
      const v = k[x.tg.key], ok = passes(x.tg, v); cls = ok ? "pass" : "fail";
      const scale = x.tg.key === "slip" ? 1.5 : 1, pos = Math.min(1, v / scale), tp = Math.min(1, x.tg.target / scale);
      meter = `<div class="meter"><span style="width:${(pos * 100).toFixed(1)}%"></span><i style="left:${(tp * 100).toFixed(1)}%"></i></div>`;
    } else if (x.alt) cls = "alt";
    return `<div class="kpi ${cls}"><div class="k">${x.k}</div><div class="v">${x.v}</div>${meter}<div class="t">${tl}</div></div>`;
  }).join("");

  const byM = group(A, rowsA(), r => A.dim(r, "month"), MEAS_A); const months = [...byM.keys()].sort();
  lineChart($("#c-ontime"), months, [{ name: "On-time", color: css("--accent"), pts: months.map((m, i) => ({ i, y: byM.get(m).on_time / byM.get(m).lines })) }],
    { ref: 0.45, refLabel: "Target 45%", endLabel: true, yf: (v, tip) => (v * 100).toFixed(tip ? 1 : 0) + "%", xf: mLabel });
  lineChart($("#c-margin"), months, [{ name: "Margin", color: css("--accent2"), pts: months.map((m, i) => ({ i, y: byM.get(m).profit / byM.get(m).net })) }],
    { ref: 0.12, refLabel: "Target 12%", endLabel: true, yf: (v, tip) => (v * 100).toFixed(tip ? 1 : 0) + "%", xf: mLabel });

  const byMode = group(A, rowsA(), r => A.dim(r, "shipping_mode"), MEAS_A);
  stackBars($("#c-modestack"), MODE_ORDER.filter(m => byMode.has(m)).map(m => { const g = byMode.get(m); return { label: m, lines: g.lines, on: g.on_time / g.lines, one: (g.within_tol - g.on_time) / g.lines, two: g.breach / g.lines }; }),
    [{ key: "on", name: "On time", color: css("--good") }, { key: "one", name: "1 day late", color: css("--warn") }, { key: "two", name: "2+ days late", color: css("--bad") }]);
}

const FINDINGS = [
  "<b>Only 42.7% of order lines arrive within the promised days</b>, and the rate barely moves across 33 months or five markets. The problem is the process and the promise, not one region.",
  "<b>First Class is promised in 1 day but always takes 2</b> (0% on time, 100% within tolerance). Promising 2 days instead would remove about a quarter of all late lines without changing how anything ships.",
  "<b>Second Class is the real operational gap:</b> promised 2 days, averages 4. About 60% of its lines are more than 1 day late in every market.",
  "<b>Discounts of $3.32M almost equal the $3.53M profit</b> (94%). Margin % hardly changes by discount band, so the cost is hidden in dollars.",
  "<b>A 10% discount cap</b> would have kept up to $1.02M (an upper bound of +29% profit), affecting 44% of lines.",
  "<b>18.7% of lines lose money</b> in every category, and they wipe out about half of the profit made on the other lines. That is why actual margin (12%) sits far below the typical line margin (27%).",
];

function renderDelivery() {
  const rows = rowsA();
  const byMode = group(A, rows, r => A.dim(r, "shipping_mode"), MEAS_A);
  // dumbbell
  const items = MODE_ORDER.filter(m => byMode.has(m)).map(m => { const g = byMode.get(m); return { m, plan: g.sched_sum / g.lines, act: g.real_sum / g.lines, lines: g.lines }; });
  const rowH = 44, { s, w } = svg($("#c-dumbbell"), items.length * rowH + 30);
  const L = 112, R = 24, max = 5; const X = v => L + (w - L - R) * v / max;
  for (let d = 0; d <= max; d++) { el(s, "line", { x1: X(d), x2: X(d), y1: 4, y2: items.length * rowH + 4, stroke: css("--line") }); el(s, "text", { x: X(d), y: items.length * rowH + 22, "text-anchor": "middle" }, d + (d === 1 ? " day" : " days")); }
  items.forEach((it, j) => {
    const y = 4 + j * rowH + rowH / 2, late = it.act > it.plan + 0.001;
    el(s, "text", { x: L - 10, y: y + 4, "text-anchor": "end", class: "lbl" }, it.m);
    el(s, "line", { x1: X(it.plan), x2: X(it.act), y1: y, y2: y, stroke: late ? css("--bad") : css("--good"), "stroke-width": 3, opacity: 0.5 });
    const p = el(s, "circle", { cx: X(it.plan), cy: y, r: 7, fill: css("--plan") });
    const a = el(s, "circle", { cx: X(it.act), cy: y, r: 7, fill: late ? css("--bad") : css("--good") });
    const html = `<b>${it.m}</b><div>Promised: ${it.plan.toFixed(2)} days</div><div>Actual: ${it.act.toFixed(2)} days</div><div>Gap: ${(it.act - it.plan >= 0 ? "+" : "") + (it.act - it.plan).toFixed(2)} days</div>`;
    hover(p, html); hover(a, html);
    el(s, "text", { x: X(Math.max(it.plan, it.act)) + 12, y: y + 4, class: "lbl" }, Math.abs(it.act - it.plan) < 0.05 ? "on plan" : (it.act - it.plan > 0 ? "+" : "") + (it.act - it.plan).toFixed(1) + " d");
  });
  // slippage distribution
  const sr = S.rows.filter(r => (F.yr === "all" || S.dim(r, "yr") === F.yr) && (F.market === "all" || S.dim(r, "market") === F.market) && (F.mode === "all" || S.dim(r, "shipping_mode") === F.mode) && (F.seg === "all" || S.dim(r, "customer_segment") === F.seg));
  const dist = new Map(); sr.forEach(r => { const d = S.val(r, "slippage_days"); dist.set(d, (dist.get(d) || 0) + S.val(r, "n")); });
  const tot = [...dist.values()].reduce((a, b) => a + b, 0);
  const keys = [...dist.keys()].sort((a, b) => a - b);
  columns($("#c-slip"), keys.map(k => ({ label: (k > 0 ? "+" : "") + k, v: dist.get(k), color: k <= 0 ? css("--good") : k === 1 ? css("--warn") : css("--bad"), tip: `<b>${k > 0 ? "+" : ""}${k} days</b><div>${fmt.int(dist.get(k))} lines (${fmt.pct(dist.get(k) / tot)})</div>` })), { yf: v => v >= 1000 ? (v / 1000) + "k" : v });
  // heat table market x mode
  const byMM = group(A, rows, r => A.dim(r, "market") + "|" + A.dim(r, "shipping_mode"), MEAS_A);
  const byMk = group(A, rows, r => A.dim(r, "market"), MEAS_A);
  const modes = MODE_ORDER.filter(m => byMode.has(m)); const markets = [...byMk.keys()].sort();
  const heat = v => { const a = Math.min(1, v / 0.65); return `background:color-mix(in srgb, var(--bad) ${Math.round(a * 70)}%, transparent)`; };
  $("#t-heat").innerHTML = `<table class="heat"><thead><tr><th>Market</th>${modes.map(m => `<th class="n">${m}</th>`).join("")}<th class="n">All</th></tr></thead><tbody>` +
    markets.map(mk => `<tr class="click${drillMarket === mk ? " sel" : ""}" data-mk="${mk}" tabindex="0"><td>${mk}</td>${modes.map(md => { const g = byMM.get(mk + "|" + md); if (!g) return "<td></td>"; const v = g.breach / g.lines; return `<td class="c" style="${heat(v)}">${fmt.pct(v, 0)}</td>`; }).join("")}<td class="c n">${fmt.pct(byMk.get(mk).breach / byMk.get(mk).lines, 1)}</td></tr>`).join("") + "</tbody></table>";
  document.querySelectorAll("#t-heat tr.click").forEach(tr => { const go = () => { drillMarket = tr.dataset.mk; renderDelivery(); }; tr.addEventListener("click", go); tr.addEventListener("keydown", e => { if (e.key === "Enter") go(); }); });
  const mk = drillMarket || markets[0];
  const byR = group(A, rows.filter(r => A.dim(r, "market") === mk), r => A.dim(r, "order_region"), MEAS_A);
  $("#drill-title").textContent = `Regions in ${mk}`;
  $("#drill-sub").textContent = drillMarket ? "Drill-down from the market row you picked." : "Showing the first market. Click a row on the left to change.";
  $("#t-drill").innerHTML = `<table><thead><tr><th>Region</th><th class="n">Lines</th><th class="n">On time</th><th class="n">Breach</th><th class="n">Avg slip</th></tr></thead><tbody>` +
    [...byR].sort((a, b) => b[1].lines - a[1].lines).map(([r, g]) => `<tr><td>${r}</td><td class="n">${fmt.int(g.lines)}</td><td class="n">${fmt.pct(g.on_time / g.lines)}</td><td class="n">${fmt.pct(g.breach / g.lines)}</td><td class="n">${(g.slip_sum / g.lines).toFixed(2)}</td></tr>`).join("") + "</tbody></table>";
}

function renderProfit() {
  const t = sum(A, rowsA(), MEAS_A);
  const cost = t.net - t.profit;
  // waterfall
  const steps = [{ l: "Gross sales", a: 0, b: t.sales, c: css("--accent") }, { l: "Discount", a: t.sales - t.discount, b: t.sales, c: css("--warn") }, { l: "Cost", a: t.profit, b: t.net, c: css("--bad") }, { l: "Profit", a: 0, b: t.profit, c: css("--good") }];
  const h = 250, { s, w } = svg($("#c-bridge"), h); const L = 50, R = 8, T = 22, Bm = 28;
  const ticks = niceTicks(0, t.sales, 4); const hi = ticks[ticks.length - 1];
  const Y = v => T + (h - T - Bm) * (1 - v / hi);
  ticks.forEach(tk => { el(s, "line", { x1: L, x2: w - R, y1: Y(tk), y2: Y(tk), stroke: css("--line") }); el(s, "text", { x: L - 6, y: Y(tk) + 4, "text-anchor": "end" }, tk === 0 ? "$0" : "$" + (tk / 1e6) + "M"); });
  const bw = (w - L - R) / steps.length;
  steps.forEach((st, j) => {
    const x = L + j * bw + bw * 0.18, ww = bw * 0.64;
    const r = el(s, "rect", { x, y: Y(st.b), width: ww, height: Math.max(1, Y(st.a) - Y(st.b)), rx: 3, fill: st.c });
    const val = st.l === "Discount" ? -t.discount : st.l === "Cost" ? -cost : st.b;
    hover(r, `<b>${st.l}</b><div>${fmt.usd(val)}</div><div>${fmt.pct(Math.abs(val) / t.sales)} of gross sales</div>`);
    el(s, "text", { x: x + ww / 2, y: Y(st.b) - 6, "text-anchor": "middle", class: "lbl" }, fmt.usd(val));
    el(s, "text", { x: x + ww / 2, y: h - 9, "text-anchor": "middle" }, st.l);
    if (j < steps.length - 1) { const nx = L + (j + 1) * bw + bw * 0.18; const yy = st.l === "Gross sales" ? Y(st.b) : Y(st.a); el(s, "line", { x1: x + ww, x2: nx, y1: yy, y2: yy, stroke: css("--muted"), "stroke-dasharray": "3 3" }); }
  });
  const gains = t.profit - t.loss_amt;
  $("#loss-stats").innerHTML = `<div><div class="k">Profit from profitable lines</div><div class="big" style="font-size:20px">${fmt.usd(gains)}</div></div><div><div class="k">Lost on loss-making lines</div><div class="big" style="font-size:20px;color:var(--bad)">${fmt.usd(t.loss_amt)}</div></div><div><div class="k">Loss-making lines</div><div class="big" style="font-size:20px">${fmt.pct(t.loss_lines / t.lines)}</div></div>`;
  // cap
  const save = t["save" + cap];
  const br = rowsB(); const byBand = group(B, br, r => B.dim(r, "discount_band"), MEAS_B);
  const affected = [...byBand].filter(([b]) => { const lo = { "0%": 0, "1-5%": 1, "6-10%": 6, "11-15%": 11, "16-25%": 16 }[b]; return lo > cap; }).reduce((a, [, g]) => a + g.lines, 0);
  const allL = [...byBand.values()].reduce((a, g) => a + g.lines, 0);
  $("#cap-stats").innerHTML = `<div><div class="k">Discount kept</div><div class="big" style="font-size:22px;color:var(--good)">${fmt.usd(save)}</div></div><div><div class="k">Profit uplift (max)</div><div class="big" style="font-size:22px">+${fmt.pct(save / t.profit, 0)}</div></div><div><div class="k">Lines affected</div><div class="big" style="font-size:22px">${fmt.pct(affected / allL, 0)}</div></div>`;
  const order = ["0%", "1-5%", "6-10%", "11-15%", "16-25%"];
  columns($("#c-band"), order.filter(b => byBand.has(b)).map(b => { const g = byBand.get(b); return { label: b, v: g.profit / g.net, color: css("--accent"), tip: `<b>Discount ${b}</b><div>Margin ${fmt.pct(g.profit / g.net)}</div><div>${fmt.int(g.lines)} lines · discount ${fmt.usd(g.discount)}</div>` }; }), { h: 180, yf: v => (v * 100).toFixed(0) + "%", labels: true });
  // category table
  const byCat = group(B, br, r => B.dim(r, "category"), MEAS_B);
  const cats = [...byCat].filter(([, g]) => g.net > 100000).sort((a, b) => b[1].net - a[1].net);
  $("#t-cat").innerHTML = `<table><thead><tr><th>Category</th><th class="n">Net sales</th><th class="n">Expected margin</th><th class="n">Actual margin</th><th class="n">Gap (pts)</th><th class="n">Margin breach</th><th class="n">Lost on loss lines</th><th class="n">Saving at 10% cap</th></tr></thead><tbody>` +
    cats.map(([c, g]) => { const m = g.profit / g.net, gap = (m - 0.27) * 100; return `<tr><td>${c}</td><td class="n">${fmt.usd(g.net)}</td><td class="n">27.0%</td><td class="n">${fmt.pct(m)}</td><td class="n" style="color:var(--bad)">${gap.toFixed(1)}</td><td class="n">${fmt.pct(g.margin_breach / g.lines)}</td><td class="n">${fmt.usd(g.loss_amt)}</td><td class="n">${fmt.usd(g.save10)}</td></tr>`; }).join("") + "</tbody></table>";
}
document.querySelectorAll("[data-cap]").forEach(b => b.addEventListener("click", () => { cap = +b.dataset.cap; document.querySelectorAll("[data-cap]").forEach(x => x.setAttribute("aria-pressed", x === b)); renderProfit(); }));

function renderForecast() {
  [["orders", "#c-fc-orders", "#fc-sub-orders", v => fmt.int(v)], ["late_rate", "#c-fc-late", "#fc-sub-late", (v, tip) => (v * 100).toFixed(tip ? 1 : 0) + "%"]].forEach(([k, host, sub, yf]) => {
    const se = D.F.series[k]; const labels = se.months.concat(se.forecast_months); const n = se.months.length, nt = se.test_prediction.length;
    $(sub).textContent = `Best model: ${se.best_model} · error on held-back months ${se.mape_by_model[se.best_model].toFixed(1)}%`;
    lineChart($(host), labels, [
      { name: "Actual", color: css("--accent"), pts: se.history.map((y, i) => ({ i, y })) },
      { name: se.best_model + " (test)", color: css("--warn"), dash: "5 4", pts: se.test_prediction.map((y, j) => ({ i: n - nt + j, y })) },
      { name: "Forecast", color: css("--bad"), width: 3, dots: true, pts: [{ i: n - 1, y: se.history[n - 1] }].concat(se.forecast.map((y, j) => ({ i: n + j, y }))) },
    ], { yf, xf: mLabel, band: [n - nt, n - 1] });
  });
  const ms = Object.keys(D.F.series.orders.mape_by_model);
  $("#t-mape").innerHTML = `<table><thead><tr><th>Model</th><th class="n">Orders</th><th class="n">Late rate</th></tr></thead><tbody>` +
    ms.map(m => { const a = D.F.series.orders.mape_by_model[m], b = D.F.series.late_rate.mape_by_model[m]; const ba = D.F.series.orders.best_model === m, bb = D.F.series.late_rate.best_model === m; return `<tr><td>${m}</td><td class="n">${a.toFixed(2)}%${ba ? ' <span class="chip pass">best</span>' : ""}</td><td class="n">${b.toFixed(2)}%${bb ? ' <span class="chip pass">best</span>' : ""}</td></tr>`; }).join("") + "</tbody></table>";
}

const allMonths = A.dims.month.slice();
$("#r-month").innerHTML = allMonths.map(m => `<option value="${m}">${mLabel(m)}</option>`).join("");
$("#r-month").value = allMonths[allMonths.length - 1];
$("#r-month").addEventListener("change", renderReport);
function renderReport() {
  const m = $("#r-month").value, i = allMonths.indexOf(m);
  const k = kpi(sum(A, rowsA({ month: m }), MEAS_A)), p = i > 0 ? kpi(sum(A, rowsA({ month: allMonths[i - 1] }), MEAS_A)) : null;
  const scope = [F.market, F.mode, F.seg].filter(x => x !== "all").join(" · ") || "All markets, modes and segments";
  $("#t-report").innerHTML = `<p class="note" style="margin:4px 0 8px">Scope: ${scope} · ${fmt.int(k.lines)} order lines</p><table><thead><tr><th>KPI</th><th class="n">Target</th><th class="n">Actual</th><th class="n">Previous month</th><th>Status</th></tr></thead><tbody>` +
    TARGETS.map(t => { const ok = passes(t, k[t.key]); return `<tr><td>${t.name}</td><td class="n">${t.op === ">=" ? "≥" : "≤"} ${t.key === "slip" ? t.target.toFixed(2) : fmt.pct(t.target, 0)}</td><td class="n">${t.f(k[t.key])}</td><td class="n">${p ? t.f(p[t.key]) : "–"}</td><td><span class="chip ${ok ? "pass" : "fail"}">${ok ? "pass" : "fail"}</span></td></tr>`; }).join("") + "</tbody></table>";
  const per = allMonths.map(mm => kpi(sum(A, rowsA({ month: mm }), MEAS_A)));
  $("#t-grid").innerHTML = `<table class="heat"><thead><tr><th>KPI</th>${allMonths.map(mm => `<th class="n" style="font-size:10px">${MONTHS[+mm.slice(5) - 1]}<br>${mm.slice(2, 4)}</th>`).join("")}</tr></thead><tbody>` +
    TARGETS.map(t => `<tr><td>${t.name}</td>${per.map((k2, j) => { const ok = passes(t, k2[t.key]); return `<td class="c" data-tip="${t.name} · ${mLabel(allMonths[j])}: ${t.f(k2[t.key])}" style="background:var(--${ok ? "good" : "bad"}-bg);color:var(--${ok ? "good" : "bad"})">${ok ? "✓" : "✗"}</td>`; }).join("")}</tr>`).join("") + "</tbody></table>";
  document.querySelectorAll("#t-grid td[data-tip]").forEach(td => hover(td, td.dataset.tip));
}

function renderMethod() {
  $("#targets-list").innerHTML = TARGETS.map(t => `<li>${t.name}: ${t.op === ">=" ? "at least" : "at most"} ${t.key === "slip" ? t.target.toFixed(2) + " days" : fmt.pct(t.target, 0)}</li>`).join("");
}

$("#findings").innerHTML = FINDINGS.map((f, i) => `<li><span class="n">${String(i + 1).padStart(2, "0")}</span><span>${f}</span></li>`).join("");

function render() {
  ({ project: () => {}, overview: renderOverview, delivery: renderDelivery, profit: renderProfit, forecast: renderForecast, report: renderReport, method: renderMethod })[current]();
}
let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(render, 150); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
new MutationObserver(render).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
route();
