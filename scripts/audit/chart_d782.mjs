// ─────────────────────────────────────────────────────────────────────────
// D782 — الرسمُ وغرفةُ التداول كما أمر المالك (2026-11-21): لوحتا قوّة الاتجاه والسيولة بدل الشريط، وزرُّ «تحليل الرسم» بجانب «الأحداث»
// مكانَ شارة السوق (والحالةُ أيقونةٌ بجانب الاسم)، والأحداثُ بالعربية وللسوق السعودي، والإطاراتُ أكثرُ ثلاثةٍ استخداماً و«مختصر · الكل» داخل
// D7M، والشاشاتُ المتعدّدة، والسعرُ كلَّ ثانيتين، و«المؤشرات» بأسعارها، وترسُ القوائم (إظهارٌ وإخفاءٌ وقسمٌ ثانٍ).
// خادمٌ مموَّهٌ بأشكال الردود الحقيقية، ويُفحص على الشاشتين.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5282;
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
const SES = { us: { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" },
  sa: { market: "sa", state: "closed", label: "السوق مغلق", detail: "يفتح بعد 13 س", next: null } };
/* صعودٌ بموجةٍ صغيرة، والحجمُ أثقلُ في الشموع الصاعدة ⇒ الاتجاهُ صاعدٌ والسيولةُ داخلة */
const bars = (n = 150) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = 600 + i * 1.1 + Math.sin(i / 2) * 3, o = 600 + (i - 1) * 1.1 + Math.sin((i - 1) / 2) * 3;
  return { date: day, open: o, high: Math.max(o, c) + 1, low: Math.min(o, c) - 1, close: c, volume: c >= o ? 3e6 : 1e6 };
});
const GROUPS = [{ id: 1, name: "الرئيسية", is_default: true, sort_order: 0 }, { id: 3, name: "المؤشرات", is_default: false, sort_order: -1 },
  { id: 2, name: "السوق الأمريكي", is_default: false, sort_order: 0 }];
const ROWS = { 1: [{ symbol: "AAPL", name: "Apple", price: 231.4, change_pct: 0.3 }],
  2: [{ symbol: "SPY", name: "SPDR S&P 500", price: 754.37, change_pct: -0.94 }, { symbol: "2222.SR", name: "أرامكو السعودية", price: 27.1, change_pct: 0.4 },
      { symbol: "NVDA", name: "NVIDIA", price: 181.2, change_pct: 1.2 }],
  3: [{ symbol: "^TASI.SR", name: "تاسي", price: 11234.5, change_pct: -0.31 }, { symbol: "^GSPC", name: "S&P 500", price: 6012.4, change_pct: 0.42 },
      { symbol: "BTC-USD", name: "بتكوين", price: 96123.1, change_pct: 2.1 }] };
const EV_US = { read_ok: true, market: "us", company: [], events: [
  { id: "e0", title: "Retail Sales m/m", ar: "مبيعاتُ التجزئة (شهرياً)", impact: "Medium", impact_ar: "متوسّط", at: "2026-11-21T13:30:00+00:00", riyadh: "2026-11-21 16:30",
    day: "اليوم", past: false, forecast: "0.3%", previous: "0.2%", what: "يقيس إنفاقَ المستهلك.", above: "يدعم الأسهم.", below: "يضغط الأسهم.", above_lean: "call", below_lean: "put" }] };
const EV_SA = { read_ok: true, market: "sa", company: [{ date: "2026-11-30", title: "أحقّيةُ توزيعٍ نقديّ للربع الثالث", kind: "توزيع" }], events: [
  { id: "s1", title: "Crude Oil Inventories", ar: "مخزوناتُ النفط الخام الأمريكية", impact: "Medium", impact_ar: "متوسّط", at: "2026-11-21T15:30:00+00:00",
    riyadh: "2026-11-21 18:30", day: "اليوم", past: false, forecast: "-1.2M", previous: "2.1M", what: "يقيس فائضَ النفط الأمريكيّ.",
    above: "فائضٌ أكبر يضغط النفطَ فأرامكو والبتروكيماويات.", below: "سحبٌ أكبر يدعم النفطَ والسوقَ السعودي.", above_lean: "neg", below_lean: "pos" }] };
