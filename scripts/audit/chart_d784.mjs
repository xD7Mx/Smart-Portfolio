// ─────────────────────────────────────────────────────────────────────────
// D784 — بأمر المالك (2026-11-22): «إعداداتُ ستوكاستيك RSI غيرُ ناضجة — يجب أن تكون ناضجةً ممتازة: أغيّر الألوان، أغيّر الرسم»،
// و«خلِّ صقر يفهم تحليلَ الرسم ويختار بناءً عليه… يحلّل الرسمَ لكامل السوق فيُظهر الفرص بجودتها ومدّتها… والتنفيذُ عندي… وفي السعوديّ بدلَ الإشارات الفرص».
//   ١ حسابُ الخادم (‏chart_tech.py) يطابق حسابَ الواجهة (‏d7m.ts · pulse.ts · indicators.ts) على شموعٍ مصنوعة: الزجزاجُ والفيبو الأربعَ عشرة
//     و‏Stoch RSI وقوّتا الاتجاه والسيولة — فما يقرؤه صقرٌ هو ما يراه المالكُ على الرسم.
//   ٢ نافذةُ Stoch RSI كتريدنق فيو: خطّا K وD (إظهارٌ ولونٌ وسُمكٌ ونوعُ خطّ) والحدودُ والخلفية — تُطبَّق وتُحفظ و«الافتراضي» يعيدها.
//   ٣ تبويبُ «الفرص» في صقر للسوقين، وشارةُ فرصة الرسم في «عقود الخيارات» — في المظهرين، على الحاسوب والجوال.
//    SHOTS=dir node scripts/audit/chart_d784.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdtempSync, writeFileSync, readFileSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };

