// ─────────────────────────────────────────────────────────────────────────
// D789 — بأمر المالك (2026-11-23): «هل المحفظةُ تدعم شركاتٍ أمريكية؟ هل المعاملاتُ ستكون صحيحة؟ هل ستدعمها الرسوم؟ أبغاها تدعم
// السوقين كاملَين — البحثَ والمحفظةَ نفسَها».
//   ١ جدولُ الحيازات: السهمُ الأمريكيّ بسعرٍ مُعلَمٍ بالدولار ومتوسّطِ تكلفةٍ بالدولار، وقيمتُه بالريال (رقمُ الخادم)؛ والقديمُ بلا سعر صرفٍ
//     تعلوه علامةٌ ظاهرة، والسعوديُّ كما كان بلا علامة دولار.
//   ٢ نافذةُ المعاملة للأمريكيّ: «سعر السهم بالدولار» وحقلُ سعر الصرف بسعر اليوم ومصدرِه، والإجماليُّ بالعملتين؛ والمعاينةُ والحفظُ يحملان سعرَ الصرف.
//   ٣ «إضافة شركة»: الحرفُ اللاتينيُّ يبحث في السوق الأمريكي، واختيارُه يجعل السوقَ أمريكياً والعملةَ دولاراً (عرضٌ لا اختيار).
//   ٤ لمسٌ ≥ 32 وخطٌّ ≥ 9.5 وبلا فيضٍ أفقيّ — في المظهرين على الحاسوب والجوال.
//    SHOTS=dir node scripts/audit/us_stocks_d789.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PORT = 5289;
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
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const body = (data, status = 200) => ({ status, contentType: "application/json",
  body: JSON.stringify(status === 200 ? { success: true, data } : { detail: data }) });
