// ─────────────────────────────────────────────────────────────────────────
// D759 (المالك 2026-11-17): «في مختبر الأبحاث خانةٌ لقيمة العقد — 150 أو 100 أو 50 دولاراً — فيُخرج أفضلَ عقود الخيارات طويلة الأجل
// على المسار والأخبار، صفقاتٍ أختار منها مع المبرّر». المتصفّحُ على الصفحة الحقيقية والخادمُ مُحاكى: التبويب، والخانةُ والقيمُ السريعة،
// والبحثُ للمالك ومتابعةُ حاله، والصفقاتُ بمقاييسها ومبرّراتها ونسخُ رمز العقد، والمستبعَدُ بسببه، والقياسُ (فيضٌ · لمسٌ · خطّ).
//    SHOTS=dir node scripts/audit/option_picks_d759.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5262;
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
const PICK = { symbol: "NVDA", name: "NVIDIA Corporation", price: 180.5, contract: "NVDA270618C00230000", type: "call", strike: 230, ask: 1.45, cost: 145,
  dte: 213, expiry: "2027-06-18", breakeven: 231.45, need_pct: 28.2, need_sigma: 0.9, pop: 21.4, delta: 0.27, iv: 48, oi: 4210, spread_pct: 6.9,
  trend: { state: "صاعد" }, news: { impact: "إيجابي", strength: 2, event: "نتائجُ فصليةٌ فوق التوقّعات (2026-11-12)" },
  reasons: ["المسار صاعد: الإغلاق 180.50 فوق متوسّط 50 (172.10) وفوق متوسّط 200 (150.40)، وتغيّرُ ثلاثة أشهر +18.0٪.",
            "الأخبار (إيجابي): نتائجُ فصليةٌ فوق التوقّعات (2026-11-12)", "العقد ينتهي بعد 213 يوماً فيبطؤ تآكلُه الزمنيّ.",
            "احتمالُ الربح عند الانتهاء نحو 21٪ تقديراً، وأقصى الخسارة كلفةُ العقد 145 دولاراً."] };
const RES = (b) => ({ budget: b, at: "2026-11-17T14:00:00+00:00", scanned: 78, news_ok: true, limits: { min_dte: 120, max_dte: 430, min_oi: 50, max_spread: 35 },
  picks: [PICK, { ...PICK, symbol: "INTC", name: "Intel Corporation", contract: "INTC270618P00018000", type: "put", strike: 18, cost: 95, pop: 38.2, delta: -0.31,
    need_pct: 12.4, trend: { state: "هابط" }, reasons: ["المسار هابط: …", "الأخبار (سلبي): استقالةُ الرئيس التنفيذيّ (2026-11-10)"] }],
  skipped: [{ symbol: "AAPL", why: "المسارُ عرضيّ — لا اتجاهَ يُشترى له عقد" }] });
const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 900 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [], posts = [];
  let state = { result: null, running: { on: false } }, polls = 0;
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_lab_view", "options"); localStorage.removeItem("sp_optpicks_budget"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (p === "/market/options-picks" && m === "GET") {
      if (state.running.on && ++polls >= 2) state = { result: RES(Number(u.searchParams.get("budget"))), running: { on: false } };
      return r.fulfill(body(state));
    }
    if (p === "/market/options-picks/run") { const b = JSON.parse(r.request().postData() || "{}").budget; posts.push(b); polls = 0; state = { result: null, running: { on: true, msg: "قراءةُ الأخبار", budget: b } }; return r.fulfill(body({ on: true })); }
    if (p === "/market/research-desk") return r.fulfill(body({ report: null, dates: [], running: { on: false } }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const tabs = await page.locator('[data-role="rl-views"] [data-view]').allTextContents().catch(() => []);
  const empty = await page.locator('[data-role="op-empty"]').textContent().catch(() => "");
  say(JSON.stringify(tabs) === JSON.stringify(["التقرير اليومي", "عقود الخيارات"]) && /قيمة العقد/.test(empty || "") && await page.locator('[data-role="op-budget"]').count() === 1,
      `${label}: ١ «عقود الخيارات» تبويبٌ في مختبر الأبحاث بجانب التقرير، وفيه خانةُ قيمة العقد`, tabs.join(" · "));
  await page.locator('[data-role="op-preset"]', { hasText: "$150" }).click();
  await page.waitForTimeout(400);
  const st = await page.locator('[data-role="op-status"]').textContent().catch(() => "");
  await page.waitForTimeout(7500);
  const cards = await page.locator('[data-role="op-pick"]').count();
  const c0 = await page.locator('[data-role="op-pick"]').first().textContent().catch(() => "");
  say(posts[0] === 150 && /قراءةُ الأخبار/.test(st || "") && cards === 2 && /NVDA/.test(c0) && /خيار شراء/.test(c0) && /\$145\.00/.test(c0) && /21٪/.test(c0)
      && /231\.45/.test(c0) && /2027-06-18/.test(c0) && /213/.test(c0),
      `${label}: ٢ «$150» يبحث ويعرض حالَه، ثمّ الصفقاتُ بعقدها (النوع · التنفيذ · الأجل · الكلفة) ومقاييسها (احتمالُ الربح · التعادل · …)`, `${st} · ${cards} صفقة`);
  const why = await page.locator('[data-role="op-pick"]').nth(1).locator(".op-why li").allTextContents().catch(() => []);
  say(why.some(x => /استقالةُ الرئيس/.test(x)) && /خيار بيع/.test(await page.locator('[data-role="op-pick"]').nth(1).textContent() || ""),
      `${label}: ٣ ولكلّ صفقةٍ مبرّرُها — المسارُ والخبر (استقالةُ رئيسٍ ⇒ خيارُ بيع)`, why.join(" | ").slice(0, 120));
  await page.locator('[data-role="op-skipped"] summary').click().catch(() => {}); await page.waitForTimeout(300);
  const sk = await page.locator('[data-role="op-skipped"]').textContent().catch(() => "");
  say(/AAPL/.test(sk || "") && /عرضيّ/.test(sk || ""), `${label}: ٤ والمستبعَدُ يُذكر بسببه`);
  await page.locator('[data-role="op-budget"]').fill("50");
  await page.locator('[data-role="op-go"]').click(); await page.waitForTimeout(7500);
  const meta = await page.locator('[data-role="op-meta"]').textContent().catch(() => "");
  say(posts.includes(50) && /\$50/.test(meta || ""), `${label}: ٥ والخانةُ تقبل أيَّ قيمة (50) وتبحث بها`, meta || "");
  if (process.env.SHOTS) await page.locator('[data-role="op"]').screenshot({ path: `${process.env.SHOTS}/op-${vp.width}.png` }).catch(() => {});
  const m = await page.evaluate(() => {
    const r = document.querySelector('[data-role="op"]'); const W = document.documentElement.clientWidth;
    let minT = 99, minF = 99;
    r.querySelectorAll("button, summary, input").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height) minT = Math.min(minT, x.height); });
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
