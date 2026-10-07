// ─────────────────────────────────────────────────────────────────────────
// D620 — بطاقةُ الإعلان: بلا زرّ «أرقام»، والمشاركةُ تنسخ الخبرَ نفسَه لا رابطَ التطبيق (بلاغُ المالك).
// يُقلَع خادمُ التطوير وتُفتح «/stars» بخادمٍ مموَّهٍ بأشكال الردود الحقيقية، ثمّ تُضاف شركةٌ بالبحث،
// ويُشترط ألّا يقع خطأٌ في الصفحة وأن تظهر إحصاءاتُها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5227;
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
const ctx = await browser.newContext({ viewport: { width: 420, height: 900 }, permissions: ["clipboard-read", "clipboard-write"] });
const page = await ctx.newPage();
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 160)));
const EV = [{ symbol: "1120", company_name: "مصرف الراجحي", title: "صرف أرباح نقدية", type: "DIVIDEND", date: "2026-10-01", url: "https://www.argaam.com/ar/company/x" }];
await page.route("**/api/v1/**", r => {
  const u = new URL(r.request().url());
  const data = u.pathname.includes("events-market") ? EV
    : u.pathname.includes("announcement-text") ? { text: "يسرّ مصرف الراجحي الإعلان عن توزيع أرباح نقدية بواقع 1.25 ريال للسهم.", source: "تداول", url: "https://www.saudiexchange.sa/ann/1" }
    : [];
  r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });
await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1500);
const tab = page.getByRole("button", { name: /مفكرة السوق/ }).first();
if (await tab.count()) { await tab.click(); await page.waitForTimeout(800); }
await page.getByText("صرف أرباح نقدية").first().click();
await page.waitForTimeout(1200);
const box = page.locator(".modal-box").first();
const txt = (await box.textContent()) || "";
say(txt.includes("1.25 ريال"), "١ نصُّ الإعلان يظهر في البطاقة", txt.slice(0, 80));
say(!txt.includes("أرقام"), "٢ ولا زرَّ «افتح في أرقام»");
await box.getByRole("button", { name: /مشاركة/ }).click();
await page.waitForTimeout(400);
const clip = await page.evaluate(() => navigator.clipboard.readText()).catch(() => "");
say(clip.includes("مصرف الراجحي") && clip.includes("1.25") && clip.includes("saudiexchange") && !clip.includes("localhost"),
    "٣ والمشاركةُ تنسخ الخبرَ ومصدرَه الرسميّ لا رابطَ التطبيق", clip.replace(/\n/g, " ⏎ ").slice(0, 160));
say(errs.length === 0, "٤ بلا خطأٍ في الصفحة", errs.join(" ‖ "));
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
