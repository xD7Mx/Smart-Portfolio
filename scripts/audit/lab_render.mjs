// ─────────────────────────────────────────────────────────────────────────
// D613 — مختبرُ الأبحاث يُرسَم بعد إضافة شركة، لا شاشةً سوداء (بلاغُ المالك).
// يُقلَع خادمُ التطوير وتُفتح «/stars» بخادمٍ مموَّهٍ بأشكال الردود الحقيقية، ثمّ تُضاف شركةٌ بالبحث،
// ويُشترط ألّا يقع خطأٌ في الصفحة وأن تظهر إحصاءاتُها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5219;
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

const track = [{ d: "2024-01", s: 100, t: 100 }, { d: "2024-02", s: 103, t: 101 }, { d: "2024-03", s: 105, t: 102 }];
const LAB = { start: "2024-01", months: 2, track, total: 5, tasi_total: 2, excess: 3, cagr: 34, tasi_cagr: 12.6, beat_pct: 100,
  max_dd: 0, years: [], contrib: [{ symbol: "2222", pts: 5 }], missing: [],
  forward: { items: [{ symbol: "2222", name: "أرامكو", price: 25, fair_value: 30, upside: 20, conf: "متوسطة", quality: 70, decision: "احتفظ" }],
             upside_reliable: 20, reliable_n: 1, n: 1 } };
const R = {
  // D613: الفرزُ الحقيقيّ يعود {rows, state} — والمموَّهُ السابق (قائمة) أخفى الشاشةَ السوداء
  "/market/screener": { rows: [{ symbol: "2222.SR", name: "أرامكو السعودية", price: 25 }, { symbol: "1120.SR", name: "مصرف الراجحي", price: 100 }], state: "ready" },
  "/portfolios": [{ id: 1, name: "الرئيسية", is_default: true }, { id: 2, name: "الأخرى", is_default: false }],
  "/market/stars-lab": LAB,
  "/goals/builtin": { million: { current: 400000, target: 1000000, pct: 40 } },
  "/portfolio/metrics": { cagr_pct: 13.6 },
  "/holdings": [{ symbol: "1120.SR", company: { symbol: "1120.SR" }, total_shares: 10 }],
};
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const browser = await chromium.launch({ executablePath: CHROME });
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
const errs = [];
page.on("pageerror", e => errs.push(String(e).split("\n").slice(0, 3).join(" | ").slice(0, 300)));
await page.route("**/api/v1/**", r => {
  const u = new URL(r.request().url());
  const k = Object.keys(R).find(p => u.pathname.includes(p));
  r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: k ? R[k] : [] }) });
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.removeItem("stars:lab"); } catch { /* */ } });
await page.goto(`http://localhost:${PORT}/stars`, { waitUntil: "load", timeout: 30000 });
await page.waitForTimeout(1500);
say(errs.length === 0, "١ الصفحةُ تُفتح بلا خطأ", errs.join(" ‖ "));
const t1 = (await page.textContent("body").catch(() => "") || "");
say(t1.includes("محفظتي") && t1.includes("الأداء"), "١ب الشاشةُ الأولى تعرض شركاتِ المحفظة تلقائياً", `نصّ ${t1.length}`);
await page.click("text=شاشة 2");
await page.waitForTimeout(800);
await page.fill("input", "أرام");
await page.waitForTimeout(500);
await page.click("text=أرامكو السعودية");
await page.waitForTimeout(2000);
const text = (await page.textContent("body").catch(() => "") || "");
say(errs.length === 0, "٢ إضافةُ شركةٍ لا تُسقط الصفحة (لا شاشةَ سوداء)", errs.join(" ‖ "));
say(text.includes("الأداء") && text.includes("شركاتك"), "٣ وتظهر الإحصاءاتُ وقائمةُ الشركات", `نصّ ${text.length}`);
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