const SHOTS = process.env.SHOTS;
const FX = { rate: 3.7521, source: "live", source_ar: "حيّ", at: "2026-11-23T23:51:17Z", pair: "USD/SAR", peg: 3.75 };
const co = (id, symbol, name, currency, extra = {}) => ({ id, symbol, name, name_ar: name, company_name: name, currency, sector: "", ...extra });
// كما يعيدها الخادم (‏_serialize): المالُ بالريال، والسعرُ ومتوسّطُ التكلفة بعملة الشركة باسمهما
const H = [
  { id: 1, company_id: 1, company: co(1, "AAPL", "Apple Inc.", "USD", { exchange: "NASDAQ" }), currency: "USD", fx_rate: 3.7521, fx_legacy: false,
    quantity: 6, total_shares: 6, invested_amount: 4279.53, total_cost: 4279.53, invested_native: 1140.6, average_cost_native: 190.1,
    average_cost: 713.26, last_price: 200, market_value: 4502.52, current_value: 4502.52, unrealized_profit: 222.99, change_pct: 0.5,
    total_dividends_received: 5.63, sort_order: 1 },
  { id: 2, company_id: 2, company: co(2, "MSFT", "Microsoft", "USD"), currency: "USD", fx_rate: 1.0, fx_legacy: true,
    quantity: 5, total_shares: 5, invested_amount: 1900, total_cost: 1900, invested_native: null, average_cost_native: null,
    average_cost: 380, last_price: 400, market_value: 2000, current_value: 2000, unrealized_profit: 100, change_pct: 0.2,
    total_dividends_received: 0, sort_order: 2 },
  { id: 3, company_id: 3, company: co(3, "2222", "أرامكو السعودية", "SAR"), currency: "SAR", fx_rate: 1.0, fx_legacy: false,
    quantity: 100, total_shares: 100, invested_amount: 2740.47, total_cost: 2740.47, invested_native: null, average_cost_native: null,
    average_cost: 27.4, last_price: 26.14, market_value: 2614, current_value: 2614, unrealized_profit: -126.47, change_pct: -0.46,
    total_dividends_received: 35, sort_order: 3 },
];
const ALLOC = { items: [{ company_id: 1, symbol: "AAPL", name: "Apple Inc.", last_price: 200, fx_rate: 3.7521, currency: "USD", quantity: 6,
  market_value: 4502.52, current_weight: 10, target_weight: 0 }], reinvestment_pool: 0, fresh_cash: 30000, available_cash: 30000, investable: 39116.52 };

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [], posts = [], previews = [], searches = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_active_portfolio", "1"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/market/fx") return r.fulfill(body(FX));
    if (p === "/market/symbol-search") { searches.push(u.searchParams.get("q"));
      return r.fulfill(body([{ symbol: "AAPL", name: "Apple Inc.", type: "EQUITY", exchange: "NASDAQ", us: true },
                             { symbol: "AAPL250117C00200000", name: "AAPL Jan 2025 200 Call", type: "OPTION", exchange: "OPR", us: true }])); }
    if (p === "/transactions/funding-preview") {
      previews.push({ q: Number(u.searchParams.get("quantity")), px: Number(u.searchParams.get("price")), fx: u.searchParams.get("fx_rate") });
      const q = Number(u.searchParams.get("quantity")), px = Number(u.searchParams.get("price")), f = Number(u.searchParams.get("fx_rate") || 1);
      return r.fulfill(body({ reinvest_qty: 0, liquidity_qty: q, reinvest_amount: 0, liquidity_amount: +(q * px * f).toFixed(2),
        company_share: 0, headroom: 0, unit_cost: px * f }));
    }
    if (p === "/transactions" && r.request().method() === "POST") { posts.push(JSON.parse(r.request().postData() || "{}")); return r.fulfill(body({ id: 9, split: null })); }
    if (p === "/holdings") return r.fulfill(body(H));
    const m = p.match(/^\/holdings\/(\d+)$/);
    if (m) return r.fulfill(body(H.find(x => String(x.company_id) === m[1]) || null));
    if (p === "/allocation") return r.fulfill(body(ALLOC));
    if (p === "/cash") return r.fulfill(body({ available_cash: 30000, total_cash: 30000 }));
    if (p === "/portfolios") return r.fulfill(body([{ id: 1, name: "محفظتي", color: "var(--chart-1)", is_default: true, include_in_aggregate: true }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/portfolio`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2200); await paint();

  // ١ جدولُ الحيازات / بطاقاتُها
  const rows = await page.evaluate(() => {
    const out = {};
    for (const el of document.querySelectorAll("tr, .hold-card, [data-role='hold-card']")) {
      const t = (el.textContent || "").replace(/\s+/g, " ");
      for (const s of ["AAPL", "MSFT", "2222"]) if (t.includes(s) && !out[s] && el.offsetParent) out[s] = t;
    }
    const usd = [...document.querySelectorAll('[data-role="hold-usd-price"]')].filter(e => e.offsetParent).map(e => e.textContent.replace(/\s+/g, ""));
    const leg = [...document.querySelectorAll('[data-role="hold-fx-legacy"]')].filter(e => e.offsetParent).map(e => e.textContent.trim());
    return { out, usd, leg };
  });
  const aapl = rows.out.AAPL || "", msft = rows.out.MSFT || "", sa = rows.out["2222"] || "";
  if (desk) {
    say(rows.usd.length === 2 && rows.usd[0] === "$200.00" && aapl.includes("$190.10") && aapl.includes("4,502.52")
        && rows.leg.length === 1 && msft.includes("سعرُ الصرف ناقص") && !sa.includes("$"),
        `${label}: ١ الأمريكيّ بسعرٍ مُعلَمٍ بالدولار (‎$200.00) ومتوسّطٍ بالدولار (‎$190.10) وقيمتُه بالريال (4,502.52)، والقديمُ معلَّمٌ، والسعوديُّ بلا دولار`,
        `${rows.usd.join(" | ")} · ${rows.leg.join(" | ")} · ${aapl.slice(0, 160)}`);
  } else {
    const cards = await page.evaluate(() => [...document.querySelectorAll("div")].filter(d => d.offsetParent && /AAPL/.test(d.textContent || "")
      && /\$190\.10/.test(d.textContent || "") && /آخر سعر \$ :/.test(d.textContent || "")).length);
    say(cards > 0 && rows.leg.length === 1, `${label}: ١ بطاقةُ الأمريكيّ: «آخر سعر $» ومتوسّطُ التكلفة بالدولار (‎$190.10)، والقديمُ معلَّمٌ في بطاقته`,
        `${cards} · ${rows.leg.join(" | ")}`);
  }
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `d789_holdings_${vp.width}.png`) }).catch(() => {});

  // ٢ نافذةُ المعاملة للأمريكيّ
  await page.locator('button[title="شراء/بيع"]:visible').first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(800);
  const modal = page.locator(".modal-box, [role=dialog]").last();
  const mtxt = ((await modal.textContent().catch(() => "")) || "").replace(/\s+/g, " ");
  const fxBox = await modal.locator('[data-role="tx-fx"]').textContent().catch(() => "");
  const nums = modal.locator('input[inputmode="decimal"], input[inputmode="numeric"]');
  await nums.nth(0).fill("10");
  await nums.nth(1).fill("190");
  await page.waitForTimeout(1400);
  const mtxt2 = ((await modal.textContent().catch(() => "")) || "").replace(/\s+/g, " ");
  const last = previews[previews.length - 1] || {};
  say(/Apple/.test(mtxt) && /سعر السهم بالدولار/.test(mtxt) && /سعرُ اليوم 3\.7521 · حيّ/.test(fxBox || "") && /\$190\.10/.test(mtxt),
      `${label}: ٢ النافذةُ للأمريكيّ: «سعر السهم بالدولار» وسعرُ الصرف بسعر اليوم ومصدرِه، ومتوسّطُك بالدولار`, (fxBox || "").trim());
  say(/\$1,900\.00 · بالريال 7,128\.99/.test(mtxt2) && last.q === 10 && last.px === 190 && last.fx === "3.7521",
      `${label}: ٢ب الإجماليُّ بالعملتين (‎$1,900 · بالريال 7,128.99)، والمعاينةُ تُطلب بسعر الصرف`, JSON.stringify(last));
  // الخطُّ واللمس في حقل الصرف وتلميحه
  const geo = await page.evaluate(() => {
    const box = document.querySelector('[data-role="tx-fx"]');
    if (!box) return null;
    const inp = box.querySelector("input"), hint = box.querySelector("p");
    const fs = el => el ? parseFloat(getComputedStyle(el).fontSize) : 99;
    return { h: inp ? inp.getBoundingClientRect().height : 0, fsHint: fs(hint), fsInp: fs(inp), over: document.documentElement.scrollWidth - document.documentElement.clientWidth };
  });
  const ok = modal.locator("button.btn-primary").first();
  await page.waitForTimeout(300);
  await ok.click().catch(() => {});
  await page.waitForTimeout(900);
  const post = posts[0] || {};
  say(post.fx_rate === 3.7521 && post.price_per_share === 190 && post.shares === 10 && post.transaction_type === "BUY",
      `${label}: ٢ج الحفظُ يحمل سعرَ صرف العملية (3.7521) والسعرَ بالدولار`, JSON.stringify(post));
  await page.keyboard.press("Escape").catch(() => {});
  await page.locator(".modal-box button[aria-label='إغلاق']").last().click().catch(() => {});
  await page.waitForTimeout(500);

  // ٣ «إضافة شركة»: البحثُ الأمريكيّ والعملةُ من السوق
  await page.locator(`button[title="إضافة شركة"]:visible`).first().click({ timeout: 6000 }).catch(() => {});
  await page.waitForTimeout(600);
  const cm = page.locator(".modal-box").last();
  await cm.locator("input").first().fill("AAPL").catch(() => {});
  await page.waitForTimeout(900);
  const hits = await cm.locator('[data-role="co-us-hit"]').count();
  const hitTxt = await cm.locator('[data-role="co-us-hit"]').first().textContent().catch(() => "");
  await cm.locator('[data-role="co-us-hit"]').first().click().catch(() => {});
  await page.waitForTimeout(400);
  const cur = await cm.locator('[data-role="co-currency"]').textContent().catch(() => "");
  const mk = await cm.locator('[data-role="co-market"]').textContent().catch(() => "");
  say(hits === 1 && /السوق الأمريكي · NASDAQ/.test(hitTxt || "") && /دولار أمريكي/.test(cur || "") && /السوق الأمريكي\s*· NASDAQ/.test(mk || "")
      && searches.includes("AAPL"),
      `${label}: ٣ «إضافة شركة» تبحث في السوق الأمريكي (الأسهمُ والصناديقُ وحدها — لا العقود)، واختيارُه يجعل السوقَ أمريكياً والعملةَ دولاراً`,
      `${hits} · ${(hitTxt || "").trim()} · ${(cur || "").trim()} · ${(mk || "").trim()}`);
  if (SHOTS) await cm.screenshot({ path: join(SHOTS, `d789_company_${vp.width}.png`) }).catch(() => {});

  // ٤ الهندسة
  if (geo) say(geo.h >= 32 && geo.fsHint >= 9.5 && geo.fsInp >= 9.5 && geo.over <= 1,
      `${label}: ٤ حقلُ سعر الصرف: لمسٌ ≥ 32 وخطٌّ ≥ 9.5 وبلا فيضٍ أفقيّ`, JSON.stringify(geo));
  else say(false, `${label}: ٤ حقلُ سعر الصرف لم يظهر`);
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