const READ = { ok: true, at: "2026-11-21T17:00:00+00:00", reading: { bias: "صاعد", headline: "السعرُ يصعد فوق VWAP ويقترب من مقاومة فيبوناتشي 0.",
  frames: [{ tf: "يوم", reading: "صاعدٌ بقوّة." }], levels: [{ kind: "مقاومة", price: 765.2, from: "فيبوناتشي 0", note: "قمّةُ الموجة" },
    { kind: "دعم", price: 742.1, from: "VWAP", note: "" }], indicators: [{ name: "Stoch RSI", reading: "في تشبّعٍ شرائيّ — حذرٌ عند المقاومة." }],
  buy: "إن ارتدّ من VWAP مع تشبّعٍ بيعيّ.", sell: "عند المقاومة مع تشبّعٍ شرائيّ.", invalid: "إغلاقٌ تحت الدعم.", risk: "تشبّعٌ شرائيّ.", dropped: 0 } };

const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [], reads = [], econ = [], lives = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d782-init")) return;
    sessionStorage.setItem("d782-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "SPY"); localStorage.setItem("sp_room_list", "g2");
    localStorage.setItem("sp_chart_tf", "1d"); localStorage.setItem("sp_room_layout", "1");
    localStorage.setItem("sp_chart_tf_use", JSON.stringify({ "15m": 5, "1d": 3, "1wk": 2, "1h": 1 }));
    localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: true, stochrsi: true, cvd: false, macd: false, d7m: true }));
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/live/")) { lives.push(Date.now()); const s = decodeURIComponent(p.split("/").pop());
      return r.fulfill(body({ symbol: s, price: 754.37, change: -7.1, change_pct: -0.94, time: new Date().toISOString(), delayed: 0, source: "ياهو",
        session: /^\d{4}/.test(s) ? SES.sa : SES.us, ext: null })); }
    if (p === "/market/sessions") return r.fulfill(body({ us: SES.us, sa: SES.sa }));
    if (p === "/market/econ-events") { econ.push(Object.fromEntries(u.searchParams)); return r.fulfill(body(u.searchParams.get("market") === "sa" ? EV_SA : EV_US)); }
    if (p === "/market/chart-read" && m === "POST") { reads.push(JSON.parse(r.request().postData() || "{}")); return r.fulfill(body(READ)); }
    if (p === "/market/watchlist/groups") return r.fulfill(body(GROUPS));
    if (p === "/market/watchlist" && m === "GET") return r.fulfill(body(ROWS[Number(u.searchParams.get("group_id"))] || []));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const shot = async n => { if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/d782-${n}-${vp.width}.png` }).catch(() => {}); };
  await shot("panels");

  // ١ لوحتا القوّة بدل الشريط
  const fp = await page.evaluate(() => {
    const e = document.querySelector('[data-role="troom-chart"] [data-role="force-panels"]'), r = e?.getBoundingClientRect();
    const t = e?.querySelector('[data-role="fp-trend"]'), l = e?.querySelector('[data-role="fp-liq"]');
    const fonts = e ? [...e.querySelectorAll("*")].filter(x => [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(x => parseFloat(getComputedStyle(x).fontSize)) : [0];
    return { h: r ? Math.round(r.height) : 0, strip: document.querySelectorAll('[data-role="d7m-strip"]').length, ts: t?.getAttribute("data-side"), ls: l?.getAttribute("data-side"),
      tw: t?.textContent || "", lw: l?.textContent || "", n: t?.querySelector('[data-role="fp-strength"]')?.textContent, minF: Math.min(...fonts) };
  });
  say(fp.strip === 0 && fp.ts === "up" && fp.ls === "up" && /قوّة الاتجاه/.test(fp.tw) && /صاعد/.test(fp.tw) && /قوّة السيولة/.test(fp.lw) && /داخلةٌ للصعود/.test(fp.lw)
      && Number(fp.n) > 0 && fp.h > 0 && fp.h <= 76 && fp.minF >= 9.5,
    `${label}: ١ لوحتان فوق الرسم — قوّةُ الاتجاه (صاعد) وقوّةُ السيولة (داخلةٌ للصعود) — بدل الشريط، بارتفاع ${fp.h}px`, `${fp.tw.slice(0, 40)} | ${fp.lw.slice(0, 40)} · خطٌّ ≥ ${fp.minF}px`);

  // ٢ «تحليل الرسم» بجانب «الأحداث» مكانَ شارة السوق، والحالةُ أيقونةٌ بجانب الاسم
  const hd = await page.evaluate(() => {
    const c = document.querySelector('[data-role="troom-chart"]');
    const ee = c?.querySelector('[data-role="ee-btn"]'), cr = c?.querySelector('[data-role="chart-read-btn"]');
    const dot = c?.querySelector('[data-role="troom-sdot"] [data-role="lq-dot"]');
    const rb = cr?.getBoundingClientRect(), re = ee?.getBoundingClientRect();
    return { badge: c?.querySelectorAll('[data-role="lq-session"]').length, dot: dot?.getAttribute("data-state"), after: !!(ee && cr && (ee.compareDocumentPosition(cr) & 4)),
      sameRow: rb && re ? Math.abs(rb.top - re.top) < 6 : false, leftOf: rb && re ? rb.right <= re.left + 2 : false, h: rb ? Math.round(rb.height) : 0, price: !!c?.querySelector('[data-role="lq-price"]') };
  });
  say(hd.badge === 0 && hd.dot === "open" && hd.after && hd.sameRow && hd.leftOf && hd.h >= 32 && hd.price,
    `${label}: ٢ زرُّ «تحليل الرسم» بجانب «الأحداث» مكانَ شارة السوق، وحالةُ السوق أيقونةٌ بجانب الاسم، والسعرُ باقٍ`, JSON.stringify(hd));

  // ٣ الإطاراتُ: أكثرُ ثلاثةٍ استخداماً بمدّتها، والجاري إن لم يكن منها، والعدُّ يُحفظ — و«مختصر · الكل» داخل D7M وحدها
  const tfs = await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] button[data-tf]').evaluateAll(es => es.map(e => e.getAttribute("data-tf")));
  await page.locator('[data-role="troom-chart"] [data-role="pc-tf-more"]').first().click(); await page.waitForTimeout(300);
  await page.locator('[data-role="pc-tf-more-menu"] button[data-tf="4h"]').first().click(); await page.waitForTimeout(1200);
  const cur = await page.locator('[data-role="troom-chart"] [data-role="pc-tf-cur"]').first().textContent().catch(() => "");
  const use = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_chart_tf_use") || "{}"));
  const fibBar = await page.locator('[data-role="pc-fibmode"]').count();
  say(JSON.stringify(tfs) === JSON.stringify(["15m", "1d", "1wk"]) && /4/.test(cur || "") && use["4h"] === 1 && use["15m"] === 5 && fibBar === 0,
    `${label}: ٣ شريطُ الإطارات أكثرُ ثلاثةٍ استخداماً مرتّبةً بمدّتها (ربعُ ساعة · يوم · أسبوع) والباقي في السهم المنبثق، والجاري يظهر ويُعدّ — ولا «مختصر · الكل» في الشريط`,
    `${tfs.join(",")} · الجاري ${cur} · ${JSON.stringify(use)}`);
  await page.locator('[data-role="troom-chart"] [data-role="pc-cfg"]').first().click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="d7m"]').first().click(); await page.waitForTimeout(400);
  const inCfg = await page.evaluate(() => ({ fib: !!document.querySelector('[role="dialog"][aria-label="إعدادات D7M"] [data-role="fib-mode"]'),
    pan: !!document.querySelector('[role="dialog"][aria-label="إعدادات D7M"] [data-role="d7m-panels-toggle"]'),
    old: /المحلّل الذكي|أداة الصفقة|مكان اللوحة/.test(document.querySelector('[role="dialog"][aria-label="إعدادات D7M"]')?.textContent || "") }));
  await page.locator('[role="dialog"][aria-label="إعدادات D7M"] button[aria-label="إغلاق"]').first().click().catch(() => {}); await page.waitForTimeout(300);
  say(inCfg.fib && inCfg.pan && !inCfg.old, `${label}: ٣ب «مختصر · الكل» ومفتاحُ اللوحتين داخل إعدادات D7M — ولا خياراتِ الشريط القديم`, JSON.stringify(inCfg));

  // ٤ «تحليل الرسم»: لقطةُ الرسم (صورتُه وأرقامُه) تُرسل، والقراءةُ تُعرض بخلاصتها ومستوياتها وخطّتها
  await page.locator('[data-role="troom-chart"] [data-role="chart-read-btn"]').first().click(); await page.waitForTimeout(1500);
  await shot("read");
  const rd = reads[0] || {}, f0 = (rd.frames || [])[0] || {};
  const view = await page.evaluate(() => ({ bias: document.querySelector('[data-role="chart-read-bias"]')?.textContent || "",
    lv: document.querySelectorAll('[data-role="chart-read-levels"] li').length, plan: document.querySelector('[data-role="chart-read-plan"]')?.textContent || "" }));
  say(rd.symbol === "SPY" && rd.market === "us" && (rd.frames || []).length === 1 && f0.tf === "4h" && (f0.bars || []).length >= 30 && (f0.levels || []).length > 0
      && (f0.shown || []).includes("d7m") && /^data:image\/jpeg;base64,/.test(f0.img || "") && f0.force?.trend?.word === "صاعد"
      && /صاعد/.test(view.bias) && view.lv === 2 && /متى الشراء/.test(view.plan) && /متى البيع/.test(view.plan),
    `${label}: ٤ «تحليلُ الرسم» يرسل صورةَ الرسم وأرقامَه (${(f0.bars || []).length} شمعة · ${(f0.levels || []).length} مستوى · ${(f0.shown || []).join("،")}) ويعرض الاتجاهَ والمستوياتِ والخطّة`,
    `${view.bias} · ${view.lv}`);
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);

  // ٥ الأحداث: عربيةٌ بلا سطرٍ إنجليزيّ — والسهمُ السعوديُّ بأحداث سوقه وشركته
  await page.locator('[data-role="troom-chart"] [data-role="ee-btn"]').first().click(); await page.waitForTimeout(600);
  const usTxt = await page.locator('[data-role="ee-item"]').allTextContents();
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  await page.locator('[data-role="troom-row"]', { hasText: "أرامكو" }).first().click(); await page.waitForTimeout(1500);
  const btnSa = await page.locator('[data-role="troom-chart"] [data-role="ee-btn"]').first().getAttribute("data-market").catch(() => null);
  await page.locator('[data-role="troom-chart"] [data-role="ee-btn"]').first().click(); await page.waitForTimeout(700);
  await shot("events-sa");
  const sa = await page.evaluate(() => ({ co: document.querySelector('[data-role="ee-company"]')?.textContent || "",
    lean: [...document.querySelectorAll('[data-role="ee-item"] [data-role="ee-lean"]')].map(e => e.getAttribute("data-lean")),
    txt: document.querySelector('[data-role="ee"]')?.textContent || "" }));
  const saReq = econ.find(q => q.market === "sa") || {};
  say(usTxt.length === 1 && !/Retail Sales/.test(usTxt[0]) && /مبيعاتُ التجزئة/.test(usTxt[0]) && /التوقّع/.test(usTxt[0]) && btnSa === "sa" && saReq.symbol === "2222.SR"
      && /أحقّيةُ توزيعٍ/.test(sa.co) && JSON.stringify(sa.lean) === JSON.stringify(["neg", "pos"]) && /سلبيٌّ للسوق السعودي/.test(sa.txt) && /أحداثُ السوق السعودي/.test(sa.txt),
    `${label}: ٥ الأحداثُ بالعربية بلا سطرٍ إنجليزيّ — وللسهم السعوديّ أحداثُ سوقه بأثرها عليه (سلبيّ · إيجابيّ) وأحداثُ الشركة`, `${JSON.stringify(sa.lean)} · ${saReq.symbol}`);
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-row"]', { hasText: "SPY" }).first().click(); await page.waitForTimeout(1200);

  // ٦ السعرُ الحيُّ كلَّ ثانيتين في الجلسة الرسمية
  const n0 = lives.length; await page.waitForTimeout(6600); const dn = lives.length - n0;
  say(dn >= 3, `${label}: ٦ السعرُ الحيُّ يُسأل كلَّ ثانيتين والسوقُ مفتوح (${dn} نداءات في 6.6 ث)`);

  // ٧ «المؤشرات» بأسعارها، وترسُ القوائم يُخفي ويُظهر ويقسم القائمةَ قسمين
  await page.locator('[data-role="troom-tab"]', { hasText: "المؤشرات" }).first().click(); await page.waitForTimeout(900);
  const idx = await page.evaluate(() => [...document.querySelectorAll('[data-role="troom-rows"] [data-role="troom-row"]')].map(r => [r.querySelector(".troom-nm")?.textContent || "",
    !!r.querySelector('[data-role="troom-price"]')]));
  await page.locator('[data-role="troom-gear"]').click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-gear-menu"] [role="checkbox"]', { hasText: "الرئيسية" }).click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-split"] [data-list="g2"]').click(); await page.waitForTimeout(900);
  await shot("list");
  const ls = await page.evaluate(() => ({ tabs: [...document.querySelectorAll('[data-role="troom-tab"]')].map(e => e.textContent),
    sec2: [...document.querySelectorAll('[data-role="troom-rows2"] [data-role="troom-row"]')].length,
    p2: document.querySelectorAll('[data-role="troom-rows2"] [data-role="troom-price"]').length, hid: JSON.parse(localStorage.getItem("sp_room_hidden") || "[]"),
    tgt: Math.min(...[...document.querySelectorAll('[data-role="troom-gear"], [data-role="troom-gear-menu"] [role="checkbox"], [data-role="troom-split"] button')]
      .map(e => Math.min(e.getBoundingClientRect().height, e.getBoundingClientRect().width))) }));
  await page.mouse.click(5, vp.height - 5); await page.waitForTimeout(300);
  say(idx.length === 3 && idx.every(([, p]) => p) && /S&P 500/.test(idx[1][0]) && !ls.tabs.includes("الرئيسية") && ls.tabs.includes("محفظتي") && JSON.stringify(ls.hid) === '["g1"]'
      && ls.sec2 === 3 && ls.p2 === 3 && ls.tgt >= 32,
    `${label}: ٧ «المؤشرات» بأسعارها كغيرها، والترسُ يُخفي «الرئيسية» من الصفّ ويقسم اللوحةَ قسمين («السوق الأمريكي» تحتها بأسعاره) — وأهدافُ اللمس ≥ 32px`,
    `${JSON.stringify(ls.tabs)} · قسمٌ ثانٍ ${ls.sec2} · لمس ${ls.tgt}`);

  // ٨ الشاشاتُ المتعدّدة: أربعٌ لكلٍّ إطارُها، و«تحليلُ الرسم» فوقها يقرأ الأطرَ كلَّها، ثمّ العودةُ لشاشةٍ واحدة
  await page.locator('[data-role="troom-chart"] [data-role="pc-layout"]').first().click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-layout-menu"] [data-layout="4"]').first().click(); await page.waitForTimeout(2500);
  await shot("multi");
  const mv = await page.evaluate(() => ({ panes: [...document.querySelectorAll('[data-role="troom-pane"] [data-role="pro-chart"]')].map(e => e.getAttribute("data-tf")),
    mini: document.querySelectorAll('[data-role="troom-pane"] .fp-mini').length, head: !!document.querySelector('[data-role="troom-mhead"] [data-role="chart-read-btn"]'),
    w: [...document.querySelectorAll('[data-role="troom-pane"]')].map(e => Math.round(e.getBoundingClientRect().width)),
    over: document.scrollingElement.scrollWidth - innerWidth }));
  await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="pc-tfs"] button[data-tf="15m"]').first().click(); await page.waitForTimeout(1000);
  const s1 = await page.evaluate(() => [localStorage.getItem("sp_chart_tf_s1"), document.querySelectorAll('[data-role="troom-pane"] [data-role="pro-chart"]')[1]?.getAttribute("data-tf")]);
  const r0 = reads.length;
  await page.locator('[data-role="troom-mhead"] [data-role="chart-read-btn"]').click(); await page.waitForTimeout(1500);
  const mr = reads[r0] || {};
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-pane"]').first().locator('[data-role="pc-layout"]').click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-layout-menu"] [data-layout="1"]').first().click(); await page.waitForTimeout(1500);
  const back = await page.evaluate(() => ({ panes: document.querySelectorAll('[data-role="troom-pane"]').length, one: document.querySelectorAll('[data-role="troom-chart"] [data-role="pro-chart"]').length,
    lay: localStorage.getItem("sp_room_layout") }));
  const wide = vp.width >= 1024;
  say(mv.panes.length === 4 && JSON.stringify(mv.panes) === JSON.stringify(["4h", "4h", "1h", "15m"]) && mv.mini === 4 && mv.head && mv.over <= 1
      && (wide ? mv.w.every(w => w > 300 && w < 700) : mv.w.every(w => w > 300)) && s1[0] === "15m" && s1[1] === "15m"
      && (mr.frames || []).length === 4 && (mr.frames || []).map(f => f.tf).join(",") === "4h,15m,1h,15m" && back.panes === 0 && back.one === 1 && back.lay === "1",
    `${label}: ٨ أربعُ شاشاتٍ لكلٍّ إطارُها (${mv.panes.join(" · ")}) ولوحتاها المختصرتان، وتبديلُ إطار شاشةٍ يُحفظ لها، و«تحليلُ الرسم» فوقها يقرأ الأطرَ الأربعة معاً — ثمّ شاشةٌ واحدة`,
    `عرض ${mv.w.join(",")} · ${(mr.frames || []).map(f => f.tf).join(",")}`);
  say(errs.length === 0, `${label}: ٩ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
