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
const LIM = { stock_max: 15, sector_max: 35, min_adv: 3000000, adv_share: 5, risk_pct: 1, min_rr: 2, heat_max: 6 };
// ‏D754: الأمرُ خطّةُ صفقةٍ كاملة — دخولٌ محدَّدٌ ووقفٌ وهدفٌ وعائدٌ بأضعاف المخاطرة وحجمٌ من مخاطرة 1٪، وحمايةُ المراكز ولوحةُ المخاطر
const ORD = (status = "pending") => ({ id: "2026-11-16-1120-b", symbol: "1120", name: "مصرف الراجحي", side: "شراء", kind: "buy", type: "محدَّد",
  shares: 120, price: 63.35, amount: 7602, confidence: 88, stop: 59.8, stop_basis: "تحت الدعم الأسبوعيّ 61.65", target: 73.4, target_basis: "القيمة العادلة",
  rr: 2.83, risk: 426, risk_pct: 0.04, reward: 1206, sizing: "حاجةُ الهدف", after: { weight: 9.8, cash: 42398 },
  why: "القناعة مكتملة", status, created: "2026-11-16T16:50",
  checks: [{ k: "القناعة مكتملة", ok: true, d: "الحكم · الشهري" }, { k: "العائد ≥ 2 أضعاف المخاطرة", ok: true, d: "الهدف 73.40 · الوقف 59.80 · 1 : 2.8" },
           { k: "مخاطرة الأمر ≤ 1٪ من المحفظة", ok: true, d: "إن ضُرب الوقف: −426 ريال (0.04٪)" },
           { k: "سيولة السهم كافية", ok: true, d: "متوسّط التداول اليوميّ 310.2 مليون ريال" },
           { k: "حجم الأمر ≤ 5٪ من تداول السهم", ok: true, d: "" }, { k: "ضمن حدّ السهم 15٪", ok: true, d: "وزنه 9.0٪ ← 9.8٪" },
           { k: "ضمن حدّ القطاع 35٪", ok: true, d: "البنوك 22.0٪" }] });
const PROT = [
  { symbol: "2222", name: "أرامكو", price: 24.1, stop: 25.2, stop_basis: "تحت الدعم الأسبوعيّ 26.00", target: 28, target_basis: "المقاومة الشهرية", d_stop: -4.56, d_target: 16.2, risk: 0, state: "كُسر الوقف", trail: false, breakeven: false },
  { symbol: "1120", name: "مصرف الراجحي", price: 63.35, stop: 61.8, stop_basis: "ثلاثةُ أضعاف المدى اليوميّ", target: 73.4, target_basis: "القيمة العادلة", d_stop: 2.45, d_target: 15.9, risk: 1860, state: "قريب من الوقف", trail: true, breakeven: false },
  { symbol: "7010", name: "إس تي سي", price: 42.5, stop: 39.1, stop_basis: "على سعر التكلفة — الربحُ محميّ", target: null, target_basis: "لا هدفَ فوق السعر", d_stop: 8, d_target: null, risk: 3400, state: "محميّ", trail: true, breakeven: true }];
const RISK = { heat: 5260, heat_pct: 1.05, heat_max: 6, cash: 50000, cash_pct: 10, top_stock: { name: "مصرف الراجحي", w: 9, max: 15 },
  top_sector: { name: "البنوك", w: 22, max: 35 }, no_stop: 0, broken: 1, near: 1, n: 3 };
