// ─────────────────────────────────────────────────────────────────────────
// D617 — كلُّ قائمةٍ منسدلة في التطبيق تُفتح وتختار وتُغلق، صفحةً صفحة (لا عيّنةٌ واحدة).
// يُقلَع خادمُ التطوير وتُفتح «/stars» بخادمٍ مموَّهٍ بأشكال الردود الحقيقية، ثمّ تُضاف شركةٌ بالبحث،
// ويُشترط ألّا يقع خطأٌ في الصفحة وأن تظهر إحصاءاتُها.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5225;
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
const DATA = {
  "/portfolios": [{ id: 1, name: "الرئيسية", is_default: true }, { id: 2, name: "الأخرى" }],
  "/market/screener": { rows: [{ symbol: "2222", name: "أرامكو", sector: "الطاقة", price: 25 }, { symbol: "1120", name: "الراجحي", sector: "البنوك", price: 100 }], state: "ready" },
  "/market/history": Array.from({ length: 300 }, (_, i) => { const t = Date.UTC(2025, 0, 1) / 1000 + i * 86400, c = 30 + Math.sin(i / 9) * 3 + i * 0.02; return { time: t, date: new Date(t * 1000).toISOString().slice(0, 10), open: c - .3, high: c + .6, low: c - .7, close: c, volume: 1e6 + i * 1000 }; }),
  "sectors": [{ sector: "الطاقة" }, { sector: "البنوك" }],
};
let total = 0;
for (let [name, path, opener, w] of [["السوق: الفلاتر (حاسوب)", "/market", "text=فرز السوق|text=الفلاتر"], ["السوق: الفلاتر (جوّال)", "/market", "text=فرز السوق|text=الفلاتر", 400],
                                    ["السوق: فرز السوق", "/market", "text=فرز السوق"], ["الحاسبات", "/calculators", null], ["مختبر الأبحاث", "/stars", null], ["السوق: دليل الشركات", "/market", 'button[aria-label="دليل الشركات"]'],
                                    ["الرسم: إعدادات D7M", "/chart", 'button[aria-label="إعدادات المؤشّر"]'],
                                    ["المحفظة: إضافة شركة", "/portfolio", "button.wealth-act >> nth=2"]]) {
  const page = await browser.newPage({ viewport: { width: w || 1280, height: 900 } });
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 160)));
  await page.route("**/api/v1/**", r => {
    const u = new URL(r.request().url()); const k = Object.keys(DATA).find(p => u.pathname.includes(p));
    r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: k ? DATA[k] : [] }) });
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });
  await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(1800);
  if (path === "/chart") {
    const dd = page.getByRole("button", { name: /SMA20/ }).first();
    if (await dd.count()) { await dd.click(); await page.waitForTimeout(400);
      const t = page.getByRole("button", { name: /^\s*D7M\s*$/ }).first();
      if (await t.count()) { await t.click(); await page.waitForTimeout(600); }
      await page.mouse.click(5, 300); await page.waitForTimeout(400); }
  }
  for (const step of (opener || "").split("|").slice(0, -1)) { const o = page.locator(step).first(); if (await o.count()) { await o.click(); await page.waitForTimeout(700); } }
  if (opener) opener = opener.split("|").pop();
  if (opener) { const o = page.locator(opener).first(); if (await o.count()) { await o.click(); await page.waitForTimeout(600); } else console.log(`     (لم يُعثر على: ${opener})`); }
  const native = await page.locator("select").count();
  // نافذةٌ أو ورقةٌ مفتوحة؟ فما خلفها مغطّى — تُجرَّب قوائمُها وحدها
  const scope = (await page.locator(".drawer-pop:visible, .modal-overlay:visible").count()) ? page.locator(".drawer-pop:visible, .modal-overlay:visible").last() : page;
  const sels = scope.locator('button[aria-haspopup="listbox"]:visible');
  const n = await sels.count();
  let ok = 0; const bad = [];
  for (let i = 0; i < n; i++) {
    const b = sels.nth(i);
    try {
      await b.click(); await page.waitForTimeout(250);
      const opts = page.locator('[role="listbox"] [role="option"]:not([aria-disabled="true"])');
      const c = await opts.count();
      if (!c) { bad.push(`#${i} بلا خيارات · lb=${await page.locator('[role="listbox"]').count()} · all=${await page.locator('[role="option"]').count()} · ${(await b.evaluate(e=>e.getAttribute("aria-expanded")))}`); await page.keyboard.press("Escape"); continue; }
      const want = ((await opts.nth(c - 1).textContent()) || "").trim();
      await opts.nth(c - 1).click(); await page.waitForTimeout(350);
      const shown = ((await b.textContent()) || "").trim();
      if (await page.locator('[role="listbox"]').count() === 0 && shown.includes(want.slice(0, 6))) ok++; else bad.push(`#${i} «${want}» ≠ «${shown}»`);
    } catch (e) { bad.push(`#${i} ${String(e).slice(0, 60)}`); }
  }
  total += ok;
  say(native === 0 && ok === n && errs.length === 0, `«${name}»: ${n} قائمة تعمل كلّها`, [`أصليّة ${native}`, ...bad, ...errs].join(" · "));
  await page.close();
}
console.log("مجموع القوائم المجرَّبة:", total);
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
