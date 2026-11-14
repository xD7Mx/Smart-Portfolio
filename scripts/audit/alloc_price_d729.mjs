// ─────────────────────────────────────────────────────────────────────────
// D729 (بأمر المالك 2026-11-14): «أبغى أضيف في القائمة… السعر، وبإمكاني تغييره… يكون أوتوماتيك على آخر سعر إغلاق…
// قبل القيمة في الجدول… لو أحطّ سعر مصرف الراجحي بدل 64 أخليه 60، فتطلع لي النسبة ويطلع لي العدد الصحيح بالضبط».
//
// الحالُ قبله: الجدولُ يحسب الأسهمَ والوزنَ بآخر إغلاقٍ وحده، ولا حقلَ للسعر.
// ١–٦ سلوكيّ: تُستورد ‏`repriceRows` نفسُها التي يستدعيها المكوّن (لا نسخةٌ منها هنا).
// ٧–… في المتصفّح: التطبيقُ الحقيقيّ (‏vite) على الحاسوب والجوال — العمودُ قبل «القيمة»، والكتابةُ تُعيد الأرقام.
//    SHOTS=dir node scripts/audit/alloc_price_d729.mjs   ← لقطاتٌ للمراجعة
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync, mkdtempSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };

const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const out = join(mkdtempSync(join(tmpdir(), "sp-d729-")), "allocMath.mjs");
await build({ entryPoints: [join(FRONT, "src/lib/allocMath.ts")], outfile: out, format: "esm", bundle: false, logLevel: "silent" });
const M = await import(pathToFileURL(out).href);
if (typeof M.repriceRows !== "function") {
  say(false, "١ دالّةُ إعادة التسعير موجودة", "لا ‏repriceRows في allocMath");
  console.log("\nالنتيجة: عطب ✖"); process.exit(1);
}
const { repriceRows, rebalanceRow } = M;

// محفظةٌ صغيرة: الراجحي 100 سهم بـ64، أرامكو 1000 بـ25، ونقدٌ 3,600 → رأسُ المال 35,000
const ROWS = [
  { company_id: 1, symbol: "1120", last_price: 64, quantity: 100, market_value: 6400, current_weight: 18.29, dividend_yield: 4 },
  { company_id: 2, symbol: "2222", last_price: 25, quantity: 1000, market_value: 25000, current_weight: 71.43, dividend_yield: 6 },
];
const INV = 35000;
const near = (a, b, e = 1e-9) => a != null && Math.abs(a - b) < e;

const same = repriceRows(ROWS, {}, INV);
say(same.count === 0 && same.investable === INV && same.rows.every((r, i) => r.current_weight === ROWS[i].current_weight && r.px === ROWS[i].last_price),
    "١ بلا سعرٍ مكتوب: الصفوفُ ورأسُ المال كما جاءت من الخادم حرفاً بحرف — لا يتغيّر رقمٌ لم يُطلب");
const eq = repriceRows(ROWS, { 1: "64" }, INV);
say(eq.count === 0, "٢ وكتابةُ آخر إغلاقٍ نفسِه ليست تعديلاً");

const p = repriceRows(ROWS, { 1: "60" }, INV);
const r1 = p.rows[0], r2 = p.rows[1];
say(p.count === 1 && near(r1.market_value, 6000) && near(p.investable, 34600) && r1.px === 60 && r1.repriced,
    "٣ الراجحي بـ60: قيمتُه 100×60 = 6,000، ورأسُ المال 35,000 − 400 = 34,600", `${r1.market_value} · ${p.investable}`);
say(near(r1.current_weight, 17.34) && near(r2.current_weight, 72.25) && r2.px === 25 && !r2.repriced,
    "٤ والنسبةُ تُعاد للشركات كلّها على رأس المال الجديد (17.34٪ · 72.25٪) — لا للمعدَّلة وحدها",
    `${r1.current_weight} · ${r2.current_weight}`);
say(near(r1.dividend_yield, 4 * 64 / 60) && r2.dividend_yield === 6 && near(r1.market_value * r1.dividend_yield / 100, 6400 * 4 / 100),
    "٥ والعائدُ بالسعر المكتوب: التوزيعُ للسهم لا يتغيّر — فدخلُ المركز نفسُه (256)", `${r1.dividend_yield.toFixed(4)}`);
// العددُ الصحيح: الراجحي هدفُه 25٪ → حاجتُه (25 − 17.34)٪ × 34,600 = 2,649.6 → بـ60 = 44 سهماً (بـ64 كانت 41)
const rb = rebalanceRow({ currentWeight: r1.current_weight, targetWeight: 25, investable: p.investable, lastPrice: r1.px, freshCash: 3600, reinvestPool: 0 });
const rb0 = rebalanceRow({ currentWeight: 18.29, targetWeight: 25, investable: INV, lastPrice: 64, freshCash: 3600, reinvestPool: 0 });
say(rb.side === "buy" && Math.floor(rb.totalAmount / 60) === 44 && Math.floor(rb0.totalAmount / 64) === 36,
    "٦ وعددُ الأسهم من السعر المكتوب: 44 سهماً بـ60 (كانت 36 بـ64 آخرِ إغلاق)",
    `${Math.floor(rb.totalAmount / 60)} · ${Math.floor(rb0.totalAmount / 64)}`);
