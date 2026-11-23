// ─────────────────────────────────────────────────────────────────────────
// D786 — بأمر المالك (2026-11-22): «التحليلُ الفنيّ خطوةٌ من بين الخطوات… يقرأ ويحلّل مثل الصفة البشرية ويربط بين كلّ شيء:
// المسار والمستويات، والنتائج، والأخبار، والأحداث، وسلوكُ المستثمرين، والصفقاتُ غيرُ الاعتيادية، والحيتان أين يتمركزون».
//   ١ بطاقةُ الفرصة تحمل مجلسَ صقر: حكمَه ودرجتَه وأعضاءه السبعة بالترتيب وحكمَ كلٍّ — و«لماذا» تُطوى وتُفتح بانسيابية بسطرِ كلّ عضو.
//   ٢ «الرابط» يقرأ الأعضاءَ معاً: قرارُه وثقتُه وما يغيّر الحكم.
//   ٣ ما رفضه عضوٌ يُعرض في «استبعدها مجلسُ صقر» مطويّاً بسببه، وعددُه في سطر المسح.
//   ٤ بطاقةُ «عقود الخيارات» تقول حكمَ المجلس ودرجتَه.
//   ٥ التباينُ (الحكمُ والأعضاءُ ≥ 4.5) والخطُّ ≥ 9.5 واللمسُ ≥ 32 وبلا فيض — في المظهرين على الحاسوب والجوال — والحركةُ تسكن مع تفضيل تقليلها.
//    SHOTS=dir node scripts/audit/chart_d786.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };

const PORT = 5286;
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
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const ROLES = ["المسار", "الرسم", "النتائج", "الأخبار", "الأحداث", "الحيتان", "المحلّلون"];
const MEM = (vs, says) => ROLES.map((role, i) => ({ role, v: vs[i], say: says[i] }));
const C1 = { verdict: "يوافق", score: 86, veto: false, oks: 6, warns: 0, members: MEM(["ok", "ok", "ok", "na", "ok", "ok", "ok"], [
  "صاعدٌ قويّ (6/10) فوق متوسّطي 50 و200، وأقوى من تاسي بـ+9.8٪ في ثلاثة أشهر", "ارتدادٌ من الدعم بجودة 81 — السعرُ في منطقة الدعم",
  "صافي الربح +28٪ عن الربع المماثل · ربحٌ في 3 أرباعٍ متتالية ونموٌّ في آخرها", "لا خبرَ جوهريّاً في عشرة أيام",
  "تاسي صاعد، والخطرُ الجيوسياسيّ منخفض", "السيولةُ داخلةٌ للصعود (قويّة) · صفقتان خاصتان في 30 يوماً بعلاوة +2.2٪",
  "3 بيوت: 2 شراء · 1 حياد — وسيطُ المستهدف 30.10 (+20٪)"]) };
const C2 = { verdict: "يوافق بتحفّظ", score: 61, veto: false, oks: 3, warns: 2, members: MEM(["warn", "ok", "ok", "warn", "ok", "na", "ok"], [
  "دون متوسّط 50 — ارتدادٌ يؤكّده الرسم", "استمرارٌ بعد تصحيح بجودة 66", "صافي الربح +4٪", "تعذّرت قراءةُ الأخبار الآن", "تاسي صاعد",
  "السيولةُ غيرُ متوفّرة", "بيتان: 2 شراء"]) };
const LINK = { decision: "شراء", confidence: "متوسطة", link: "المسارُ الصاعدُ والنتائجُ المتتاليةُ والسيولةُ الداخلةُ تجتمع عند منطقة الدعم.", conflict: "",
  watch: "إغلاقٌ دون 24.20 يُبطلها" };
