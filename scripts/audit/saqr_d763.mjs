// ─────────────────────────────────────────────────────────────────────────
// D763 (المالك 2026-11-18): «التقريرُ اليوميّ خلّه في مفكرة السوق بجانب الجزيرة كابيتال والراجحي… وفي مختبر الأبحاث عقودُ الخيارات
// وتبويبُ المحفظة وتبويبُ صقر — وكيلُ تداولٍ آليّ… وهذه صورةُ شاشته». المتصفّحُ على الصفحة الحقيقية والخادمُ مُحاكى:
// التقريرُ في مفكرة السوق بجانب «التوقعات»، وتبويباتُ المختبر الثلاثة، والمحفظةُ (الملخّصُ والهدف والمراكزُ وإشارةُ الخروج والمغلقةُ وإدخالُ
// المالك وإغلاقُه)، ولوحةُ صقر (المركزُ وأنظمتُه الثمانية بحالها، والزوايا، وحالُ الأنظمة والتعرّض و‏SPY والجلسة والنجاح والمنحنى،
// والإشاراتُ والسجلُّ والقواعد، والتشغيلُ والدورة) — في المظهرين، على الحاسوب والجوال، بلا فيضٍ ولا لمسٍ صغيرٍ ولا خطٍّ صغير،
// والحركةُ تسكن مع تفضيل تقليلها.
//    SHOTS=dir node scripts/audit/saqr_d763.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5263;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await new Promise(r => setTimeout(r, 500)); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const SHOTS = process.env.SHOTS;
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { us: { market: "us", state: "open", label: "مفتوح", detail: "يغلق بعد 3 ساعات", next: iso(now + 3 * 3600e3) },
              sa: { market: "sa", state: "closed", label: "مغلق", detail: "يفتح بعد 12 ساعة", next: iso(now + 12 * 3600e3) } };
const POS = (o) => ({ id: "p1", contract: "F270115C00012000", symbol: "F", type: "call", strike: 12, expiry: "2027-01-15", qty: 1, entry_px: 0.40, cost: 40.65,
  opened: iso(now - 86400e3), stop: 0.24, peak: 0.52, bid: 0.52, ask: 0.55, S: 12.4, S0: 11.5, target: 13.2, target_label: "قمّة السنة", delta: 0.42, iv: 33,
  why: ["المسارُ صاعد: الإغلاق 11.50 وفوق متوسّط 200 (10.40)، وتغيّرُ ثلاثة أشهر +12.0٪.", "العقد: دلتا +0.42 · تذبذب 33٪ · تآكل 0.41 دولار يومياً"],
  src: "saqr", auto: true, value: 52, pl: 11.35, pl_pct: 27.9, ...o });
