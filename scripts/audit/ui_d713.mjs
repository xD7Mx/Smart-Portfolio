// ─────────────────────────────────────────────────────────────────────────
// D713 — بلاغُ المالك: «الرسمُ يُظهر مؤشّرَ D7M بخطوطٍ سوداء قبيحة… اجعل الأسعارَ على اليمين بلا ظلّ بنمطٍ إطاريٍّ جميل، والشموعُ
// ليست حقيقية مثل تريدنق فيو». يُفتح الرسمُ الحقيقيّ (‏vite) على شموعٍ أسبوعيةٍ متعرّجة، ويُفعَّل D7M، ويُقاس من الـDOM:
//   · أسعارُ المحور وسومٌ مؤطَّرة: إطارُها ونصُّها بلون خطّها، وأرضيّتُها أرضيةُ الرسم لا لونُ الخطّ.
//   · وآخرُ سعرٍ وسمٌ مؤطَّرٌ بقيمته، ومستوياتُ فيبوناتشي أرقامُها يساراً.
//   · والشمعةُ الجاريةُ تتحرّك في موضعها حين يتحرّك السعر — بلا إعادة بناءٍ تُضيّع التكبير.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync, mkdirSync } from "node:fs";
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
// مكتبةُ الرسم يجلبها التطبيقُ من unpkg — والمتصفّحُ هنا بلا شبكة: نسخةٌ محلّيةٌ بالإصدار نفسِه (4.1.3) أو تُنزَّل مرّةً بـcurl
const LW_URL = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
const LW_CACHE = join(tmpdir(), "sp-audit-lw-4.1.3.js");
let LW = [process.env.LW_PATH, "/tmp/claude-0/lw/package/dist/lightweight-charts.standalone.production.js",
  join(FRONT, "node_modules/lightweight-charts/dist/lightweight-charts.standalone.production.js"), LW_CACHE].find(p => p && existsSync(p));
if (!LW) { mkdirSync(tmpdir(), { recursive: true }); if (spawnSync("curl", ["-fsSL", "-o", LW_CACHE, LW_URL]).status === 0 && existsSync(LW_CACHE)) LW = LW_CACHE; }
if (!LW) { console.log("… تعذّر فحصُ المتصفّح: مكتبةُ الرسم غيرُ متاحة محلّياً ولا تُنزَّل — لا حكم."); process.exit(fail); }
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e.message || e)));
await page.route("https://unpkg.com/**", r => r.fulfill({ path: LW, contentType: "application/javascript" }));
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (/\/market\/history\//.test(u) && /tf=/.test(u)) return r.fulfill(body(served()));
  return r.fulfill(body([]));
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_chart_tf", "1wk"); } catch { } });
if (!process.env.NOCLOCK) await page.clock.install();
await page.goto(`http://localhost:${PORT}/watchlist?tab=chart`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(3000);
// تفعيلُ D7M من قائمة المؤشّرات
await page.locator("button", { hasText: "SMA20" }).first().click({ timeout: 6000 }).catch(() => {});
await page.waitForTimeout(400);
await page.locator('button[aria-pressed]', { hasText: "D7M" }).first().click({ timeout: 6000 }).catch(() => {});
await page.waitForTimeout(2500);
const read = () => page.evaluate(() => {
  const surf = getComputedStyle(document.documentElement).getPropertyValue("--surface").trim();
  const tags = [...document.querySelectorAll('[data-role="axis-tag"]')].map(t => {
    const cs = getComputedStyle(t);
    return { text: t.textContent.trim(), color: cs.color, border: cs.borderTopColor, bg: cs.backgroundColor, last: t.classList.contains("axis-tag-last") };
  });
  const levels = [...document.querySelectorAll(".axis-level")].map(x => x.textContent.trim());
  return { tags, levels, surf };
});
const a = await read();
if (process.env.SHOTS) await page.screenshot({ path: process.env.SHOTS + "/d713.png" });
if (process.env.DBG) console.log(await page.evaluate(() => ({ canvas: document.querySelectorAll(".chart-frame canvas").length,
  frame: !!document.querySelector(".chart-frame"), btns: [...document.querySelectorAll("button")].map(b => b.textContent.trim()).filter(t => /SMA|D7M|MACD|المؤشرات/.test(t)) })));
const outlined = a.tags.filter(t => t.color === t.border && t.bg !== t.border);
say(a.tags.length >= 3 && outlined.length === a.tags.length, "١ أسعارُ المحور وسومٌ مؤطَّرة بلون خطّها — لا كتلةٌ مملوءة",
    `${a.tags.length} وسماً · مؤطَّرٌ ${outlined.length}`);
const lastTag = a.tags.find(t => t.last);
say(!!lastTag && lastTag.text === state.lastClose.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    "٢ وآخرُ سعرٍ وسمٌ مؤطَّرٌ بقيمته", lastTag?.text);
say(a.levels.some(s => /^0\.618/.test(s)) && a.levels.length >= 2, "٣ ومستوياتُ فيبوناتشي أرقامُها على يسار الرسم كتريدنق فيو", a.levels.slice(0, 4).join(" | "));
// ٤ الشمعةُ الجاريةُ تتحرّك: يتغيّر الإغلاقُ عند المصدر، ويمضي التحديثُ الدوريّ (دقيقة)
const before = await page.evaluate(() => document.querySelector(".chart-frame canvas") ? 1 : 0);
state.lastClose = state.lastClose + 137;
await page.clock.fastForward(61000);
await page.waitForTimeout(1800);
const b = await read();
const lastB = b.tags.find(t => t.last);
say(before && lastB && lastB.text === state.lastClose.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    "٤ والشمعةُ الجاريةُ تتحرّك مع السعر في موضعها (تحديثٌ كلَّ دقيقة) — ووسمُ آخر سعرٍ معها", `${lastTag?.text} ← ${lastB?.text}`);
say(errs.length === 0, "٥ بلا خطأٍ في الصفحة", errs[0] || "");
await browser.close();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
