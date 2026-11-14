// ─────────────────────────────────────────────────────────────────────────
// D731 (بأمر المالك 2026-11-14): «إدارة السيولة… ما عجبني التصميم، عيد التصميم… أبغاها أوتوماتيكية — يعرف الشركات
// وأوزانها المستهدفة ويعرف الرصيد… تخصيصُ بعض الأشياء، لكن أوامر الشراء أوتوماتيكية».
// الحالُ قبله: قيمةُ دفعةٍ ونسبةٌ لكلّ شركةٍ وخمسةُ مربّعاتٍ تؤشَّر، ثمّ عددُ دفعاتٍ يُكتب لكلّ أمر — كلُّه باليد.
// ١–٨ سلوكيّ: ‏buildOrders نفسُها (لا نسخةٌ منها) على محافظَ عشوائيّة — لا يتجاوز مجموعٌ ميزانيتَه أبداً.
// ٩–… المتصفّح: التطبيقُ الحقيقيّ (‏vite) والخادمُ مُحاكًى — الأوامرُ تظهر وحدها، والتخصيصُ يحرّكها، والتسجيلُ يعبّئ المعاملة.
//    SHOTS=dir node scripts/audit/liquidity_orders_d731.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };

const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const out = join(mkdtempSync(join(tmpdir(), "sp-d731-")), "allocMath.mjs");
await build({ entryPoints: [join(FRONT, "src/lib/allocMath.ts")], outfile: out, format: "esm", bundle: false, logLevel: "silent" });
const M = await import(pathToFileURL(out).href);
if (typeof M.buildOrders !== "function") { say(false, "١ دالّةُ الأوامر الآليّة موجودة"); console.log("\nالنتيجة: عطب ✖"); process.exit(1); }
const { buildOrders } = M;

// محفظة: نقد 30,000 · الراجحي 6,400 (هدف 30٪) · أرامكو 12,000 (هدف 40٪) · سدافكو 3,000 (هدف 30٪) ⇒ رأسُ المال 51,400
const R = [
  { company_id: 1, px: 64, market_value: 6400, target_weight: 30 },
  { company_id: 2, px: 25, market_value: 12000, target_weight: 40 },
  { company_id: 3, px: 178.6, market_value: 3000, target_weight: 30 },
];
const INV = 51400;
const a = buildOrders(R, { investable: INV, budget: 30000 });
const needs = a.orders.map(o => +o.need.toFixed(2));
say(JSON.stringify(needs) === JSON.stringify([9020, 8560, 12420]) && Math.abs(a.needTotal - 30000) < 1e-6,
    "١ حاجةُ كلّ شركة = ما ينقصها لهدفها من رأس المال كلّه (30٪ × 51,400 − 6,400 = 9,020 …) ومجموعُها النقدُ كلُّه", JSON.stringify(needs));
say(a.spent <= 30000 + 1e-9 && a.orders.every(o => Number.isInteger(o.shares)) && a.left >= -1e-9 && a.left < 178.6,
    "٢ أسهمٌ صحيحة، والمجموعُ لا يتجاوز الميزانية، والباقي دون سعر أغلى سهم", `${a.spent.toFixed(2)} · باقٍ ${a.left.toFixed(2)}`);
const half = buildOrders(R, { investable: INV, budget: 15000 });
say(half.spent <= 15000 && half.orders.every((o, i) => Math.abs(o.alloc - needs[i] / 2) < 1e-6),
    "٣ ميزانيةٌ دون الحاجات (دفعةٌ من اثنتين): تُقسَم بنسب الحاجات — نصفُ كلّ حاجة", half.orders.map(o => o.shares).join(","));
const ex = buildOrders(R, { investable: INV, budget: 30000, excluded: new Set([2]) });
say(ex.orders[1].shares === 0 && ex.orders[0].shares <= Math.ceil(9020 / 64) && ex.orders[2].shares <= Math.ceil(12420 / 178.6),
    "٤ المستبعدةُ لا تأخذ شيئاً، ولا تُضخَّم أختُها فوق هدفها (سهمٌ زائدٌ بالتقريب على الأكثر)", ex.orders.map(o => o.shares).join(","));
