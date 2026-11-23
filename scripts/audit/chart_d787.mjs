// ─────────────────────────────────────────────────────────────────────────
// D787 — بأمر المالك (2026-11-23):
//   «خلِّ في خيار ثلاث شاشات، وخيارَ تكبير الأربع مع بعض بجانب تحليل الرسم… واجعل كلَّ شاشةٍ منفصلة — مو شرط نفس الشركة… في كلّ شاشةٍ بحث:
//    أضغط تاسي أو أضع رمزَ شركةٍ في السوقين أو رمزَ العقد نفسِه ويفتح»، «ضع في الفرص وعقود الخيارات رمزاً أضغط عليه فأنسخه في البحث ويظهر في
//    الشاشة — بطريقةٍ مشابهةٍ لتريدنق فيو»، «سلسلةُ العقود في الفرص ما تفتح»، «ما العقودُ المناسبةُ لهذه الفرصة؟ النطاقُ اللي نسبةُ نجاحه
//    أعلى بتصميمٍ جميل والباقي نطاقٌ مساعد — دليلٌ إرشاديّ»، «وطني للحديد والصلب ما وجدتُ لها رمزاً»، «الكلّ وشهر وشهران وحتى الربع القادم
//    ما لها داعي»، «الرسومُ حول صقر رسميةٌ احترافيةٌ غامضة — لا تفضح قوّته».
//   ١ تطبيعُ الرمز: تاسي · الرباعيُّ السعوديّ · بادئةُ السوق · العقدُ بصيغتَي OCC وتريدنق فيو — والصيغةُ تذهب وتعود.
//   ٢ الشاشاتُ: ثلاثٌ (كبيرةٌ واثنتان)، ولكلٍّ رمزُها وبحثُها، والقائمةُ تفتح في المختارة، والرابطُ يعيدها تتبع الأولى، وتُحفظ؛ و«تكبيرُ الشاشات» يملأ النافذة ويعود بـEsc.
//   ٣ الفرص: بلا مرشّح المدّة، ورمزٌ يُنسخ، والسلسلةُ تُفتح بدليل الفرصة: الأجلُ المتّسعُ لمدّتها، و«الأنسب» و«المساعد»، وأفضلُ العقود برموزٍ تُنسخ.
//   ٤ «عقودُ الخيارات»: رمزُ العقد بصيغة تريدنق فيو يُنسخ — ويُفتح في بحث الشاشة.
//   ٥ حولَ صقر: أنوارٌ بلا أسماء، ومسحٌ يدور حين يعمل ويسكن مع تقليل الحركة.
//   ٦ البحثُ يجد «حديد وطني» برمزها الجديد 1325 من دليل «تداول» الحيّ، ويُخفي رمزَها القديم 9513.
//   ٧ التباينُ والخطُّ واللمسُ وبلا فيض — في المظهرين على الحاسوب والجوال.
//    SHOTS=dir node scripts/audit/chart_d787.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };

