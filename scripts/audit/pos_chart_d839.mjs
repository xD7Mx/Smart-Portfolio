// ─────────────────────────────────────────────────────────────────────────
// D839 — رسمُ المركز المفتوح في بطاقته (المالك 2026-11-25): «حتى أراقب شكلَ العقد مباشرةً… ضع الرسمَ نفسَه في بطاقة المركز المفتوح —
// بياناتُ المركز فوق، وفي الأسفل الرسمُ البيانيّ للعقد نفسِه أو للسهم — واجعل مسبّبات الاختيار في سهمٍ ينسدل… ولا تكون البطاقةُ أكبرَ من الآن».
//  ١ البطاقة: البياناتُ فوق والرسمُ تحتها مرسوماً (شموعُ العقد بإطار الساعة)، بخطوط الدخول والوقف والجني — ولا تمريرَ ولا تكبيرَ داخلها.
//  ٢ «العقد | السهم»: زرٌّ يبدّل إلى رسم السهم (بمستواه عند الدخول وهدفه) بانسيابية؛ ومركزُ السهم رسمُه وحدَه بلا زرّ.
//  ٣ أسبابُ الاختيار مطويّةٌ خلف سهمٍ ينسدل وينطوي بانسيابية — ولا تكبر البطاقةُ عمّا كانت (الأسبابُ ظاهرةً ومسارُ السهم).
//  ٤ المظهران والجوال والحاسوب، وتقليلُ الحركة — بلا خطأ.
//    node scripts/audit/pos_chart_d839.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5339;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "", next: null };
const WHY = ["من «عقود الخيارات» (دفترُ 200$ · توصيةٌ منذ 2026-11-23): درجةُ 49 من 100.", "الأطروحة: المسارُ هابطٌ تحت متوسّط 200.",
  "الأخبار: سلبيٌّ قويّ — خفضُ التوقّعات.", "الهدف 3.50 (حركةٌ متوقّعةٌ بانحرافٍ واحد)."];
const OPT = { id: "p1", kind: "option", contract: "NIO271217P00003000", symbol: "NIO", name: "NIO Inc.", type: "put", strike: 3, expiry: "2027-12-17", qty: 1,
  entry_px: 1.01, cost: 101.65, opened: iso(now - 30 * 3600e3), stop: 0.61, peak: 1.05, bid: 0.91, ask: 0.95, S: 4.3, S0: 4.5, target: 3.5, why: WHY,
  src: "saqr", auto: true, value: 91, pl: -10.65, pl_pct: -9.9, take_x: 2 };
const STK = { ...OPT, id: "p2", kind: "stock", contract: "SOFI", symbol: "SOFI", name: "SoFi", type: "stock", strike: null, expiry: null, qty: 5, entry_px: 9.72,
  cost: 48.6, stop: 9.04, bid: 9.9, ask: 9.92, S: 9.9, S0: 9.72, target: 12.23, value: 49.5, pl: 0.9, pl_pct: 1.8, take_x: null, why: WHY.slice(1) };
const ST = { market: "us", ccy: "USD", on: true, capital: 1000, goal: 100000, cash: 800, equity: 940, pl: -60, pl_pct: -6, progress: 0, started: iso(now - 86400e3 * 7),
  tier: { frac: 0.25, seats: 4 }, positions: [OPT, STK], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0,
  today: { wins: 0, losses: 0, realized: 0, new: 0 }, exposure: { contracts: 1, cost: 150, value: 140, ret: -6 }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 940]],
  signals: [], log: [], gates: [], scan: null, session: SES, last_cycle: null, last_check: null, health: {}, broker: { linked: false, name: "IBKR" }, runs: [],
  running: { on: false, msg: "", at: null }, settings: { opt_stop: 40, stock_stop: 7, take_x: 2, mode: "balanced", auto: true, sides: "both", instruments: "both" },
  day: null, orders: [], pulse: null, geo: null, rules: { stop: 0.6, take: 2, growth: 15 }, regime: null, opps: null };