const STATE = {
  on: true, capital: 100, goal: 10000, cash: 59.35, equity: 137.2, pl: 37.2, pl_pct: 37.2, progress: 6.9, started: iso(now - 9 * 86400e3),
  tier: { frac: 0.5, seats: 2 },
  positions: [POS({}), POS({ id: "p2", contract: "NIO270115P00004000", symbol: "NIO", type: "put", strike: 4, entry_px: 0.30, cost: 30.65, bid: 0.15, value: 15, pl: -15.65,
    pl_pct: -51.1, stop: 0.18, src: "manual", auto: false, alert: "stop", target: null, S0: null, why: ["مركزٌ أدخله المالك يدوياً."] })],
  closed: [
    { ...POS({}), id: "c1", contract: "SOFI261218C00015000", symbol: "SOFI", exit_px: 0.9, proceeds: 89.35, pl: 48.7, pl_pct: 119.8, closed: iso(now - 2 * 3600e3), reason: "take", reason_ar: "تضاعف العقد — جنيُ الربح" },
    { ...POS({}), id: "c2", contract: "AAL261218P00012000", symbol: "AAL", type: "put", exit_px: 0.22, proceeds: 21.35, pl: -19.3, pl_pct: -47.5, closed: iso(now - 30 * 3600e3), reason: "stop", reason_ar: "بلغ الوقف" },
    { ...POS({}), id: "c3", contract: "INTC261218C00025000", symbol: "INTC", exit_px: 0.61, proceeds: 60.35, pl: 19.7, pl_pct: 48.5, closed: iso(now - 50 * 3600e3), reason: "trail", reason_ar: "وقفٌ متحرّكٌ يحمي الربح" }],
  n_closed: 3, wins: 2, losses: 1, win_rate: 66.7, realized: 49.1, fees: 4.55,
  today: { wins: 1, losses: 0, realized: 48.7, new: 1 },
  exposure: { contracts: 2, cost: 71.3, value: 67, ret: -6.0 },
  equity_curve: Array.from({ length: 40 }, (_, i) => [iso(now - (40 - i) * 3600e3), 100 + i * 0.9 + (i % 5) * 1.3]),
  signals: [
    { at: iso(now - 600e3), sym: "F", side: "call", verdict: "chosen", contract: "F270115C00012000", why: "دلتا +0.42 · احتمالُ ربح 41٪ · عائدٌ عند الهدف 1.8× · كلفة 41$" },
    { at: iso(now - 600e3), sym: "PLTR", side: "call", verdict: "accepted", why: "دلتا +0.38 · احتمالُ ربح 33٪" },
    { at: iso(now - 600e3), sym: "AAPL", verdict: "refused", why: "المسارُ عرضيّ — لا اتجاهَ يُشترى له عقد" },
    { at: iso(now - 600e3), sym: "TSLA", side: "put", verdict: "refused", why: "المستشار: الفارقُ 11٪ (نحو 9 دولار للعقد)" }],
  log: [
    { at: iso(now - 600e3), kind: "buy", text: "شراء 1 × F Call 12 · 2027-01-15 بسعر 0.40 (الكلفة مع العمولة 40.65$) — الوقف 0.24 والهدف 13.20.", sym: "F" },
    { at: iso(now - 7200e3), kind: "sell", text: "بيع 1 × SOFI Call 15 بسعر 0.90 — تضاعف العقد.", sym: "SOFI" },
    { at: iso(now - 9000e3), kind: "alert", text: "إشارةُ خروجٍ لمركزك اليدويّ NIO Put 4: بلغ الوقف.", sym: "NIO" },
    { at: iso(now - 99000e3), kind: "info", text: "بدأت تجربةٌ جديدة برأس مال 100.00 دولار — والهدف 10,000." }],
  gates: [], scan: { at: iso(now - 600e3), universe: 131, movers: 41, pool: 24, deep: 8, budget: 68.6, tier: { frac: 0.5, seats: 2 },
    full: { cboe: 5407, market: 3183, optionable: 2791, passed: 812, excluded: { "منطقةُ الضيق المالي": 251, "دينٌ مفرط": 49 } } },
  settings: { per_trade: 100, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 7, take_x: 2, mode: "attack", day_target: 100 },
  day: { date: "2026-11-19", pl: 37.2, target: 100, hit: null, new: 1, progress: 37.2 },
  session: SES.us, last_cycle: iso(now - 120e3), last_check: iso(now - 120e3),
  health: { news: true, events: true, quotes: iso(now - 120e3) }, broker: { linked: false, name: "IBKR" },
  runs: [{ started: iso(now - 30 * 86400e3), ended: iso(now - 9 * 86400e3), capital: 100, equity: 81.4, trades: 6 }], running: { on: false, msg: "", at: null },
  rules: { fee: 0.65, stop: 0.6, take: 2, dte: [7, 60], max_spread: 8, delta: [0.3, 0.75], burn: 10, exit_dte: 3, day_loss: 20, max_new_day: 10,
    mode: "attack", scan_min: 5, fight: 2.5, open_wait: 10, close_wait: 15, fed_h: 4, trail: [1.3, 1.5, 0.8], warn_ok: true, cool: 2,
    tiers: [[500, 0.5, 2], [2000, 0.3, 3], [10000, 0.2, 5], [null, 0.1, 8]] },
};
// ‏D764: السوقُ السعوديّ — أسهمُ شركاتٍ بالريال، وقراءةُ تاسي والأحداث
const SA_STATE = { ...STATE, market: "sa", ccy: "SAR", capital: 1000, goal: 100000, cash: 818.6, equity: 1002.4, pl: 2.4, pl_pct: 0.24, progress: 0.05,
  tier: { frac: 0.25, seats: 4 }, broker: { linked: false, name: "الوسيط السعوديّ" },
  positions: [{ ...POS({}), id: "s1", kind: "stock", contract: "1120", symbol: "1120", name: "Al Rajhi Bank", type: "stock", strike: null, expiry: null, qty: 2,
    entry_px: 90.02, cost: 180.32, bid: 91.2, ask: 91.3, S: 91.25, S0: 90.0, target: 105, stop: 84.62, value: 182.4, pl: 2.08, pl_pct: 1.2,
    why: ["تاسي صاعد: 11,500 وفوق متوسّط 200.", "النتائج: صافي الربح +28٪ عن الربع المماثل."] }],
  closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0.28, today: { wins: 0, losses: 0, realized: 0, new: 1 },
  exposure: { contracts: 2, cost: 180.32, value: 182.4, ret: 1.2 },
  regime: { verdict: "صاعد", state: "صاعد", close: 11500, sma50: 11300, sma200: 11000, ret3m: 4.2, chg: 0.35 },
  settings: { per_trade: null, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 6, take_x: 2, mode: "balanced", day_target: null }, day: null,
  pulse: { at: iso(now), adv: 141, dec: 102, unch: 29, turnover: 5.24e9, leaders: [["البنوك", 1.16], ["الاتصالات", 0.62], ["التأمين", 0.41]],
    laggards: [["الطاقة", -1.2], ["المواد الأساسية", -0.8], ["النقل", -0.3]], results: { strong: 88, neutral: 71, weak: 111, pending: 0, unknown: 2 },
    quarter: "2026-09-30", brent: { px: 88.55, chg: -4.9, chg5: -4.5 } },
  geo: { level: "متوسط", why: "توتّرٌ إقليميّ في الممرّات البحرية", sectors: ["البتروكيماويات", "النقل"], brent: "برنت 78.20 دولاراً — اليوم +1.2٪", n: 32, at: iso(now) },
  signals: [{ at: iso(now), sym: "1120", name: "Al Rajhi Bank", verdict: "chosen", contract: "1120", why: "صافي الربح +28٪ · أقوى من تاسي" },
            { at: iso(now), sym: "4190", name: "Jarir", verdict: "refused", why: "نتائجُ الربع المنتهي 2026-09-30 لم تصدر بعد" }],
  log: [{ at: iso(now), kind: "buy", text: "شراء 2 سهم من 1120 بسعر 90.02", sym: "1120" }],
  scan: { at: iso(now), universe: 271, movers: 0, pool: 38, deep: 15, budget: 250, tier: { frac: 0.25, seats: 4 } },
  rules: { market: "sa", fee_pct: 0.155, stop: 0.94, trail: [1.08, 1.12, 0.94], time_days: 42, min_turnover: 5e6, max_spread: 0.6, growth: 15, tasi_panic: -1.5,
    day_loss: 10, max_new_day: 2, tiers: [[10000, 0.25, 4], [50000, 0.2, 5], [null, 0.1, 8]] } };