// ═════ ١ تطبيعُ الرمز ═════
const ES = join(FRONT, "node_modules/esbuild/lib/main.js");
if (existsSync(ES)) {
  const esbuild = await import(pathToFileURL(ES).href);
  const dir = mkdtempSync(join(tmpdir(), "d787-"));
  writeFileSync(join(dir, "e.ts"), `export { normalizeSymbol } from ${JSON.stringify(join(FRONT, "src/lib/symbols.ts"))};
export { toOcc, tvCode, parseOption } from ${JSON.stringify(join(FRONT, "src/lib/options.ts"))};`);
  await (esbuild.build || esbuild.default.build)({ entryPoints: [join(dir, "e.ts")], bundle: true, format: "esm", outfile: join(dir, "m.mjs"), platform: "neutral", logLevel: "silent" });
  const M = await import(pathToFileURL(join(dir, "m.mjs")).href);
  const C = [["تاسي", "^TASI.SR"], ["TASI", "^TASI.SR"], ["TADAWUL:TASI", "^TASI.SR"], ["1120", "1120.SR"], ["١١٢٠", "1120.SR"], ["TADAWUL:1325", "1325.SR"],
    ["nvda", "NVDA"], ["NASDAQ:NVDA", "NVDA"], ["NVDA270617C00200000", "NVDA270617C00200000"], ["NVDA270617C200", "NVDA270617C00200000"],
    ["OPRA:NVDA270617C200.0", "NVDA270617C00200000"], ["spy 261120 p 582.5", "SPY261120P00582500"], ["BRK.B", "BRK.B"], ["^GSPC", "^GSPC"], ["ابحث", null], ["12345", null]];
  const bad = C.filter(([i, o]) => M.normalizeSymbol(i) !== o).map(([i, o]) => `${i}→${M.normalizeSymbol(i)}≠${o}`);
  const rt = ["NVDA270617C00200000", "SPY261120P00582500", "AAPL261218C00012500"].every(s => M.toOcc(M.tvCode(M.parseOption(s))) === s)
    && M.tvCode(M.parseOption("NVDA270617C00200000")) === "NVDA270617C200" && M.tvCode(M.parseOption("SPY261120P00582500")) === "SPY261120P582.5";
  say(!bad.length && rt, "١ ما يُكتب في البحث يُطبَّع مرّة: «تاسي» مؤشّرُها، والرباعيُّ سعوديٌّ (وبالأرقام العربية)، وبادئةُ السوق تُرفع، والعقدُ بصيغتَي OCC "
    + "وتريدنق فيو (‏NVDA270617C200) رمزُ OCC — والصيغةُ تذهب وتعود، وما لا يُفهم لا يُخمَّن", bad.join(" · "));
}

// ═════ في المتصفّح ═════
const PORT = 5287;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await new Promise(r => setTimeout(r, 500)); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const SHOTS = process.env.SHOTS;
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const bars = (n = 160, base = 90) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = base + i * 0.08 + Math.sin(i / 2) * 1.2, o = base + (i - 1) * 0.08 + Math.sin((i - 1) / 2) * 1.2;
  return { date: day, open: o, high: Math.max(o, c) + 0.6, low: Math.min(o, c) - 0.6, close: c, volume: c >= o ? 3e6 : 1e6 };
});
const ROLES = ["المسار", "الرسم", "النتائج", "الأخبار", "الأحداث", "الحيتان", "المحلّلون"];
const COUNCIL = { verdict: "يوافق", score: 84, veto: false, oks: 6, warns: 0, members: ROLES.map(role => ({ role, v: "ok", say: `${role}: يؤيّد` })) };
const OPP = (sym, name, side, q, hn, setup, extra = {}) => ({ symbol: sym, name, setup, side, quality: q, horizon: { 1: "شهر", 2: "شهران", 3: "حتى الربع القادم" }[hn], horizon_n: hn,
  entry: side === "long" ? [98, 101] : [128, 131], target: side === "long" ? 120 : 118, stop: side === "long" ? 92 : 133.5, rr: 2.3, zone: "الدعم",
  where: "في منطقة الدعم", close: side === "long" ? 100 : 129.5, trend: { word: "صاعد", level: "قويّ", strength: 62 },
  liq: { word: "داخلةٌ للصعود", level: "متوسّطة", strength: 48, tag: null }, k: 18.4, rsi: 44.2, weekly: "صاعد", reasons: [], council: COUNCIL, ...extra });
const OPPS = {
  us: { market: "us", at: iso(now - 7200e3), universe: 812, screened: 790, read: 150, found: 2, min_q: 50, job: { on: false, msg: "", at: null }, rejected: [],
    items: [OPP("NVDA", "NVIDIA", "long", 77, 3, "ارتدادٌ من الدعم"), OPP("TSLA", "Tesla", "short", 63, 2, "رفضٌ من المقاومة"),
      ...Array.from({ length: 16 }, (_, i) => OPP(`F${i}`, `Filler ${i}`, "long", 60, 1, "ارتدادٌ من الدعم"))] },
  sa: { market: "sa", at: iso(now - 3600e3), universe: 268, screened: 266, read: 266, found: 1, min_q: 50, job: { on: false, msg: "", at: null }, rejected: [],
    items: [OPP("1325", "حديد وطني", "long", 70, 2, "ارتدادٌ من الدعم")] } };
