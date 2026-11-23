// ─────────────────────────────────────────────────────────────────────────
// D788 — بأمر المالك (2026-11-23): «التطبيقُ يدعم تعدّدَ المحافظ — هل سيدعمها التقرير؟ خلِّ فيه خياراً: إدخالُ المحفظة أو التقريرُ بدون محفظة،
// وفي السويتش نفسِه: للمحافظ كاملةً أو لمحفظةٍ معيّنة».
//   ١ مبدّلُ «محفظة التقرير» فوق الأيام: بلا محفظة · كلّ المحافظ (إن تعدّدت) · كلُّ محفظةٍ باسمها — والطلبُ يحمل اختيارَه (‏pf)، و«بلا محفظة»
//     صفحاتُ السوق وحدها، والاختيارُ يُحفظ.
//   ٢ يومٌ لم يُكتب له تقريرُ المحافظ مجتمعةً يقول ذلك صراحةً — ولا يدّعي.
//   ٣ لمسٌ ≥ 32 وخطٌّ ≥ 9.5 وبلا فيض — في المظهرين على الحاسوب والجوال.
//    SHOTS=dir node scripts/audit/chart_d788.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const PORT = 5288;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await new Promise(r => setTimeout(r, 500)); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const SHOTS = process.env.SHOTS;
const HEAD = { date: "2026-11-23", label: "الاثنين 23 نوفمبر 2026", headline: "عنوان", close: 11500, pct: 0.3, view: "احتفاظ", picks: 1 };
const DATES = [{ date: "2026-11-23", label: "الاثنين 23 نوفمبر 2026" }, { date: "2026-11-22", label: "الأحد 22 نوفمبر 2026" }];
const PAPER = (part, pf) => `<!doctype html><html lang="ar" dir="rtl"><body style="margin:0"><section class="page" style="min-height:900px"><h1>التقرير اليومي</h1>`
  + (part === "market" ? "" : `<h1 data-pf="${pf}">محفظتنا واختياراتنا</h1>`) + "</section></body></html>";
const PFS = [{ id: 1, name: "محفظتي", is_archived: false }, { id: 2, name: "المضاربية", is_archived: false }];

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [], reqs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d788-init")) return;
    sessionStorage.setItem("d788-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_active_portfolio", "1"); localStorage.removeItem("sp_report_pf");
    sessionStorage.setItem("sp:market:tab", "calendar");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/market/research-desk") { reqs.push(["head", u.searchParams.get("pf") || ""]);
      const pf = u.searchParams.get("pf") || "";
      return r.fulfill(body({ report: HEAD, dates: DATES, running: { on: false }, pf, market_only: pf === "none" || (pf === "all" && u.searchParams.get("day") === "2026-11-22") })); }
    if (p === "/market/research-desk/paper") { reqs.push(["paper", u.searchParams.get("pf") || "", u.searchParams.get("part")]);
      return r.fulfill(body({ html: PAPER(u.searchParams.get("pf") === "none" ? "market" : "all", u.searchParams.get("pf") || "1"), date: "2026-11-23" })); }
    if (p === "/portfolios") return r.fulfill(body(PFS));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500); await paint();
  await page.locator('[data-role="ev-report"]').click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const chips = await page.locator('[data-role="rl-pf"] .seg-btn').evaluateAll(bs => bs.map(b => [b.getAttribute("data-v"), b.textContent.trim(), b.getAttribute("aria-pressed")]));
  const h1s = () => page.evaluate(() => [...(document.querySelector('[data-role="rl-doc"] iframe')?.contentDocument?.querySelectorAll("h1") || [])].map(h => h.textContent));
  const first = await h1s();
  await page.locator('[data-role="rl-pf"] [data-v="none"]').click(); await page.waitForTimeout(1200);
  const none = await h1s();
  await page.locator('[data-role="rl-pf"] [data-v="all"]').click(); await page.waitForTimeout(1200);
  const all = await h1s();
  const saved = await page.evaluate(() => localStorage.getItem("sp_report_pf"));
  await page.locator('[data-role="rl-day"]').nth(1).click().catch(() => {}); await page.waitForTimeout(1200);
  const note = await page.locator('[data-role="rl-pf-note"]').textContent().catch(() => "");
  await page.locator('[data-role="rl-pf"] [data-v="2"]').click(); await page.waitForTimeout(1200);
  const p2 = await page.evaluate(() => document.querySelector('[data-role="rl-doc"] iframe')?.contentDocument?.querySelector("[data-pf]")?.getAttribute("data-pf"));
  if (SHOTS) await page.locator('[data-role="daily-report"]').screenshot({ path: `${SHOTS}/d788-switch-${vp.width}-${theme}.png` }).catch(() => {});
  say(JSON.stringify(chips.map(c => c[0])) === '["none","all","1","2"]' && chips.find(c => c[0] === "1")[2] === "true" && first.length === 2
      && none.length === 1 && reqs.some(x => x[0] === "paper" && x[1] === "none") && all.length === 2 && reqs.some(x => x[0] === "paper" && x[1] === "all")
      && saved === "all" && p2 === "2",
    `${label}: ١ مبدّلُ «محفظة التقرير»: بلا محفظة (صفحاتُ السوق وحدها) · كلّ المحافظ · كلُّ محفظةٍ باسمها — والنشطةُ مختارةٌ ابتداءً، والطلبُ يحمل الاختيار ويُحفظ`,
    JSON.stringify({ chips: chips.map(c => c[0]), first, none, all, saved, p2 }));
  say(/لم يُكتب تقريرُ المحافظ مجتمعةً لهذا اليوم/.test(note || ""), `${label}: ٢ يومٌ لم يُكتب له تقريرُ المحافظ مجتمعةً يقول ذلك صراحةً (صفحاتُ السوق وحدها)`, note || "");
  const m = await page.evaluate(() => { const r = document.querySelector('[data-role="daily-report"]'); const W = document.documentElement.clientWidth; let minT = 99, minF = 99;
    r?.querySelectorAll('[data-role="rl-pf"] button').forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height) minT = Math.min(minT, x.height); });
    r?.querySelectorAll('[data-role="rl-pf"] *, [data-role="rl-pf-note"]').forEach(e => { if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
      minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    const main = document.querySelector(".app-main");
    return { minT, minF, over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W }; });
  say(m.minT >= 32 && m.minF >= 9.5 && m.over <= 1 && errs.length === 0, `${label}: ٣ لمسٌ ≥ 32 وخطٌّ ≥ 9.5 وبلا فيض — ولا خطأ`, JSON.stringify({ ...m, err: errs[0] || "" }));
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
