// ─────────────────────────────────────────────────────────────────────────
// لجنةُ التصميم بإشراف «نِصاب» تتصفّح التطبيقَ بعين الجوال (بأمر المالك).
//
// «أريد لجنةَ التصميم أن تتصفّح التطبيق من وضع الجوال وترى القبحَ البصريَّ
// بعينها». فيُفتح كلُّ شاشةٍ على 390×844 ويُقاس ما رآه المالك:
//   · عنصرٌ يتجاوز عرضَ الشاشة فتنزلق الصفحةُ أفقياً (تبويباتُ السوق).
//   · رسمٌ ليس في المنتصف (صفحةُ السهم).
//   · بطاقةُ رسمٍ تأسر اللمسةَ العموديّة فتتجمّد الصفحة (touch-action).
// وتُحفظ لقطةٌ لكلّ شاشةٍ في SP_SHOTS إن ضُبط.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5227;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const SHOTS = process.env.SP_SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

const BARS = Array.from({ length: 130 }, (_, i) => {
  const d = new Date(Date.UTC(2026, 2, 1) + i * 86400000);
  const c = 30 + Math.sin(i / 9) * 2 + i * 0.02;
  return { date: d.toISOString().slice(0, 10), time: 0, open: c - .2, high: c + .4, low: c - .5, close: c, volume: 1e6 };
});
const ANALYSIS = { symbol: "4030", name: "البحري", price: 35.54, change_pct: 0.34,
  fair_value: 38.2, fair_value_upside_pct: 7.5,
  fundamentals: { market_cap: 3.4e10, eps: 2.63, pe_ratio: 13.5, week52_high: 41, week52_low: 27, book_value: 11.66, dividend_yield: 3.1 },
  technical: { rsi: 52, trend: "محايد", support: 34, resistance: 37 },
  governance: { score: 79 }, score: 79, decision: { label: "احتفاظ" }, evaluable: true };
const HOLD = [{ id: 17, company_id: 17, symbol: "4030",
  company: { id: 17, symbol: "4030", company_name: "الشركة الوطنية السعودية للنقل البحري", name_ar: "البحري" },
  quantity: 0, market_value: 0, last_price: 35.54, average_price: 0 }];
const SCREEN = [{ symbol: "4030", name: "البحري", sector: "النقل", price: 35.54, change_pct: .34, rsi: 52,
  dividend_yield: 3.1, finance_score: 79, fair_value: 38.2, fair_value_upside_pct: 7.5, high_52w: 41, low_52w: 27 }];
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  await new Promise(r => setTimeout(r, 500));
  try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { }
}
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }

const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
const page = await ctx.newPage();
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (/\/market\/history\//.test(u)) return r.fulfill(body(BARS));
  if (/\/market\/company\//.test(u) || /\/ai\/stock-opinion\//.test(u)) return r.fulfill(body(ANALYSIS));
  if (/\/companies\/\d+(\?|$)/.test(u)) return r.fulfill(body(HOLD[0].company));
  if (/\/holdings\/\d+(\?|$)/.test(u)) return r.fulfill(body(HOLD[0]));
  if (/\/holdings(\?|$)/.test(u)) return r.fulfill(body(HOLD));
  if (/\/market\/screener(\?|$)/.test(u)) return r.fulfill(body({ rows: SCREEN, state: "ready" }));
  return r.fulfill(body([]));
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });

const STOPS = [["السوق", "/market"], ["الرسم البياني", "/chart"], ["صفحة السهم", "/portfolio/17"],
               ["المحفظة", "/portfolio"], ["الإشعارات", "/notifications"]];
for (const [name, path] of STOPS) {
  await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2200);
  const m = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const over = [];
    for (const el of document.querySelectorAll("body *")) {
      const r = el.getBoundingClientRect();
      if (r.width < 4 || r.height < 4) continue;
      // ما في حاويةٍ تمرّر أفقياً عمداً لا يُحسب — ذاك تصميم.
      let p = el.parentElement, scroller = false;
      while (p && !p.classList.contains("app-main")) { const s = getComputedStyle(p); if (/(auto|scroll)/.test(s.overflowX) && p.scrollWidth > p.clientWidth + 1) { scroller = true; break; } p = p.parentElement; }
      if (scroller) continue;
      if (r.right > W + 1 || r.left < -1) over.push(`${el.tagName.toLowerCase()}.${String(el.className).split(" ")[0]} [${Math.round(r.left)},${Math.round(r.right)}]`);
    }
    const lock = [...document.querySelectorAll(".chart-lock, canvas")].filter(e => getComputedStyle(e).touchAction === "none").length;
    const cv = [...document.querySelectorAll(".chart-lock, .recharts-responsive-container")].map(e => {
      const r = e.getBoundingClientRect(); return Math.round(Math.abs(r.left - (W - r.right)));
    });
    const mainEl = document.querySelector(".app-main");
    return { W, sw: Math.max(document.documentElement.scrollWidth, mainEl ? mainEl.scrollWidth : 0), over: over.slice(0, 4), lock, cv };
  });
  say(m.sw <= m.W + 1, `«${name}» لا تنزلق أفقياً على الجوال`, `عرضُ المحتوى ${m.sw} والشاشة ${m.W}`);
  say(m.over.length === 0, `«${name}» لا عنصرَ يتجاوز حدَّ الشاشة`, m.over.join(" · "));
  say(m.lock === 0, `«${name}» لا رسمَ يأسر التمريرَ العموديّ`, m.lock ? `${m.lock} عنصراً touch-action:none` : "");
  const off = m.cv.filter(x => x > 24);
  say(off.length === 0, `«${name}» الرسومُ في المنتصف`, off.length ? `انحرافُ الهامشين ${off.join(",")}px` : "");
  if (SHOTS) {
    await page.screenshot({ path: join(SHOTS, `${path.replace(/\W+/g, "_") || "root"}.png`), fullPage: false });
    const cards = await page.$$(".recharts-responsive-container, .chart-lock");
    for (let i = 0; i < Math.min(cards.length, 2); i++) {
      await cards[i].scrollIntoViewIfNeeded().catch(() => {});
      await page.screenshot({ path: join(SHOTS, `${path.replace(/\W+/g, "_")}_chart${i}.png`) });
    }
  }
}
await browser.close(); stop();
console.log((fail ? "FAIL" : "PASS") + " لجنةُ التصميم — عينُ الجوال");
process.exit(fail);
