// ─────────────────────────────────────────────────────────────────────────
// D698 (بأمر المالك 2026-10-13): «أضف للتقرير رسمَ شموعٍ للفترة بشكل تصميم التطبيق كما تفعل تقاريرُ البنوك».
// يُفتح التطبيقُ الحقيقيّ (‏vite) ويُفتح تقريرُ ربعٍ من ورقة السهم، ويُقاس من الـDOM: شموعٌ أسبوعيةٌ بلون الصعود والهبوط، ونطاقُ الفترة
// مظلَّلٌ واسمُها عليه، وآخرُ إغلاقٍ خطٌّ وقيمة، وأشهرٌ بالعربية وأسعارٌ لاتينية، والخطُّ ≥ 9.5px؛ وبلا شموعٍ لا رسمَ مختلَق.
//    SHOTS=dir node scripts/audit/ui_d698.mjs   ← لقطةٌ للمراجعة
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5252;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

// اثنان وخمسون أسبوعاً تنتهي 2026-10-04 — صعودٌ وهبوطٌ متناوبان
const pts = [];
let px = 24;
for (let i = 0; i < 52; i++) {
  const d = new Date(Date.UTC(2025, 9, 12) + i * 7 * 864e5).toISOString().slice(0, 10);
  const o = px, c = +(px + (i % 3 === 0 ? -0.6 : 0.45)).toFixed(2);
  pts.push({ d, o, h: +(Math.max(o, c) + 0.3).toFixed(2), l: +(Math.min(o, c) - 0.3).toFixed(2), c });
  px = c;
}
const REPORT = (withCandles) => ({
  symbol: "2222", name: "أرامكو السعودية", latest: true, kind: "quarter",
  header: { recommendation: "انتظار", price: px, target_12m: 26.1, change: 4.2, dividend_yield: 4.1, total_return: 8.3,
            fair_value: 25.4, fair_value_conf: "مرتفعة" },
  table: { as_of: "2026-06-30", prior_year: "2025-06-30", prev_quarter: "2026-03-31", rows: [] },
  market: {}, performance: {}, research: null, insights: [],
  candles: withCandles ? { interval: "أسبوعي", points: pts, from: "2026-03-31", to: "2026-06-30" } : null,
});

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const withCandles of [true, false]) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", r => {
    const u = r.request().url();
    if (/\/market\/quarter-reports\//.test(u)) return r.fulfill(body({ quarters: ["2026-06-30"], years: [] }));
    if (/\/market\/quarter-report\//.test(u)) return r.fulfill(body(REPORT(withCandles)));
    if (/\/market\/watchlist\/groups/.test(u)) return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }]));
    if (/\/market\/watchlist(\?|$)/.test(u)) return r.fulfill(body([{ symbol: "2222", name: "أرامكو السعودية", price: px, change_pct: 0.4 }]));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2200);
  await page.locator('[data-sort-key="2222"]').first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator('[role="tab"]', { hasText: "التقارير" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1200);
  // زرُّ «عرض» في قائمة تقارير الشركة نفسِها (في الورقة أزرارُ «عرض» أخرى)
  const viewBtn = page.locator('button[title="عرض"]');
  if (await viewBtn.count()) await viewBtn.first().click({ timeout: 5000 }).catch(() => {});
  else await page.locator(".card", { hasText: "تقارير الشركة" }).locator("button", { hasText: "عرض" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const m = await page.evaluate(() => {
    const svg = document.querySelector('[data-role="report-candles"]');
    if (!svg) return { svg: false };
    const rects = [...svg.querySelectorAll("rect")];
    const fills = rects.map(r => r.getAttribute("fill"));
    const texts = [...svg.querySelectorAll("text")].map(t => ({ s: t.textContent, f: parseFloat(getComputedStyle(t).fontSize) }));
    return {
      svg: true, n: rects.length, fills: [...new Set(fills)], texts: texts.map(t => t.s),
      minFont: Math.min(...texts.map(t => t.f)), band: rects.some(r => r.getAttribute("opacity") === "0.12"),
      dashed: !!svg.querySelector('line[stroke-dasharray]'), w: svg.getBoundingClientRect().width,
    };
  });
  if (withCandles) {
    say(m.svg && m.n >= 52, "١ التقريرُ يحمل رسمَ الشموع: شمعةٌ لكلّ أسبوع", `${m.n ?? 0} مستطيلاً`);
    say(m.svg && m.fills.length >= 3, "٢ والشموعُ بلونَي الصعود والهبوط من ورق التقرير", (m.fills || []).join(" · "));
    say(m.svg && m.band && m.texts.includes("الربع الثاني 2026"), "٣ ونطاقُ الفترة مظلَّلٌ واسمُها عليه");
    say(m.svg && m.dashed && m.texts.includes(px.toFixed(2)), "٤ وآخرُ إغلاقٍ خطٌّ متقطّعٌ وقيمتُه", px.toFixed(2));
    say(m.svg && m.texts.some(s => /^(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)$/.test(s))
        && !m.texts.some(s => /[٠-٩]/.test(s)) && m.minFont >= 9.5,
        "٥ والأشهرُ بالعربية والأسعارُ لاتينية، وأصغرُ خطٍّ ≥ 9.5px", `${m.minFont}px`);
    if (SHOTS) {
      const el = await page.$('[data-role="report-candles"]');
      if (el) await el.screenshot({ path: join(SHOTS, "report_candles.png") });
    }
  } else {
    say(!m.svg, "٦ وبلا شموعٍ من المصدر لا رسمَ مختلَق — يُحذف القسمُ كلُّه");
  }
  say(errs.length === 0, `${withCandles ? "مع" : "بلا"} شموع: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