const REJ = [{ symbol: "4030", name: "البحري", setup: "ارتدادٌ من الدعم", side: "long", quality: 70, why: ["الأخبار: إقالةُ الرئيس التنفيذيّ — خبرٌ جوهريٌّ معاكس"] },
  { symbol: "2380", name: "بترو رابغ", setup: "استمرارٌ بعد تصحيح", side: "long", quality: 58, why: ["النتائج: خسارةٌ للربع الثاني على التوالي — تأكيدُ ضعف"] }];
const OPP = (sym, name, side, q, hn, setup, extra = {}) => ({ symbol: sym, name, setup, side, quality: q, horizon: { 1: "شهر", 2: "شهران", 3: "حتى الربع القادم" }[hn], horizon_n: hn,
  entry: side === "long" ? [24.6, 25.1] : [128, 131], target: side === "long" ? 27.4 : 118, stop: side === "long" ? 24.2 : 133.5, rr: 2.3, zone: "الدعم",
  where: side === "long" ? "في منطقة الدعم" : "في منطقة المقاومة", close: side === "long" ? 25.0 : 129.5,
  trend: { word: side === "long" ? "صاعد" : "هابط", level: "قويّ", strength: 62 }, liq: { word: "داخلةٌ للصعود", level: "متوسّطة", strength: 48, tag: "تجميعٌ خفيّ" },
  k: 18.4, rsi: 44.2, weekly: "صاعد", reasons: ["الاتجاه صاعد قويّ (62/100)"], ...extra });
const OPPS = {
  sa: { market: "sa", at: iso(now - 3600e3), universe: 268, screened: 266, read: 266, found: 2, min_q: 50, job: { on: false, msg: "", at: null }, rejected: REJ,
    items: [OPP("2222", "أرامكو السعودية", "long", 81, 3, "ارتدادٌ من الدعم", { council: C1, link: LINK }), OPP("1120", "مصرف الراجحي", "long", 66, 2, "استمرارٌ بعد تصحيح", { council: C2 })] },
  us: { market: "us", at: iso(now - 7200e3), universe: 812, screened: 790, read: 150, found: 1, min_q: 50, job: { on: false, msg: "", at: null }, rejected: [],
    items: [OPP("NVDA", "NVIDIA", "long", 77, 3, "اختراقُ المقاومة", { council: C1 })] } };
const ST = m => ({ market: m, ccy: m === "sa" ? "SAR" : "USD", on: true, capital: 1000, goal: 100000, cash: 1000, equity: 1000, pl: 0, pl_pct: 0, progress: 0,
  started: iso(now - 86400e3), tier: { frac: 0.25, seats: 4 }, positions: [], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0,
  today: { wins: 0, losses: 0, realized: 0, new: 0 }, exposure: { contracts: 0, cost: 0, value: 0, ret: null }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 1000]],
  signals: [], log: [], gates: [], scan: null, session: null, last_cycle: null, last_check: null, health: {}, broker: { linked: false, name: "IBKR" }, runs: [],
  running: { on: false, msg: "", at: null }, settings: { per_trade: null, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 6, take_x: 2,
    mode: "balanced", day_target: null, auto: false }, day: null, orders: [], pulse: null, geo: null, rules: { stop: 0.6, take: 2 },
  regime: m === "sa" ? { verdict: "صاعد", state: "صاعد", close: 11500, sma50: 11300, sma200: 11000, ret3m: 4.2, chg: 0.35 } : null,
  opps: { at: OPPS[m].at, universe: OPPS[m].universe, screened: OPPS[m].screened, read: OPPS[m].read, found: OPPS[m].found } });
