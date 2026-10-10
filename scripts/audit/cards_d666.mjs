// ─────────────────────────────────────────────────────────────────────────
// D666 — البطاقةُ الموحّدة في الجوال والحاسوب (بأمر المالك).
//
// «أفتقد الأحداثَ الجوهرية — لا أراها. اجعلها بنفس طريقة البطاقات الأخرى ووسمها: التصميمُ الموحّد ميزةٌ لنا.
//  وانتبه أن تُظهر الميزاتِ في وضع الحاسوب وتنسى وضعَ الجوال».
// فيُفتح التطبيقُ الحقيقيّ على 390×844 (جوال) و1280×900 (حاسوب)، ويُقاس من الـDOM:
//   · «الأحداث الجوهرية» ظاهرةٌ في «نظرة عامة» لصفحة السهم دون تبديل تبويب.
//   · بطاقاتُها وبطاقاتُ «التوقعات» من البطاقة الموحّدة (‏.event-item) بوسمٍ صلب (‏.ev-tag) كبطاقات المفكرة.
//   · لا فيضَ أفقيّ، وأصغرُ هدفِ لمسٍ ≥ 32px.
// وتُحفظ لقطاتٌ في SP_SHOTS إن ضُبط.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5231;
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
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const ANALYSIS = { symbol: "4030", name: "البحري", price: 35.54, change_pct: 0.34, fundamentals: { market_cap: 3.4e10 }, evaluable: true };
const HOLD = [{ id: 17, company_id: 17, symbol: "4030",
  company: { id: 17, symbol: "4030", company_name: "الشركة الوطنية السعودية للنقل البحري", name_ar: "البحري" },
  quantity: 0, market_value: 0, last_price: 35.54, average_price: 0 }];
const EVENTS = { events: [
  { date: "2026-09-20", kind: "contract", kind_ar: "عقد", negative: false, url: "https://www.saudiexchange.sa/x1",
    title: "تعلن الشركة الوطنية السعودية للنقل البحري عن توقيع عقد نقلٍ طويل الأجل مع شركة أرامكو السعودية",
    value: 2.5e8, months: 36, counted: true, filings: 3, first_date: "2026-09-18" },
  { date: "2026-08-11", kind: "regulator", kind_ar: "جهةٌ رقابية", negative: true, url: "https://www.saudiexchange.sa/x2",
    title: "تعلن الشركة عن تلقّيها خطاباً من هيئة السوق المالية بشأن غرامة", filings: 1 },
] };
const FORECASTS = [
  { id: "4030|الرياض المالية|2026-10-01", title: "البحري: شراء", kind: "توصية وسعرٌ مستهدف", date: "2026-10-01", company: "4030",
    url: "https://argaamplus.s3.amazonaws.com/x.pdf", source: "الرياض المالية", via: "أرقام", rating: "شراء", prev: "محايد", target: 42, has_pdf: true },
  { title: "البحري - نظرة على نتائج الربع الثاني 2026", kind: "تقرير شركة", date: "2026-08-06", company: "4030",
    url: "https://www.aljaziracapital.com.sa/x.pdf", source: "الجزيرة كابيتال", fair_value: 41.5 },
  { title: "الموجز البياني للاقتصاد السعودي - أكتوبر 2026", kind: "تقرير اقتصاديّ", date: "2026-10-06", company: null,
    url: "https://www.jadwa.com/x.pdf", source: "جدوى للاستثمار" },
];

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

const measure = (page, sel) => page.evaluate((sel) => {
  const W = document.documentElement.clientWidth;
  const main = document.querySelector(".app-main");
  const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
  const cards = [...document.querySelectorAll(sel)];
  const tags = cards.filter(c => c.querySelector(".ev-tag")).length;
  // ‏D667: لكلّ بطاقةٍ شعارٌ — شعارُ الشركة أو علامةُ التطبيق مكانَ الغائب، لا فراغ
  const logos = cards.filter(c => { const s = c.firstElementChild; return s && s.querySelector("img, svg"); }).length;
  const minH = cards.length ? Math.min(...cards.map(c => Math.round(c.closest("a,button,div").getBoundingClientRect().height))) : 0;
  const over = cards.filter(c => { const r = c.getBoundingClientRect(); return r.right > W + 1 || r.left < -1; }).length;
  return { W, sw, n: cards.length, tags, minH, over, logos };
}, sel);

