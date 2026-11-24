// ─────────────────────────────────────────────────────────────────────────
// D794–D799 — غرفةُ التداول كما أمر المالك (2026-11-24):
//  ‏D794 «التكبيرُ كأوّلِ مرّة قبل تقسيم الشاشات: يملأ المتصفّحَ على الحاسوب والجوال، وزرُّ التصغير أصلُ إليه بلا صعوبة»، و«صفٌّ خارجيٌّ أساسيّ
//        فيه الأحداثُ وتحليلُ الرسم وبجانبه زرُّ تقسيم الشاشة والتكبير والتصغير — خارج الشاشات».
//  ‏D795 «الإطاراتُ تُنتخب بالتفضيل — نجمةٌ في قائمة الإطارات، وتظهر بترتيب ضغطي — والمخصَّصُ (6 دقائق) يُفضَّل أيضاً — وما يكون إجباري».
//  ‏D796 «لوحتا قوّة الاتجاه والسيولة: احفظ الكلماتِ والألوان، وبدل الأرقام (57 · 65 · ADX 24) مؤشّرٌ كميزان الماء، والتفاصيلُ إن أردتُها».
//  ‏D798 «ألوانٌ رئيسيةٌ في إعدادات المؤشّرات كتريدنق فيو (أبيض · أصفر · أحمر · أخضر · المتشبّعة)»، و«منتقي الألوان يُغلق إذا ضغطتُ بسرعة».
//  ‏D799 «على الجوال: مستوياتُ الفيبوناتشي ليست ثابتةً أمام الشموع — تلحقني كنقاطٍ متّصلة» و«نقاطٌ منقّطةٌ متّصلةٌ بالأرقام عند التكبير والتصغير».
//
//   أ  طبقةُ الرسم (‏chartOverlay) بمحاكٍ: الخطُّ والمنطقةُ يبدآن من موجتهما (‏x0) لا من حافّة اللوحة، وما بدأ يمينَ المشهد لا يُرسم، والرقمُ المثبَّت
//      لا يُلصق بالحافّة إن خرجت شمعتُه، ولا مِهمازَ منقّطاً حين ‏leaders=false.
//   ب  الإعدادُ موصول: «ثابتةٌ على الشموع» افتراضاً، والرسمُ يمرّر ‏x0 ويطفئ المِهمازَ على الشاشة الضيّقة — ويُقرأ ذلك من سمات الرسم في المتصفّح.
//   ج  المتصفّح (الحاسوب فاتحاً · الجوال داكناً): الصفُّ الخارجيّ، والتكبيرُ، والمفضّلاتُ (والمخصَّص، والمزامنةُ بين الشاشات)، والموازينُ،
//      ولوحةُ الألوان (لا يُهدم الزرّ، ولا تُغلق النافذةُ بالضغط السريع، وحقلُ الرقم يبقى في يدك).
//    SHOTS=dir node scripts/audit/troom_d794.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const rd = p => readFileSync(join(FRONT, p), "utf8");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ═ أ طبقةُ الرسم ═
const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const tmp = mkdtempSync(join(tmpdir(), "sp-d799-"));
await build({ entryPoints: [join(FRONT, "src/lib/chartOverlay.ts")], outfile: join(tmp, "over.mjs"), format: "esm", bundle: true, logLevel: "silent" });
const { ChartOverlay } = await import(pathToFileURL(join(tmp, "over.mjs")).href);
/* الشمعةُ k عند ‏OFF + 10k؛ عرضُ اللوحة 600 */
const draw = (part, OFF = 0) => {
  const rec = [];
  const ctx = new Proxy({ measureText: (t) => ({ width: String(t).length * 6 }) },
    { get: (t, k) => (k in t ? t[k] : (...a) => { rec.push([k, a]); }), set: (t, k, v) => { t[k] = v; return true; } });
  const ov = new ChartOverlay();
  ov.attached({ chart: { timeScale: () => ({ logicalToCoordinate: (k) => OFF + 10 * k, options: () => ({ barSpacing: 10 }) }) },
                series: { priceToCoordinate: (p) => 400 - p }, requestUpdate() { } });
  ov.set({ textTop: 10, ...part });
  ov.paneViews()[0].renderer().draw({ useMediaCoordinateSpace: (cb) => cb({ context: ctx, mediaSize: { width: 600, height: 400 } }) });
  return rec;
};
const L = (price, o = {}) => ({ price, color: "W", lcolor: "W", label: price.toFixed(2), lx: 40, lpos: "above", width: 1, ...o });
const moves = r => r.filter(x => x[0] === "moveTo").map(x => x[1][0]);
const fills = r => r.filter(x => x[0] === "fillRect").map(x => x[1][0]);
const texts = r => r.filter(x => x[0] === "fillText").length;
const dashes = r => r.filter(x => x[0] === "setLineDash" && Array.isArray(x[1][0]) && x[1][0][0] === 2).length;
{
  const a1 = draw({ levels: [L(300, { x0: 20, label: undefined }), L(200, { label: undefined })], bands: [{ p1: 300, p2: 290, color: "R", x0: 20 }] });
  // المشهدُ سُحب إلى الماضي: بدايةُ الموجة (20) يمينَ اللوحة ⇒ لا خطَّ ولا منطقة
  const a2 = draw({ levels: [L(300, { x0: 20, label: undefined })], bands: [{ p1: 300, p2: 290, color: "R", x0: 20 }] }, 400);
  say(JSON.stringify(moves(a1)) === "[200,0]" && JSON.stringify(fills(a1)) === "[200]" && moves(a2).length === 0 && fills(a2).length === 0,
      "أ١ الخطُّ والمنطقةُ يبدآن من أوّل الموجة (لا من حافّة اللوحة) فيثبتان على الشموع، وما بدأ يمينَ المشهد لا يُرسم — والقديمُ بلا ‏x0 على العرض كلِّه",
      `${JSON.stringify(moves(a1))} · ${JSON.stringify(fills(a1))} · ${moves(a2).length}`);
  // الرقمُ المثبَّت: شمعتُه (40) خارج المشهد يميناً ⇒ لا رقمَ ملصقٌ بالحافّة؛ وغيرُ المثبَّت كما كان
  const a3 = draw({ levels: [L(300, { x0: 20 })] }, 300), a4 = draw({ levels: [L(300)] }, 300), a5 = draw({ levels: [L(300, { x0: 20 })] }, 0);
  say(texts(a3) === 0 && texts(a4) === 1 && texts(a5) === 1,
      "أ٢ رقمُ المستوى المثبَّت يتبع شمعتَه: إن خرجت من المشهد لم يُلصق بالحافّة (وهو «اللحاق» الذي رآه المالك)", `${texts(a3)} · ${texts(a4)} · ${texts(a5)}`);
  const crowd = [L(300), L(297), L(294), L(291)];
  const on = draw({ levels: crowd, leaders: true }), off = draw({ levels: crowd, leaders: false });
  say(dashes(on) >= 1 && dashes(off) === 0 && texts(off) >= 1,
      "أ٣ المِهمازُ المنقّطُ (النقاطُ المتّصلةُ بالأرقام) يُطفأ حين ‏leaders=false — والرقمُ يبقى على خطّه أو يُترك", `${dashes(on)} · ${dashes(off)} · ${texts(off)}`);
}

