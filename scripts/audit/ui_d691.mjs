// ─────────────────────────────────────────────────────────────────────────
// D691 — مفتاحُ «إظهار الساعة» في الإعدادات لا يعمل: مخزنُ الإعدادات يُعلن `setShowClock` ولا ينفّذه، فالنقرُ يرمي
// `onChange is not a function` والساعةُ باقية. كان مخفيّاً بين تسعة أخطاء أنواعٍ تُركت «ملاحظاتٍ قديمة» (ts_undefined.py ٢).
// يُفتح التطبيقُ الحقيقيّ (‏vite) وتُنقر المفاتيحُ ويُقاس: لا خطأ، وتنقلب حالتُها، وتُحفظ.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5247;
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

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e.message || e)));
await page.route("**/api/v1/**", r => r.fulfill(body([])));
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
await page.goto(`http://localhost:${PORT}/settings`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(2200);
// الساعةُ في تبويب «التخصيص» من الإعدادات
await page.locator("button", { hasText: "التخصيص" }).first().click({ timeout: 5000 }).catch(() => {});
await page.waitForTimeout(400);

const flip = async (label, key) => {
  const sw = page.locator("div.panel", { hasText: label }).locator('[role="switch"]').first();
  const before = await sw.getAttribute("aria-checked", { timeout: 5000 }).catch(() => null);
  const n0 = errs.length;
  await sw.click({ timeout: 5000 }).catch(() => {});
  await sleep(250);
  const after = await sw.getAttribute("aria-checked").catch(() => null);
  const saved = await page.evaluate((k) => { try { return JSON.parse(localStorage.getItem("sp-app-store") || "{}").state?.[k]; } catch { return undefined; } }, key);
  return { before, after, saved, thrown: errs.slice(n0) };
};
const c = await flip("إظهار الساعة", "showClock");
say(c.before != null && c.thrown.length === 0, "١ النقرُ على «إظهار الساعة» لا يرمي خطأً", c.thrown[0] || `قبل ${c.before}`);
say(c.before != null && c.after !== c.before && String(c.saved) === c.after,
    "٢ وتنقلب حالتُه وتُحفظ — الساعةُ تُخفى فعلاً", `${c.before} ← ${c.after} · محفوظ ${c.saved}`);
const s = await flip("إظهار الثواني", "clockSeconds");
say(s.before != null && s.after !== s.before && s.thrown.length === 0, "٣ وجارُه «إظهار الثواني» كما كان يعمل — لا يُكسر بالإصلاح",
    `${s.before} ← ${s.after}`);
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
