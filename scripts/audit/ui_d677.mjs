// ─────────────────────────────────────────────────────────────────────────
// D677 · D678 · D679 — ملاحظاتُ المالك (2026-10-10) في الجوال والحاسوب:
//   «مختبرُ الأبحاث ينتقل مكانَ المراقبة، والمراقبةُ قسمٌ مكانه — والشركاتُ ثلاثٌ في الصفّ على الحاسوب واثنتان على الجوال،
//    وتفاصيلُها ملمومة» · «سيطر على التصاميم الشاذّة: سويتش، زر، قائمة منسدلة» ·
//   «المستشارُ الآليّ في تحليل الذكاء مكانَ التقرير الشامل، بتصميمٍ يحاكي التطبيق».
// يُفتح التطبيقُ الحقيقيّ (‏vite) على 390×844 و1280×900 ويُقاس من الـDOM. لقطاتٌ في SP_SHOTS إن ضُبط.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5233;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const SHOTS = process.env.SP_SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const WL = [["2222", "أرامكو السعودية", 24.1, 0.42], ["1120", "مصرف الراجحي", 62.3, -0.81], ["7010", "الاتصالات السعودية", 41.2, 1.12],
  ["2280", "المراعي", 44.44, 0.0], ["4190", "جرير للتسويق", 13.9, -0.3], ["1150", "مصرف الإنماء", 26.5, 0.6], ["4013", "د. سليمان الحبيب", 268.0, 1.4]]
  .map(([symbol, name, price, change_pct]) => ({ symbol, name, price, change_pct }));
const SCR = { rows: WL.map((w, i) => ({ symbol: `${w.symbol}.SR`, name: w.name, price: w.price, fair_value: +(w.price * (1 + (i - 3) / 20)).toFixed(2),
  upside_pct: (i - 3) * 5, fair_value_conf: "متوسطة", decision: ["شراء", "انتظار", "احتفاظ", "تجنب", "شراء قوي", "انتظار", "شراء"][i] })) };