/* سلسلةُ NVDA عند 100: آجالٌ 4 · 25 · 53 · 116 · 206 يوماً؛ وأسعارٌ واقعيةٌ (قيمةٌ ذاتيةٌ + قيمةٌ زمنية) ودلتاهات */
const EXPS = [[1, "2026-11-27", 4], [2, "2026-12-18", 25], [3, "2027-01-15", 53], [4, "2027-03-19", 116], [5, "2027-06-17", 206]].map(([t, date, dte]) => ({ t, date, dte }));
const CALL = { 80: [21.5, .93], 85: [17, .88], 90: [12.8, .8], 95: [9, .68], 100: [6, .55], 105: [3.8, .42], 110: [2.2, .3], 115: [1.2, .2], 120: [0.7, .13], 125: [0.4, .08] };
const occ = (root, date, cp, k) => `${root}${date.slice(2, 4)}${date.slice(5, 7)}${date.slice(8, 10)}${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
const chain = (sym, t) => { const e = EXPS.find(x => x.t === t) || EXPS[0];
  const row = (k, cp) => { const [ask, d] = CALL[k]; const put = cp === "P"; const a = put ? Math.max(0.3, ask + k - 100 - 0.5) : ask;
    return { contract: occ(sym, e.date, cp, k), strike: k, last: a - 0.05, bid: a - 0.1, ask: a, pct: 1.2, volume: 500, oi: 2000, iv: 42, itm: put ? k > 100 : k < 100,
      g: { iv: 42, delta: put ? -(1 - d) : d, gamma: 0.02, theta: -0.03, vega: 0.1, itm: d, pop: 0.4, px: a, src: "ask", spread: 2, be: put ? k - a : k + a } }; };
  const ks = Object.keys(CALL).map(Number);
  return { symbol: sym, name: sym, price: 100, expirations: EXPS, expiry: e.t, calls: ks.map(k => row(k, "C")), puts: ks.map(k => row(k, "P")),
    stats: { atm_iv: 42, move: 6, move_pct: 6, pcr_vol: 0.8, pcr_oi: 0.9, max_pain: 100, vol: { call: 1000, put: 800 }, oi: { call: 5000, put: 4000 } }, session: SES }; };
const ST = m => ({ market: m, ccy: m === "sa" ? "SAR" : "USD", on: true, capital: 1000, goal: 100000, cash: 1000, equity: 1000, pl: 0, pl_pct: 0, progress: 0,
  started: iso(now - 86400e3), tier: { frac: 0.25, seats: 4 }, positions: [], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0,
  today: { wins: 0, losses: 0, realized: 0, new: 0 }, exposure: { contracts: 0, cost: 0, value: 0, ret: null }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 1000]],
  signals: [], log: [], gates: [], scan: m === "us" ? { at: iso(now), universe: 900, full: { optionable: 812, passed: 300 } } : null, session: null, last_cycle: null, last_check: null,
  health: {}, broker: { linked: false, name: "IBKR" }, runs: [], running: { on: false, msg: "", at: null },
  settings: { per_trade: null, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 6, take_x: 2, mode: "balanced", day_target: null, auto: true },
  day: null, orders: [], pulse: null, geo: null, rules: { stop: 0.6, take: 2, growth: 15 },
  regime: m === "sa" ? { verdict: "صاعد", state: "صاعد", close: 11500, sma50: 11300, sma200: 11000, ret3m: 4.2, chg: 0.35 } : null,
  opps: { at: OPPS[m].at, universe: OPPS[m].universe, screened: OPPS[m].screened, read: OPPS[m].read, found: OPPS[m].found } });
const PICK = { symbol: "NVDA", name: "NVIDIA", contract: "NVDA270617C00200000", type: "call", strike: 200, ask: 1.45, bid: 1.35, cost: 145, dte: 207, expiry: "2027-06-17",
  breakeven: 201.45, need_pct: 8.2, pop: 36, p_touch: 52, target: 214, target_label: "قمّة السنة", rr: 2.1, delta: 0.41, iv: 44, oi: 3200, spread_pct: 7, spread_usd: 10,
  px_src: "ask", opened: "2026-11-22", new: true, pl_pct: 0, mid_now: 1.4, entry_mid: 1.4, trend: { state: "صاعد" }, reasons: ["الأطروحة: المسار صاعد"], chart: null };
/* دليلُ «تداول» الحيّ: القائمةُ الثابتةُ كلُّها إلّا 9513 (نُقلت)، و1325 «حديد وطني» في الرئيسية */
const SC = readFileSync(join(FRONT, "src/data/saudiCompanies.ts"), "utf8");
const DIR = [...SC.matchAll(/symbol: "(\d{4})", name_ar: "([^"]*)"/g)].filter(m => m[1] !== "9513").map(m => ({ symbol: m[1], name_ar: m[2], name_en: "", sector: "", market: "main" }));
DIR.push({ symbol: "1325", name_ar: "وطني للحديد والصلب", name_en: "Watani Iron Steel Co.", sector: "المواد الأساسية", market: "main" });   // ‏كما في دليل «تداول» (قِيس على الخادم)

const CONTRAST = () => {
  const parse = s => { s = (s || "").trim();
    let m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = s.match(/^color\(srgb\s+([^)]+)\)$/);
    if (m) { const [a, al] = m[1].split("/"); const p = a.trim().split(/\s+/).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, al ? Number(al) : 1]; }
    return [0, 0, 0, 0]; };
  const over = (t, b) => { const a = t[3] + b[3] * (1 - t[3]); if (!a) return [0, 0, 0, 0]; return [0, 1, 2].map(i => (t[i] * t[3] + b[i] * b[3] * (1 - t[3])) / a).concat(a); };
  const bgOf = el => { const L = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) L.push(c); if (c[3] >= 1) break; }
    let acc = parse(getComputedStyle(document.body).backgroundColor); if (acc[3] < 1) acc = [255, 255, 255, 1];
    for (let i = L.length - 1; i >= 0; i--) acc = over(L[i], acc); return acc; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  return el => { const bg = bgOf(el), fg = over(parse(getComputedStyle(el).color), bg); const a = lum(fg), b = lum(bg); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
};
const MEAS = ([sel, src]) => { const cr = eval(`(${src})()`); const W = document.documentElement.clientWidth; let minT = 99, minF = 99, minC = 99;
  const root = document.querySelector(sel);
  root?.querySelectorAll("button, summary, input").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
  root?.querySelectorAll("*").forEach(e => { if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) {
    minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); if (e.closest(".so-code, .ocg-code, .ocg, .troom-phead")) minC = Math.min(minC, cr(e)); } });
  const main = document.querySelector(".app-main");
  return { minT, minF, minC: +minC.toFixed(2), over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W }; };

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, permissions: ["clipboard-read", "clipboard-write"] });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d787-init")) return;
    sessionStorage.setItem("d787-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_room_layout", "1"); localStorage.removeItem("sp_room_panes");
    localStorage.setItem("sp_saqr_tab", "opps"); localStorage.setItem("sp_saqr_market", "us");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: decodeURIComponent(p.split("/").pop()), price: 100, change: 0.4, change_pct: 0.6, time: new Date().toISOString(), delayed: 0, source: "ياهو", session: SES, ext: null }));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa", state: "closed", label: "السوق مغلق" } }));
    if (p === "/market/saqr" && m === "GET") return r.fulfill(body(ST(u.searchParams.get("market") === "sa" ? "sa" : "us")));
    if (p === "/market/saqr/opportunities" && m === "GET") return r.fulfill(body(OPPS[u.searchParams.get("market") === "sa" ? "sa" : "us"]));
    if (p.startsWith("/market/options/")) return r.fulfill(body(chain(decodeURIComponent(p.split("/").pop()), Number(u.searchParams.get("date")) || 1)));
    if (p === "/market/options-picks") return r.fulfill(body({ result: { budget: 150, at: iso(now), picks: [PICK], exits: [], skipped: [], scanned: 98, news_ok: true, closed: false,
      limits: { min_dte: 150, max_dte: 430, min_oi: 100, max_spread: 10 } }, running: { on: false } }));
    if (p === "/market/saudi-directory") return r.fulfill(body({ at: iso(now), rows: DIR, complete: true }));
    if (p === "/market/symbol-search") return r.fulfill(body([]));
    if (p === "/holdings") return r.fulfill(body([{ company: { symbol: "2222", name_ar: "أرامكو السعودية" }, last_price: 25, change_pct: 0.4 },
      { company: { symbol: "1120", name_ar: "مصرف الراجحي" }, last_price: 61, change_pct: -0.2 }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });

  // ═ ٢ الشاشات ═
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2600); await paint();
  await page.locator('[data-role="pc-layout"]').first().click(); await page.waitForTimeout(250);
  const opts = await page.locator('[data-layout]').evaluateAll(bs => bs.map(b => b.getAttribute("data-layout")));
  await page.locator('[data-layout="3"]').first().click(); await page.waitForTimeout(1400);
  const g3 = await page.evaluate(() => { const g = document.querySelector('[data-role="troom-grid"]'); const ps = [...document.querySelectorAll('[data-role="troom-pane"]')];
    const r = ps.map(p => p.getBoundingClientRect()); return { cls: g?.className || "", n: ps.length, heads: document.querySelectorAll('[data-role="troom-phead"]').length,
      searches: document.querySelectorAll('[data-role="troom-psearch"]').length, big: r[0] && r[1] ? Math.round(r[0].height) : 0, small: r[1] ? Math.round(r[1].height) : 0,
      side: r[0] && r[1] ? Math.round(r[0].left - r[1].left) : 0, syms: ps.map(p => p.dataset.symbol) }; });
  const typeIn = async (k, text) => {
    const box = page.locator('[data-role="troom-pane"]').nth(k).locator('[data-role="troom-psearch"]');
    await box.locator(".inline-search-btn").click(); await page.waitForTimeout(200);
    await box.locator("input").fill(text); await page.waitForTimeout(350); await box.locator("input").press("Enter"); await page.waitForTimeout(900);
  };
  await typeIn(1, "NVDA270617C200");
  await typeIn(2, "تاسي");
  const syms1 = await page.locator('[data-role="troom-pane"]').evaluateAll(ps => ps.map(p => p.dataset.symbol));
  // القائمةُ تفتح في الشاشة المختارة (الثالثة بعد البحث فيها)
  await page.locator('[data-role="troom-pane"]').nth(2).click({ position: { x: 40, y: 80 } }).catch(() => {}); await page.waitForTimeout(200);
  await page.locator('[data-role="troom-row"], [data-sym]').filter({ hasText: "1120" }).first().click().catch(() => {}); await page.waitForTimeout(900);
  const syms2 = await page.locator('[data-role="troom-pane"]').evaluateAll(ps => ps.map(p => p.dataset.symbol));
  await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="troom-plink"]').click().catch(() => {}); await page.waitForTimeout(700);
  const syms3 = await page.locator('[data-role="troom-pane"]').evaluateAll(ps => ps.map(p => p.dataset.symbol));
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_room_panes") || "[]"));
  if (SHOTS) await page.locator('[data-role="troom-chart"]').screenshot({ path: `${SHOTS}/d787-panes-${vp.width}-${theme}.png` }).catch(() => {});
  const wideG3 = vp.width >= 1024 ? g3.big > g3.small * 1.6 && g3.side !== 0 : true;
  say(opts.join() === "1,2,3,4" && /\bg3\b/.test(g3.cls) && g3.n === 3 && g3.heads === 3 && g3.searches === 3 && wideG3
      && syms1[0] === "2222.SR" && syms1[1] === "NVDA270617C00200000" && syms1[2] === "^TASI.SR"
      && syms2[0] === "2222.SR" && syms2[2] === "1120" && syms3[1] === "2222.SR" && saved[1] === null && saved[2] === "1120",
    `${label}: ٢ ثلاثُ شاشات (كبيرةٌ واثنتان بجانبها)، ولكلٍّ رمزُها وبحثُها: عقدٌ ملصوقٌ بصيغة تريدنق فيو في الثانية و«تاسي» في الثالثة — والقائمةُ تفتح في المختارة `
      + "لا في الأولى، والرابطُ يعيد الثانيةَ تتبع الأولى، والاختيارُ يُحفظ", JSON.stringify({ opts, g3, syms1, syms2, syms3, saved }));
  // ٢ب «تكبيرُ الشاشات»
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(500);
  const wd = await page.evaluate(() => { const r = document.querySelector('[data-role="troom-chart"]').getBoundingClientRect();
    return { top: Math.round(r.top), h: Math.round(r.height), w: Math.round(r.width), on: document.documentElement.classList.contains("troom-wide-on"), ih: innerHeight, iw: document.documentElement.clientWidth }; });
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/d787-wide-${vp.width}-${theme}.png` }).catch(() => {});
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  const wd0 = await page.evaluate(() => ({ on: document.documentElement.classList.contains("troom-wide-on"), wide: document.querySelector('[data-role="troom-chart"]').dataset.wide }));
  say(wd.top === 0 && wd.h >= wd.ih - 1 && wd.w >= wd.iw - 1 && wd.on && !wd0.on && wd0.wide === "0",
    `${label}: ٢ب «تكبيرُ الشاشات» بجانب «تحليل الرسم» يملأ النافذةَ بالشاشات كلِّها، وEsc يعيدها`, JSON.stringify({ wd, wd0 }));

  // ═ ٦ البحثُ يجد «حديد وطني» برمزها الجديد ═
  const box = page.locator('[data-role="troom-pane"]').nth(0).locator('[data-role="troom-psearch"]');
  await box.locator(".inline-search-btn").click(); await page.waitForTimeout(700);
  await box.locator("input").fill("وطني للحديد"); await page.waitForTimeout(500);
  const sh = await page.locator('[data-role="search-sa"]').evaluateAll(bs => bs.map(b => b.textContent.replace(/\s+/g, " ").trim()));
  await box.locator("input").press("Escape").catch(() => {});
  say(sh.some(t => /1325/.test(t) && /وطني للحديد والصلب/.test(t)) && !sh.some(t => /9513/.test(t)),
    `${label}: ٦ البحثُ يجد «وطني للحديد والصلب» برمزها الجديد 1325 من دليل «تداول» الحيّ، ولا يعرض رمزَها القديم 9513`, JSON.stringify(sh).slice(0, 160));

  // ═ ٣ الفرص (الأمريكيّ) ═
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2400); await paint();
  await page.locator('[data-role="sq-market"] [data-market="us"]').click().catch(() => {}); await page.waitForTimeout(900);
  await page.locator('[data-role="sq-nav"] [data-view="opps"]').click().catch(() => {}); await page.waitForTimeout(900);
  const noH = await page.evaluate(() => !document.querySelector('[data-role="so-h"]'));
  await page.locator('[data-role="so-code"]').first().click(); await page.waitForTimeout(300);
  const clip1 = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
  const ok1 = await page.locator('[data-role="so-code"]').first().evaluate(b => b.classList.contains("ok"));
  await page.locator('[data-role="so-chain"]').first().click(); await page.waitForTimeout(1500);
  const oc = await page.evaluate(() => { const m = document.querySelector('[data-role="oc"]'); const sh = m?.querySelector(".oc-sheet"); const r = sh?.getBoundingClientRect();
    const rows = [...document.querySelectorAll('[data-role="oc-row"]')].map(x => [Number(x.querySelector(".ocx-k b")?.textContent), x.dataset.band]);
    return { open: !!m, shown: m?.dataset.shown, vis: !!r && r.width > 200 && r.height > 200 && r.top < innerHeight && r.bottom > 0, op: sh ? getComputedStyle(sh).opacity : "",
      guide: !!document.querySelector('[data-role="oc-guide"]'), exp: document.querySelector('[data-role="oc-exp"].on')?.textContent || "",
      fit: [...document.querySelectorAll('[data-role="oc-exp"][data-fit="1"]')].length, dte: document.querySelector('[data-role="oc-guide-dte"]')?.textContent || "",
      core: rows.filter(x => x[1] === "core").map(x => x[0]), aux: rows.filter(x => x[1] === "aux").map(x => x[0]),
      best: [...document.querySelectorAll('[data-role="oc-guide-code"]')].map(b => b.textContent.trim()),
      leg: document.querySelector('[data-role="oc-guide-core"]')?.textContent || "" }; });
  if (oc.best[0]) { await page.locator('[data-role="oc-guide-code"]').first().click(); await page.waitForTimeout(300); }
  const clip2 = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
  if (SHOTS) await page.locator('[data-role="oc"] .oc-sheet').screenshot({ path: `${SHOTS}/d787-guide-${vp.width}-${theme}.png` }).catch(() => {});
  const m3 = await page.evaluate(MEAS, ['[data-role="oc"]', CONTRAST.toString()]).catch(e => ({ err: String(e).slice(0, 120) }));
  say(noH && clip1 === "NVDA" && ok1 && oc.open && oc.shown === "1" && oc.vis && oc.op === "1" && oc.guide,
    `${label}: ٣ الفرص بلا مرشّح المدّة، ورمزُ السهم يُنسخ بضغطة («NVDA» في الحافظة وعلامةُ نُسخ)، و«سلسلةُ العقود» تُفتح ظاهرةً فوق الصفحة بدليل الفرصة`,
    JSON.stringify({ noH, clip1, ok1, open: oc.open, shown: oc.shown, vis: oc.vis, op: oc.op, guide: oc.guide }));
  say(/16 مارس|19 مارس|مارس/.test(oc.exp) && oc.fit === 2 && /يتّسع/.test(oc.dte) && JSON.stringify(oc.core) === "[90,95,100,105]" && JSON.stringify(oc.aux) === "[80,85,110,115]"
      && !oc.core.includes(120) && JSON.stringify(oc.best) === '["NVDA270319C100","NVDA270319C95","NVDA270319C105"]' && clip2 === oc.best[0] && /90/.test(oc.leg) && /105/.test(oc.leg),
    `${label}: ٣ب الدليلُ يختار أوّلَ أجلٍ يتّسع لمدّة الفرصة (حتى الربع القادم ⇐ 116 يوماً)، ويرسم «الأنسب» (يتعادل قبل ستّين بالمئة من الطريق إلى الهدف، دلتا 0.35–0.80، `
      + "ويربح نصفَ ثمنه عند الهدف) و«المساعد» حوله، وأفضلُ ثلاثة عقودٍ (الأقربُ إلى دلتا 0.60) برموز تريدنق فيو تُنسخ", JSON.stringify({ exp: oc.exp, fit: oc.fit, core: oc.core, aux: oc.aux, best: oc.best, clip2 }));
  say(m3 && m3.minT >= 32 && m3.minF >= 9.5 && m3.minC >= 4.5 && m3.over <= 1, `${label}: ٧ السلسلةُ بدليلها: لمسٌ ≥ 32 وخطٌّ ≥ 9.5 وتباينُ الدليل ≥ 4.5 وبلا فيض`, JSON.stringify(m3));
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  /* ٣ج السببُ الجذريّ نفسُه: قائمةٌ طويلةٌ والفرصةُ في آخرها — كانت النافذةُ تُرسم داخل لوحة صقر (حركتُها تُبقي تحويلاً فتصير مرجعَ ‏fixed)
     فتمتدّ بطولها وتقع السلسلةُ خارج الشاشة. والنافذةُ الآن في جذر الصفحة: تغطّي الشاشةَ بالضبط والسلسلةُ فيها */
  const last = page.locator('[data-role="so-chain"]').last();
  await last.scrollIntoViewIfNeeded(); await page.waitForTimeout(300); await last.click(); await page.waitForTimeout(1100);
  const far = await page.evaluate(() => { const m = document.querySelector('[data-role="oc"]'), sh = m?.querySelector(".oc-sheet");
    const a = m?.getBoundingClientRect(), c = sh?.getBoundingClientRect();
    return { top: a ? Math.round(a.top) : null, h: a ? Math.round(a.height) : null, vh: innerHeight, s0: c ? Math.round(c.top) : null, s1: c ? Math.round(c.bottom) : null,
      body: m?.parentElement === document.body }; });
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  say(far.top === 0 && far.h === far.vh && far.s0 >= 0 && far.s1 <= far.vh + 1 && far.body,
    `${label}: ٣ج «سلسلةُ العقود» من آخر فرصةٍ في قائمةٍ طويلة تُفتح على الشاشة نفسِها — النافذةُ في جذر الصفحة تغطّي الشاشةَ بالضبط (كانت داخل لوحة صقر فتقع خارجها)`,
    JSON.stringify(far));

  // ═ ٤ «عقودُ الخيارات»: رمزُ العقد يُنسخ ═
  await page.locator('[data-role="sq-nav"] [data-view="options"]').click().catch(() => {}); await page.waitForTimeout(1300);
  const code = await page.locator('[data-role="op-code"]').first().textContent().catch(() => "");
  await page.locator('[data-role="op-code"]').first().click().catch(() => {}); await page.waitForTimeout(300);
  const clip3 = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
  say((code || "").trim() === "NVDA270617C200" && clip3 === "NVDA270617C200",
    `${label}: ٤ بطاقةُ «عقود الخيارات» تحمل رمزَ العقد بصيغة تريدنق فيو ويُنسخ بضغطة — ويُفتح إن لُصق في بحث أيّ شاشة (١ · ٢)`, JSON.stringify({ code, clip3 }));

  // ═ ٥ حولَ صقر ═
  await page.locator('[data-role="sq-nav"] [data-view="dash"]').click().catch(() => {}); await page.waitForTimeout(1200);
  const hub = await page.evaluate(() => { const h = document.querySelector('[data-role="sq-hub"]'); const ns = [...document.querySelectorAll('[data-role="sq-node"]')];
    const txt = [...(h?.querySelectorAll("*") || [])].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => e.textContent.trim());
    return { n: ns.length, text: ns.map(x => x.textContent.trim()).join(""), titles: [...(h?.querySelectorAll("[title]") || [])].length, txt, live: h?.dataset.live,
      sweep: getComputedStyle(document.querySelector(".sq-sweep")).animationName, ticks: document.querySelectorAll(".sq-tick").length }; });
  if (SHOTS) await page.locator('[data-role="sq-hub"]').screenshot({ path: `${SHOTS}/d787-hub-${vp.width}-${theme}.png` }).catch(() => {});
  await page.emulateMedia({ reducedMotion: "reduce" }); await page.waitForTimeout(250);
  const rm = await page.evaluate(() => ({ sweep: getComputedStyle(document.querySelector(".sq-sweep")).animationName, orbit: getComputedStyle(document.querySelector(".sq-orbit")).animationName }));
  await page.emulateMedia({ reducedMotion: "no-preference" });
  say(hub.n === 8 && hub.text === "" && hub.titles === 0 && hub.txt.length === 1 && hub.ticks === 72 && (hub.live !== "1" || hub.sweep !== "none") && rm.sweep === "none" && rm.orbit === "none"
      && errs.length === 0,
    `${label}: ٥ حولَ صقر قرصُ أداة: 72 تدريجاً وأنوارٌ ثمانيةٌ بلا أسماءٍ ولا تلميحات (النصُّ الوحيدُ حالُه)، ومسحٌ يدور حين يعمل ويسكن مع تقليل الحركة — ولا خطأ`,
    JSON.stringify({ ...hub, rm, err: errs[0] || "" }).slice(0, 240));
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