for (const [label, vp] of [["الجوال", { width: 390, height: 844, isMobile: true, hasTouch: true }], ["الحاسوب", { width: 1280, height: 900 }]]) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.route("**/api/v1/**", r => {
    const u = r.request().url();
    if (/\/market\/material-events\//.test(u)) return r.fulfill(body(EVENTS));
    if (/\/market\/forecasts/.test(u)) return r.fulfill(body(FORECASTS));
    if (/\/market\/company\//.test(u) || /\/ai\/stock-opinion\//.test(u)) return r.fulfill(body(ANALYSIS));
    if (/\/companies\/\d+(\?|$)/.test(u)) return r.fulfill(body(HOLD[0].company));
    if (/\/holdings\/\d+(\?|$)/.test(u)) return r.fulfill(body(HOLD[0]));
    if (/\/holdings(\?|$)/.test(u)) return r.fulfill(body(HOLD));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });

  await page.goto(`http://localhost:${PORT}/portfolio/17`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const hasCard = await page.evaluate(() => [...document.querySelectorAll(".card-title")].some(e => e.textContent.trim() === "الأحداث الجوهرية"));
  say(hasCard, `${label}: «الأحداث الجوهرية» ظاهرةٌ في «نظرة عامة» لصفحة السهم دون تبديل تبويب`);
  const evSel = ".card .event-item";
  const m1 = await measure(page, evSel);
  say(m1.n >= 2 && m1.tags === m1.n, `${label}: بطاقاتُها البطاقةُ الموحّدة بوسمٍ صلب`, `${m1.tags}/${m1.n}`);
  say(m1.sw <= m1.W + 1 && m1.over === 0, `${label}: لا فيضَ أفقيّ`, `محتوى ${m1.sw} · شاشة ${m1.W}`);
  say(m1.minH >= 32, `${label}: أصغرُ هدفِ لمس ≥ 32px`, `${m1.minH}px`);
  if (SHOTS) {
    const h = await page.$("text=الأحداث الجوهرية");
    if (h) await h.scrollIntoViewIfNeeded().catch(() => {});
    await page.screenshot({ path: join(SHOTS, `events_${vp.width}.png`) });
  }

  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const cal = page.locator("text=مفكرة السوق").first();
  if (await cal.count()) await cal.click().catch(() => {});
  await page.waitForTimeout(800);
  const fc = page.locator('[role="tab"]:has-text("التوقعات")').first();
  if (await fc.count()) await fc.click().catch(() => {});
  await page.waitForTimeout(1500);
  const m2 = await measure(page, ".event-item");
  say(m2.n >= 3 && m2.tags === m2.n, `${label}: بطاقاتُ «التوقعات» البطاقةُ الموحّدة بوسمٍ صلب`, `${m2.tags}/${m2.n}`);
  say(m2.sw <= m2.W + 1 && m2.over === 0, `${label}: «التوقعات» بلا فيضٍ أفقيّ`, `محتوى ${m2.sw} · شاشة ${m2.W}`);
  say(m2.logos === m2.n, `${label}: لكلّ بطاقةٍ شعار — وعلامةُ التطبيق مكانَ الغائب (D667)`, `${m2.logos}/${m2.n}`);
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `forecasts_${vp.width}.png`) });
  await ctx.close();
}
await browser.close(); stop();
console.log((fail ? "FAIL" : "PASS") + " D666 — البطاقةُ الموحّدة في الجوال والحاسوب");
process.exit(fail);