const PICK = { symbol: "NVDA", name: "NVIDIA", contract: "NVDA270617C00200000", type: "call", strike: 200, ask: 1.45, bid: 1.35, cost: 145, dte: 207, expiry: "2027-06-17",
  breakeven: 201.45, need_pct: 8.2, pop: 36, p_touch: 52, target: 214, target_label: "قمّة السنة", rr: 2.1, delta: 0.41, iv: 44, oi: 3200, spread_pct: 7, spread_usd: 10,
  px_src: "ask", opened: "2026-11-22", new: true, pl_pct: 0, mid_now: 1.4, entry_mid: 1.4, trend: { state: "صاعد" },
  reasons: ["الأطروحة: المسار صاعد", "قراءةُ الرسم: اختراقُ المقاومة — جودتُها 77 من 100 ومدّتُها حتى الربع القادم، ومجلسُ صقر يوافق (82/100)"],
  chart: { setup: "اختراقُ المقاومة", side: "long", quality: 77, horizon: "حتى الربع القادم", where: "فوق المقاومة",
    council: { verdict: "يوافق", score: 82, oks: 5, warns: 1, members: C1.members }, link: LINK } };

/* التباين: لونُ النصّ على خلفيته الفعلية — تُركَّب الخلفياتُ الشفّافةُ صعوداً حتى أرضيةٍ معتمة (كما يرسمها المتصفّح) */
const CONTRAST = () => {
  const parse = s => { s = (s || "").trim();
    let m = s.match(/^rgba?\(([^)]+)\)$/);
    if (m) { const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; }
    m = s.match(/^color\(srgb\s+([^)]+)\)$/);
    if (m) { const [a, al] = m[1].split("/"); const p = a.trim().split(/\s+/).map(Number); return [p[0] * 255, p[1] * 255, p[2] * 255, al ? Number(al) : 1]; }
    return [0, 0, 0, 0]; };
  const over = (top, bot) => { const a = top[3] + bot[3] * (1 - top[3]); if (!a) return [0, 0, 0, 0];
    return [0, 1, 2].map(i => (top[i] * top[3] + bot[i] * bot[3] * (1 - top[3])) / a).concat(a); };
  const bgOf = el => { const layers = []; for (let e = el; e; e = e.parentElement) { const c = parse(getComputedStyle(e).backgroundColor); if (c[3] > 0) layers.push(c); if (c[3] >= 1) break; }
    let acc = parse(getComputedStyle(document.body).backgroundColor); if (acc[3] < 1) acc = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) acc = over(layers[i], acc); return acc; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  return el => { const bg = bgOf(el), fg = over(parse(getComputedStyle(el).color), bg); const a = lum(fg), b = lum(bg); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
};

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["سطح المكتب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.setDefaultTimeout(6000);
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  const paint = () => page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d786-init")) return;
    sessionStorage.setItem("d786-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_saqr_tab", "opps"); localStorage.setItem("sp_saqr_market", "sa");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "X", price: 64.2, change: 0.4, change_pct: 0.6, time: new Date().toISOString(), delayed: 0, source: "ياهو", session: SES, ext: null }));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa", state: "closed", label: "السوق مغلق" } }));
    if (p === "/market/saqr" && m === "GET") return r.fulfill(body(ST(u.searchParams.get("market") === "sa" ? "sa" : "us")));
    if (p === "/market/saqr/opportunities" && m === "GET") return r.fulfill(body(OPPS[u.searchParams.get("market") === "sa" ? "sa" : "us"]));
    if (p === "/market/options-picks") return r.fulfill(body({ result: { budget: 150, at: iso(now), picks: [PICK], exits: [], skipped: [], scanned: 98, news_ok: true, closed: false,
      limits: { min_dte: 150, max_dte: 430, min_oi: 100, max_spread: 10 } }, running: { on: false } }));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2600); await paint(); await page.waitForTimeout(300);
  await page.locator('[data-role="sq-nav"] [data-view="opps"]').click().catch(() => {}); await page.waitForTimeout(700);

  // ١ المجلسُ على البطاقة
  const c1 = await page.evaluate(() => { const card = document.querySelector('[data-role="so-card"]'); const box = card?.querySelector('[data-role="so-council"]');
    const v = box?.querySelector('[data-role="so-verdict"]');
    return { verdict: v?.textContent || "", cls: v?.className || "", members: [...(box?.querySelectorAll('[data-role="so-member"]') || [])].map(li => [li.textContent.trim(), li.dataset.v]),
      score: box?.textContent.match(/(\d+)\/100/)?.[1], whyOpen: box?.querySelector('[data-role="so-why"]')?.open,
      card2: document.querySelectorAll('[data-role="so-card"]')[1]?.querySelector('[data-role="so-verdict"]')?.className || "" }; });
  const sum = page.locator('[data-role="so-card"]').first().locator('[data-role="so-why"] summary');
  await sum.click(); await page.waitForTimeout(350);
  const why = await page.evaluate(() => { const d = document.querySelector('[data-role="so-card"] [data-role="so-why"]');
    return { open: d?.open, lines: [...(d?.querySelectorAll("ul li") || [])].map(li => li.textContent.trim()), h: d?.querySelector("summary")?.getBoundingClientRect().height }; });
  if (SHOTS) await page.locator('[data-role="so-card"]').first().screenshot({ path: `${SHOTS}/d786-card-${vp.width}-${theme}.png` }).catch(() => {});
  const ok1 = c1.verdict === "المجلس يوافق" && /\bok\b/.test(c1.cls) && /\bwarn\b/.test(c1.card2) && c1.score === "86"
    && JSON.stringify(c1.members.map(x => x[0])) === JSON.stringify(ROLES) && c1.members.map(x => x[1]).join() === "ok,ok,ok,na,ok,ok,ok" && c1.whyOpen === false
    && why.open === true && why.lines.length === 7 && why.lines[2].includes("ربحٌ في 3 أرباعٍ متتالية") && why.lines[3].includes("غير متوفّر") && why.h >= 32;
  say(ok1, `${label}: ١ بطاقةُ الفرصة تحمل مجلسَ صقر: حكمَه ودرجتَه وأعضاءه السبعة بالترتيب بحكم كلٍّ، و«لماذا» مطويّةٌ تُفتح بسطر كلّ عضو (وغيرُ المتوفّر يقول ذلك)`,
    JSON.stringify({ v: c1.verdict, s: c1.score, m: c1.members.map(x => x[1]).join(), n: why.lines.length, h: why.h }));

  // ٢ «الرابط»
  const lk = await page.evaluate(() => { const b = document.querySelector('[data-role="so-card"] [data-role="so-link"]');
    return { star: !!b?.querySelector(".ai-star"), t: b?.textContent || "", second: !!document.querySelectorAll('[data-role="so-card"]')[1]?.querySelector('[data-role="so-link"]') }; });
  say(lk.star && /الرابط: شراء/.test(lk.t) && /ثقةٌ متوسطة/.test(lk.t) && /ما يغيّر الحكم: إغلاقٌ دون 24\.20/.test(lk.t) && !lk.second,
    `${label}: ٢ «الرابط» يقرأ الأعضاءَ معاً: قرارُه وثقتُه وما يغيّر الحكم — ولا رابطَ لما لم يُقرأ`, lk.t.slice(0, 80));

  // ٣ المستبعَد
  const rj0 = await page.evaluate(() => { const d = document.querySelector('[data-role="so-rejected"]');
    return { open: d?.open, sum: d?.querySelector("summary")?.textContent || "", meta: document.querySelector('[data-role="so-meta"]')?.textContent || "",
      h: d?.querySelector("summary")?.getBoundingClientRect().height }; });
  await page.locator('[data-role="so-rejected"] summary').click(); await page.waitForTimeout(350);
  const rj = await page.locator('[data-role="so-rej"]').evaluateAll(ls => ls.map(l => l.textContent.trim()));
  if (SHOTS) await page.locator('[data-role="so-rejected"]').screenshot({ path: `${SHOTS}/d786-rej-${vp.width}-${theme}.png` }).catch(() => {});
  say(rj0.open === false && /\(\s*2\s*\)/.test(rj0.sum) && /الفرصُ بعد مجلس صقر:\s*2/.test(rj0.meta) && /استبعد المجلسُ\s*2/.test(rj0.meta) && rj0.h >= 32
      && rj.length === 2 && /إقالةُ الرئيس/.test(rj[0]) && /الثاني على التوالي/.test(rj[1]),
    `${label}: ٣ ما رفضه عضوٌ يُعرض في «استبعدها مجلسُ صقر» مطويّاً بسببه (إقالةُ الرئيس · ثاني ربعِ خسارة)، وعددُه في سطر المسح`, JSON.stringify({ meta: rj0.meta.slice(-70), rj: rj.map(x => x.slice(0, 40)) }));

  // ٥ التباينُ والخطُّ واللمسُ والفيض
  const meas = await page.evaluate(`(${CONTRAST})()`).then(() => null).catch(() => null);
  const m5 = await page.evaluate(src => { const cr = eval(`(${src})()`); const r = document.querySelector('[data-role="so"]'); const W = document.documentElement.clientWidth;
    const chips = [...document.querySelectorAll('[data-role="so-verdict"], [data-role="so-member"]')].map(cr);
    let minT = 99, minF = 99;
    r?.querySelectorAll("button, summary").forEach(b => { const x = b.getBoundingClientRect(); if (x.width && x.height && b.offsetParent) minT = Math.min(minT, x.height); });
    r?.querySelectorAll('[data-role="so-council"] *, [data-role="so-rejected"] *, [data-role="so-link"] *').forEach(e => {
      if (e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    const main = document.querySelector(".app-main");
    return { minC: Math.min(...chips), n: chips.length, minT, minF, over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W }; }, CONTRAST.toString());
  say(meas === null && m5.n >= 15 && m5.minC >= 4.5 && m5.minF >= 9.5 && m5.minT >= 32 && m5.over <= 1,
    `${label}: ٥ التباين (الحكمُ والأعضاءُ ≥ 4.5) والخطُّ ≥ 9.5 واللمسُ ≥ 32 — بلا فيض`, JSON.stringify({ ...m5, minC: +m5.minC.toFixed(2) }));

  // ٥ب الحركة: «لماذا» تُفتح بانسيابية وتسكن مع تفضيل تقليلها
  const anim = await page.evaluate(() => getComputedStyle(document.querySelector('[data-role="so-why"][open] ul')).animationName);
  await page.emulateMedia({ reducedMotion: "reduce" }); await page.waitForTimeout(200);
  const anim0 = await page.evaluate(() => getComputedStyle(document.querySelector('[data-role="so-why"][open] ul')).animationName);
  await page.emulateMedia({ reducedMotion: "no-preference" });
  say(anim !== "none" && anim0 === "none", `${label}: ٥ب «لماذا» تُفتح بانسيابية وتسكن مع تفضيل تقليل الحركة`, `${anim} → ${anim0}`);

  // ٤ «عقود الخيارات»: حكمُ المجلس في البطاقة
  await page.locator('[data-role="sq-market"] [data-market="us"]').click(); await page.waitForTimeout(1400);
  await page.locator('[data-role="sq-nav"] [data-view="options"]').click(); await page.waitForTimeout(1200);
  const chip = await page.locator('[data-role="op-council"]').first().textContent().catch(() => "");
  const cc = await page.evaluate(src => { const el = document.querySelector('[data-role="op-council"]'); return el ? eval(`(${src})()`)(el) : 0; }, CONTRAST.toString());
  if (SHOTS) await page.locator('[data-role="op-pick"]').first().screenshot({ path: `${SHOTS}/d786-pick-${vp.width}-${theme}.png` }).catch(() => {});
  say(/المجلس يوافق/.test(chip || "") && /82\/100/.test(chip || "") && cc >= 4.5 && errs.length === 0,
    `${label}: ٤ بطاقةُ «عقود الخيارات» تقول حكمَ مجلس صقر ودرجتَه — ولا خطأ`, JSON.stringify({ chip, cc: +cc.toFixed(2), err: errs[0] || "" }));
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
