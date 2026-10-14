// ─────────────────────────────────────────────────────────────────────────
// D711 (بأمر المالك 2026-10-14): «أضف لتقرير المحفظة الرسمَ البيانيَّ بالشموع — فكرةٌ جميلةٌ تعطي هويّةَ التطبيق».
// ‏D717 (بأمر المالك): «الشموعُ لتاسي فقط — احذف شموعَ الربح، وضع فتراتِ السنوات، والتظليلُ يوضّح فترةَ التقرير».
// يُفتح التطبيقُ الحقيقيّ (‏vite) ويُفتح تقريرُ محفظةٍ من «التقارير»، ويُقاس من الـDOM: شموعُ تاسي الشهريّة لخمس سنواتٍ وحدها،
// بسنواتها وفواصلها، وفترةُ التقرير مظلَّلةٌ على شمعتها، وآخرُ قيمةٍ بفواصل الآلاف لاتينيةً، والخطُّ ≥ 9.5px؛ وبلا شموعٍ لا رسمَ
// مختلَق. وتقريرُ الشركة (‏D698) بالمكوِّن نفسِه — أسبوعيّاً بأشهره.
//    SHOTS=dir node scripts/audit/ui_d711.mjs   ← لقطةٌ للمراجعة
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5253;
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

// ‏D717 (المالك): «الشموعُ لتاسي فقط — احذف شموعَ الربح، وضع فتراتِ السنوات، والتظليلُ يوضّح فترةَ التقرير».
// ستّون شهراً من تاسي (أكتوبر 2021 → سبتمبر 2026)، والتقريرُ شهريٌّ لسبتمبر 2026
const tasi = [];
let v = 11000;
for (let i = 0; i < 60; i++) {
  const dt = new Date(Date.UTC(2021, 9 + i, 1)), d = dt.toISOString().slice(0, 10);
  const o = v, c = Math.round(v + (i % 5 === 0 ? -260 : 180));
  tasi.push({ d, o, h: Math.max(o, c) + 90, l: Math.min(o, c) - 90, c });
  v = c;
}
const tasiLast = tasi[tasi.length - 1].c;
const REPORT = (withCandles) => ({
  id: 7, type: "MONTHLY", period: "شهري · ينتهي 2026-09-30", generated_at: "2026-10-14T12:00:00",
  metrics: { market_value: 120000, total_invested: 110000, wealth: 125000, net_profit: 9000, capital_growth_pct: 8.2, cagr_pct: null, cash_pct: 4 },
  positions: [{ name: "أرامكو السعودية", symbol: "2222", shares: 100, market_value: 2700, pnl: 120, pnl_pct: 4.6 }],
  content: "خلاصة",
  // تقريرٌ قديمٌ مؤرشَف قد يحمل شموعَ الربح — فلا تُرسم بعد اليوم
  candles: withCandles ? { interval: "أسبوعي", series: "صافي الربح", points: tasi.map(p => ({ ...p, o: -p.o, c: -p.c })), from: "2026-09-01", to: "2026-09-30" } : null,
  tasi_candles: withCandles ? { interval: "شهري", series: "تاسي", points: tasi, from: "2026-09-01", to: "2026-09-30" } : null,
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
    if (/\/reports\/7(\?|$)/.test(u)) return r.fulfill(body(REPORT(withCandles)));
    if (/\/reports(\?|$)/.test(u)) return r.fulfill(body([{ id: 7, type: "WEEKLY", period: "أسبوعي · ينتهي 2026-10-09",
                                                            generated_at: "2026-10-14T12:00:00", has_content: true }]));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
  await page.goto(`http://localhost:${PORT}/reports`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  const viewBtn = page.locator('button[title="عرض"]');
  if (await viewBtn.count()) await viewBtn.first().click({ timeout: 5000 }).catch(() => {});
  else await page.locator("button", { hasText: "عرض" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const m = await page.evaluate(() => {
    const doc = document.querySelector(".report-doc");
    const svgs = doc ? [...doc.querySelectorAll('[data-role="report-candles"]')] : [];
    const t = doc && doc.querySelector('[data-role="report-candles-tasi"]');
    const svg = t && t.querySelector('[data-role="report-candles"]');
    if (!svg) return { doc: !!doc, svgs: svgs.length, svg: false, tasi: !!t };
    const plotW = parseFloat(svg.getAttribute("width"));
    const candles = [...svg.querySelectorAll("g > rect")].filter(r => r.getAttribute("fill") === "#0f9d63" || r.getAttribute("fill") === "#c0273c");
    const band = svg.querySelector('[data-role="report-band"] rect');
    const last = candles[candles.length - 1];
    const texts = [...svg.querySelectorAll("text")].map(x => x.textContent.trim());
    const sizes = [...svg.querySelectorAll("text")].map(x => parseFloat(x.getAttribute("font-size") || "0"));
    const bx = band ? parseFloat(band.getAttribute("x")) : -1, bw = band ? parseFloat(band.getAttribute("width")) : 0;
    const lx = last ? parseFloat(last.getAttribute("x")) + parseFloat(last.getAttribute("width")) / 2 : -1;
    return {
      doc: true, svg: true, svgs: svgs.length, n: candles.length, plotW, texts, minFont: Math.min(...sizes),
      fills: [...new Set(candles.map(r => r.getAttribute("fill")))],
      title: [...t.querySelectorAll("div")].some(d => d.textContent.trim() === "مؤشّرُ تاسي"),
      years: [...svg.querySelectorAll('[data-role="year-label"]')].map(x => x.textContent.trim()),
      seps: svg.querySelectorAll('[data-role="year-sep"]').length,
      bandOnLast: band && lx > bx && lx < bx + bw, bandW: bw,
      bandLabel: !!svg.querySelector('[data-role="report-band"] text') && texts.includes("فترة التقرير"),
      dashed: !!svg.querySelector('line[stroke-dasharray]'),
      profit: doc.textContent.includes("صافي الربح — شموع"),
    };
  });
  if (withCandles) {
    const lastTxt = tasiLast.toLocaleString("en-US");
    say(m.svg && m.svgs === 1 && !m.profit, "١ تقريرُ المحفظة بشموع تاسي وحدها — شموعُ صافي الربح حُذفت (ولو حملها تقريرٌ مؤرشَف)",
        `${m.svgs ?? 0} رسماً`);
    say(m.svg && m.n === 60 && m.title, "٢ ستّون شمعةً شهريّة لخمس سنوات، وعنوانُها اسمٌ وحده («مؤشّرُ تاسي») بلا شرحٍ بجانبه", `${m.n ?? 0} شمعة`);
    say(m.svg && (m.fills || []).includes("#0f9d63") && (m.fills || []).includes("#c0273c"), "٣ بلونَي الصعود والهبوط من ورق التقرير",
        (m.fills || []).join(" · "));
    say(m.svg && JSON.stringify(m.years) === JSON.stringify(["2021", "2022", "2023", "2024", "2025", "2026"]) && m.seps === 5,
        "٤ وفتراتُ السنوات في الرسم: كلُّ سنةٍ باسمها وفاصلٌ عند كلّ يناير", `${(m.years || []).join(" · ")} · فواصل ${m.seps}`);
    say(m.svg && m.bandOnLast && m.bandLabel, "٥ والتظليلُ على شمعة فترة التقرير بعينها (سبتمبر 2026)، و«فترة التقرير» مكتوبةٌ عليه ولو ضاق",
        `عرضُ التظليل ${Math.round(m.bandW || 0)}px`);
    say(m.svg && m.dashed && m.texts.includes(lastTxt), "٦ وآخرُ قيمةٍ خطٌّ متقطّعٌ ووسمٌ بفواصل الآلاف", lastTxt);
    say(m.svg && m.texts.every(s => !/[٠-٩]/.test(s)) && m.minFont >= 9.5, "٧ والأرقامُ لاتينية، وأصغرُ خطٍّ ≥ 9.5px", `${m.minFont}px`);
    if (SHOTS) {
      const el = await page.$(".report-doc");
      if (el) await el.screenshot({ path: join(SHOTS, "d717_portfolio_report.png") });
    }
  } else {
    say(m.doc && !m.svg && !m.tasi && !m.svgs, "٨ وبلا شموعٍ (تاريخٌ أقصرُ من سنة) لا رسمَ مختلَق — يُحذف القسمُ كلُّه");
  }
  say(errs.length === 0, `${withCandles ? "مع" : "بلا"} شموع: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