const bad = repriceRows(ROWS, { 1: "", 2: "0" }, INV);
say(bad.count === 0 && M.priceOverride("abc") == null && M.priceOverride("-3") == null,
    "٦ب والفارغُ والصفرُ والنصُّ ليست سعراً — يبقى آخرُ إغلاق");

// ── في المتصفّح ──
const PORT = 5251;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر فحصُ المتصفّح: غيرُ متاح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const ITEMS = ROWS.map((r, i) => ({ ...r, name: ["مصرف الراجحي", "أرامكو السعودية"][i], target_weight: [25, 60][i], sharia_status: "pure" }));
const ALLOC = { items: ITEMS, reinvestment_pool: 0, fresh_cash: 3600, available_cash: 3600, investable: INV };

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكمَ للمتصفّح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp, theme] of [["الحاسوب", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", r => /\/allocation(\?|$)/.test(r.request().url()) ? r.fulfill(body(ALLOC)) : r.fulfill(body([])));
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe");
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/portfolio`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1800);
  await page.locator("nav button", { hasText: "لوحة التحكم" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(300);
  await page.locator("button", { hasText: "التوزيع النسبي" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const scope = desk ? "table" : '[data-role="alloc-cards"]';
  const inputs = page.locator(`${scope} [data-role="alloc-price"]`);
  const first = await inputs.first().inputValue().catch(() => null);
  if (desk) {
    const heads = await page.evaluate(() => [...document.querySelectorAll("table th")].map(t => t.textContent.trim()));
    const iP = heads.indexOf("السعر"), iV = heads.indexOf("القيمة");
    say(iP >= 0 && iP === iV - 1, `${label}: عمودُ «السعر» قبل «القيمة» مباشرةً`, heads.join(" | "));
  }
  say(first === "64", `${label}: الحقلُ يبدأ بآخر إغلاق (64)`, String(first));
  const cellText = async () => page.evaluate((desk) => {
    if (desk) { const tr = document.querySelector("table tbody tr"); return tr ? [...tr.children].map(td => td.textContent.trim()) : []; }
    const c = document.querySelector('[data-role="alloc-card"]'); return c ? [...c.querySelectorAll('[data-role="cell"]')].map(x => x.textContent.trim()) : [];
  }, desk);
  const before = await cellText();
  // الكتابةُ حرفاً حرفاً كالمالك — والحقلُ يحفظ تركيزَه بين الحرفين
  await inputs.first().click();
  await inputs.first().press("Control+a");
  await inputs.first().pressSequentially("60", { delay: 60 });
  const focused = await page.evaluate(() => document.activeElement?.getAttribute("data-role"));
  await inputs.first().press("Enter");
  await page.waitForTimeout(400);
  const after = await cellText();
  const val = await inputs.first().inputValue();
  const on = await inputs.first().evaluate(e => e.classList.contains("alloc-px-on"));
  say(focused === "alloc-price" && val === "60" && on, `${label}: «60» تُكتب حرفاً حرفاً بلا فقد تركيز، ويُرى الحقلُ معدَّلاً`, `${focused} · ${val} · ${on}`);
  const joined = after.join(" ¦ ");
  say(desk ? (after[2] === "6,000" && after[3].includes("17.34") && after[6] === "44")
           : /44\s*سهم/.test(after[1] || ""),
      `${label}: القيمةُ 6,000 والنسبةُ 17.34٪ والأسهمُ 44 — من السعر المكتوب`, joined);
  const tag = page.locator('[data-role="alloc-price-tag"]');
  say(await tag.count() === 1 && /\(1\)/.test(await tag.textContent()), `${label}: وسمُ «بسعرٍ مكتوب (1)» يظهر`);
  const m = await page.evaluate((scope) => {
    const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const els = [...document.querySelectorAll(`${scope} [data-role="alloc-price"], ${scope} [data-role="alloc-price-reset"], [data-role="alloc-price-tag"]`)];
    return { over: sw - W, minT: Math.min(...els.map(e => e.getBoundingClientRect().height)),
             ar: /[٠-٩۰-۹]/.test(els.map(e => e.value || e.textContent).join("")) };
  }, scope);
  say(m.over <= 1 && m.minT >= 32 && !m.ar, `${label}: لا فيضَ أفقيّ، وهدفُ اللمس ≥ 32px، والأرقامُ لاتينية`, `${m.over}px · ${Math.round(m.minT)}px`);
  if (SHOTS) { const el = await page.$(desk ? "table" : '[data-role="alloc-cards"]'); if (el) await el.screenshot({ path: join(SHOTS, `alloc_px_${vp.width}_${theme}.png`) }); }
  // العودة: الفارغُ يعيد آخرَ إغلاق، والوسمُ يعيد الكلّ
  await inputs.first().fill("");
  await inputs.first().press("Enter");
  await page.waitForTimeout(300);
  const back1 = await inputs.first().inputValue();
  await inputs.nth(1).fill("24");
  await inputs.nth(1).press("Enter");
  await page.waitForTimeout(300);
  await tag.click().catch(() => {});
  await page.waitForTimeout(300);
  const back2 = await inputs.nth(1).inputValue();
  const restored = await cellText();
  say(back1 === "64" && back2 === "25" && await tag.count() === 0 && restored.join("|") === before.join("|"),
      `${label}: الحقلُ الفارغ يعود إلى آخر إغلاق، والوسمُ يعيد الكلّ — والأرقامُ كما كانت`, `${back1} · ${back2}`);
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
