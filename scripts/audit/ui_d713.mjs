// ─────────────────────────────────────────────────────────────────────────
// D713 — بلاغُ المالك: «الرسمُ يُظهر مؤشّرَ D7M بخطوطٍ سوداء قبيحة… اجعل الأسعارَ على اليمين بلا ظلّ بنمطٍ إطاريٍّ جميل، والشموعُ
// ليست حقيقية مثل تريدنق فيو». يُفتح الرسمُ الحقيقيّ (‏vite) على شموعٍ أسبوعيةٍ متعرّجة، ويُفعَّل D7M، ويُقاس من الـDOM:
//   · أسعارُ المحور وسومٌ مؤطَّرة: إطارُها ونصُّها بلون خطّها، وأرضيّتُها أرضيةُ الرسم لا لونُ الخطّ.
//   · وآخرُ سعرٍ وسمٌ مؤطَّرٌ بقيمته، ومستوياتُ فيبوناتشي أرقامُها يساراً.
//   · والشمعةُ الجاريةُ تتحرّك في موضعها حين يتحرّك السعر — بلا إعادة بناءٍ تُضيّع التكبير.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync, mkdirSync, mkdtempSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5255;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };

// ٠ (بلا متصفّح) — لا كتلةَ ملوّنةً من المكتبة على المحور، ولا حبرَ نصٍّ أسودَ لخطوط المؤشّر
const SRC = readFileSync(join(FRONT, "src/components/analysis/NativeChart.tsx"), "utf8");
say(!/axisLabelVisible:\s*true/.test(SRC) && /lastValueVisible:\s*false,\s*\/\*\s*‏D713/.test(SRC) && !/const ink = C\("fib"\)/.test(SRC)
    && SRC.includes('priceFormat: { type: "volume" }, priceLineVisible: false, lastValueVisible: false'),
    "٠ لا وسمَ مكتبةٍ مملوءاً على المحور (المستويات · الخطّ الأفقيّ · آخرُ سعر)، ولا خطوطَ مؤشّرٍ بحبر النصّ");

if (!PW || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: غيرُ متاح."); process.exit(fail); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });

// مئةٌ وعشرون أسبوعاً متعرّجة (صعودٌ ثمّ هبوطٌ ثمّ صعود) — ليجد الفيبوناتشي ضلعه
const bars = [];
let px = 10000;
for (let i = 0; i < 120; i++) {
  const d = new Date(Date.UTC(2024, 6, 7) + i * 7 * 864e5).toISOString().slice(0, 10);
  const drift = i < 45 ? 60 : i < 80 ? -75 : 55;
  const o = px, c = Math.round(px + drift + (i % 3 === 0 ? -40 : 25));
  bars.push({ date: d, open: o, high: Math.max(o, c) + 35, low: Math.min(o, c) - 35, close: c, volume: 1000 });
  px = c;
}
const state = { lastClose: bars[bars.length - 1].close };
const served = () => { const b = bars.map(x => ({ ...x })); const l = b[b.length - 1]; l.close = state.lastClose; l.high = Math.max(l.high, l.close); l.low = Math.min(l.low, l.close); return b; };

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(fail); }
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e.message || e)));
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (/\/market\/history\//.test(u) && /tf=/.test(u)) return r.fulfill(body(served()));
  return r.fulfill(body([]));
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_chart_tf", "1wk"); } catch { } });
if (!process.env.NOCLOCK) await page.clock.install();
await page.goto(`http://localhost:${PORT}/watchlist?tab=chart`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(3000);
// ‏D736: غرفةُ التداول على الرسم الاحترافيّ (‏chart/ProChart) — الوسومُ والمستوياتُ تُرسم على اللوحة نفسِها (‏lib/chartOverlay) لا عناصرَ
// صفحة؛ فيُقاس الرسمُ من طبقته: تُستدعى دالّةُ الرسم بلوحةٍ تسجّل ما يُرسم، ويُقرأ من الرسم الحيّ ما وُسم (سماتُ التشخيص).
const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const ovOut = join(mkdtempSync(join(tmpdir(), "sp-d713-")), "overlay.mjs");
await build({ entryPoints: [join(FRONT, "src/lib/chartOverlay.ts")], outfile: ovOut, format: "esm", bundle: true, logLevel: "silent" });
const { ChartOverlay } = await import(pathToFileURL(ovOut).href);
const rec = [];
const fake = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (...args) => { rec.push([k, args, { fill: t.fillStyle, stroke: t.strokeStyle, align: t.textAlign }]); }), set: (t, k, v) => { t[k] = v; return true; } });
const target = { useMediaCoordinateSpace: (cb) => cb({ context: fake, mediaSize: { width: 70, height: 400 } }) };
const ov = new ChartOverlay();
ov.attached({ chart: { timeScale: () => ({ logicalToCoordinate: (k) => (Number.isInteger(k) ? 100 + 10 * k : 0), options: () => ({ barSpacing: 10 }) }) },
              series: { priceToCoordinate: (p) => 400 - p }, requestUpdate() { } });
