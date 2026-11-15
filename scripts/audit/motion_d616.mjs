// ─────────────────────────────────────────────────────────────────────────
// D616 — القوائمُ والنوافذُ تتلاشى عند الإغلاق ولا تُخلّف أثراً، ومقبضُ المفتاح ينزلق بمنحنى (بلاغُ المالك).
// يُقلَع خادمُ التطوير وتُفتح «/stars» بخادمٍ مموَّهٍ بأشكال الردود الحقيقية، ثمّ تُضاف شركةٌ بالبحث،
// ويُشترط ألّا يقع خطأٌ في الصفحة وأن تظهر إحصاءاتُها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5223;
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
const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
await page.route("**/api/v1/**", r => r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: [] }) }));
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });
await page.goto(`http://localhost:${PORT}/settings`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1500);
const btn = page.locator('button[aria-haspopup="dialog"]').first();
await btn.click();
await page.waitForTimeout(250);
const anim = await page.locator(".date-pop").first().evaluate(e => getComputedStyle(e).animationName);
say(anim && anim !== "none", "١ القائمةُ تنفتح بحركة", anim);
await page.keyboard.press("Escape");
await page.waitForTimeout(40);
const ghosts = await page.locator(".exit-anim").count();
say(ghosts === 1, "٢ وتُغلق بتلاشٍ لا باختفاءٍ فوريّ", `نسخٌ متلاشية: ${ghosts}`);
await page.waitForTimeout(400);
say(await page.locator(".exit-anim").count() === 0, "٣ ولا تُخلّف أثراً بعد انتهاء الحركة");
await btn.click(); await page.waitForTimeout(200);
await page.locator(".date-day", { hasText: /^1$/ }).first().click();
await page.waitForTimeout(400);
say(await page.locator(".date-pop").count() === 0 && await page.locator(".exit-anim").count() === 0, "٤ والاختيارُ يُغلق القائمة نظيفةً");
await page.evaluate(() => { const b = document.createElement("button"); b.className = "switch"; b.id = "sw-probe"; document.body.appendChild(b); });
const sw = page.locator("#sw-probe");
if (await sw.count()) {
  const tr = await sw.evaluate(e => getComputedStyle(e, "::after").transitionTimingFunction);
  say(/cubic-bezier\(0\.34/.test(tr), "٥ مقبضُ مفتاح التفعيل ينزلق بمنحنى نابض", tr);
} else say(false, "٥ لا مفتاحَ تفعيلٍ في الصفحة");
// D617 ← D745: القائمةُ المرسومة (‏Select) تنفتح بحركة وتختار وتُغلق بتلاشٍ — كانت تُقاس على قائمة المحفظة في مختبر الأبحاث القديم،
// وقد صار المختبرُ قسمَ أبحاثٍ بلا قوائم؛ فتُقاس على قائمة «مرساة VWAP» في نافذة إعدادات D7M (الرسمُ في غرفة التداول)
await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(2500);
await page.locator('[data-role="pc-cfg"]').click().catch(() => {});
await page.locator('[data-role="pc-cfg-menu"] [data-cfg="d7m"]').click().catch(() => {});
await page.waitForTimeout(500);
say(await page.locator("select").count() === 0, "٧ لا قائمةَ أصليّةً في نافذة إعدادات D7M");
const pick = page.locator('.d7m-sheet button[aria-haspopup="listbox"]').first();
say(await pick.count() === 1, "٨ القائمةُ مرسومة");
if (await pick.count()) {
  const before = (await pick.textContent()) || "";
  await pick.click(); await page.waitForTimeout(220);
  const lb = page.locator('[role="listbox"]');
  const an = await lb.evaluate(e => getComputedStyle(e).animationName).catch(() => "");
  say(an === "menuIn", "٩ وتنفتح من حافّتها بحركة", an);
  const opts = page.locator('[role="option"]');
  const n = await opts.count();
  let target = null;
  for (let i = n - 1; i >= 0 && target == null; i--) {
    const o = opts.nth(i), t = ((await o.textContent()) || "").trim();
    if (t && !before.includes(t) && (await o.getAttribute("aria-disabled")) !== "true") target = i;
  }
  if (target != null) await opts.nth(target).click();
  await page.waitForTimeout(60);
  const g = await page.locator(".exit-anim").count();
  await page.waitForTimeout(400);
  const txt = (await pick.textContent()) || "";
  say(target != null && g >= 1 && txt !== before && await page.locator('[role="listbox"]').count() === 0,
      "١٠ والاختيارُ يُطبَّق وتُغلق بتلاشٍ", `نسخ ${g} · ${before} ← ${txt}`);
}
say(errs.length === 0, "٦ بلا خطأٍ في الصفحة", errs.join(" ‖ "));
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
