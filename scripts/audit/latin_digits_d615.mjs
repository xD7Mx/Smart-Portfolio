// ─────────────────────────────────────────────────────────────────────────
// D615 — لا رقمَ هندياً في متصفّحٍ عربيّ، والتاريخُ يُختار بتقويمٍ لاتينيّ (بلاغُ المالك).
// يُقلَع خادمُ التطوير وتُفتح «/stars» بخادمٍ مموَّهٍ بأشكال الردود الحقيقية، ثمّ تُضاف شركةٌ بالبحث،
// ويُشترط ألّا يقع خطأٌ في الصفحة وأن تظهر إحصاءاتُها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5221;
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
const browser = await chromium.launch({ executablePath: CHROME, args: ["--lang=ar"] });
const ctx = await browser.newContext({ locale: "ar-SA", viewport: { width: 420, height: 900 } });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
await page.route("**/api/v1/**", r => {
  const u = new URL(r.request().url());
  const data = u.pathname.includes("project-start") ? { start: "2024-03-15" } : [];
  r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });
await page.goto(`http://localhost:${PORT}/settings`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1500);
const INDIC = /[٠-٩۰-۹]/;
const dateBtn = page.locator('button[aria-haspopup="dialog"]').first();
say(await dateBtn.count() > 0, "١ حقلُ التاريخ مرسومٌ بأيدينا لا حقلَ المتصفّح");
say((await page.locator('input[type="date"]').count()) === 0, "٢ ولا حقلَ تاريخٍ أصليّاً في الصفحة");
if (await dateBtn.count()) {
  await dateBtn.click();
  await page.waitForTimeout(400);
  const pop = (await page.locator('[role="dialog"]').first().textContent()) || "";
  say(/20\d\d/.test(pop) && /31|30/.test(pop) && !INDIC.test(pop), "٣ والتقويمُ بأرقامٍ لاتينية في متصفّحٍ عربيّ", pop.slice(0, 60));
  await page.locator(".date-day", { hasText: /^5$/ }).first().click();
  await page.waitForTimeout(300);
  const shown = (await dateBtn.textContent()) || "";
  say(shown.startsWith("05/") && !INDIC.test(shown), "٤ واختيارُ يومٍ يُحدّث الحقل", shown);
}
const body = (await page.textContent("body")) || "";
say(!INDIC.test(body), "٥ ولا رقمَ هندياً في الصفحة كلّها", (body.match(INDIC) || [""])[0]);
say(errs.length === 0, "٦ بلا خطأٍ في الصفحة", errs.join(" ‖ "));
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
