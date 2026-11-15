// ─────────────────────────────────────────────────────────────────────────
// D750 — أوامرُ المستشار الآليّ على منهج «سندباد» (بأمر المالك 2026-11-16): الأمرُ بأرقامه وثقتِه وبوّاباتِه، واعتمادُ المالك أو رفضُه،
// والإيقافُ والاستئناف، والحدودُ وسجلُّ الدقّة — في بطاقة «المستشار الآلي» بلا خطأٍ ولا فيضٍ وبأهدافِ لمسٍ ≥ 32px.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5250;
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
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const LIM = { stock_max: 15, sector_max: 35, min_adv: 3000000, adv_share: 5 };
const ORD = (status = "pending") => ({ id: "2026-11-16-1120-b", symbol: "1120", name: "مصرف الراجحي", side: "شراء", shares: 120, price: 63.35, amount: 7602,
  confidence: 88, why: "القناعة مكتملة", status, created: "2026-11-16T16:50",
  checks: [{ k: "القناعة مكتملة", ok: true, d: "الحكم · الشهري" }, { k: "سيولة السهم كافية", ok: true, d: "متوسّط التداول اليوميّ 310.2 مليون ريال" },
           { k: "حجم الأمر ≤ 5٪ من تداول السهم", ok: true, d: "" }, { k: "ضمن حدّ السهم 15٪", ok: true, d: "وزنه 9.0٪ ← 9.8٪" },
           { k: "ضمن حدّ القطاع 35٪", ok: true, d: "البنوك 22.0٪" }] });
const VIEW = (status, paused = false) => ({ paused, limits: LIM, orders: paused ? [] : [ORD(status)], history: [], asof: "2026-11-16T16:50",
  held: [{ symbol: "2222", name: "أرامكو", why: "قطاعُه بلغ حدَّه 35٪" }], record: { n: 0, measure_days: 30 } });
const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(5000);
  const errs = [], posts = [];
  let state = VIEW("pending");
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (p === "/ai/robo" && m === "GET") return r.fulfill(body(state));
    if (p.startsWith("/ai/robo/orders/")) { posts.push(p); state = VIEW(p.endsWith("/approve") ? "approved" : "rejected"); return r.fulfill(body(state)); }
    if (p === "/ai/robo/pause") { const b = JSON.parse(r.request().postData() || "{}"); posts.push("pause:" + b.paused); state = VIEW("pending", !!b.paused); return r.fulfill(body(state)); }
    if (p === "/ai/portfolio-autopilot") return r.fulfill(body({ verdict: "المحفظة على مسارها.", actions: [], flags: [], asof: "2026-11-16" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/ai?tab=advisor`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const card = await page.locator('[data-role="robo-order"]').first().textContent().catch(() => "");
  const checks = await page.locator('[data-role="robo-order"] .robo-checks li').count();
  say(/120/.test(card) && /63\.35/.test(card) && /7,602/.test(card) && /ثقة 88٪/.test(card) && checks === 5,
      `${label}: ١ الأمرُ بأرقامه — 120 سهماً × 63.35 = 7,602 ريال، وثقتُه، وبوّاباتُه الخمس`, (card || "").slice(0, 90));
  const lims = await page.locator('[data-role="robo-limits"]').textContent().catch(() => "");
  say(/حدّ السهم 15٪/.test(lims) && /حدّ القطاع 35٪/.test(lims) && /3 مليون/.test(lims) && /5٪ من تداول السهم/.test(lims) && /دقّة المستشار/.test(lims),
      `${label}: ٢ الحدودُ وسجلُّ الدقّة ظاهرة`);
  const st0 = await page.locator('[data-role="robo-status"]').first().textContent().catch(() => "");
  await page.locator('[data-role="robo-approve"]').first().click().catch(() => {}); await page.waitForTimeout(600);
  const st1 = await page.locator('[data-role="robo-status"]').first().textContent().catch(() => "");
  say(st0 === "بانتظار اعتمادك" && posts.includes("/ai/robo/orders/2026-11-16-1120-b/approve") && /معتمد/.test(st1 || "")
      && await page.locator('[data-role="robo-approve"]').count() === 0, `${label}: ٣ «اعتماد» يعتمد الأمرَ كمدير المحفظة — وتختفي أزرارُه`, `${st0} ← ${st1}`);
  await page.locator('[data-role="robo-pause"]').click().catch(() => {}); await page.waitForTimeout(600);
  const paused = await page.locator('[data-role="robo-state"]').textContent().catch(() => "");
  const empty = await page.locator('[data-role="robo-empty"]').textContent().catch(() => "");
  say(posts.includes("pause:true") && paused === "موقوف" && /موقوف/.test(empty || ""), `${label}: ٤ الإيقافُ يُسكت الأوامر ويقول ذلك`);
  await page.locator('[data-role="robo-held"] summary').click().catch(() => {}); await page.waitForTimeout(300);
  const held = await page.locator('[data-role="robo-held"]').textContent().catch(() => "");
  say(/أرامكو/.test(held || "") && /حدَّه 35٪/.test(held || ""), `${label}: ٥ والمؤجّلُ بالبوّابات يُذكر بسببه`);
  const m = await page.evaluate(() => {
    const r = document.querySelector('[data-role="robo"]'); const W = document.documentElement.clientWidth;
    let minT = 99, minF = 99;
    r.querySelectorAll("button, summary").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height) minT = Math.min(minT, x.height); });
    r.querySelectorAll("*").forEach(e => { if (e.childElementCount === 0 && e.textContent.trim()) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    return { over: document.documentElement.scrollWidth - W, minT, minF };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5, `${label}: ٦ لا فيض، وأهدافُ اللمس ≥ 32px، والخطُّ ≥ 9.5px`, JSON.stringify(m));
  say(errs.length === 0, `${label}: ٧ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