const fee = buildOrders(R, { investable: INV, budget: 30000, feePct: 0.155 });
say(fee.spent + fee.fees <= 30000 + 1e-6 && fee.fees > 0, "٥ والعمولةُ تُحجز أوّلاً: الأوامرُ بعمولتها لا تتجاوز ما في الحساب",
    `${(fee.spent + fee.fees).toFixed(2)} ≤ 30,000`);
const over = buildOrders([{ company_id: 1, px: 64, market_value: 30000, target_weight: 30 }, ...R.slice(1)], { investable: 75000, budget: 30000 });
say(over.orders[0].shares === 0, "٦ الشركةُ فوق هدفها لا يُشترى منها");
// خاصيّة: على مئات المحافظ العشوائيّة لا يتجاوز المجموعُ بعمولته الميزانيةَ، ولا تأخذ شركةٌ أكثرَ من حاجتها إلا سهماً
let worst = 0, overNeed = 0, seed = 7;
const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
for (let k = 0; k < 400; k++) {
  const n = 1 + Math.floor(rnd() * 8);
  const rows = Array.from({ length: n }, (_, i) => ({ company_id: i + 1, px: +(1 + rnd() * 300).toFixed(2),
    market_value: Math.round(rnd() * 50000), target_weight: Math.round(rnd() * 30) }));
  const cash = Math.round(rnd() * 80000), inv = rows.reduce((s, r) => s + r.market_value, 0) + cash;
  const b = rnd() < .5 ? cash : cash / (2 + Math.floor(rnd() * 4));
  const f = rnd() < .5 ? 0 : +(rnd() * .3).toFixed(3);
  const p = buildOrders(rows, { investable: inv, budget: b, feePct: f });
  worst = Math.max(worst, p.spent + p.fees - b);
  for (const o of p.orders) if (o.cost > o.need + o.px + 1e-6) overNeed++;
}
say(worst <= 1e-6 && overNeed === 0, "٧ على 400 محفظةٍ عشوائيّة: لا تجاوزَ للميزانية بعمولتها، ولا أمرَ فوق حاجته بأكثر من سهم",
    `أسوأ تجاوز ${worst.toExponential(1)} · ${overNeed}`);