// ═════ ١ المطابقة: الخادمُ يحسب كما ترسم الواجهة ═════
const ES = join(FRONT, "node_modules/esbuild/lib/main.js");
if (!existsSync(ES)) console.log("… لم تُقَس المطابقة: esbuild غيرُ مثبّت");
else {
  const esbuild = await import(pathToFileURL(ES).href);
  const dir = mkdtempSync(join(tmpdir(), "d784-"));
  writeFileSync(join(dir, "entry.ts"), [
    `export { zigzag, autoFib } from ${JSON.stringify(join(FRONT, "src/components/analysis/d7m.ts"))};`,
    `export { trendForce, liquidityForce } from ${JSON.stringify(join(FRONT, "src/components/analysis/pulse.ts"))};`,
    `export { stochRsi, STOCHRSI_DEFAULTS } from ${JSON.stringify(join(FRONT, "src/lib/indicators.ts"))};`].join("\n"));
  await (esbuild.build || esbuild.default.build)({ entryPoints: [join(dir, "entry.ts")], bundle: true, format: "esm", outfile: join(dir, "m.mjs"),
    platform: "neutral", logLevel: "silent" });
  const M = await import(pathToFileURL(join(dir, "m.mjs")).href);
  // شموعٌ مصنوعةٌ ببذرةٍ ثابتة (‏mulberry32): ثلاثةُ مساراتٍ — صاعدٌ وهابطٌ ومتذبذب
  const rng = seed => () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const series = (seed, drift) => { const r = rng(seed), out = []; let p = 80;
    for (let i = 0; i < 420; i++) { const o = p, c = Math.max(1, o * (1 + drift + (r() - 0.5) * 0.04)), h = Math.max(o, c) * (1 + r() * 0.012), l = Math.min(o, c) * (1 - r() * 0.012);
      out.push({ date: new Date(Date.UTC(2025, 0, 1) + i * 864e5).toISOString().slice(0, 10), open: o, high: h, low: l, close: c, volume: Math.round(1e5 + r() * 9e5) }); p = c; }
    return out; };
  const sets = [series(7, 0.0015), series(11, -0.0012), series(23, 0.0)];
  const ts = sets.map(b => { const f = M.autoFib(b, 3, 7), s = M.stochRsi(b.map(x => x.close), M.STOCHRSI_DEFAULTS), T = M.trendForce(b), L = M.liquidityForce(b, true);
    return { piv: M.zigzag(b, 3, 7).map(p => [p.index, p.price, p.isHigh]), fib: f ? Object.fromEntries(f.lines.map(x => [String(x.level), x.price])) : null,
      k: s.k.slice(-60), d: s.d.slice(-60), t: T && [T.side, T.strength], l: L && [L.side, L.strength] }; });
  writeFileSync(join(dir, "bars.json"), JSON.stringify(sets));
  const py = spawnSync("python3", ["-c", `
import json, sys
sys.path.insert(0, ${JSON.stringify(join(ROOT, "backend"))})
from app.services import chart_tech as T
out = []
for b in json.load(open(${JSON.stringify(join(dir, "bars.json"))})):
    f = T.auto_fib(b, 3, 7)
    k, d = T.stoch_rsi([x["close"] for x in b])
    tf, lf = T.trend_force(b), T.liquidity_force(b)
    out.append({"piv": [[p["index"], p["price"], p["high"]] for p in T.zigzag(b, 3, 7)], "fib": {str(lv): v for lv, v in f["lines"].items()} if f else None,
                "k": k[-60:], "d": d[-60:], "t": tf and [tf["side"], tf["strength"]], "l": lf and [lf["side"], lf["strength"]]})
print(json.dumps(out))`], { encoding: "utf-8" });
  let pyo = null;
  try { pyo = JSON.parse(py.stdout); } catch { /* */ }
  const num = v => (v == null ? null : Number(v));
  const close = (a, b) => (a == null && b == null) || (a != null && b != null && Math.abs(a - b) <= 1e-6 * Math.max(1, Math.abs(a)));
  const lvKey = k => String(Number(k));
  const rows = pyo ? ts.map((t, i) => {
    const p = pyo[i];
    const piv = t.piv.length === p.piv.length && t.piv.every((x, j) => x[0] === p.piv[j][0] && close(x[1], p.piv[j][1]) && x[2] === p.piv[j][2]);
    const fib = !!t.fib && !!p.fib && Object.keys(t.fib).length === 14 && Object.entries(t.fib).every(([k, v]) => close(v, num(p.fib[lvKey(k)] ?? p.fib[k])));
    const sr = t.k.every((v, j) => close(v, p.k[j])) && t.d.every((v, j) => close(v, p.d[j]));
    const fo = t.t[0] === p.t[0] && Math.abs(t.t[1] - p.t[1]) <= 1 && t.l[0] === p.l[0] && Math.abs(t.l[1] - p.l[1]) <= 1;   // ‏round بايثون مصرفيّ: ±1 عند النصف
    return { piv, fib, sr, fo, n: t.piv.length };
  }) : [];
  say(rows.length === 3 && rows.every(r => r.piv && r.fib && r.sr && r.fo && r.n >= 4),
    "١ حسابُ الخادم يطابق حسابَ الواجهة على ثلاثة مسارات: الزجزاجُ بمحاوره، والفيبو بمستوياته الأربعَ عشرة، وStoch RSI ‏(K · D)، وقوّتا الاتجاه والسيولة — "
    + "فما يقرؤه صقرٌ هو ما يراه المالك", pyo ? JSON.stringify(rows) : (py.stderr || "").slice(-200));
}

// ═════ ٢ و٣ في المتصفّح ═════
const PORT = 5284;
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
const bars = (n = 160) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = 600 + i * 1.1 + Math.sin(i / 2) * 6, o = 600 + (i - 1) * 1.1 + Math.sin((i - 1) / 2) * 6;
  return { date: day, open: o, high: Math.max(o, c) + 1, low: Math.min(o, c) - 1, close: c, volume: c >= o ? 3e6 : 1e6 };
});
const OPP = (sym, name, side, q, hn, setup, extra = {}) => ({ symbol: sym, name, setup, side, quality: q, horizon: { 1: "شهر", 2: "شهران", 3: "حتى الربع القادم" }[hn], horizon_n: hn,
  entry: side === "long" ? [24.6, 25.1] : [128, 131], target: side === "long" ? 27.4 : 118, stop: side === "long" ? 24.2 : 133.5, rr: 2.3, zone: "الدعم",
  where: side === "long" ? "في منطقة الدعم" : "في منطقة المقاومة", close: side === "long" ? 25.0 : 129.5,
  trend: { word: side === "long" ? "صاعد" : "هابط", level: "قويّ", strength: 62 }, liq: { word: "داخلةٌ للصعود", level: "متوسّطة", strength: 48, tag: "تجميعٌ خفيّ" },
  k: 18.4, rsi: 44.2, weekly: "صاعد", reasons: ["الاتجاه صاعد قويّ (62/100)"], ...extra });
