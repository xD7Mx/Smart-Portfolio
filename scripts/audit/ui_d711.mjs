// ─────────────────────────────────────────────────────────────────────────
// D711 (بأمر المالك 2026-10-14): «أضف لتقرير المحفظة الرسمَ البيانيَّ بالشموع — فكرةٌ جميلةٌ تعطي هويّةَ التطبيق».
// يُفتح التطبيقُ الحقيقيّ (‏vite) ويُفتح تقريرُ محفظةٍ من «التقارير»، ويُقاس من الـDOM: شموعُ صافي الربح الأسبوعية بلونَي الصعود
// والهبوط، وفترةُ التقرير مظلَّلة، والصفرُ خطٌّ حين تعبره السلسلة، وآخرُ قيمةٍ بفواصل الآلاف لاتينيةً، وأشهرٌ بالعربية، والخطُّ ≥ 9.5px؛
// وبلا شموعٍ لا رسمَ مختلَق. وتقريرُ الشركة (‏D698) بالرسم نفسِه — مكوِّنٌ واحدٌ لورقةٍ واحدة.
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

// اثنان وخمسون أسبوعاً من صافي الربح: يبدأ خاسراً ويعبر الصفر ويصعد بتذبذب
const pts = [];
let v = -1800;
for (let i = 0; i < 52; i++) {
  const d = new Date(Date.UTC(2025, 9, 12) + i * 7 * 864e5).toISOString().slice(0, 10);
  const o = v, c = Math.round(v + (i % 4 === 0 ? -260 : 330));
  pts.push({ d, o, h: Math.max(o, c) + 120, l: Math.min(o, c) - 120, c });
  v = c;
}
const last = pts[pts.length - 1].c;
// وتاسي في الأسابيع نفسِها (اقتراحُ المالك: الجزءُ الثاني يلي الأوّل)
const tasi = pts.map((p, i) => { const o = 11000 + i * 9, c = o + (i % 5 === 0 ? -40 : 30); return { d: p.d, o, h: Math.max(o, c) + 25, l: Math.min(o, c) - 25, c }; });
const tasiLast = tasi[tasi.length - 1].c;
const REPORT = (withCandles) => ({
  id: 7, type: "WEEKLY", period: "أسبوعي · ينتهي 2026-10-09", generated_at: "2026-10-14T12:00:00",
  metrics: { market_value: 120000, total_invested: 110000, wealth: 125000, net_profit: last, capital_growth_pct: 8.2, cagr_pct: null, cash_pct: 4 },
  positions: [{ name: "أرامكو السعودية", symbol: "2222", shares: 100, market_value: 2700, pnl: 120, pnl_pct: 4.6 }],
  content: "خلاصة",
  candles: withCandles ? { interval: "أسبوعي", series: "صافي الربح", points: pts, from: "2026-10-03", to: "2026-10-09" } : null,
  tasi_candles: withCandles ? { interval: "أسبوعي", series: "تاسي", points: tasi, from: "2026-10-03", to: "2026-10-09" } : null,
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
    const svg = doc && doc.querySelector('[data-role="report-candles"]');
    if (!svg) return { doc: !!doc, svg: false, tasi: doc && doc.querySelector('[data-role="report-candles-tasi"]') ? {} : null };
    const rects = [...svg.querySelectorAll("rect")];
    const texts = [...svg.querySelectorAll("text")].map(t => t.textContent.trim());
    const sizes = [...svg.querySelectorAll("text")].map(t => parseFloat(t.getAttribute("font-size") || "0"));
    return {
      doc: true, svg: true, n: rects.length, fills: [...new Set(rects.map(r => r.getAttribute("fill")))],
      band: rects.some(r => r.getAttribute("opacity") === "0.12"), zero: !!svg.querySelector('[data-role="candles-zero"]'),
      dashed: !!svg.querySelector('line[stroke-dasharray]'), texts, minFont: Math.min(...sizes),
      title: doc.textContent.includes("حركةُ صافي الربح — شموعٌ أسبوعيّة لاثني عشر شهراً"),
      svgs: doc.querySelectorAll('[data-role="report-candles"]').length,
      tasi: (() => { const t = doc.querySelector('[data-role="report-candles-tasi"]'); if (!t) return null;
        const sv = t.querySelector('[data-role="report-candles"]');
        return { title: t.textContent.includes("مؤشّرُ تاسي — الأسابيعُ نفسُها"), n: sv ? sv.querySelectorAll("rect").length : 0,
                 texts: sv ? [...sv.querySelectorAll("text")].map(x => x.textContent.trim()) : [],
                 after: !!(t.compareDocumentPosition && svg.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING) }; })(),
    };
  });
  if (withCandles) {
    const lastTxt = last.toLocaleString("en-US", { maximumFractionDigits: 0 });
    say(m.svg && m.n >= 52 && m.title, "١ تقريرُ المحفظة يحمل شموعَ صافي الربح: شمعةٌ لكلّ أسبوع، وعنوانُها", `${m.n ?? 0} مستطيلاً`);
    say(m.svg && (m.fills || []).includes("#0f9d63") && (m.fills || []).includes("#c0273c"), "٢ بلونَي الصعود والهبوط من ورق التقرير",
        (m.fills || []).join(" · "));
    say(m.svg && m.band, "٣ وفترةُ التقرير مظلَّلةٌ بلون الهويّة");
    say(m.svg && m.zero, "٤ والصفرُ خطٌّ حين تعبره السلسلة — الربحُ والخسارةُ على جانبيه");
    say(m.svg && m.dashed && m.texts.includes(lastTxt), "٥ وآخرُ قيمةٍ خطٌّ متقطّعٌ ووسمٌ بفواصل الآلاف", lastTxt);
    say(m.svg && m.texts.some(s => /^(يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر)$/.test(s))
        && m.texts.every(s => !/[٠-٩]/.test(s)) && m.minFont >= 9.5, "٦ والأشهرُ بالعربية والأرقامُ لاتينية، وأصغرُ خطٍّ ≥ 9.5px", `${m.minFont}px`);
    say(m.tasi && m.tasi.title && m.tasi.n >= 52 && m.tasi.after && m.tasi.texts.includes(tasiLast.toLocaleString("en-US")),
        "٨ والجزءُ الثاني يلي الأوّل: شموعُ تاسي في الأسابيع نفسِها بعنوانها وآخرِ قيمتها", JSON.stringify({ n: m.tasi?.n, after: m.tasi?.after }));
    if (SHOTS) {
      const el = await page.$(".report-doc");
      if (el) await el.screenshot({ path: join(SHOTS, "d711_portfolio_report.png") });
    }
  } else {
    say(m.doc && !m.svg && !m.tasi, "٧ وبلا شموعٍ (تاريخٌ أقصرُ من عشرة أسابيع) لا رسمَ مختلَق — يُحذف القسمُ كلُّه، وتاسي معه");
  }
  say(errs.length === 0, `${withCandles ? "مع" : "بلا"} شموع: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
