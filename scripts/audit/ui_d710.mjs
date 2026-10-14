// ─────────────────────────────────────────────────────────────────────────
// D710 — الصورةُ الشخصيةُ دائرةٌ في كلّ موضع كما في الترويسة (بلاغُ المالك: «أيقونةُ الشخصية بجانب مساء الخير مربّعٌ وليست دائرة»).
// القاعدةُ الموحَّدة `.card, .panel… { border-radius: 14px }` بعد الأدوات وبالخصوصية نفسِها فغلبت `rounded-full` — فإطارُ الصورة
// مربّعٌ بزوايا وإن دُوِّرت الصورةُ نفسُها (‏D178). فيُقاس **الإطار** في المتصفّح: نصفُ قطره ≥ نصفَ عرضه، في الترحيب والإعدادات والدخول.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5231;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await new Promise(r => setTimeout(r, 500)); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
// صورةٌ نقطيّةٌ حقيقية (‏PNG مربّع 8×8) — فيُرسم الإطارُ حولها كما في الإنتاج
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAgAAAAICAIAAABLbSncAAAAEklEQVR4nGP4z8CAFTEMLQkAZhQ/wQGz0OsAAAAASUVORK5CYII=", "base64");
const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (u.includes("/settings/avatar")) return r.fulfill({ status: 200, contentType: "image/png", body: PNG });
  if (u.includes("/settings/profile")) return r.fulfill({ status: 200, contentType: "application/json",
    body: JSON.stringify({ success: true, data: { name: "المالك", has_avatar: true } }) });
  return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: [] }) });
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });

async function frame(path, sel, tab = null) {
  await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 });
  if (tab) {
    const b = page.locator("nav button", { hasText: tab }).first();
    try { await b.waitFor({ timeout: 8000 }); await b.click(); } catch { return null; }
  }
  const loc = page.locator(sel).first();
  try { await loc.waitFor({ state: "attached", timeout: 8000 }); } catch { return null; }
  return loc.evaluate(e => {
    const cs = getComputedStyle(e);
    return { w: e.getBoundingClientRect().width, h: e.getBoundingClientRect().height, r: parseFloat(cs.borderTopLeftRadius) };
  });
}
const round = f => f && f.w > 0 && Math.abs(f.w - f.h) < 1 && f.r >= f.w / 2 - 0.5;
const desc = f => f ? `${Math.round(f.w)}×${Math.round(f.h)} · نصفُ القطر ${f.r}px` : "لم يُرسم";

const g = await frame("/portfolio", "h1 >> xpath=ancestor::div[contains(@class,'gap-3')][1]/div[contains(@class,'rounded-full')]");
say(round(g), "١ إطارُ الصورة بجانب التحية دائرة", desc(g));
const s = await frame("/settings", "div.w-20.h-20.rounded-full", "الملف الشخصي");
say(round(s), "٢ وإطارُها في الإعدادات دائرة", desc(s));
await page.evaluate(() => { try { localStorage.removeItem("sp_token"); } catch { /* */ } });
const l = await frame("/login", "div.w-24.h-24.rounded-full");
say(l == null || round(l), "٣ وفي شاشة الدخول دائرة (إن رُسمت)", desc(l));
say(errs.length === 0, "٤ بلا خطأٍ في الصفحات", errs.slice(0, 2).join(" | "));
await browser.close();
stop();
console.log(fail ? "\nالنتيجة: عطب ✖" : "\nالنتيجة: نظيف ✔");
process.exit(fail);