const OPPS = {
  sa: { market: "sa", at: iso(now - 3600e3), universe: 268, screened: 266, read: 266, found: 3, min_q: 50, job: { on: false, msg: "", at: null },
    items: [OPP("2222", "أرامكو السعودية", "long", 81, 3, "ارتدادٌ من الدعم", { link: { decision: "شراء", confidence: "متوسطة", link: "السعرُ يرتدّ من منطقة الدعم 24.6 مع تشبّعٍ بيعيّ في Stoch RSI والنتائجُ تؤيّد",
      watch: "إغلاقٌ دون 24.2" } }), OPP("1120", "مصرف الراجحي", "long", 66, 2, "استمرارٌ بعد تصحيح"), OPP("2010", "سابك", "long", 54, 1, "ارتدادٌ من منطقة الوسط")] },
  us: { market: "us", at: iso(now - 7200e3), universe: 812, screened: 790, read: 150, found: 3, min_q: 50, job: { on: false, msg: "", at: null },
    items: [OPP("NVDA", "NVIDIA", "long", 77, 3, "اختراقُ المقاومة"), OPP("TSLA", "Tesla", "short", 63, 2, "رفضٌ من المقاومة"), OPP("AAPL", "Apple", "long", 58, 1, "ارتدادٌ من الدعم")] } };
const ST = m => ({ market: m, ccy: m === "sa" ? "SAR" : "USD", on: true, capital: 1000, goal: 100000, cash: 1000, equity: 1000, pl: 0, pl_pct: 0, progress: 0,
  started: iso(now - 86400e3), tier: { frac: 0.25, seats: 4 }, positions: [], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0,
  today: { wins: 0, losses: 0, realized: 0, new: 0 }, exposure: { contracts: 0, cost: 0, value: 0, ret: null }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 1000]],
  signals: m === "sa" ? [{ at: iso(now), sym: "4190", name: "Jarir", verdict: "refused", why: "الرسم: لا فرصةَ الآن — السعرُ بين الوسط والمقاومة" }] : [],
  log: [], gates: [], scan: m === "sa" ? { at: iso(now), universe: 271, movers: 0, pool: 30, deep: 15, budget: 250, tier: { frac: 0.25, seats: 4 } } : null,
  session: null, last_cycle: null, last_check: null, health: {}, broker: { linked: false, name: "IBKR" }, runs: [], running: { on: false, msg: "", at: null },
  settings: { per_trade: null, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 6, take_x: 2, mode: "balanced", day_target: null, auto: false },
  day: null, orders: [], pulse: null, geo: null, rules: { stop: 0.6, take: 2 },
  regime: m === "sa" ? { verdict: "صاعد", state: "صاعد", close: 11500, sma50: 11300, sma200: 11000, ret3m: 4.2, chg: 0.35 } : null,
  opps: { at: OPPS[m].at, universe: OPPS[m].universe, screened: OPPS[m].screened, read: OPPS[m].read, found: OPPS[m].found } });
