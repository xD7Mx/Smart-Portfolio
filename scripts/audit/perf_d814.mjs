// ─────────────────────────────────────────────────────────────────────────
// D814 (الواجهة) — «التطبيقُ يأخذ وقتاً: عند التحميل أو البحث أو المسح أو تشغيل الإطارات أو الرسم — خلِّه سريعاً» (المالك 2026-11-24).
//  ١ التحميل: كانت الصفحاتُ كلُّها في ملفٍّ واحد (‏694KB مضغوطاً قبل أوّل صفحة)؛ فكلُّ صفحةٍ ملفٌّ يُنزَّل حين تُفتح (والباقي في وقت الفراغ)،
//    والإطارُ (الشريطُ والقائمة) باقٍ وما ينتظرها شريطٌ رفيعٌ متحرّك يحترم تقليلَ الحركة — لا شاشةٌ فارغة.
//  ٢ الإطارات: شموعُ الإطارات المفضّلة للرمز تُجلب في وقت الفراغ بعد رسم الجاري — فالضغطُ عليها يرسم فوراً من الذاكرة بلا انتظار.
//    node scripts/audit/perf_d814.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ═ ١ ساكنٌ على المصدر ═
const app = readFileSync(join(FRONT, "src/App.tsx"), "utf8"), lay = readFileSync(join(FRONT, "src/components/common/MainLayout.tsx"), "utf8");
const css = readFileSync(join(FRONT, "src/styles/globals.css"), "utf8");
const eager = [...app.matchAll(/^import\s+(\w+Page)\s+from\s+"\.\/pages\//gm)].map(m => m[1]);
say(eager.join() === "LoginPage" && /React\.lazy\(pageLoaders\.watchlist\)/.test(app) && /warmPages/.test(app) && /<Suspense fallback=\{<div className="page-wait"/.test(lay)
    && /\.page-wait::after[^}]*animation: pageWait/.test(css) && /prefers-reduced-motion: reduce\) \{ \.page-wait::after \{ animation: none/.test(css),
    "١ كلُّ صفحةٍ تُنزَّل حين تُفتح (والدخولُ وحده في الملفّ الأوّل)، والباقي في وقت الفراغ، والانتظارُ شريطٌ متحرّكٌ داخل الإطار يحترم تقليلَ الحركة",
    `في الملفّ الأوّل: ${eager.join(", ")}`);

// ═ ٢ الإطاراتُ المفضّلة تُجلب سلفاً ═
const PORT = 5304;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const bars = (n, tf) => Array.from({ length: n }, (_, i) => {
  const step = tf === "1wk" ? 7 * 864e5 : tf === "1h" ? 36e5 : 864e5;
  const t = new Date(Date.UTC(2026, 0, 4) + i * step).toISOString();
  const c = 100 + i * 0.2 + Math.sin(i / 3) * 4;
  return { date: tf === "1h" ? t.slice(0, 16).replace("T", " ") : t.slice(0, 10), open: c - 0.5, high: c + 1, low: c - 1, close: c, volume: 2e6 };
});
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errs = [], log = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
await page.addInitScript(() => { try {
  if (sessionStorage.getItem("d814-init")) return;
  sessionStorage.setItem("d814-init", "1");
  localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_layout", "1");
  localStorage.setItem("sp_chart_tf", "1d"); localStorage.setItem("sp_chart_tf_fav", JSON.stringify(["1d", "1wk", "1h"]));
} catch { /* */ } });
await page.route("**/api/v1/**", async r => {
  const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
  if (/^\/market\/history\//.test(p)) { const tf = u.searchParams.get("tf"); log.push([Date.now(), tf]); await sleep(400); return r.fulfill(body(bars(160, tf))); }
  if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
  return r.fulfill(body([]));
});
await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(5000);
const before = log.map(x => x[1]);
const chart = page.locator('[data-role="troom-chart"] [data-role="pro-chart"]').first();
const t0 = Date.now();
await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] [data-tf="1wk"]').first().click();
let ms = -1;
for (let i = 0; i < 60; i++) { const tf = await chart.getAttribute("data-tf"), n = Number(await chart.getAttribute("data-bars")); if (tf === "1wk" && n === 160) { ms = Date.now() - t0; break; } await sleep(25); }
const pend = await page.locator('[data-role="troom-chart"] .pc-progress').count();
say(before.includes("1d") && before.includes("1wk") && before.includes("1h") && ms >= 0 && ms < 350 && pend === 0,
    "٢ الإطاراتُ المفضّلة (أسبوع · ساعة) تُجلب في وقت الفراغ بعد رسم اليوميّ — والضغطُ على «أسبوع» يرسمه من الذاكرة فوراً بلا مؤشّر انتظار (والشبكةُ هنا 400ms)",
    `جُلب قبل الضغط: ${before.join(",")} · رُسم بعد ${ms}ms`);
say(errs.length === 0, "لا خطأ في الصفحة", errs[0] || "");
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
