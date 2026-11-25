// ─────────────────────────────────────────────────────────────────────────
// D826 — «تأخيرٌ في تحميل صفحات تريدنق فيو لجميع الإطارات» (المالك 2026-11-24).
// قِيس: الرسمُ نفسُه سريع (الإطارُ المخبّأُ يُرسم في أقلَّ من 50ms حتى بمعالجٍ أبطأَ أربعَ مرّات)، لكنّ شموعَ الإطار تُرمى من ذاكرة المتصفّح بعد
// خمس دقائقَ من مغادرته، والمفضّلةُ تُجلب سلفاً مرّةً واحدةً عند فتح الرمز — فبعد دقائقَ على إطارٍ واحدٍ يعود كلُّ إطارٍ آخرَ إلى الشبكة
// والخادم (‏772ms بشبكةٍ 600ms؛ وعلى الجوال ثانيةٌ إلى ثلاث).
//  ١ بعد ستّ دقائقَ على اليوميّ: «ساعة» تُرسم فوراً من الذاكرة قبل وصول الشبكة (وتُنعَش في الخلفية).
//  ٢ إطارٌ من «كلّ الإطارات» يبدأ جلبُه حين يقترب منه المؤشّرُ — قبل الضغطة.
//    node scripts/audit/chart_cache_d826.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5326;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const N = { "1d": 400, "1h": 333, "1wk": 222, "4h": 177 };
const gen = tf => { const n = N[tf] || 150, st = tf === "1h" ? 36e5 : tf === "4h" ? 4 * 36e5 : tf === "1wk" ? 7 * 864e5 : 864e5, t0 = Date.UTC(2026, 10, 24) - n * st;
  return Array.from({ length: n }, (_, i) => { const c = 20 + Math.sin(i / 9); const t = new Date(t0 + i * st).toISOString();
    return { date: /h$/.test(tf) ? t.slice(0, 16).replace("T", " ") : t.slice(0, 10), open: c, high: c + .2, low: c - .2, close: c, volume: 1e6 }; }); };
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
await page.clock.install();
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_layout", "1");
  localStorage.setItem("sp_chart_tf", "1d"); localStorage.setItem("sp_chart_tf_fav", JSON.stringify(["1d", "1wk", "1h"])); } catch { /* */ } });
const net = [];
await page.route("**/api/v1/**", async r => {
  const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
  if (/^\/market\/history\//.test(p)) { const tf = u.searchParams.get("tf"); net.push(tf); await sleep(600); return r.fulfill(body(gen(tf))); }
  if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
  return r.fulfill(body([]));
});
await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.clock.runFor(8000);
await sleep(3500);
const first = [...net];
await page.clock.runFor(6 * 60_000);
await sleep(1500);
const chart = page.locator('[data-role="troom-chart"] [data-role="pro-chart"]').first();
net.length = 0;
const s = Date.now();
await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] [data-tf="1h"]').first().click().catch(() => {});
let ms = -1;
for (let i = 0; i < 120; i++) { if ((await chart.getAttribute("data-tf")) === "1h" && Number(await chart.getAttribute("data-bars")) === N["1h"]) { ms = Date.now() - s; break; }
  await page.clock.runFor(30); await sleep(10); }
say(first.includes("1wk") && first.includes("1h") && ms >= 0 && ms < 450,
    "١ بعد ستّ دقائقَ على اليوميّ: «ساعة» تُرسم فوراً من ذاكرة المتصفّح قبل وصول الشبكة (‏600ms هنا) وتُنعَش في الخلفية — كانت تُرمى بعد خمس دقائق",
    `جُلب أوّلاً ${first.join(",")} · رُسمت بعد ${ms}ms · طلباتٌ عندها ${net.join(",") || "لا شيء"}`);

net.length = 0;
await page.locator('[data-role="troom-chart"] [data-role="pc-tf-more"]').first().click().catch(() => {});
await page.clock.runFor(300); await sleep(300);
await page.locator('[data-role="pc-tfgrid"] [data-tf="4h"]').first().hover().catch(() => {});
await page.clock.runFor(200); await sleep(400);
const hovered = net.includes("4h");
say(hovered, "٢ إطارٌ من «كلّ الإطارات» يبدأ جلبُه حين يقترب منه المؤشّرُ — قبل الضغطة", `طلباتٌ عند الاقتراب: ${net.join(",") || "لا شيء"}`);
say(errs.length === 0, "لا خطأ في الصفحة", errs[0] || "");
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