// ═ ب الإعدادُ موصول ═
const pc = rd("src/components/chart/ProChart.tsx"), d7 = rd("src/components/analysis/d7m.ts"), pn = rd("src/components/analysis/D7MPanel.tsx");
say(/fibAnchor: "fixed" as "fixed" \| "moving"/.test(d7) && /\(st\.cfg\.fibAnchor \|\| "fixed"\) === "fixed" \? D\.fib\.startIndex : undefined/.test(pc)
    && (pc.match(/, x0 \}\)/g) || []).length >= 3 && /leaders: false \}\);/.test(pc)   /* ‏D805: لا مِهمازَ في أيّ عرض */
    && /data-role="fib-anchor"/.test(pn) && /«ثابتةٌ على الشموع»|ثابتةٌ على الشموع/.test(pn) && /تتبع الشاشة/.test(pn),
    "ب١ «ثابتةٌ على الشموع» افتراضاً و«تتبع الشاشة» خيارٌ في إعدادات D7M، والرسمُ يمرّر بدايةَ الموجة للخطوط والمناطق ويطفئ المِهمازَ في كلّ عرض (‏D805)");

// ═ ج المتصفّح ═
const PORT = 5294;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const SHOTS = process.env.SHOTS;
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
/* صعودٌ بموجة، والحجمُ أثقلُ في الصاعدة ⇒ لوحتا القوّة تُحسبان */
const bars = (n = 150) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = 600 + i * 1.1 + Math.sin(i / 2) * 3 + Math.sin(i / 9) * 14, o = 600 + (i - 1) * 1.1 + Math.sin((i - 1) / 2) * 3 + Math.sin((i - 1) / 9) * 14;
  return { date: day, open: o, high: Math.max(o, c) + 1, low: Math.min(o, c) - 1, close: c, volume: c >= o ? 3e6 : 1e6 };
});

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب · فاتح", { width: 1366, height: 860 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d794-init")) return;
    sessionStorage.setItem("d794-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_room_layout", "1"); localStorage.removeItem("sp_room_panes"); localStorage.removeItem("sp_chart_tf_fav");
    localStorage.removeItem("sp_d7m_cfg_v2"); localStorage.removeItem("sp_stochrsi_cfg"); localStorage.setItem("sp_chart_tf", "1d");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2800);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  const shot = async n => { if (SHOTS) await page.screenshot({ path: join(SHOTS, `d794_${n}_${vp.width}_${theme}.png`) }).catch(() => {}); };

  // ── ج١ ‏D794 الصفُّ الخارجيّ ──
  const row = () => page.evaluate(() => {
    const h = document.querySelector('[data-role="troom-mhead"]'), chart = document.querySelector('[data-role="troom-chart"]');
    const inHead = k => !!h?.querySelector(`[data-role="${k}"]`);
    const inCharts = k => [...document.querySelectorAll('[data-role="pro-chart"]')].some(c => c.querySelector(`[data-role="${k}"]`));
    /* ‏D801 (المالك 2026-11-24): «زرُّ تقسيم الشاشات بجانب الإطارات — لا آخرَ شيءٍ على اليسار»: واحدٌ بعد أزرار الإطارات مباشرة، لا في الصفّ الخارجيّ */
    const lay = document.querySelectorAll('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').length === 1
      && document.querySelectorAll('[data-role="troom-layout"]').length === 1 && !inHead("troom-layout");
    return { head: !!h && h.parentElement === chart, ee: inHead("ee-btn"), read: inHead("chart-read-btn"), lay, wide: inHead("troom-wide"),
      inner: ["pc-layout", "pc-full", "chart-read-btn", "ee-btn"].filter(inCharts) };
  });
  const r1 = await row();
  await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first()   /* ‏D801: بجانب الإطارات */.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-layout-menu"] [data-layout="2"]').click(); await page.waitForTimeout(1800);
  const r2 = await row();
  say(r1.head && r1.ee && r1.read && r1.lay && r1.wide && !r1.inner.length && r2.head && r2.read && r2.lay && r2.wide && !r2.inner.length,
      `${label}: ج١ صفٌّ خارجيٌّ واحد فوق الشاشات (الأحداث · تحليل الرسم · التكبير) في الشاشة الواحدة والمتعدّدة، وزرُّ «الشاشات» بجانب الإطارات (‏D801) — ولا ملءَ شاشةٍ ولا تحليلَ داخل شاشة`,
      JSON.stringify({ r1, r2 }));

  // ── ج٢ ‏D795 المفضّلاتُ مشتركةٌ بين الشاشات، والمخصَّصُ يُفضَّل ──
  const favOf = k => page.locator('[data-role="troom-pane"]').nth(k).locator('[data-role="pc-tfs"] button[data-fav="1"]').evaluateAll(es => es.map(e => e.getAttribute("data-tf")));
  const f0 = [await favOf(0), await favOf(1)];
  await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="pc-tf-more"]').click(); await page.waitForTimeout(300);
  await page.locator('[data-role="pc-tf-more-menu"] [data-star="1wk"]').click(); await page.waitForTimeout(200);
  await page.locator('[data-role="pc-tf-more-menu"] [data-star="1d"]').click(); await page.waitForTimeout(200);
  await page.locator('[data-role="pc-tf-more-menu"] [data-role="pc-custom"] input').fill("6");
  await page.locator('[data-role="pc-tf-more-menu"] [data-role="pc-custom"] .seg-btn', { hasText: "دقيقة" }).click();
  await page.locator('[data-role="pc-tf-more-menu"] [data-role="pc-custom-apply"]').click(); await page.waitForTimeout(1200);
  const ctf = await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="pro-chart"]').getAttribute("data-tf");
  await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="pc-tf-more"]').click(); await page.waitForTimeout(300);
  const starN = await page.locator(`[data-role="pc-tf-more-menu"] [data-star="${ctf}"]`).count();
  await page.locator(`[data-role="pc-tf-more-menu"] [data-star="${ctf}"]`).click().catch(() => {}); await page.waitForTimeout(250);
  await page.keyboard.press("Escape"); await page.mouse.click(5, 5).catch(() => {}); await page.waitForTimeout(300);
  const f1 = [await favOf(0), await favOf(1)];
  const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_chart_tf_fav") || "[]"));
  say(f0[0].length === 0 && f0[1].length === 0 && ctf === "6m" && starN === 1 && JSON.stringify(f1[0]) === JSON.stringify(["1wk", "1d", "6m"])
      && JSON.stringify(f1[1]) === JSON.stringify(f1[0]) && JSON.stringify(saved) === JSON.stringify(f1[0]),
      `${label}: ج٢ لا إطارَ مفروضاً؛ والنجمةُ تضع الإطارَ في الشريط بترتيب الضغط (أسبوع ثمّ يوم ثمّ «6 دقائق» المخصَّص) — في الشاشات كلِّها معاً، ويُحفظ`,
      JSON.stringify({ f0, ctf, starN, f1, saved }));

  // ── ج٣ ‏D796 الموازينُ بلا أرقام — والصغيرةُ في الشاشات المتعدّدة كذلك ──
  const mini = await page.evaluate(() => [...document.querySelectorAll('[data-role="troom-pane"] [data-role="force-panels"]')].map(f => ({
    mini: f.classList.contains("fp-mini"), digits: /\d/.test(f.textContent || ""), g: f.querySelectorAll('[data-role="fp-gauge"]').length,
    words: [...f.querySelectorAll('[data-role="fp-trend"], [data-role="fp-liq"]')].map(x => (x.textContent || "").trim()).join(" | ") })));
  say(mini.length >= 1 && mini.every(m => m.mini && !m.digits && m.g >= 1 && m.words.length > 0),
      `${label}: ج٣ لوحتا القوّة الصغيرتان في الشاشات المتعدّدة كلمةٌ ولونٌ وميزان — بلا رقم`, JSON.stringify(mini).slice(0, 240));

  // عودةٌ إلى شاشةٍ واحدة
  await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first()   /* ‏D801: بجانب الإطارات */.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-layout-menu"] [data-layout="1"]').click(); await page.waitForTimeout(1800);
  const big = await page.evaluate(() => { const t = document.querySelector('[data-role="troom-chart"] [data-role="fp-trend"]');
    return { n0: t?.querySelectorAll('[data-role="fp-strength"]').length ?? -1, word: t?.querySelector('[data-role="fp-word"]')?.textContent || "",
      score: Number(t?.querySelector('[data-role="fp-gauge"]')?.getAttribute("data-score")), faceDigits: /\d/.test(t?.querySelector('[data-role="fp-face"]')?.textContent || "x") }; });
  await page.locator('[data-role="troom-chart"] [data-role="fp-trend"] [data-role="fp-face"]').click(); await page.waitForTimeout(450);
  const det = await page.evaluate(() => { const t = document.querySelector('[data-role="troom-chart"] [data-role="fp-trend"]'), d = t?.querySelector('[data-role="fp-detail"]');
    return { n: d?.querySelector('[data-role="fp-strength"]')?.textContent || "", exp: t?.querySelector('[data-role="fp-face"]')?.getAttribute("aria-expanded"),
      anim: d ? getComputedStyle(d).animationName + "|" + getComputedStyle(d).transitionProperty : "" }; });
  await shot("gauge");
  await page.locator('[data-role="troom-chart"] [data-role="fp-trend"] [data-role="fp-face"]').click(); await page.waitForTimeout(450);
  const closed = await page.locator('[data-role="troom-chart"] [data-role="fp-trend"] [data-role="fp-strength"]').count();
  say(big.n0 === 0 && big.word.length > 0 && big.score >= 0 && big.score <= 100 && !big.faceDigits && Number(det.n) >= 0 && det.n !== "" && det.exp === "true" && closed === 0
      && /fp|fade|rise|slide|height|grid|opacity|all/i.test(det.anim),
      `${label}: ج٣ب الوجهُ كلمةٌ وميزانٌ بلا رقم، والضغطُ يفتح القوّةَ وشواهدَها بانسياب ويطويها`, JSON.stringify({ big, det, closed }));

  // ── ج٤ ‏D794 التكبيرُ في الشاشة الواحدة: يملأ النافذة، والرسمُ إلى قاعها، والزرُّ ظاهرٌ — وEsc والزرُّ يعيدانه ──
  if (!desk) await page.evaluate(() => scrollTo(0, 0));
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(1600);
  await shot("wide1");
  const W1 = await page.evaluate(() => { const c = document.querySelector('[data-role="troom-chart"]'), r = c.getBoundingClientRect(),
    p = document.querySelector('[data-role="troom-one"] [data-role="pro-chart"]').getBoundingClientRect(), b = document.querySelector('[data-role="troom-wide"]').getBoundingClientRect();
    return { r: [r.left, r.top, r.width, r.height].map(Math.round), pb: Math.round(p.bottom), btn: [Math.round(b.top), Math.round(b.bottom)], sh: c.scrollHeight - c.clientHeight,
      iw: document.documentElement.clientWidth, ih: innerHeight, on: document.documentElement.classList.contains("troom-wide-on") }; });
  await page.keyboard.press("Escape"); await page.waitForTimeout(500);
  const esc = await page.locator('[data-role="troom-chart"]').getAttribute("data-wide");
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(900);
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(600);
  const back = await page.locator('[data-role="troom-chart"]').getAttribute("data-wide");
  say(W1.on && W1.r[0] === 0 && W1.r[1] === 0 && W1.r[2] >= W1.iw - 1 && Math.abs(W1.r[3] - W1.ih) <= 1 && Math.abs(W1.pb - W1.ih) <= 2 && W1.sh <= 1
      && W1.btn[0] >= 0 && W1.btn[1] <= W1.ih && esc === "0" && back === "0",
      `${label}: ج٤ التكبيرُ يملأ النافذةَ والرسمُ إلى قاعها بلا تمرير، وزرُّ التصغير ظاهرٌ — وEsc والزرُّ نفسُه يعيدانه`, JSON.stringify({ W1, esc, back }));

  // ── ج٥ ‏D794 أربعُ شاشاتٍ مكبَّرة: الصفُّ لاصقٌ أعلى النافذة وإن مُرِّرت الشاشات ──
  await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first()   /* ‏D801: بجانب الإطارات */.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-layout-menu"] [data-layout="4"]').click(); await page.waitForTimeout(1500);
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(1600);
  await page.evaluate(() => { const c = document.querySelector('[data-role="troom-chart"]'); c.scrollTop = c.scrollHeight; }); await page.waitForTimeout(400);
  await shot("wide4");
  const W4 = await page.evaluate(() => { const c = document.querySelector('[data-role="troom-chart"]'), b = document.querySelector('[data-role="troom-wide"]').getBoundingClientRect();
    return { st: Math.round(c.scrollTop), btn: [Math.round(b.top), Math.round(b.bottom)], ih: innerHeight }; });
  await page.locator('[data-role="troom-wide"]').click(); await page.waitForTimeout(600);
  const back4 = await page.locator('[data-role="troom-chart"]').getAttribute("data-wide");
  say(W4.btn[0] >= 0 && W4.btn[1] <= W4.ih && back4 === "0" && (desk || W4.st > 0),
      `${label}: ج٥ في الشاشات المكبَّرة زرُّ التصغير لاصقٌ أعلى النافذة — يُضغط بلا تمريرٍ إليه${desk ? "" : " وإن مُرِّرت الشاشاتُ إلى آخرها"}`, JSON.stringify({ W4, back4 }));
  await page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first()   /* ‏D801: بجانب الإطارات */.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-layout-menu"] [data-layout="1"]').click(); await page.waitForTimeout(1800);

  // ── ج٦ ‏D799 الفيبو ثابتةٌ على الشموع افتراضاً، و«تتبع الشاشة» خيار — والمِهمازُ مطفأٌ على الجوال ──
  const fibAt = () => page.evaluate(() => { const r = document.querySelector('[data-role="troom-one"] [data-role="pro-chart"]'); return { x0: r?.dataset.fibX0 ?? null, lead: r?.dataset.leaders ?? null }; });
  const fx = await fibAt();
  await page.locator('[data-role="troom-chart"] [data-role="pc-cfg"]').first().click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="d7m"]').first().click(); await page.waitForTimeout(500);
  const dlg = page.locator('[data-role="d7m-settings"]');
  const anchorOn = await dlg.locator('[data-role="fib-anchor"] button[aria-pressed="true"]').getAttribute("data-anchor").catch(() => "");
  await dlg.locator('[data-role="fib-anchor"] [data-anchor="moving"]').click(); await page.waitForTimeout(600);
  const fm = await fibAt();
  await dlg.locator('[data-role="fib-anchor"] [data-anchor="fixed"]').click(); await page.waitForTimeout(600);
  const ff = await fibAt();
  say(anchorOn === "fixed" && /^\d+$/.test(fx.x0 || "") && fm.x0 === "" && ff.x0 === fx.x0 && fx.lead === "0",
      `${label}: ج٦ مستوياتُ الفيبو «ثابتةٌ على الشموع» افتراضاً تبدأ من موجتها، و«تتبع الشاشة» خيارٌ يعيدها على العرض، والمِهمازُ المنقّطُ مطفأٌ على ${desk ? "الحاسوب" : "الجوال"} (‏D805)`,
      JSON.stringify({ anchorOn, fx, fm, ff }));

  // ── ج٧ ‏D798 لوحةُ الألوان: الزرُّ لا يُهدم، والنافذةُ لا تُغلق بالضغط السريع، وحقلُ الرقم يبقى في اليد ──
  const upBtn = dlg.locator('[data-color="trendUp"] [data-role="color-pick-btn"]'), dnBtn = dlg.locator('[data-color="trendDown"] [data-role="color-pick-btn"]');
  await upBtn.evaluate(e => { e.__d798 = 1; });
  await upBtn.click(); await page.waitForTimeout(250);
  const pal = await page.evaluate(() => { const pop = document.querySelector('[data-role="color-pick-pop"]');
    const hx = [...(pop?.querySelectorAll("[data-hex]") || [])].map(b => b.getAttribute("data-hex")); const r = pop?.getBoundingClientRect();
    const sw = [...(pop?.querySelectorAll(".cp-sw") || [])].map(b => Math.min(b.getBoundingClientRect().width, b.getBoundingClientRect().height));
    return { n: hx.length, has: ["#ffffff", "#ffeb3b", "#f23645", "#4caf50", "#089981", "#000000"].every(h => hx.includes(h)), inView: !!r && r.left >= 0 && r.right <= document.documentElement.clientWidth,
      minSw: Math.min(...sw) }; });
  await page.locator('[data-role="color-pick-pop"] [data-hex="#ffeb3b"]').click(); await page.waitForTimeout(120);
  /* ‏D798ب (كشفه هذا الفحص): كانت اللوحةُ تُقصّ داخل نافذة الإعدادات حين يكون زرُّها في العمود الأيمن — فكلُّ زرٍّ في النافذة تُفتح لوحتُه
     كاملةً داخل الشاشة، وأوّلُ ألوانها وآخرُها هما ما تحت الإصبع فعلاً */
  const allBtns = dlg.locator('[data-role="color-pick-btn"]'), nB = await allBtns.count(), clipped = [];
  for (let i = 0; i < nB; i++) {
    await allBtns.nth(i).scrollIntoViewIfNeeded(); await allBtns.nth(i).click(); await page.waitForTimeout(220);
    const ok = await page.evaluate(() => { const pop = document.querySelector('[data-role="color-pick-pop"]'); if (!pop) return "none";
      const r = pop.getBoundingClientRect(), W = document.documentElement.clientWidth;
      if (r.left < 0 || r.right > W || r.top < 0 || r.bottom > innerHeight) return "out";
      const sw = pop.querySelectorAll(".cp-sw"); const hit = e => { const q = e.getBoundingClientRect(); const t = document.elementFromPoint(q.left + q.width / 2, q.top + q.height / 2); return !!t && e.contains(t); };
      return hit(sw[0]) && hit(sw[sw.length - 1]) ? "ok" : "covered"; });
    if (ok !== "ok") clipped.push(`${i}:${ok}`);
    await page.keyboard.press("Escape"); await page.waitForTimeout(150);
  }
  say(nB >= 12 && clipped.length === 0 && await dlg.count() === 1,
      `${label}: ج٧أ لوحةُ كلّ زرِّ لونٍ في الإعدادات (${nB}) تُفتح كاملةً داخل الشاشة وألوانُها تحت الإصبع — لا تُقصّ في العمود الأيمن، وEsc يطويها وحدها`,
      clipped.join(" · ") || `${nB}`);
  // ضغطٌ سريعٌ متتابع: الهابطُ ثمّ لونُه ثمّ الصاعدُ ثمّ لونُه — بلا انتظار
  await dnBtn.click(); await page.locator('[data-role="color-pick-pop"] [data-hex="#9c27b0"]').click();
  await upBtn.click(); await page.locator('[data-role="color-pick-pop"] [data-hex="#4caf50"]').click();
  await page.waitForTimeout(300);
  const after = await page.evaluate(() => { const d = document.querySelector('[data-role="d7m-settings"]'), b = d?.querySelector('[data-color="trendUp"] [data-role="color-pick-btn"]');
    const cfg = JSON.parse(localStorage.getItem("sp_d7m_cfg_v2") || "{}");
    return { open: !!d, same: b?.__d798 === 1, label: b?.getAttribute("aria-label") || "", up: cfg.colors?.trendUp, dn: cfg.colors?.trendDown }; });
  // حقلُ «فترة المحور»: رقمان متتاليان والمؤشّرُ في الحقل نفسِه
  const num = dlg.locator('[data-role="d7m-trend"] input[type="number"]').first();
  await num.evaluate(e => { e.__d798 = 1; });
  await num.click(); await num.press("Control+a"); await page.keyboard.type("12", { delay: 60 }); await page.waitForTimeout(250);
  const nf = await page.evaluate(() => ({ same: document.activeElement?.__d798 === 1, v: document.activeElement?.value }));
  await shot("colors");
  say(pal.n === 40 && pal.has && pal.inView && pal.minSw >= 32 && after.open && after.same && /#4caf50/.test(after.label) && after.up === "#4caf50" && after.dn === "#9c27b0"
      && nf.same && nf.v === "12",
      `${label}: ج٧ لوحةُ ألوانٍ كتريدنق فيو (أربعون: الأبيض والأصفر والأحمر والأخضر والمتشبّعة، كلٌّ ≥ 32px داخل الشاشة)؛ والضغطُ السريعُ المتتابع لا يُغلق النافذة `
      + "ولا يهدم الزرّ، واللونان يُحفظان — وحقلُ الرقم يبقى في اليد بين حرفٍ وحرف", JSON.stringify({ pal, after, nf }));
  await dlg.locator('button[aria-label="إغلاق"]').first().click().catch(() => {}); await page.waitForTimeout(400);

  // ── ج٨ ‏D798 إعداداتُ Stoch RSI: اللوحةُ نفسُها، واللونُ يصل ويُحفظ ──
  await page.locator('[data-role="troom-chart"] [data-role="pc-cfg"]').first().click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="stochrsi"]').first().click(); await page.waitForTimeout(500);
  const sr = page.locator('[data-role="ind-settings"]');
  await sr.locator('[data-role="sr-k"] [data-role="color-pick-btn"]').click(); await page.waitForTimeout(250);
  const srN = await page.locator('[data-role="color-pick-pop"] [data-hex]').count();
  await page.locator('[data-role="color-pick-pop"] [data-hex="#ff9800"]').click(); await page.waitForTimeout(400);
  const srCfg = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_stochrsi_cfg") || "{}"));
  const srOpen = await sr.count();
  say(srN === 40 && srOpen === 1 && JSON.stringify(srCfg).includes("#ff9800"),
      `${label}: ج٨ إعداداتُ Stoch RSI باللوحة نفسِها، واللونُ المختارُ يُحفظ والنافذةُ قائمة`, `${srN} · ${JSON.stringify(srCfg).slice(0, 120)}`);
  await sr.locator('button[aria-label="إغلاق"]').first().click().catch(() => {}); await page.waitForTimeout(300);

  const over = await page.evaluate(() => document.scrollingElement.scrollWidth - innerWidth);
  say(errs.length === 0 && over <= 1, `${label}: لا خطأ في الصفحة ولا فيضَ أفقيّ`, errs[0] || `${over}px`);
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