const PAPER = `<!doctype html><html dir="rtl"><body><section class="page"><h1>التقرير اليومي</h1><p>خبرٌ محليّ</p></section>
  <section class="page"><h1>محفظتنا واختياراتنا</h1><p>لا اختياراتِ اليوم.</p></section></body></html>`;

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [], posts = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_lab_view", "report"); localStorage.removeItem("sp_saqr_tab"); } catch { /* */ } });
  // المظهرُ صنفُ الجذر نفسُه (‏applyTheme) — يُفرض بعد كلّ تحميل
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  let st = JSON.parse(JSON.stringify(STATE));
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (p === "/market/saqr" && m === "GET") return r.fulfill(body(u.searchParams.get("market") === "sa" ? SA_STATE : st));
    if (p.startsWith("/market/saqr/")) {
      const pl = JSON.parse(r.request().postData() || "{}"); posts.push([p, pl]);
      if (p === "/market/saqr/toggle") st = { ...st, on: !!pl.on };
      if (p === "/market/saqr/settings" && pl.budget) st = { ...st, capital: Number(pl.budget) };
      if (p.startsWith("/market/saqr/close/")) st = { ...st, positions: st.positions.filter(x => !p.endsWith(x.id)) };
      return r.fulfill(body(p === "/market/saqr/run" ? { on: true } : st));
    }
    if (p === "/market/sessions") return r.fulfill(body(SES));
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "SPY", price: 590.12, change: 2.4, change_pct: 0.41, session: SES.us }));
    if (p.startsWith("/market/history/")) return r.fulfill(body(Array.from({ length: 60 }, (_, i) => ({ time: i, close: 560 + i * 0.5 + (i % 7) }))));
    if (p === "/market/research-desk") return r.fulfill(body({ report: { date: "2026-11-17", label: "الثلاثاء 17 نوفمبر 2026" },
      dates: [{ date: "2026-11-17", label: "الثلاثاء 17 نوفمبر 2026" }, { date: "2026-11-16", label: "الاثنين 16 نوفمبر 2026" }], running: { on: false } }));
    if (p === "/market/research-desk/paper") return r.fulfill(body({ html: PAPER, date: "2026-11-17" }));
    if (p.startsWith("/market/options/")) return r.fulfill(body(null));
    return r.fulfill(body([]));
  });

  // ١ التقريرُ اليوميّ في مفكرة السوق بجانب «التوقعات»
  await page.addInitScript(() => { try { sessionStorage.setItem("sp:market:tab", "calendar"); } catch { /* */ } });
  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1800); await paint();
  const sw = await page.locator('[role="tablist"][aria-label="المفكرة والإفصاحات وتوصيات المحللين"] [role="tab"]').allTextContents().catch(() => []);
  await page.locator('[data-role="ev-report"]').click().catch(() => {});
  await page.waitForTimeout(1800);
  const rep = await page.evaluate(() => ({ doc: !!document.querySelector('[data-role="daily-report"] [data-role="rl-doc"] iframe'),
    h1: document.querySelector('[data-role="rl-doc"] iframe')?.contentDocument?.querySelector("h1")?.textContent || "",
    days: [...document.querySelectorAll('[data-role="rl-day"]')].map(b => b.textContent.trim()), pdf: !!document.querySelector('[data-role="rl-pdf"]') }));
  const iF = sw.indexOf("التوقعات"), iR = sw.indexOf("التقرير اليومي");
  say(iF >= 0 && iR === iF + 1 && rep.doc && rep.h1 === "التقرير اليومي" && JSON.stringify(rep.days) === JSON.stringify(["17", "16"]) && rep.pdf,
      `${label}: ١ التقريرُ اليوميّ تبويبٌ في مفكرة السوق بجانب «التوقعات» (حيث الجزيرة والراجحي) — بورقته وأيامه وملفّه`, `${sw.join("/")} · ${JSON.stringify(rep)}`);

  // ٢ المختبر: عقودُ الخيارات · المحفظة · صقر — و«التقرير» المحفوظُ قديماً يفتح على عقود الخيارات
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000); await paint();
  const tabs = await page.locator('[data-role="rl-views"] [data-view]').allTextContents().catch(() => []);
  const sel = await page.locator('[data-role="rl-views"] [aria-selected="true"]').textContent().catch(() => "");
  say(JSON.stringify(tabs) === JSON.stringify(["عقود الخيارات", "المحفظة", "صقر"]) && sel === "عقود الخيارات" && await page.locator('[data-role="op"]').count() === 1
      && await page.locator('[data-role="rl-doc"]').count() === 0,
      `${label}: ٢ مختبرُ الأبحاث: عقودُ الخيارات · المحفظة · صقر — بلا التقرير، ومن حفظ «التقرير» يفتح على عقود الخيارات`, `${tabs.join(" · ")} · ${sel}`);

  // ٣ المحفظة
  await page.locator('[data-role="rl-views"] [data-view="portfolio"]').click();
  await page.waitForTimeout(1200);
  const sum = await page.locator('[data-role="sp-sum"]').textContent().catch(() => "");
  const goal = await page.locator('[data-role="sp-goal"]').textContent().catch(() => "");
  const cards = page.locator('[data-role="sp-pos"]');
  const c0 = await cards.nth(0).textContent().catch(() => ""), c1 = await cards.nth(1).textContent().catch(() => "");
  const rows = await page.locator('[data-role="sp-closed-row"]').count();
  say(/\$137\.20/.test(sum) && /\+\$37\.20/.test(sum) && /\$100/.test(goal) && /\$10,000/.test(goal) && /×1\.37/.test(goal) && /×100/.test(goal)
      && await cards.count() === 2 && /صقر/.test(c0) && /F 12 شراء/.test(c0) && /\+\$11\.35/.test(c0) && /يدويّ/.test(c1) && /إشارةُ خروج/.test(c1) && rows === 3,
      `${label}: ٣ المحفظة: رأسُ المال الآن وربحُه منذ البداية، والطريقُ من 100 إلى 10,000 (×1.37 من ×100)، والمراكزُ بمصدرها (صقر · يدويّ) وربحِها، `
      + `وإشارةُ الخروج على مركز المالك، والمغلقةُ بأسبابها`, `${(sum || "").slice(0, 60)} · ${rows}`);
  await page.locator('[data-role="sp-add"]').click(); await page.waitForTimeout(450);
  const addOpen = await page.evaluate(() => getComputedStyle(document.querySelector(".sp-addf-wrap")).opacity);
  await page.locator('[data-role="sp-addf"] input').first().fill("pltr270115c00030000");
  await page.locator('[data-role="sp-addf"] button[type="submit"]').click(); await page.waitForTimeout(700);
  await cards.nth(1).locator('[data-role="sp-close"]').click(); await page.waitForTimeout(300);
  await cards.nth(1).locator('[data-role="sp-close-ok"]').click(); await page.waitForTimeout(800);
  const opened = posts.find(x => x[0] === "/market/saqr/open"), closed = posts.find(x => x[0].startsWith("/market/saqr/close/"));
  say(addOpen === "1" && opened && opened[1].contract === "PLTR270115C00030000" && opened[1].qty === 1 && closed && closed[0].endsWith("/p2")
      && await page.locator('[data-role="sp-pos"]').count() === 1,
      `${label}: ٣ب المالكُ يُدخل مركزاً نفّذه (يتفتّح نموذجُه بانسيابية) ويُغلق مركزاً بسعر الطلب الحيّ — وأمرُه يتقدّم`, JSON.stringify(opened?.[1] || {}));

  // ٤ صقر
  await page.locator('[data-role="rl-views"] [data-view="saqr"]').click();
  await page.waitForTimeout(1500);
  const hub = await page.evaluate(() => {
    const ns = [...document.querySelectorAll('[data-role="sq-node"]')];
    return { n: ns.length, live: document.querySelector('[data-role="sq-hub"]')?.getAttribute("data-live"),
      broker: !!ns.find(x => x.dataset.k === "broker"), fund: ns.find(x => x.dataset.k === "fund")?.textContent || "", ibkr: /IBKR/.test(document.querySelector('[data-role="sq-hub"]')?.textContent || ""),
      ok: ns.filter(x => x.dataset.state === "ok").length, ai: !!document.querySelector('[data-k="ai"] .ai-star'),
      stats: [...document.querySelectorAll('[data-role="sq-stat"]')].map(x => x.textContent.replace(/\s+/g, " ").trim()),
      state: document.querySelector('[data-role="sq-state"]')?.textContent || "" };
  });
  say(hub.n === 8 && hub.live === "1" && !hub.broker && !hub.ibkr && /812/.test(hub.fund) && /الفرز الأساسي/.test(hub.fund) && hub.ok >= 6 && hub.ai && /يعمل الآن/.test(hub.state)
      && hub.stats.length === 4 && /صفقات مفتوحة ?1 ?من ?2/.test(hub.stats[0]) && /\+\$11\.35/.test(hub.stats[1]) && /1 \/ 0/.test(hub.stats[2]) && /\+\$48\.70/.test(hub.stats[3]),
      `${label}: ٤ لوحةُ صقر من الصورة: صقرٌ في المركز وأنظمتُه الثمانية بحالها (بلا IBKR — ‏D767 — ومكانَه «الفرزُ الأساسيّ»)، والزوايا الأربع: المفتوحة · الربحُ الحاليّ · رابحةُ اليوم/خاسرتُه · المحقَّقُ بعد العمولات`,
      JSON.stringify(hub).slice(0, 200));
  const dash = await page.evaluate(() => ({
    cards: ["sq-health", "sq-exposure", "sq-spy", "sq-session", "sq-win", "sq-equity", "sq-gates"].filter(k => document.querySelector(`[data-role="${k}"]`)).length,
    ring: document.querySelector('[data-role="sq-ring"]')?.textContent || "", curve: !!document.querySelector('[data-role="sq-curve"] path.line'),
    spy: document.querySelector('[data-role="sq-spy"]')?.textContent || "", ses: document.querySelector('[data-role="sq-session"]')?.textContent || "",
    tele: document.querySelector('[data-role="sq-health"]')?.textContent || "" }));
  say(dash.cards === 7 && /67%/.test(dash.ring) && dash.curve && /590\.12/.test(dash.spy) && /\d\d:\d\d:\d\d/.test(dash.ses) && !/تلغرام|IBKR/.test(dash.tele) && /التنفيذ\s*بأسعار السوق/.test(dash.tele) && /الفرزُ الأساسيّ\s*812/.test(dash.tele),
      `${label}: ٤ب البطاقات: حالُ الأنظمة · التعرّض · SPY حيّاً · جلسةُ السوق بعدٍّ تنازليّ · نسبةُ النجاح (67%) · منحنى رأس المال · بوّاباتُ الدخول`, JSON.stringify(dash).slice(0, 160));
  await page.locator('[data-role="sq-nav"] [data-view="signals"]').click(); await page.waitForTimeout(500);
  const sig = await page.evaluate(() => [...document.querySelectorAll('[data-role="sq-signal"]')].map(x => x.dataset.verdict));
  const scan = await page.locator('[data-role="sq-scan"]').textContent().catch(() => "");
  const fundSum = await page.locator('[data-role="sq-fund"]').textContent().catch(() => "");
  await page.locator('[data-role="sq-nav"] [data-view="log"]').click(); await page.waitForTimeout(500);
  const logs = await page.evaluate(() => [...document.querySelectorAll('[data-role="sq-log-row"]')].map(x => x.dataset.kind));
  await page.locator('[data-role="sq-nav"] [data-view="rules"]').click(); await page.waitForTimeout(500);
  const rules = await page.locator('[data-role="sq-rules"]').textContent().catch(() => "");
  say(JSON.stringify(sig) === JSON.stringify(["chosen", "accepted", "refused", "refused"]) && /2791/.test(scan) && /812/.test(scan) && /300/.test(fundSum || "")
      && JSON.stringify(logs) === JSON.stringify(["buy", "sell", "alert", "info"]) && /7–60/.test(rules) && /8%/.test(rules) && /هجوميّ/.test(rules),
      `${label}: ٥ الإشاراتُ بقبولها ورفضها وأسبابها (وكم ورقةً لها عقودُ خيارات قرأ وكم اجتاز الأساس، وأعدادُ المستبعَد — ‏D766)، والسجلُّ بأنواعه، والقواعدُ بأرقامها`, `${sig.join(",")} · ${logs.join(",")} · ${(scan || "").slice(0, 90)} · ${fundSum} · ${rules.slice(0, 60)}`);
  await page.locator('[data-role="sq-nav"] [data-view="dash"]').click(); await page.waitForTimeout(400);
  await page.locator('[data-role="sq-toggle"]').click(); await page.waitForTimeout(700);
  const offState = await page.locator('[data-role="sq-state"]').textContent().catch(() => "");
  await page.locator('[data-role="sq-run"]').click(); await page.waitForTimeout(500);
  const tg = posts.find(x => x[0] === "/market/saqr/toggle"), rn = posts.find(x => x[0] === "/market/saqr/run");
  say(tg && tg[1].on === false && /موقوف/.test(offState) && !!rn, `${label}: ٦ المالكُ يوقف صقراً ويشغّله ويطلب دورةً الآن`, offState);
  await page.locator('[data-role="sq-toggle"]').click(); await page.waitForTimeout(700);

  // ٧ القياس: لا فيض، لمسٌ ≥ 32، خطٌّ ≥ 9.5 — في الصفحتين
  const meas = async sel => page.evaluate(sel => {
    const r = document.querySelector(sel); if (!r) return null; const W = document.documentElement.clientWidth;
    let minT = 99, minF = 99;
    r.querySelectorAll("button, input, summary").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
    r.querySelectorAll("*").forEach(e => { if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    const main = document.querySelector(".app-main");
    return { over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W, minT, minF };
  }, sel);
  const mq = await meas('[data-role="sq"]');
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/saqr-${vp.width}-${theme}.png`, fullPage: true }).catch(() => {});
  await page.locator('[data-role="rl-views"] [data-view="portfolio"]').click(); await page.waitForTimeout(900);
  const mp = await meas('[data-role="sp"]');
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/saqr-pf-${vp.width}-${theme}.png`, fullPage: true }).catch(() => {});
  say(mq && mp && mq.over <= 1 && mp.over <= 1 && mq.minT >= 32 && mp.minT >= 32 && mq.minF >= 9.5 && mp.minF >= 9.5,
      `${label}: ٧ لا فيضَ أفقيّ، وأهدافُ اللمس ≥ 32px، والخطُّ ≥ 9.5px — في صقر والمحفظة`, JSON.stringify({ mq, mp }));
  // ٨ الحركةُ تسكن مع تفضيل تقليلها
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.locator('[data-role="rl-views"] [data-view="saqr"]').click(); await page.waitForTimeout(700);
  const rm = await page.evaluate(() => ({ orbit: getComputedStyle(document.querySelector(".sq-orbit")).animationName, halo: getComputedStyle(document.querySelector(".sq-halo")).animationName,
    node: getComputedStyle(document.querySelector(".sq-node")).animationName }));
  await page.emulateMedia({ reducedMotion: "no-preference" }); await page.waitForTimeout(300);
  const mv = await page.evaluate(() => getComputedStyle(document.querySelector(".sq-orbit")).animationName);
  say(rm.orbit === "none" && rm.halo === "none" && rm.node === "none" && mv !== "none", `${label}: ٨ المدارُ والنبضُ والظهورُ يتحرّكون — ويسكنون مع تفضيل تقليل الحركة`, JSON.stringify({ rm, mv }));
  // ١٠ ‏D764: الشعارُ صورةُ المالك — الصقرُ الآليّ في المركز وفي الترويسة، يتوهّج حين يعمل
  await page.waitForFunction(() => [...document.querySelectorAll('[data-role="sq-emblem"] img')].every(i => i.complete && i.naturalWidth > 0), null, { timeout: 8000 }).catch(() => {});
  const em = await page.evaluate(() => { const core = document.querySelector('[data-role="sq-core"] [data-role="sq-emblem"]'), head = document.querySelector('.sq-id [data-role="sq-emblem"]');
    const im = core?.querySelector("img");
    return { n: document.querySelectorAll('[data-role="sq-emblem"]').length, live: !!core?.classList.contains("live"), nat: im?.naturalWidth || 0, alt: im?.alt,
      w: core?.getBoundingClientRect().width || 0, hw: head?.getBoundingClientRect().width || 0, bg: getComputedStyle(core || document.body).backgroundColor,
      bird: !!document.querySelector(".lucide-bird") }; });
  if (SHOTS) await page.locator('[data-role="sq-hub"]').screenshot({ path: `${SHOTS}/emblem-${vp.width}-${theme}.png` }).catch(() => {});
  say(em.n === 2 && em.live && em.nat >= 160 && em.alt === "صقر" && em.w >= 100 && em.hw >= 28 && /rgba\(0, 0, 0, 0\)|transparent/.test(em.bg) && !em.bird,
      `${label}: ١٠ شعارُ صقر صورةُ المالك (الصقرُ الآليّ) بشفافيتها بلا أرضية — في المركز والترويسة، ويتوهّج حين يعمل — بلا أيقونة طائرٍ عامّة`, JSON.stringify(em));
  // ١١ ‏D764: السوقُ السعوديّ — المحفظةُ بالريال وأسهمُ شركات، ولوحةُ صقر بأنظمتها: النتائجُ الربعية وتاسي والأحداثُ الجيوسياسية
  await page.locator('[data-role="sq-market"] [data-market="sa"]').click(); await page.waitForTimeout(1100);
  const sa = await page.evaluate(() => ({ head: document.querySelector(".sq-id")?.textContent || "", nodes: [...document.querySelectorAll('[data-role="sq-node"]')].map(x => x.dataset.k),
    tasi: document.querySelector('[data-role="sq-tasi"]')?.textContent || "", read: document.querySelector('[data-role="sq-pulse"]')?.textContent || "",
    spy: !!document.querySelector('[data-role="sq-spy"]'), geoTxt: /جيوسياس/.test(document.querySelector('[data-role="sq"]')?.textContent || ""),
    br: document.querySelector('[data-k="breadth"]')?.textContent || "", mk: document.querySelector('[data-role="sq"]')?.getAttribute("data-market") }));
  await page.locator('[data-role="sq-nav"] [data-view="rules"]').click(); await page.waitForTimeout(400);
  const saRules = await page.locator('[data-role="sq-rules"]').textContent().catch(() => "");
  await page.locator('[data-role="rl-views"] [data-view="portfolio"]').click(); await page.waitForTimeout(900);
  const saPf = await page.evaluate(() => ({ mk: document.querySelector('[data-role="sp"]')?.getAttribute("data-market"), sum: document.querySelector('[data-role="sp-sum"]')?.textContent || "",
    card: document.querySelector('[data-role="sp-pos"]')?.textContent || "" }));
  if (SHOTS) await page.screenshot({ path: `${SHOTS}/saqr-sa-pf-${vp.width}-${theme}.png`, fullPage: true }).catch(() => {});
  say(sa.mk === "sa" && /السعوديّ/.test(sa.head) && ["results", "tasi", "breadth"].every(k => sa.nodes.includes(k)) && !sa.nodes.includes("geo") && !sa.nodes.includes("broker")
      && sa.nodes.length === 7 && /141/.test(sa.br) && !sa.geoTxt && /11,500/.test(sa.tasi) && !sa.spy
      && /اتّساعُ السوق/.test(sa.read) && /5\.24 مليار ريال/.test(sa.read) && /البنوك/.test(sa.read) && /88 قوية/.test(sa.read) && /برنت/.test(sa.read)
      && /اتجاهُ المؤشّر العامّ أوّلاً/.test(saRules) && /النتائجُ الربعية/.test(saRules)
      && saPf.mk === "sa" && /1,002\.40 ر\.س/.test(saPf.sum) && /سهم/.test(saPf.card) && /1120/.test(saPf.card) && /Al Rajhi/.test(saPf.card),
      `${label}: ١١ السوقُ السعوديّ: محفظةٌ بالريال وأسهمُ شركات، ولوحةُ صقر بأنظمتها (النتائجُ الربعية · تاسي · اتّساعُ السوق) ونبضُ السوق (الاتّساعُ · التداول · القطاعات · النتائج · برنت) بلا «الأحداث الجيوسياسية» (‏D767)، وقواعدُه بصياغةٍ احترافية`,
      JSON.stringify({ ...sa, read: sa.read.slice(0, 40), saPf: saPf.sum.slice(0, 40) }));
  /* ١٢ ‏D767: «أضف خيارَ تحديد الميزانية — 150 أو 100 — وخلّ فيه مرونة»: الميزانيةُ في المحفظة وأوامرُ المالك في «الإعدادات» */
  await page.locator('[data-role="sp-budget-edit"]').click(); await page.waitForTimeout(300);
  await page.locator('[data-role="sp-budget"] .seg-btn').first().click(); await page.waitForTimeout(150);
  await page.locator('[data-role="sp-budget-ok"]').click(); await page.waitForTimeout(700);
  const pBud = posts.filter(x => x[0] === "/market/saqr/settings").map(x => x[1]);
  await page.locator('[data-role="sq-market"] [data-market="us"]').click(); await page.waitForTimeout(500);
  await page.locator('[data-role="rl-views"] [data-view="saqr"]').click(); await page.waitForTimeout(900);
  await page.locator('[data-role="sq-nav"] [data-view="rules"]').click(); await page.waitForTimeout(500);
  await page.locator('[data-role="sq-budget-preset"]', { hasText: "$150" }).click(); await page.waitForTimeout(150);
  await page.locator('[data-role="sq-per-trade"]').fill("40");
  await page.locator('[data-role="sq-settings"] [data-v="calls"]').click();
  await page.locator('[data-role="sq-save"]').click(); await page.waitForTimeout(700);
  const pSet = posts.filter(x => x[0] === "/market/saqr/settings").map(x => x[1]);
  const savedMsg = await page.locator('[data-role="sq-save-msg"]').textContent().catch(() => "");
  const ms = await page.evaluate(() => { const r = document.querySelector('[data-role="sq-settings"]'); let minT = 99;
    r?.querySelectorAll("button, input").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
    return { minT, over: document.documentElement.scrollWidth - document.documentElement.clientWidth }; });
  say(pBud.length === 1 && pBud[0].market === "sa" && Number(pBud[0].budget) === 1000 && pSet.length === 2 && pSet[1].market === "us" && String(pSet[1].budget) === "150"
      && String(pSet[1].per_trade) === "40" && pSet[1].sides === "calls" && pSet[1].mode === "attack" && String(pSet[1].day_target) === "100"
      && /حُفظت الأوامر/.test(savedMsg || "") && ms.minT >= 32 && ms.over <= 1,
      `${label}: ١٢ الميزانيةُ تُعدَّل من المحفظة (1,000 ر.س للسعوديّ)، وأوامرُ المالك في «الإعدادات» (150$ · حدُّ صفقةٍ 40 · شراءٌ فقط) تُحفظ لسوقها`,
      JSON.stringify({ pBud, last: pSet[1], ms }).slice(0, 220));
  /* ١٣ ‏D768: «بعد إيقاف تلغرام ضع تاريخ الصفقة ووقتَ بدئها»، و«صقرٌ متحفّظٌ جداً — يجب أن يكون وحشاً شرساً… 100 دولار للعقد… وأقلُّ شيءٍ 100 دولار ربحاً يومياً» */
  await page.locator('[data-role="sq-nav"] [data-view="dash"]').click(); await page.waitForTimeout(500);
  const d13 = await page.evaluate(() => ({ day: document.querySelector('[data-role="sq-day"]')?.textContent || "",
    risk: document.querySelector('[data-role="sq-hub"] [data-k="risk"]')?.textContent || document.querySelector('[data-k="risk"]')?.textContent || "" }));
  if (SHOTS) await page.locator('[data-role="sq-day"]').screenshot({ path: `${SHOTS}/sq-day-${vp.width}-${theme}.png` }).catch(() => {});
  await page.locator('[data-role="rl-views"] [data-view="portfolio"]').click(); await page.waitForTimeout(900);
  const p13 = await page.evaluate(() => ({ when: [...document.querySelectorAll('[data-role="sp-opened"]')].map(e => e.textContent || ""),
    ct: [...document.querySelectorAll('[data-role="sp-closed-time"]')].map(e => e.textContent || ""), kday: document.querySelector('[data-role="sp-day"]')?.textContent || "" }));
  if (SHOTS) await page.locator('[data-role="sp-pos"]').first().screenshot({ path: `${SHOTS}/sp-when-${vp.width}-${theme}.png` }).catch(() => {});
  const ST = /\d{2}\/\d{2} \d{2}:\d{2}/, DUR = /\d+ ي( \d+ س)?|\d+ س( \d+ د)?|\d+ د/;
  say(/هدفُ اليوم/.test(d13.day) && /\$100/.test(d13.day) && /\+\$37\.20/.test(d13.day) && /الهجوميّ/.test(d13.day) && /\$100/.test(d13.risk)
      && p13.when.length >= 1 && p13.when.every(t => /فُتحت/.test(t) && ST.test(t) && /منذ/.test(t) && DUR.test(t))
      && p13.ct.length === 3 && p13.ct.every(t => (t.match(/\d{2}\/\d{2} \d{2}:\d{2}/g) || []).length === 2 && DUR.test(t))
      && /ربحُ اليوم/.test(p13.kday) && /\$100/.test(p13.kday),
      `${label}: ١٣ كلُّ مركزٍ بتاريخ فتحه ووقته ومدّته، وكلُّ مغلقةٍ بوقتَي الدخول والخروج ومدّتها، وهدفُ اليوم (100$) في اللوحة والمحفظة، والنمطُ الهجوميّ بـ100$ للصفقة`,
      JSON.stringify({ d13: { day: d13.day.slice(0, 60), risk: d13.risk }, w: p13.when[0], c: p13.ct[0], k: p13.kday.slice(0, 40) }).slice(0, 260));
  say(errs.length === 0, `${label}: ٩ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