const src = readFileSync(join(FRONT, "src/components/portfolio/LiquidityTab.tsx"), "utf-8");
say(/buildOrders\(priced\.rows/.test(src) && !/liquidityApi/.test(src) && !/tranches\.map/.test(src),
    "٨ الشاشةُ تشتقّ الأوامرَ من الدالّة — لا مربّعاتِ دفعاتٍ ولا نسبَ تُكتب ولا خطّةَ تُحفظ في الخادم");

// ── المتصفّح ──
const PORT = 5254;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر فحصُ المتصفّح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const NAMES = ["مصرف الراجحي", "أرامكو السعودية", "سدافكو"], SYMS = ["1120", "2222", "2270"];
const ITEMS = R.map((r, i) => ({ company_id: r.company_id, symbol: SYMS[i], name: NAMES[i], last_price: r.px, quantity: r.market_value / r.px,
  market_value: r.market_value, current_weight: +(r.market_value / INV * 100).toFixed(2), target_weight: r.target_weight,
  reinvest_share: [600, 800, 600][i], sharia_status: "pure" }));
const ALLOC = { items: ITEMS, reinvestment_pool: 2000, fresh_cash: 28000, available_cash: 30000, investable: INV };
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", r => {
    const p = new URL(r.request().url()).pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/allocation") return r.fulfill(body(ALLOC));
    if (/^\/holdings\/\d+$/.test(p)) return r.fulfill(body({ total_shares: 100, average_cost: 50, invested_amount: 5000 }));
    if (p === "/cash") return r.fulfill(body({ available_cash: 30000 }));
    return r.fulfill(body([]));
  });
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe"); localStorage.removeItem("sp.liq.v2");
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/portfolio`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1800);
  await page.locator("nav button", { hasText: "لوحة التحكم" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(300);
  await page.locator("button:visible", { hasText: "إدارة السيولة" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1200);
  const read = () => page.evaluate(() => [...document.querySelectorAll('[data-role="liq-order"]')].map(c =>
    Number((c.querySelector('[data-role="liq-shares"] span[dir="ltr"]')?.textContent || "").replace(/,/g, "")) || 0));
  const total = () => page.evaluate(() => Number((document.querySelector('[data-role="liq-total"] .ms-auto')?.textContent || "").replace(/[^\d.]/g, "")));
  const s0 = await read();
  const exp = a.orders.map(o => o.shares);
  say(JSON.stringify(s0) === JSON.stringify(exp) && Math.abs(await total() - a.spent) < 0.01,
      `${label}: الأوامرُ تظهر وحدها — أسهمُ كلّ شركةٍ كما تحسبها الدالّة، والمجموعُ ${a.spent.toFixed(2)}`, `${s0} · ${exp}`);
  const noOld = await page.evaluate(() => !document.querySelector('[data-role="liq"] input[type="checkbox"]') && !/النسبة المستهدفة %/.test(document.body.textContent));
  say(noOld, `${label}: لا مربّعاتِ دفعاتٍ ولا نسبَ تُكتب باليد`);
  await page.locator('[data-role="liq-controls"] button', { hasText: "دفعات" }).click();
  await page.waitForTimeout(250);
  const t2 = await total();
  say(t2 <= 15000 && t2 > 14000, `${label}: «دفعات 1/2» — الأوامرُ لنصف السيولة`, `${t2}`);
  await page.locator('[data-role="liq-controls"] button', { hasText: "كل السيولة" }).click();
  await page.locator('[data-role="liq-toggle"]').nth(1).click();
  await page.waitForTimeout(300);
  const s3 = await read();
  say(s3[1] === 0 && s3[0] === ex.orders[0].shares && s3[2] === ex.orders[2].shares,
      `${label}: استبعادُ أرامكو يُخرجها، ولا يضخّم أختيها`, `${s3}`);
  await page.locator('[data-role="liq-toggle"]').nth(1).click();
  const px = page.locator('[data-role="liq-price"]').first();
  await px.click(); await px.press("Control+a"); await px.pressSequentially("60", { delay: 50 }); await px.press("Enter");
  await page.waitForTimeout(300);
  const s4 = await read();
  const R4 = M.repriceRows(ITEMS, { 1: "60" }, INV);
  const exp4 = buildOrders(R4.rows.map(r => ({ ...r, px: r.px })), { investable: R4.investable, budget: 30000 }).orders.map(o => o.shares);
  say(JSON.stringify(s4) === JSON.stringify(exp4), `${label}: سعرُ الراجحي 60 يُعيد أوامرَه (والأوزانَ كلَّها)`, `${s4} · ${exp4}`);
  const m = await page.evaluate(() => {
    const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const root = document.querySelector('[data-role="liq"]');
    const t = [...root.querySelectorAll("button, input")].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height);
    const f = [...root.querySelectorAll("*")].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
      .map(e => parseFloat(getComputedStyle(e).fontSize));
    return { over: sw - W, minT: Math.min(...t), minF: Math.min(...f), ar: /[٠-٩]/.test(root.textContent) };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5 && !m.ar, `${label}: لا فيضَ أفقيّ، ولمسٌ ≥ 32px، وخطٌّ ≥ 9.5px، وأرقامٌ لاتينية`,
      `${m.over}px · ${Math.round(m.minT)}px · ${m.minF}px`);
  if (SHOTS) { const el = await page.$('[data-role="liq"]'); if (el) await el.screenshot({ path: join(SHOTS, `liq_${vp.width}_${theme}.png`) }); }
  await page.locator('[data-role="liq-record"]').first().click();
  await page.waitForTimeout(700);
  const vals = await page.locator(".modal-box input[inputmode]").evaluateAll(es => es.slice(0, 2).map(e => e.value));
  say(vals[0] === String(s4[0]) && vals[1] === "60", `${label}: «سجّل التنفيذ» يفتح المعاملة بعدد الأمر وسعره`, JSON.stringify(vals));
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
