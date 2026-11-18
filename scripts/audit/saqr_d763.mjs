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
  gates: [], scan: { at: iso(now - 600e3), universe: 131, movers: 41, pool: 24, deep: 8, budget: 68.6, tier: { frac: 0.5, seats: 2 } },
  session: SES.us, last_cycle: iso(now - 120e3), last_check: iso(now - 120e3),
  health: { news: true, events: true, quotes: iso(now - 120e3), telegram: true }, broker: { linked: false, name: "IBKR" },
  runs: [{ started: iso(now - 30 * 86400e3), ended: iso(now - 9 * 86400e3), capital: 100, equity: 81.4, trades: 6 }], running: { on: false, msg: "", at: null },
  rules: { fee: 0.65, stop: 0.6, take: 2, dte: [21, 200], max_spread: 8, delta: [0.35, 0.8], burn: 3, exit_dte: 14, day_loss: 15, max_new_day: 3,
    tiers: [[500, 0.5, 2], [2000, 0.3, 3], [10000, 0.2, 5], [null, 0.1, 8]] },
};
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
    if (p === "/market/saqr" && m === "GET") return r.fulfill(body(st));
    if (p.startsWith("/market/saqr/")) {
      const pl = JSON.parse(r.request().postData() || "{}"); posts.push([p, pl]);
      if (p === "/market/saqr/toggle") st = { ...st, on: !!pl.on };
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
      broker: ns.find(x => x.dataset.k === "broker")?.dataset.state, brokerT: ns.find(x => x.dataset.k === "broker")?.textContent || "",
      ok: ns.filter(x => x.dataset.state === "ok").length, ai: !!document.querySelector('[data-k="ai"] .ai-star'),
      stats: [...document.querySelectorAll('[data-role="sq-stat"]')].map(x => x.textContent.replace(/\s+/g, " ").trim()),
      state: document.querySelector('[data-role="sq-state"]')?.textContent || "" };
  });
  say(hub.n === 8 && hub.live === "1" && hub.broker === "off" && /غير مربوط/.test(hub.brokerT) && hub.ok >= 6 && hub.ai && /يعمل الآن/.test(hub.state)
      && hub.stats.length === 4 && /صفقات مفتوحة ?1 ?من ?2/.test(hub.stats[0]) && /\+\$11\.35/.test(hub.stats[1]) && /1 \/ 0/.test(hub.stats[2]) && /\+\$48\.70/.test(hub.stats[3]),
      `${label}: ٤ لوحةُ صقر من الصورة: صقرٌ في المركز وأنظمتُه الثمانية بحالها (والوسيطُ «غيرُ مربوط» صراحةً)، والزوايا الأربع: المفتوحة · الربحُ الحاليّ · رابحةُ اليوم/خاسرتُه · المحقَّقُ بعد العمولات`,
      JSON.stringify(hub).slice(0, 200));
  const dash = await page.evaluate(() => ({
    cards: ["sq-health", "sq-exposure", "sq-spy", "sq-session", "sq-win", "sq-equity", "sq-gates"].filter(k => document.querySelector(`[data-role="${k}"]`)).length,
    ring: document.querySelector('[data-role="sq-ring"]')?.textContent || "", curve: !!document.querySelector('[data-role="sq-curve"] path.line'),
    spy: document.querySelector('[data-role="sq-spy"]')?.textContent || "", ses: document.querySelector('[data-role="sq-session"]')?.textContent || "",
    tele: document.querySelector('[data-role="sq-health"]')?.textContent || "" }));
  say(dash.cards === 7 && /67%/.test(dash.ring) && dash.curve && /590\.12/.test(dash.spy) && /\d\d:\d\d:\d\d/.test(dash.ses) && /تلغرام\s*مربوط/.test(dash.tele) && /IBKR\s*غير مربوط/.test(dash.tele),
      `${label}: ٤ب البطاقات: حالُ الأنظمة · التعرّض · SPY حيّاً · جلسةُ السوق بعدٍّ تنازليّ · نسبةُ النجاح (67%) · منحنى رأس المال · بوّاباتُ الدخول`, JSON.stringify(dash).slice(0, 160));
  await page.locator('[data-role="sq-nav"] [data-view="signals"]').click(); await page.waitForTimeout(500);
  const sig = await page.evaluate(() => [...document.querySelectorAll('[data-role="sq-signal"]')].map(x => x.dataset.verdict));
  const scan = await page.locator('[data-role="sq-scan"]').textContent().catch(() => "");
  await page.locator('[data-role="sq-nav"] [data-view="log"]').click(); await page.waitForTimeout(500);
  const logs = await page.evaluate(() => [...document.querySelectorAll('[data-role="sq-log-row"]')].map(x => x.dataset.kind));
  await page.locator('[data-role="sq-nav"] [data-view="rules"]').click(); await page.waitForTimeout(500);
  const rules = await page.locator('[data-role="sq-rules"]').textContent().catch(() => "");
  say(JSON.stringify(sig) === JSON.stringify(["chosen", "accepted", "refused", "refused"]) && /131/.test(scan) && /41/.test(scan)
      && JSON.stringify(logs) === JSON.stringify(["buy", "sell", "alert", "info"]) && /21–200/.test(rules) && /8%/.test(rules),
      `${label}: ٥ الإشاراتُ بقبولها ورفضها وأسبابها (وكم قرأ من السوق ومن الأنشط اليوم)، والسجلُّ بأنواعه، والقواعدُ بأرقامها`, `${sig.join(",")} · ${logs.join(",")}`);
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
  say(errs.length === 0, `${label}: ٩ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
