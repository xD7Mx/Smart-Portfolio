// ─────────────────────────────────────────────────────────────────────────
// D712 (المالك): «بدلاً من أن تكون [إيماءةُ السحب] قاسية اجعلها تتبع حركةَ الإصبع عند السحب ولو بدايةَ رأس القائمة — نتيجةُ حركةٍ
// بطيئةٍ جميلة». كانت السحبةُ تُحكم عند الرفع وحدَه ثمّ تُشغَّل حركةٌ محفوظة. فيُقاس بلمسٍ حقيقيّ (‏CDP) على شاشة جوال:
// القائمةُ أثناء السحب حيث الإصبع (حافّتُها أوّلاً)، والغطاءُ يغمق بقدرها، والرفعُ يستقرّ بالمسافة والسرعة، والسحبُ المعاكسُ يتبع
// الإصبعَ مغلقاً، والقصيرةُ البطيئةُ ترتدّ، والنفضةُ السريعةُ تفتح، والتمريرُ الرأسيّ لا يحرّكها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5254;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e.message || e)));
await page.route("**/api/v1/**", r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: [] }) }));
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(2200);
const cdp = await ctx.newCDPSession(page);
const T = (type, x, y) => cdp.send("Input.dispatchTouchEvent", { type, touchPoints: type === "touchEnd" ? [] : [{ x, y }] });
const glide = async (x0, x1, y, steps, gap) => { for (let s = 1; s <= steps; s++) { await T("touchMove", x0 + (x1 - x0) * s / steps, y); await sleep(gap); } };
const state = () => page.evaluate(() => {
  const a = document.querySelector(".mobile-drawer"), sc = document.querySelector(".drawer-scrim");
  if (!a) return { on: false };
  const m = getComputedStyle(a).transform, tx = m && m !== "none" ? parseFloat(m.split(",")[4]) : 0;
  return { on: true, tx: Math.round(tx), op: sc ? +(+getComputedStyle(sc).opacity).toFixed(2) : null };
});

// ١–٣ الفتحُ يتبع الإصبع: حافّتُها أوّلاً ثمّ بقدر السحب، والغطاءُ بقدرها، والرفعُ يستقرّ مفتوحةً
await T("touchStart", 330, 500);
await glide(330, 230, 500, 6, 30);
await sleep(120);
const a1 = await state();
await glide(230, 150, 500, 5, 30);
await sleep(120);
const a2 = await state();
say(a1.on && Math.abs(a1.tx - 156) <= 14 && a2.on && Math.abs(a2.tx - 76) <= 14 && a2.tx < a1.tx,
    "١ القائمةُ أثناء السحب حيث الإصبع — 100px ⇒ تظهر 100px، و180px ⇒ 180px (لا حركةٌ محفوظة)", `${a1.tx}px ← ${a2.tx}px من الحافّة`);
say(a1.op != null && a2.op > a1.op && Math.abs(a1.op - 0.39) <= 0.08, "٢ والغطاءُ يغمق بقدر ما ظهر منها", `${a1.op} ← ${a2.op}`);
await sleep(150);
await T("touchEnd");
await sleep(500);
const a3 = await state();
say(a3.on && Math.abs(a3.tx) <= 2, "٣ والرفعُ بعد أكثر من ثلثها يستقرّ مفتوحةً بحركةٍ ناعمة", `${a3.tx}px`);

// ٤ الإغلاقُ يتبع الإصبعَ كذلك
await T("touchStart", 120, 500);
await glide(120, 220, 500, 6, 30);
await sleep(120);
const c1 = await state();
await glide(220, 300, 500, 5, 30);
await sleep(150);
const c2 = await state();
await T("touchEnd");
await sleep(500);
const c3 = await state();
say(c1.on && Math.abs(c1.tx - 100) <= 14 && c2.tx > c1.tx && !c3.on,
    "٤ والسحبُ المعاكسُ يُعيدها مع الإصبع ثمّ تُغلق", `${c1.tx}px ← ${c2.tx}px ← ${c3.on ? "مفتوحة" : "أُغلقت"}`);

// ٥ القصيرةُ البطيئةُ ترتدّ
await T("touchStart", 330, 500);
await glide(330, 290, 500, 4, 40);
await sleep(160);
const s1 = await state();
await T("touchEnd");
await sleep(500);
const s2 = await state();
say(s1.on && Math.abs(s1.tx - 216) <= 14 && !s2.on, "٥ ورأسُها يظهر بسحبةٍ قصيرة، فإن رُفع الإصبعُ ببطءٍ ارتدّت", `${s1.tx}px ← ${s2.on ? "بقيت" : "ارتدّت"}`);

// ٦ النفضةُ السريعةُ تفتحها ولو قصيرة
await T("touchStart", 330, 500);
await glide(330, 260, 500, 3, 8);
await T("touchEnd");
await sleep(500);
const f1 = await state();
say(f1.on && Math.abs(f1.tx) <= 2, "٦ والنفضةُ السريعةُ تفتحها ولو قصيرة", `${f1.on ? f1.tx + "px" : "لم تفتح"}`);
await T("touchStart", 80, 500); await glide(80, 340, 500, 5, 10); await T("touchEnd"); await sleep(500);

// ٧ التمريرُ الرأسيّ لا يحرّكها
await T("touchStart", 200, 640);
for (let s = 1; s <= 6; s++) { await T("touchMove", 200 - s, 640 - s * 55); await sleep(20); }
await T("touchEnd");
await sleep(400);
const v1 = await state();
say(!v1.on, "٧ والتمريرُ الرأسيّ لا يحرّكها");
say(errs.length === 0, "٨ بلا خطأٍ في الصفحة", errs[0] || "");
await browser.close();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