const PICK = { symbol: "NVDA", name: "NVIDIA", contract: "NVDA270617C00200000", type: "call", strike: 200, ask: 1.45, bid: 1.35, cost: 145, dte: 207, expiry: "2027-06-17",
  breakeven: 201.45, need_pct: 8.2, pop: 36, p_touch: 52, target: 214, target_label: "قمّة السنة", rr: 2.1, delta: 0.41, iv: 44, oi: 3200, spread_pct: 7, spread_usd: 10,
  px_src: "ask", opened: "2026-11-22", new: true, pl_pct: 0, mid_now: 1.4, entry_mid: 1.4, trend: { state: "صاعد" },
  reasons: ["الأطروحة: المسار صاعد", "قراءةُ الرسم: اختراقُ المقاومة — جودتُها 77 من 100 ومدّتُها حتى الربع القادم"],
  chart: { setup: "اختراقُ المقاومة", side: "long", quality: 77, horizon: "حتى الربع القادم", where: "فوق المقاومة" } };

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [], posts = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d784-init")) return;
    sessionStorage.setItem("d784-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "1120"); localStorage.setItem("sp_room_list", "mine");
    localStorage.removeItem("sp_stochrsi_cfg");
    localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: true, stochrsi: true, cvd: false, macd: false, d7m: false }));
    localStorage.setItem("sp_saqr_tab", "signals"); localStorage.setItem("sp_saqr_market", "sa");   // ‏تبويبٌ محفوظٌ قديماً «الإشارات» ⇐ يُفتح على «الفرص»
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "X", price: 64.2, change: 0.4, change_pct: 0.6, time: new Date().toISOString(), delayed: 0, source: "ياهو", session: SES, ext: null }));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa", state: "closed", label: "السوق مغلق" } }));
    if (p === "/market/saqr" && m === "GET") return r.fulfill(body(ST(u.searchParams.get("market") === "sa" ? "sa" : "us")));
    if (p === "/market/saqr/opportunities" && m === "GET") return r.fulfill(body(OPPS[u.searchParams.get("market") === "sa" ? "sa" : "us"]));
    if (p === "/market/options-picks") return r.fulfill(body({ result: { budget: 150, at: iso(now), picks: [PICK], exits: [], skipped: [], scanned: 98, news_ok: true, closed: false,
      limits: { min_dte: 150, max_dte: 430, min_oi: 100, max_spread: 10 } }, running: { on: false } }));
    if (m === "POST") { posts.push([p, JSON.parse(r.request().postData() || "{}")]); return r.fulfill(body({ ...OPPS.sa, job: { on: true, msg: "قراءةُ السوق كلِّه", at: iso(now) } })); }
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });

  // ٢ نافذةُ Stoch RSI
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000); await paint();
  await page.locator('[data-role="pc-cfg"]').first().click(); await page.waitForTimeout(200);
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="stochrsi"]').first().click(); await page.waitForTimeout(400);
  const dlg = page.locator('[data-role="ind-settings"]');
  const fs = await dlg.evaluate(d => ["sr-k", "sr-d", "sr-bands", "sr-bg"].filter(k => d.querySelector(`[data-role="${k}"]`)).length).catch(() => 0);
  await dlg.locator('[data-role="sr-k"] [data-role="color-pick-btn"]').click(); await page.waitForTimeout(200);   // ‏D798: لوحةُ الألوان ثمّ «مخصَّص»
  await page.locator('[data-role="color-pick-pop"] input[type="color"]').fill("#ff0000"); await page.waitForTimeout(250);   // اللوحةُ فوق النافذة (‏D798ب)
  await dlg.locator('[data-role="sr-k"] button', { hasText: "متقطّع" }).click(); await page.waitForTimeout(200);
  await dlg.locator('[data-role="sr-k"] button', { hasText: /^3$/ }).click(); await page.waitForTimeout(200);
  await dlg.locator('[data-role="sr-d"] [role="switch"]').click(); await page.waitForTimeout(200);
  await dlg.locator('[data-role="sr-bands"] input[aria-label="قيمةُ العلويّ"]').fill("85"); await page.waitForTimeout(200);
  await dlg.locator('[data-role="sr-bg"] input[aria-label="الشفافية ٪"]').fill("25"); await page.waitForTimeout(500);
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_stochrsi_cfg") || "{}"));
  const kCol = await page.locator('[data-role="pane-tag"][data-ind="stochrsi"] b').first().evaluate(e => getComputedStyle(e).color).catch(() => "");
  const dm = await dlg.evaluate(d => { let minT = 99, minF = 99;
    d.querySelectorAll("button, input").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
    d.querySelectorAll("*").forEach(e => { if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    return { minT, minF }; });
  if (SHOTS) await dlg.screenshot({ path: `${SHOTS}/d784-sr-${vp.width}-${theme}.png` }).catch(() => {});
  await dlg.locator('[data-role="ind-reset"]').click(); await page.waitForTimeout(400);
  const back = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_stochrsi_cfg") || "{}"));
  await dlg.locator('button[aria-label="إغلاق"]').first().click().catch(() => {});
  say(fs === 4 && saved.kColor === "#ff0000" && saved.kStyle === "dashed" && saved.kWidth === 3 && saved.dOn === false && saved.upper === 85 && saved.bgOpacity === 25
      && kCol === "rgb(255, 0, 0)" && dm.minT >= 32 && dm.minF >= 9.5 && back.kColor === "" && back.kStyle === "solid" && back.dOn === true && back.upper === 80,
    `${label}: ٢ نافذةُ Stoch RSI ناضجةٌ كتريدنق فيو: خطّا K وD (إظهارٌ ولونٌ وسُمكٌ ونوعُ خطّ) والحدودُ (قيمٌ وإظهارٌ ولونٌ ونوع) والخلفيةُ (لونٌ وشفافية) — `
      + "تُطبَّق فوراً (لونُ K في المفتاح) وتُحفظ، و«الافتراضي» يعيدها — ولمسٌ ≥ 32 وخطٌّ ≥ 9.5", JSON.stringify({ fs, kCol, dm, saved: { k: saved.kColor, s: saved.kStyle, w: saved.kWidth } }));

  // ٣ الفرص في صقر — السعوديّ: «الإشارات» المحفوظةُ قديماً تُفتح «الفرص»
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2400); await paint();
  const nav = await page.locator('[data-role="sq-nav"] [data-view]').evaluateAll(bs => bs.map(b => [b.getAttribute("data-view"), b.textContent.trim(), b.getAttribute("aria-selected")]));
  const sa = await page.evaluate(() => ({ cards: [...document.querySelectorAll('[data-role="so-card"]')].map(c => ({ side: c.dataset.side, h: c.dataset.h,
      q: c.querySelector('[data-role="so-q"] .sp-bar i')?.style.width, hz: c.querySelector('[data-role="so-hz"]')?.textContent, chip: c.querySelector('[data-role="so-side-chip"]')?.textContent })),
    meta: document.querySelector('[data-role="so-meta"]')?.textContent || "", ai: !!document.querySelector('[data-role="so-link"] .ai-star'),
    node: document.querySelector('[data-role="sq-node"][data-k="opps"]')?.getAttribute("data-state") || "", oldNode: !!document.querySelector('[data-role="sq-node"][data-k="signals"]'),
    sig: document.querySelector('[data-role="sq-signals"]')?.textContent || "", sigOpen: document.querySelector('[data-role="sq-signals"]')?.open,
    sideF: !!document.querySelector('[data-role="so-side"]'), chain: !!document.querySelector('[data-role="so-chain"]') }));
  if (SHOTS) await page.locator('[data-role="so"]').screenshot({ path: `${SHOTS}/d784-opps-sa-${vp.width}-${theme}.png` }).catch(() => {});
  say(nav.some(([k, t, s]) => k === "opps" && t === "الفرص" && s === "true") && !nav.some(([k]) => k === "signals" || k === "options")
      && sa.cards.length === 3 && sa.cards[0].q === "81%" && sa.cards[0].hz === "حتى الربع القادم" && sa.cards.every(c => c.chip === "شراء") && sa.ai
      && /268/.test(sa.meta) && /266/.test(sa.meta) && /الفرصُ بعد مجلس صقر:\s*3/.test(sa.meta) && sa.node === "ok" && !sa.oldNode
      && sa.sigOpen === false && /قراراتُ صقر/.test(sa.sig) && !sa.sideF && !sa.chain,
    `${label}: ٣ السعوديّ: «الفرص» بدل «الإشارات» (والمحفوظُ قديماً يُفتح عليها) — بطاقاتٌ بجودتها ومدّتها وجهتها، و«الرابط» لأفضلها، ونورُ «الفرص» في لوحة صقر (‏D787: بلا اسم)، `
      + "وقراراتُ صقر مطويّةٌ تحتها — بلا عقودٍ ولا بيع", JSON.stringify({ nav: nav.map(x => x[0]), n: sa.cards.length, node: sa.node, meta: sa.meta.slice(0, 50) }));
  /* ‏D787 (المالك: «الكلّ وشهر وشهران وحتى الربع القادم ما لها داعي»): لا مرشّحَ للمدّة — والمدّةُ على البطاقة */
  const f2 = await page.evaluate(() => ({ none: !document.querySelector('[data-role="so-h"]'), hz: document.querySelectorAll('[data-role="so-hz"]').length }));
  await page.locator('[data-role="so-run"]').click(); await page.waitForTimeout(500);
  const runP = posts.find(x => x[0] === "/market/saqr/opportunities/run");
  const meas = await page.evaluate(() => { const r = document.querySelector('[data-role="so"]'); const W = document.documentElement.clientWidth; let minT = 99, minF = 99;
    r?.querySelectorAll("button, summary").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
    r?.querySelectorAll("*").forEach(e => { if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    const main = document.querySelector(".app-main");
    return { over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W, minT, minF }; });
  say(f2.none && f2.hz === 3 && runP && runP[1].market === "sa" && meas.over <= 1 && meas.minT >= 32 && meas.minF >= 9.5,
    `${label}: ٣ب لا مرشّحَ للمدّة (‏D787) والمدّةُ على كلّ بطاقة، و«امسح الآن» للمالك يطلب مسحَ سوقه — بلا فيضٍ، ولمسٌ ≥ 32، وخطٌّ ≥ 9.5`, JSON.stringify({ f2, meas }));
  await page.locator('[data-role="so-card"]').first().locator('[data-role="so-open"]').click(); await page.waitForTimeout(900);
  const room = await page.evaluate(() => ({ sym: localStorage.getItem("sp_room_symbol"), path: location.pathname, search: location.search }));
  say(room.sym === "2222.SR" && room.path === "/watchlist" && !/tab=lab/.test(room.search),
    `${label}: ٣ج «افتح الرسم» يفتح الشركةَ في غرفة التداول برمزها السعوديّ`, JSON.stringify(room));

  // ٣د الأمريكيّ: الفرصُ بجهتيها وسلسلةُ عقودها، وشارةُ فرصة الرسم في «عقود الخيارات»
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000); await paint();
  await page.locator('[data-role="sq-market"] [data-market="us"]').click(); await page.waitForTimeout(1400);
  await page.locator('[data-role="sq-nav"] [data-view="opps"]').click(); await page.waitForTimeout(900);
  const us0 = await page.locator('[data-role="so-card"]').count();
  await page.locator('[data-role="so-side"] button[data-v="short"]').click(); await page.waitForTimeout(400);
  const us1 = await page.locator('[data-role="so-card"]').evaluateAll(cs => cs.map(c => [c.dataset.side, c.querySelector('[data-role="so-side-chip"]')?.textContent]));
  const usx = await page.evaluate(() => ({ chain: document.querySelectorAll('[data-role="so-chain"]').length, sig: !!document.querySelector('[data-role="sq-signals"]') }));
  if (SHOTS) await page.locator('[data-role="so"]').screenshot({ path: `${SHOTS}/d784-opps-us-${vp.width}-${theme}.png` }).catch(() => {});
  await page.locator('[data-role="sq-nav"] [data-view="options"]').click(); await page.waitForTimeout(1200);
  const chip = await page.locator('[data-role="op-chart"]').first().textContent().catch(() => "");
  if (SHOTS) await page.locator('[data-role="op-pick"]').first().screenshot({ path: `${SHOTS}/d784-pick-${vp.width}-${theme}.png` }).catch(() => {});
  say(us0 === 3 && JSON.stringify(us1) === '[["short","بيع"]]' && usx.chain === 1 && !usx.sig && /اختاره الرسم/.test(chip || "") && /اختراقُ المقاومة/.test(chip || "") && /77/.test(chip || ""),
    `${label}: ٣د الأمريكيّ: «الفرص» بجهتيها (شراءٌ وبيع) ومرشّحُها، ولكلّ فرصةٍ سلسلةُ عقودها — وبطاقةُ «عقود الخيارات» تقول إنّ الرسمَ اختارها بنوعه وجودته`,
    JSON.stringify({ us0, us1, usx, chip }));
  // ٤ الحركة: تسكن مع تفضيل تقليلها
  await page.locator('[data-role="sq-nav"] [data-view="opps"]').click(); await page.waitForTimeout(500);
  await page.emulateMedia({ reducedMotion: "reduce" }); await page.waitForTimeout(300);
  const rm = await page.evaluate(() => getComputedStyle(document.querySelector('[data-role="so-card"]')).animationName);
  await page.emulateMedia({ reducedMotion: "no-preference" }); await page.waitForTimeout(200);
  say(rm === "none" && errs.length === 0, `${label}: ٤ البطاقاتُ تظهر بانسيابية وتسكن مع تفضيل تقليل الحركة — ولا خطأ`, errs[0] || rm);
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