ov.set({ bg: "BG", levels: [{ price: 200, color: "RED", tag: true, bold: true, rank: 0 }, { price: 120, color: "GOLD", tag: true, text: "0.618 · اتجاه", rank: 2 },
                              { price: 60, color: "INK", tag: true, text: "1.618", rank: 3 }] });
ov.priceAxisPaneViews()[0].renderer().draw(target);
const fills = rec.filter(r => r[0] === "fill"), strokes = rec.filter(r => r[0] === "stroke"), texts = rec.filter(r => r[0] === "fillText");
say(fills.length === 3 && fills.every(f => f[2].fill === "BG") && JSON.stringify(strokes.map(x => x[2].stroke)) === JSON.stringify(["RED", "GOLD", "INK"])
    && JSON.stringify(texts.map(x => x[2].fill)) === JSON.stringify(["RED", "GOLD", "INK"]) && texts[0][1][0] === "200.00",
    "١ أسعارُ المحور وسومٌ مؤطَّرة بلون خطّها — إطارُها ونصُّها بلونه وأرضيّتُها أرضيةُ الرسم، لا كتلةٌ مملوءة",
    `${fills.length} وسماً · أرضية ${[...new Set(fills.map(f => f[2].fill))].join(",")}`);
rec.length = 0; fake.textAlign = "";
ov.paneViews()[0].renderer().draw(target);
const lv = rec.filter(r => r[0] === "fillText");
say(lv.length === 2 && lv.every(t => t[2].align === "left" && t[1][1] === 8) && /^0\.618/.test(lv[0][1][0]),
    "٣ ومستوياتُ فيبوناتشي أرقامُها على يسار الرسم كتريدنق فيو", lv.map(t => `${t[1][0]}@${t[1][1]}`).join(" | "));

// تفعيلُ D7M من قائمة المؤشّرات
await page.locator('[data-role="pc-ind"]').click({ timeout: 6000 }).catch(() => {});
await page.waitForTimeout(400);
await page.locator('[data-role="pc-ind-menu"] [data-ind="d7m"]').click({ timeout: 6000 }).catch(() => {});
await page.waitForTimeout(2500);
const read = () => page.evaluate(() => {
  const r = document.querySelector('[data-role="pro-chart"]');
  return r ? { last: r.dataset.last, lv: Number(r.dataset.lv), tags: Number(r.dataset.tags), vis: r.dataset.vis, c: document.querySelector('[data-k="c"]')?.textContent } : {};
});
const a = await read();
if (process.env.SHOTS) await page.screenshot({ path: process.env.SHOTS + "/d713.png" });
const fmt = (v) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
say(a.last === fmt(state.lastClose) && a.tags >= 3, "٢ وآخرُ سعرٍ وسمٌ مؤطَّرٌ بقيمته — ومعه وسومُ مستويات D7M", `${a.last} · ${a.tags} وسماً`);
say(a.lv >= 2, "٣ب ومستوياتُ D7M مسمّاةٌ على الرسم الحيّ", `${a.lv} مستوى`);
// ٤ الشمعةُ الجاريةُ تتحرّك: يتغيّر الإغلاقُ عند المصدر، ويمضي التحديثُ الدوريّ (دقيقة) — واللوحةُ نفسُها والتكبيرُ نفسُه
await page.evaluate(() => { document.querySelector('[data-role="pc-stage"] canvas').__same = 1; });
state.lastClose = state.lastClose + 137;
await page.clock.fastForward(61000);
await page.waitForTimeout(1800);
const b = await read();
const same = await page.evaluate(() => document.querySelector('[data-role="pc-stage"] canvas')?.__same === 1);
say(same && b.last === fmt(state.lastClose) && b.c === fmt(state.lastClose) && b.vis === a.vis,
    "٤ والشمعةُ الجاريةُ تتحرّك مع السعر في موضعها (تحديثٌ كلَّ دقيقة) — ووسمُ آخر سعرٍ معها، بلا إعادة بناءٍ تُضيّع التكبير", `${a.last} ← ${b.last} · المعروض ${a.vis} ← ${b.vis}`);
say(errs.length === 0, "٥ بلا خطأٍ في الصفحة", errs[0] || "");
await browser.close();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