/* شموعُ الساعة بختم الخادم (ساعةُ الرياض) — العقدُ 90 شمعةً والسهمُ 70: عددان مختلفان يميّزان أيَّ رسمٍ رُسم */
const hourly = (n, base, drift) => Array.from({ length: n }, (_, i) => { const t = new Date(now - (n - i) * 3600e3 + 3 * 3600e3).toISOString();
  const c = base + drift * i + Math.sin(i / 3) * base * 0.01; return { date: `${t.slice(0, 10)} ${t.slice(11, 16)}`, open: c, high: c * 1.01, low: c * 0.99, close: c, volume: 100 }; });

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme, reduce] of [["الحاسوب · فاتح", { width: 1366, height: 900 }, "light", false], ["الجوال · داكن", { width: 390, height: 844 }, "dark", false],
  ["تقليلُ الحركة", { width: 390, height: 844 }, "light", true]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, colorScheme: theme, reducedMotion: reduce ? "reduce" : "no-preference" });
  const page = await ctx.newPage();
  const errs = [], asked = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_saqr_market", "us"); localStorage.setItem("sp_saqr_tab", "portfolio"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p.startsWith("/market/history/")) { const s = decodeURIComponent(p.split("/").pop()); asked.push(`${s}@${u.searchParams.get("tf")}`);
      return r.fulfill(body(s.includes("P000") ? hourly(90, 1.0, -0.0006) : s === "NIO" ? hourly(70, 4.5, -0.002) : hourly(60, 9.7, 0.003))); }
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa" } }));
    if (p === "/market/saqr") return r.fulfill(body(ST));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await sleep(900);
  await page.locator('[data-role="sq-nav"] [data-view="portfolio"]').click().catch(() => {});
  await sleep(2200);
  const card = page.locator('[data-role="sp-pos"]').first();
  const m1 = await card.evaluate(c => {
    const box = c.querySelector('[data-role="sp-chartbox"]'), mt = c.querySelector(".sp-pos-m"), cv = box ? [...box.querySelectorAll("canvas")] : [];
    const ink = cv.some(k => { try { const g = k.getContext("2d"); const d = g.getImageData(0, 0, k.width, k.height).data; for (let i = 3; i < d.length; i += 4 * 97) if (d[i] > 0) return true; } catch { /* */ } return false; });
    const wb = c.querySelector(".sp-why-b");
    return { has: !!box, below: !!(box && mt && box.getBoundingClientRect().top >= mt.getBoundingClientRect().bottom - 1), canvases: cv.length, ink,
      view: box?.dataset.view, seg: !!c.querySelector('[data-role="sp-chart-view"]'), h: Math.round(c.getBoundingClientRect().height),
      whyH: wb ? Math.round(wb.getBoundingClientRect().height) : -1, whyExp: c.querySelector('[data-role="sp-why-toggle"]')?.getAttribute("aria-expanded"),
      path: !!c.querySelector('[data-role="sp-path"]'), chartH: box ? Math.round(box.getBoundingClientRect().height) : 0 };
  });
  /* مقياسُ «لا تكبر»: البطاقةُ كما كانت = هي الآن − الرسم − زرُّ الأسباب + الأسبابُ ظاهرةً (ارتفاعُها المفتوح) + مسارُ السهم (‏≈ 30) */
  await card.locator('[data-role="sp-why-toggle"]').click().catch(() => {}); await sleep(reduce ? 120 : 500);
  const m2 = await card.evaluate(c => ({ whyH: Math.round(c.querySelector(".sp-why-b").getBoundingClientRect().height), exp: c.querySelector('[data-role="sp-why-toggle"]').getAttribute("aria-expanded"),
    tr: getComputedStyle(c.querySelector(".sp-why-b")).transitionDuration, cardH: Math.round(c.getBoundingClientRect().height),
    inActs: !!c.querySelector('.sp-acts [data-role="sp-why-toggle"]') }));
  await card.locator('[data-role="sp-why-toggle"]').click().catch(() => {}); await sleep(reduce ? 120 : 500);
  const whyBack = await card.evaluate(c => Math.round(c.querySelector(".sp-why-b").getBoundingClientRect().height));
  /* كانت البطاقةُ: الأسبابُ ظاهرةً (كما هي مفتوحةً الآن) ومسارُ السهم إلى هدفه (سطرٌ وشريطٌ ≈ 28) — بلا رسم */
  const before = m2.cardH - m1.chartH + 28;
  const nAsk0 = asked.length;
  await card.locator('[data-role="sp-chart-view"] [data-v="s"]').click().catch(() => {}); await sleep(1600);
  const v2 = await card.evaluate(c => c.querySelector('[data-role="sp-chartbox"]')?.dataset.view);
  const stockAsk = asked.slice(nAsk0);
  const stk = await page.locator('[data-role="sp-pos"]').nth(1).evaluate(c => ({ seg: !!c.querySelector('[data-role="sp-chart-view"]'), view: c.querySelector('[data-role="sp-chartbox"]')?.dataset.view,
    canv: c.querySelectorAll('[data-role="sp-chartbox"] canvas').length }));
  const lines = await page.evaluate(() => document.querySelectorAll('[data-role="sp-chartbox"] canvas').length);
  if (process.env.SHOTS) { await card.locator('[data-role="sp-chart-view"] [data-v="c"]').click().catch(() => {}); await sleep(900);
    await card.screenshot({ path: join(process.env.SHOTS, `d839-${vp.width}-${theme}${reduce ? "-rm" : ""}.png`) }).catch(() => {}); }

  say(m1.has && m1.below && m1.canvases > 0 && m1.ink && asked.includes("NIO271217P00003000@1h") && !m1.path && m1.chartH >= 100 && m1.chartH <= 140,
    `${label}: ١ البطاقة: البياناتُ فوق والرسمُ تحتها مرسوماً (العقدُ بإطار الساعة) بخطوط الدخول والوقف والجني — ومسارُ السهم خطٌّ فيه`,
    JSON.stringify({ ...m1, asked: asked.slice(0, 3) }));
  say(m1.seg && m1.view === "c" && v2 === "s" && stockAsk.includes("NIO@1h") && !stk.seg && stk.view === "s" && stk.canv > 0,
    `${label}: ٢ «العقد | السهم» يبدّل إلى رسم السهم — ومركزُ السهم رسمُه وحدَه بلا زرّ`, JSON.stringify({ v2, stockAsk, stk }));
  say(m1.whyH <= 1 && m1.whyExp === "false" && m2.whyH > 30 && m2.exp === "true" && m2.inActs && whyBack <= 1 && (reduce ? m2.tr === "0s" : m2.tr !== "0s") && m1.h <= before + 8,
    `${label}: ٣ الأسبابُ مطويّةٌ خلف سهمٍ في صفّ الأزرار ينسدل وينطوي ${reduce ? "(فوراً مع تقليل الحركة)" : "بانسيابية"} — والبطاقةُ لا تكبر عمّا كانت`,
    JSON.stringify({ الآن: m1.h, كانت: before, مفتوحة: m2.whyH, tr: m2.tr }));
  say(errs.length === 0, `${label}: ٤ لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
