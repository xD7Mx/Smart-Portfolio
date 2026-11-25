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
const PICK = { symbol: "NVDA", name: "NVIDIA Corporation", contract: "NVDA270618C00230000", type: "call", strike: 230, ask: 1.45, bid: 1.37, cost: 145,
  dte: 213, expiry: "2027-06-18", breakeven: 231.45, need_pct: 28.2, pop: 21.4, p_touch: 38, target: 245, target_label: "قمّة السنة", rr: 0.9,
  delta: 0.34, iv: 48, oi: 4210, spread_pct: 5.7, spread_usd: 8, px_src: "ask", opened: "2026-11-17", new: false, pl_pct: 12.4, mid_now: 1.58, entry_mid: 1.41,
  trend: { state: "صاعد" },
  reasons: ["الأطروحة: المسار صاعد — الإغلاق 180.50 فوق متوسّط 50 (172.10) وفوق متوسّط 200 (150.40)، وتغيّرُ ثلاثة أشهر +18.0٪.",
            "الأخبار (إيجابي): نتائجُ فصليةٌ فوق التوقّعات (2026-11-12)",
            "الهدفُ الفنيّ 245.00 (قمّة السنة)، ونقطةُ التعادل 231.45 (+28.2٪ من السعر) دونه — إن بلغه السهمُ عند الانتهاء ربح العقدُ 0.9 ضعفَ كلفته.",
            "لماذا تنفيذ 230: أعلى درجةٍ بين العقود السائلة ضمن ميزانيتك بدلتا +0.34 — لا بعيدٌ كاليانصيب ولا عميقٌ غالٍ.",
            "الفارقُ بين العرض والطلب 8 دولار للعقد (6٪) — العرضُ والطلبُ حيّان.",
            "خطّةُ الخروج: وقفٌ إن هبط العقدُ إلى نصف كلفته، وجنيٌ عند بلوغ السهمِ الهدفَ أو تضاعفِ العقد، وخروجٌ قبل 60 يوماً من الانتهاء (2027-04-19)."] };