const VIEW = (status, paused = false) => ({ paused, limits: LIM, orders: paused ? [] : [ORD(status)], history: [], asof: "2026-11-16T16:50",
  held: [{ symbol: "2222", name: "أرامكو", why: "قطاعُه بلغ حدَّه 35٪" }], protect: PROT, risk: RISK,
  record: { n: 0, measure_days: 30, plans: { n: 4, target: 2, stop: 1, open: 1, avg_r: 1.2 } } });
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
  if (process.env.SHOTS) await page.locator('[data-role="robo"]').screenshot({ path: `${process.env.SHOTS}/robo-${vp.width}.png` }).catch(() => {});
  const card = await page.locator('[data-role="robo-order"]').first().textContent().catch(() => "");
  const checks = await page.locator('[data-role="robo-order"] .robo-checks li').count();
  const gates = await page.locator('[data-role="robo-gates"]').first().textContent().catch(() => "");
  say(/120/.test(card) && /63\.35/.test(card) && /7,602/.test(card) && /88٪/.test(card) && checks === 7 && /اجتاز 7 من 7/.test(gates || ""),
      `${label}: ١ الأمرُ بأرقامه — 120 سهماً عند 63.35 = 7,602 ريال، وثقتُه، وبوّاباتُه السبع مطويّةً بعددها`, (card || "").slice(0, 90));
  const lad = await page.locator('[data-role="robo-ladder"]').first().textContent().catch(() => "");
  const met = await page.locator('[data-role="robo-metrics"]').first().textContent().catch(() => "");
  const siz = await page.locator('[data-role="robo-sizing"]').first().textContent().catch(() => "");
  say(/وقف 59\.80/.test(lad || "") && /دخول 63\.35/.test(lad || "") && /هدف 73\.40/.test(lad || "") && /1 : 2\.8/.test(met || "") && /−426/.test(met || "")
      && /\+1,206/.test(met || "") && /حاجةُ الهدف/.test(siz || ""),
      `${label}: ١ب ‏D754 تذكرةُ الصفقة: سلّمُ الوقف والدخول والهدف، والعائدُ بأضعاف المخاطرة، وما يُخسر لو ضُرب الوقف، والقيدُ الذي حكم الحجم`, `${lad} | ${met}`);
  const risk = await page.locator('[data-role="robo-risk"] .robo-tile').allTextContents().catch(() => []);
  say(risk.length === 4 && /−5,260/.test(risk[0]) && /1\.05٪/.test(risk[0]) && /مصرف الراجحي/.test(risk[2]) && /البنوك/.test(risk[3]),
      `${label}: ١ج ‏D754 لوحةُ المخاطر: ما تخسره المحفظةُ لو ضُربت الوقوفُ كلُّها، والنقد، وأكبرُ سهمٍ وقطاعٍ بحدّيهما`, risk.join(" | ").slice(0, 120));
  const rows = await page.locator('[data-role="robo-prot-row"]').evaluateAll(es => es.map(e => e.dataset.state));
  const ptxt = await page.locator('[data-role="robo-protect"]').textContent().catch(() => "");
  say(rows.length === 3 && rows[0] === "كُسر الوقف" && /على التكلفة/.test(ptxt || "") && /25\.20/.test(ptxt || "") && /1 كُسر وقفُه/.test(ptxt || ""),
      `${label}: ١د ‏D754 حمايةُ كلّ مركز: وقفُه وهدفُه ومسافتاهما وحالُه — والمكسورُ أوّلاً`, rows.join(" · "));
  const lims = await page.locator('[data-role="robo-limits"]').textContent().catch(() => "");
  const rec = await page.locator('[data-role="robo-record"]').textContent().catch(() => "");
  say(/حدّ السهم 15٪/.test(lims) && /حدّ القطاع 35٪/.test(lims) && /3 مليون/.test(lims) && /مخاطرة الأمر ≤ 1٪/.test(lims) && /العائد ≥ 2/.test(lims)
      && /2 بلغت هدفها/.test(rec || "") && /1 ضُرب وقفها/.test(rec || "") && /\+1\.2R/.test(rec || ""),
      `${label}: ٢ الحدودُ وسجلُّ الخطط (بلغ هدفَه · ضُرب وقفُه · متوسّطُ الناتج) ظاهرة`, rec || "");
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
  say(/أرامكو/.test(held || "") && /حدَّه 35٪/.test(held || ""), `${label}: ٥ والمؤجّلُ بشروطه يُذكر بسببه`);
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