const AUTOPILOT = { asof: "2026-10-10", verdict: "المحفظة: فرصتا شراءٍ بشروطهما، ومركزٌ يحتاج تخفيفاً.", goal: "هدف 1,000,000: أنجزتَ 46٪ وتصل بعد 6.1 سنة.",
  points: [{ t: "الراجحي عند دعمه الأسبوعيّ وإجماعُ البيوت فوق سعره 12٪", tone: "+" }, { t: "الاتصالات تركّزٌ 27٪ من المحفظة", tone: "-" },
           { t: "جرير: عقدٌ جوهريٌّ بـ250 مليون يدعم الإيراد", tone: "+" }, { t: "السيولة 9٪ تنتظر قناعةً مكتملة", tone: "=" }],
  flags: ["تركّز: الاتصالات 27.4% من المحفظة"],
  actions: [{ symbol: "1120", name: "مصرف الراجحي", action: "اشترِ الآن", level: "60.20–61.40", why: "دعمٌ شهريّ وجودة 82" },
            { symbol: "7010", name: "الاتصالات السعودية", action: "خفّف", level: "42.80–43.50", why: "فوق وزنها المستهدف 7 نقاط" }],
  protections: ["أرامكو: لا شراءَ فوق المقاومة الأسبوعية"], principles: [{ p: "اشترِ حين يكون الخوفُ سيّد السوق", book: "المستثمر الذكي", page: 213 }] };

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) {
  await new Promise(r => setTimeout(r, 500));
  try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { }
}
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp, cols] of [["الجوال", { width: 390, height: 844, isMobile: true, hasTouch: true }, 2], ["الحاسوب", { width: 1280, height: 900 }, 3]]) {
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: !!vp.isMobile, hasTouch: !!vp.hasTouch, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.route("**/api/v1/**", r => {
    const u = r.request().url();
    if (/\/market\/watchlist\/groups/.test(u)) return r.fulfill(body([{ id: 1, name: "الرئيسية", color: "var(--chart-1)", is_default: true }]));
    if (/\/market\/watchlist(\?|$)/.test(u)) return r.fulfill(body(WL));
    if (/\/market\/screener/.test(u)) return r.fulfill(body(SCR));
    if (/\/ai\/portfolio-autopilot\/plan/.test(u)) return r.fulfill(body({ target: 1000000, plan: {} }));
    if (/\/ai\/portfolio-autopilot/.test(u)) return r.fulfill(body(AUTOPILOT));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });

  // ١ · المراقبةُ قسمٌ ببطاقاتٍ: اثنتان في الصفّ على الجوال، وثلاثٌ على الحاسوب
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const wl = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const grid = [...document.querySelectorAll("div.grid")].find(g => g.className.includes("lg:grid-cols-3") && g.children.length >= 6);
    const cards = grid ? [...grid.children] : [];
    const tops = cards.map(c => Math.round(c.getBoundingClientRect().top));
    const perRow = tops.filter(t => t === tops[0]).length;
    const minH = cards.length ? Math.min(...cards.map(c => Math.round(c.getBoundingClientRect().height))) : 0;
    const withFv = cards.filter(c => c.textContent.includes("العادل")).length;
    const h1 = [...document.querySelectorAll("h1")].some(h => h.textContent.trim() === "المراقبة");
    return { W, sw, n: cards.length, perRow, minH, withFv, h1 };
  });
  say(wl.h1 && wl.n === 7, `${label}: «المراقبة» قسمٌ مستقلٌّ ببطاقةٍ لكلّ شركة`, `${wl.n} بطاقات`);
  say(wl.perRow === cols, `${label}: ${cols === 2 ? "بطاقتان" : "ثلاثُ بطاقاتٍ"} في الصفّ`, `${wl.perRow}`);
  say(wl.withFv === wl.n, `${label}: تفاصيلُ ملمومة — العادلُ والقرارُ في كلّ بطاقة`, `${wl.withFv}/${wl.n}`);
  say(wl.sw <= wl.W + 1 && wl.minH >= 32, `${label}: لا فيضَ أفقيّ، والبطاقةُ هدفُ لمسٍ ≥ 32px`, `محتوى ${wl.sw} · شاشة ${wl.W} · ${wl.minH}px`);
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `watchlist_${vp.width}.png`), fullPage: true });

  // ٢ · القائمةُ الجانبية: المراقبةُ مكانَ المختبر
  const nav = await page.evaluate(() => ({ wl: !!document.querySelector('a[href="/watchlist"]'), stars: !!document.querySelector('a[href="/stars"]') }));
  say(nav.wl && !nav.stars, `${label}: بندُ «المراقبة» في القائمة مكانَ «مختبر الأبحاث»`);

  // ٣ · المختبرُ تبويبٌ في المحفظة
  await page.goto(`http://localhost:${PORT}/stars`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const lab = await page.evaluate(() => ({
    url: location.pathname + location.search,
    tab: [...document.querySelectorAll("nav button")].some(b => b.textContent.trim() === "المختبر" && b.getAttribute("aria-pressed") === "true"),
    title: document.body.textContent.includes("مختبر الأبحاث"),
    noWatchTab: ![...document.querySelectorAll("nav button")].some(b => b.textContent.trim() === "المراقبة"),
  }));
  say(lab.tab && lab.title && lab.noWatchTab, `${label}: «المختبر» تبويبٌ في المحفظة مكانَ «المراقبة»، والرابطُ القديم يفتحه`, lab.url);
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `lab_${vp.width}.png`) });

  // ٤ · المستشارُ في تحليل الذكاء مكانَ التقرير الشامل
  await page.goto(`http://localhost:${PORT}/ai`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const ai = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const t = document.body.textContent;
    return { adv: t.includes("المستشار الآلي") && t.includes("اشترِ الآن"), rep: t.includes("التقرير الشامل"), W, sw };
  });
  say(ai.adv && !ai.rep, `${label}: «المستشار الآلي» في تحليل الذكاء ولا «تقريرَ شاملاً»`);
  say(ai.sw <= ai.W + 1, `${label}: المستشارُ بلا فيضٍ أفقيّ`, `محتوى ${ai.sw} · شاشة ${ai.W}`);
  if (SHOTS) {
    const h = await page.$("text=المستشار الآلي");
    if (h) await h.scrollIntoViewIfNeeded().catch(() => {});
    await page.screenshot({ path: join(SHOTS, `advisor_${vp.width}.png`) });
  }
  await page.goto(`http://localhost:${PORT}/governance`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  say(!(await page.evaluate(() => document.body.textContent.includes("المستشار الآلي"))), `${label}: ولا مستشارَ في الحوكمة — لا تكرار`);

  // ٥ · لا عنصرَ تحكّمٍ من نظام الجهاز في هذه الصفحات (D678)
  let natives = 0;
  for (const path of ["/watchlist", "/portfolio?tab=lab", "/ai", "/settings"]) {
    await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(1200);
    natives += await page.evaluate(() => document.querySelectorAll('select, input[type="checkbox"], input[type="radio"]').length);
  }
  say(natives === 0, `${label}: لا قائمةَ منسدلةً ولا صندوقَ اختيارٍ من نظام الجهاز — عناصرُ التطبيق وحدها`, `${natives}`);
  await ctx.close();
}
await browser.close(); stop();
console.log((fail ? "FAIL" : "PASS") + " D677 · D678 · D679 — المراقبةُ قسمٌ والمختبرُ تبويب · عناصرُ التحكّم الموحّدة · المستشارُ في تحليل الذكاء");
process.exit(fail);