const RES = (b) => ({ budget: b, at: "2026-11-18T14:00:00+00:00", scanned: 90, news_ok: true, closed: true, limits: { min_dte: 150, max_dte: 430, min_oi: 100, max_spread: 10 },
  picks: [PICK, { ...PICK, symbol: "INTC", name: "Intel Corporation", contract: "INTC270618P00018000", type: "put", strike: 18, cost: 95, pop: 38.2, delta: -0.41,
    need_pct: 12.4, px_src: "snap", quote_at: "2026-11-17T20:40", spread_pct: 4.2, spread_usd: 4, new: true, opened: "2026-11-18", pl_pct: 0, trend: { state: "هابط" },
    reasons: ["الأطروحة: المسار هابط — …", "الأخبار (سلبي): استقالةُ الرئيس التنفيذيّ (2026-11-10)"],
    saqr: { state: "approve", text: "صقر يوافق: فرصةُ هبوط", p30: 61.4, floor: 60 } }],
  gate: { approved: 4, scan: true, text: "التوصياتُ الجديدةُ من فرص صقر الموافَق عليها اليوم وحدها (4) — بنسبة نجاحٍ لا تقلّ عن حدّك." },
  exits: [{ contract: "NIO270319P00004000", symbol: "NIO", type: "put", opened: "2026-11-10", closed: "2026-11-18", status: "stop", status_ar: "بلغ الوقف",
    why: "هبط العقدُ إلى 0.40 — نصفُ سعر الدخول (0.80) أو دونه: بلغ الوقف.", pl_pct: -50 }],
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
    if (p.startsWith("/market/options/")) return r.fulfill(body(null));
    if (p === "/market/options-picks" && m === "GET") {
      if (state.running.on && ++polls >= 2) state = { result: RES(Number(u.searchParams.get("budget"))), running: { on: false } };
      return r.fulfill(body(state));
    }
    if (p === "/market/options-picks/run") { const b = JSON.parse(r.request().postData() || "{}").budget; posts.push(b); polls = 0; state = { result: null, running: { on: true, msg: "قراءةُ الأخبار", budget: b } }; return r.fulfill(body({ on: true })); }
    if (p === "/market/research-desk") return r.fulfill(body({ report: null, dates: [], running: { on: false } }));
    // ‏D778: تذكرةُ الشراء من بطاقة التوصية — طلبُ العقد وعرضُه الآن، والأمر
    if (p.startsWith("/market/saqr/quote/")) return r.fulfill(body({ bid: 1.40, ask: 1.48, live: true, price: 231.2, dte: 210, name: "NVIDIA" }));
    if (p === "/market/saqr/order") { posts.push(["order", JSON.parse(r.request().postData() || "{}")]); return r.fulfill(body([])); }   // حالُ صقر الكاملُ ليس موضوعَ هذا الحارس
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const tabs = (await page.locator('[data-role="sq-nav"] [data-view]').allTextContents().catch(() => [])).map(t => t.trim());
  const sel = ((await page.locator('[data-role="sq-nav"] [aria-selected="true"]').textContent().catch(() => "")) || "").trim();
  const empty = await page.locator('[data-role="op-empty"]').textContent().catch(() => "");
  say(tabs.includes("عقود الخيارات") && sel === "عقود الخيارات" && await page.locator('[data-role="rl-views"]').count() === 0
      && /قيمة العقد/.test(empty || "") && await page.locator('[data-role="op-budget"]').count() === 1,
      `${label}: ١ «عقود الخيارات» تبويبٌ داخل صقر (‏D777 — لا تبويبَ فوق المختبر)، ومن حفظه قديماً يفتح عليه، وفيه خانةُ قيمة العقد`, `${tabs.join(" · ")} · ${sel}`);
  await page.locator('[data-role="op-preset"]', { hasText: "$150" }).click();
  await page.waitForTimeout(400);
  const st = await page.locator('[data-role="op-status"]').textContent().catch(() => "");
  await page.waitForTimeout(7500);
  const cards = await page.locator('[data-role="op-pick"]').count();
  const c0 = await page.locator('[data-role="op-pick"]').first().textContent().catch(() => "");
  say(posts[0] === 150 && /قراءةُ الأخبار/.test(st || "") && cards === 2 && /NVDA/.test(c0) && /خيار شراء/.test(c0) && /\$145\.00/.test(c0) && /21%/.test(c0)
      && /245\.00/.test(c0) && /0\.9×/.test(c0) && /الفارق \$8 \(6%\)/.test(c0) && /18 يونيو/.test(c0) && /213/.test(c0),
      `${label}: ٢ «$150» يراجع ويعرض حالَه، ثمّ التوصياتُ بعقدها (النوع · التنفيذ · الأجل · الكلفة · الفارقُ بالدولار) ومقاييسها (الهدفُ الفنيّ · العائدُ عنده · الاحتمالات)`, `${st} · ${cards} صفقة`);
  /* ٢ج ‏D778 (المالك): «نكتفي بعقود الخيارات، وحُطّ في البطاقة نفسِها تنفيذ — زرٌّ بعبارة شراء… يطلع لي سعرُ العرض وسعرُ الطلب، وأشتري بسعرٍ محدّد
     وأبيع بسعرٍ محدّد أو بنسبة، جنيُ ربحٍ أو خيارٌ إلحاقيّ» */
  const c1 = page.locator('[data-role="op-pick"]').first();
  const buyTxt = ((await c1.locator('[data-role="op-buy"]').textContent().catch(() => "")) || "").trim();
  await c1.locator('[data-role="op-buy"]').click(); await page.waitForTimeout(1200);
  const quote = ((await c1.locator('[data-role="of-quote"]').textContent().catch(() => "")) || "").replace(/\s+/g, " ");
  const lim0 = await c1.locator('[data-role="of-limit"]').inputValue().catch(() => "");
  await c1.locator('[data-role="of-type"] [data-v="stp_lmt"]').click(); await page.waitForTimeout(300);
  await c1.locator('[data-role="of-stop"]').fill("1.55"); await c1.locator('[data-role="of-limit"]').fill("1.60");
  await c1.locator('[data-role="of-tif"] [data-v="day"]').click();
  await c1.locator('[data-role="of-att"] [data-v="trail"]').click(); await page.waitForTimeout(300);
  await c1.locator('[data-role="of-trail"] [data-v="20"]').click();
  await c1.locator('[data-role="of-plus"]').click();
  const types = (await c1.locator('[data-role="of-type"] [data-v]').allTextContents()).map(t => t.trim());
  const atts = (await c1.locator('[data-role="of-att"] [data-v]').allTextContents()).map(t => t.trim());
  const tk = await page.evaluate(() => { const r = document.querySelector('[data-role="op-pick"] [data-role="order-form"]'); let minT = 99;
    r?.querySelectorAll("button, input").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height > 2) minT = Math.min(minT, x.height); });
    return { minT, over: document.documentElement.scrollWidth - document.documentElement.clientWidth }; });
  if (process.env.SHOTS) await c1.screenshot({ path: `${process.env.SHOTS}/op-ticket-${vp.width}.png` }).catch(() => {});
  await c1.locator('[data-role="of-send"]').click(); await page.waitForTimeout(700);
  const od = (posts.filter(x => Array.isArray(x) && x[0] === "order").pop() || [])[1];
  say(buyTxt === "شراء" && /1\.40/.test(quote) && /1\.48/.test(quote) && /0\.08/.test(quote) && /حيّ/.test(quote) && lim0 === "1.48"
      && JSON.stringify(types) === JSON.stringify(["سوق", "محدَّد", "إيقاف", "إيقافٌ محدَّد"])
      && JSON.stringify(atts) === JSON.stringify(["لا شيء", "جنيُ ربح", "وقفُ خسارة", "وقفٌ مطارِد", "براكت"])
      && od && od.contract === "NVDA270618C00230000" && od.otype === "stp_lmt" && od.stop === 1.55 && od.limit === 1.6 && od.tif === "day" && od.trail_pct === 20
      && od.qty === 2 && tk.minT >= 32 && tk.over <= 1,
      `${label}: ٢ج «شراء» في بطاقة التوصية (‏D778) يفتح التذكرة: الطلبُ والعرضُ والفارقُ الآن (حيّاً)، وسعرُ الحدّ يتبع العرض — ثمّ النوعُ والمدّةُ `
      + `والأمرُ المرفق كالوسيط`, JSON.stringify({ quote: quote.slice(0, 80), lim0, od, tk }).slice(0, 280));
  /* ‏D762: الدفترُ يحفظ التوصية — «قائمةٌ منذ» بربحها منذ الدخول، و«جديدةٌ اليوم» */
  const s0 = await page.locator('[data-role="op-pick"]').nth(0).locator('[data-role="op-state"]').textContent().catch(() => "");
  const s1 = await page.locator('[data-role="op-pick"]').nth(1).locator('[data-role="op-state"]').textContent().catch(() => "");
  say(/قائمةٌ منذ 17 نوفمبر/.test(s0 || "") && /\+12\.4%/.test(s0 || "") && /الأطروحةُ سليمة/.test(s0 || "") && /جديدة اليوم/.test(s1 || ""),
      `${label}: ٢ب التوصيةُ تبقى بتاريخها وربحِها منذ الدخول («قائمةٌ منذ 17 نوفمبر · +12.4%»)، والجديدةُ موسومة`, `${s0} | ${s1}`);
  /* ‏D840: القرارُ الواحد — موافقةُ صقر ونسبةُ نجاحها على التوصية الجديدة، وقاعدةُ القائمة فوقها؛ والقديمةُ بلا شارة (لا اختلاق) */
  const sq1 = await page.locator('[data-role="op-pick"]').nth(1).locator('[data-role="op-saqr"]').textContent().catch(() => "");
  const sq0 = await page.locator('[data-role="op-pick"]').nth(0).locator('[data-role="op-saqr"]').count();
  const gate = await page.locator('[data-role="op-gate"]').textContent().catch(() => "");
  say(/صقر يوافق/.test(sq1 || "") && /61%/.test(sq1 || "") && /60%/.test(sq1 || "") && sq0 === 0 && /فرص صقر الموافَق عليها/.test(gate || ""),
      `${label}: ٢ج ‏D840 التوصيةُ الجديدةُ عليها موافقةُ صقر ونسبةُ نجاحها وحدُّ المالك، وقاعدةُ القائمة ظاهرة`, `${sq1} | ${gate}`);
  const why = await page.locator('[data-role="op-pick"]').nth(0).locator(".op-why li").allTextContents().catch(() => []);
  say(why.some(x => /الهدفُ الفنيّ/.test(x)) && why.some(x => /^لماذا تنفيذ 230/.test(x)) && why.some(x => /خطّةُ الخروج/.test(x))
      && /خيار بيع/.test(await page.locator('[data-role="op-pick"]').nth(1).textContent() || ""),
      `${label}: ٣ ولكلّ توصيةٍ مبرّرُها — الأطروحةُ والهدفُ الفنيّ ولماذا هذا التنفيذ وخطّةُ الخروج`, why.join(" | ").slice(0, 120));
  const snaps = await page.locator('[data-role="op-snap"]').count();
  const inSnap = await page.locator('[data-role="op-pick"]').nth(1).locator('[data-role="op-snap"]').count();
  const meta0 = await page.locator('[data-role="op-meta"]').textContent().catch(() => "");
  const ex = await page.locator('[data-role="op-exit"]').first().textContent().catch(() => "");
  const copies = await page.locator('[data-role="op-copy"]').count();
  say(snaps === 1 && inSnap === 1 && /آخر جلسة/.test(meta0 || "") && /فارقٌ ≤ 10%/.test(meta0 || "") && /بلغ الوقف/.test(ex || "") && /-50\.0%/.test(ex || "") && copies === 0,
      `${label}: ٣ب العرضُ والطلبُ من آخر جلسةٍ يُوسمان والسوقُ مغلق، و«إشاراتُ خروج» بسببها وخسارتها — ولا زرَّ نسخٍ لرمزٍ مبهم`, `${snaps} · ${(ex || "").slice(0, 40)}`);
  /* «فتح في الرسم» يذهب إلى غرفة التداول بالعقد نفسِه، و«سلسلة العقود» تفتح سلسلةَ السهم */
  await page.locator('[data-role="op-chain"]').first().click(); await page.waitForTimeout(700);
  const chainOpen = await page.locator('[data-role="oc"]').count();
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  await page.locator('[data-role="op-open"]').first().click(); await page.waitForTimeout(1200);
  const roomSym = await page.evaluate(() => localStorage.getItem("sp_room_symbol"));
  const url = page.url();
  say(chainOpen === 1 && roomSym === "NVDA270618C00230000" && !/tab=lab/.test(url) && /\/watchlist/.test(url),
      `${label}: ٣ج «سلسلة العقود» تفتح سلسلةَ السهم، و«فتح في الرسم» يذهب إلى رسم العقد نفسِه في غرفة التداول`, `${chainOpen} · ${roomSym} · ${url.slice(-20)}`);
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
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
