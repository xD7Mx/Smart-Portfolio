// ─────────────────────────────────────────────────────────────────────────
// D810–D812 — بأمر المالك (2026-11-24):
//  ‏D810 «ضع ميزةَ النقرتين لكلّ شاشة ليتكبّر المؤشّرُ الذي حصل عليه النقر — مؤشّرُ دحم يكون لوحده بوضع التكبير بعد النقرتين ويأخذ
//        مكانَ بقية الشاشة، ونفسُ الكلام لو نقرتُ نقرتين على ستوكاستيك آر إس آي أو أيّ مؤشّرٍ داخل أيّ شاشة».
//  ‏D811 «في خيارات حفظ الإطارات: السطرُ الطويلُ الذي يبدأ بتخصيص — اكتفِ بجملة: إنشاء لوحة جديدة»، و«احذف خيارَ الثلاث الذي تكون
//        الكبيرةُ فيه على اليمين، واكتفِ بجملة ثلاث شاشات: الكبيرةُ فوق والصغيرتان تحت بجانب بعض».
//  ‏D813 (كُشف في أثناء ‏D810): إخفاءُ خطّ ‏D (أو ‏K) من إعدادات ستوكاستيك يُحفظ ولا يُطبَّق — سطرُ «العين» كان يُظهر خطوطَ المؤشّر كلَّها.
//  ‏D812 «علامةُ البحث داخل الإطارات لا تدعم المؤشّرات — تاسي أو غيره، وبرنت والذهب وغيرها؛ مربّعُ البحث سبيلُنا إلى الرسم المراد،
//        فيجب دعمُ السوق السعوديّ والأمريكيّ والمؤشّرات أيضاً داخل كلّ إطار».
//    SHOTS=dir node scripts/audit/troom_d810.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ═ ساكنٌ على المصدر ═
const nc = t => t.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1");
const src = f => nc(readFileSync(join(FRONT, f), "utf8"));
const lm = src("src/components/market/LayoutMenu.tsx"), trs = src("src/components/market/TradeRoom.tsx"), pcs = src("src/components/chart/ProChart.tsx");
const cat = src("src/data/marketCatalog.ts");
say(/name: "ثلاث شاشات"/.test(lm) && !/"side"|LayoutPanelLeft|كبيرةٌ وبجانبها/.test(lm + trs) && />إنشاء لوحة جديدة</.test(lm) && !/تخصيص/.test(lm.replace(/\/\*[\s\S]*?\*\//g, ""))
    && !/sp_room_var3/.test(trs),
    "٠أ قائمةُ الشاشات: «ثلاث شاشات» وحدها (لا ترتيبَ «الكبيرةُ على اليمين»)، وزرُّ الحفظ «إنشاء لوحة جديدة» لا السطرُ الطويل");
const need = ["^TASI.SR", "^GSPC", "^IXIC", "^DJI", "BZ=F", "CL=F", "GC=F", "SI=F", "BTC-USD"];
say(need.every(s => cat.includes(`symbol: "${s}"`)) && /subscribeDblClick/.test(pcs) && /setStretchFactor/.test(pcs) && /prefers-reduced-motion/.test(pcs),
    "٠ب دليلُ المؤشّرات والسلع (تاسي · S&P · ناسداك · داو · برنت · غرب تكساس · الذهب · الفضّة · بتكوين) في البحث، والنقرتان تكبّران لوحةً بانسيابٍ يحترم تقليلَ الحركة");

// والكاشفُ على الخادم (هل يرسم الخادمُ كلَّ ما يجده البحث؟) يحمل القائمةَ نفسَها — لا رمزَ في البحث بلا فحصٍ على الخادم
const catSyms = [...cat.matchAll(/symbol: "([^"]+)"/g)].map(m => m[1]);
const doorSyms = [...readFileSync(join(ROOT, "scripts/audit/market_catalog_door_d812.py"), "utf8").match(/SYMBOLS = \[([\s\S]*?)\]/)[1].matchAll(/"([^"]+)"/g)].map(m => m[1]);
say(catSyms.length >= 15 && JSON.stringify(catSyms) === JSON.stringify(doorSyms), "٠ج كلُّ رمزٍ في دليل البحث يفحصه كاشفُ الخادم (القائمتان متطابقتان)", `${catSyms.length} · ${doorSyms.length}`);

const PORT = 5302;
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
const bars = (n = 150) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = 100 + i * 0.2 + Math.sin(i / 3) * 4, o = 100 + (i - 1) * 0.2 + Math.sin((i - 1) / 3) * 4;
  return { date: day, open: o, high: Math.max(o, c) + 1, low: Math.min(o, c) - 1, close: c, volume: c >= o ? 3e6 : 1e6 };
});
const sum = a => a.reduce((x, y) => x + y, 0);

const browser = await chromium.launch({ executablePath: CHROME });
const RUNS = [["الحاسوب · داكن", { width: 1440, height: 900 }, "dark", false], ["الحاسوب · فاتح", { width: 1366, height: 860 }, "light", false],
  ["الجوال · فاتح (لمس)", { width: 390, height: 844 }, "light", true], ["الحاسوب · تقليلُ الحركة", { width: 1440, height: 900 }, "dark", false, "reduce"]];
for (const [label, vp, theme, touch, motion] of RUNS) {
  const desk = vp.width >= 1024, calm = motion === "reduce";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, hasTouch: touch, isMobile: touch, reducedMotion: calm ? "reduce" : "no-preference" });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d810-init")) return;
    sessionStorage.setItem("d810-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_room_layout", "1"); localStorage.setItem("sp_room_var3", "side");   // قيمةٌ قديمةٌ لترتيبٍ حُذف — لا أثرَ لها
    localStorage.removeItem("sp_room_sizes"); localStorage.removeItem("sp_room_presets");
    localStorage.setItem("sp_room_panes", JSON.stringify([null, "1120", "2010", null])); localStorage.setItem("sp_chart_tf", "1d");
    localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: true, stochrsi: true, cvd: true, macd: false, d7m: true }));
    localStorage.setItem("sp_stochrsi_cfg", JSON.stringify({ dOn: false }));   // ‏D813: خطُّ ‏D مخفيٌّ من الإعدادات
    localStorage.setItem("sp_chart_ind_v3_s1", JSON.stringify({ vol: true, stochrsi: true, cvd: false, macd: true, d7m: true }));
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p === "/market/symbol-search") return r.fulfill(body([]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2800);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.waitForTimeout(300);
  const shot = async n => { if (SHOTS) await page.screenshot({ path: join(SHOTS, `d810_${n}_${vp.width}_${theme}${calm ? "_calm" : ""}.png`) }).catch(() => {}); };
  const chart = (k = 0) => page.locator('[data-role="troom-chart"] [data-role="pro-chart"]').nth(k);
  const hs = async (k = 0) => (await chart(k).getAttribute("data-pane-h") || "").split(",").filter(Boolean).map(Number);
  // موضعُ وسط اللوحة i: من أعلى المسرح بمجموع ما فوقها (وفاصلُ كلّ لوحةٍ بكسل)
  const at = async (k, i) => {
    const st = await chart(k).locator('[data-role="pc-stage"]').boundingBox(), h = await hs(k);
    return { x: st.x + st.width * 0.4, y: st.y + sum(h.slice(0, i)) + i + Math.max(1, h[i]) / 2 };
  };
  const dbl = async ({ x, y }) => {
    if (touch) { await page.touchscreen.tap(x, y); await page.waitForTimeout(90); await page.touchscreen.tap(x, y); }
    else await page.mouse.dblclick(x, y);
  };
  const look = (k = 0) => chart(k).evaluate(c => ({
    solo: c.dataset.solo, legOff: c.querySelector('[data-role="pc-legend"]')?.classList.contains("pc-leg-off"),
    legOp: getComputedStyle(c.querySelector('[data-role="pc-legend"]')).opacity,
    tags: [...c.querySelectorAll('[data-role="pane-tag"]')].map(t => t.dataset.ind), back: c.querySelectorAll('[data-role="pc-solo-back"]').length,
    cfgOpen: !!document.querySelector('[data-role="ind-settings"], [data-role="pc-ind-cfg"], .ind-settings'),
  }));

  // ── ٠ ‏D813: خطُّ ‏D المخفيُّ من الإعدادات لا يُرسم، وخطُّ ‏K يُرسم ──
  const lines0 = await chart(0).getAttribute("data-lines") || "";
  say(/\bstochrsi:10\b/.test(lines0), `${label}: ٠ إخفاءُ خطّ D من إعدادات ستوكاستيك يُخفيه فعلاً (وK ظاهر)`, lines0);

  // ── ١ ‏D810: النقرتان على ستوكاستيك آر إس آي ⇒ وحدها بالارتفاع كلّه، بانتقال؛ ومرّةً أخرى ⇒ يعود الكلّ ──
  const h0 = await hs();
  await dbl(await at(0, 1));
  await page.waitForTimeout(calm ? 40 : 90);
  const hMid = await hs();
  await page.waitForTimeout(700);
  const h1 = await hs(), l1 = await look();
  await shot("solo_stoch");
  const tot1 = sum(h1);
  const morph = calm ? hMid[1] === h1[1] : hMid[1] > h0[1] + 4 && hMid[1] < h1[1] - 4;
  say(h0.length === 3 && h1.length === 3 && l1.solo === "stochrsi" && h1[1] >= 0.97 * tot1 && h1[0] <= 4 && h1[2] <= 4
      && l1.legOff && l1.legOp === "0" && JSON.stringify(l1.tags) === '["stochrsi"]' && l1.back === 1 && morph && !l1.cfgOpen,
      `${label}: ١ النقرتان على ستوكاستيك آر إس آي تكبّرانه وحده فيأخذ ارتفاعَ الرسم كلَّه (والرسمُ وسي في دي مطويّان وأسماؤهما مخفيّة)`
        + (calm ? " — فوراً لمن يفضّل تقليلَ الحركة" : " — بانتقالٍ لا قفزة"),
      JSON.stringify({ h0, hMid, h1, l1 }));
  await dbl(await at(0, 1));
  await page.waitForTimeout(800);
  const h2 = await hs(), l2 = await look();
  say(l2.solo === "" && h2.every((v, i) => Math.abs(v - h0[i]) <= 3) && l2.tags.length === 2 && !l2.legOff && l2.back === 0,
      `${label}: ٢ والنقرتان مرّةً أخرى تعيدان اللوحاتِ كلَّها بارتفاعاتها الأولى`, JSON.stringify({ h0, h2, l2 }));

  // ── ٣ ‏D810: النقرتان على الرسم نفسِه (وفيه مؤشّر D7M) ⇒ هو وحده؛ وزرُّ العودة في رأسه يعيد الكلّ ──
  await dbl(await at(0, 0));
  await page.waitForTimeout(800);
  const h3 = await hs(), l3 = await look(), lines3 = await chart(0).getAttribute("data-lines") || "";
  await shot("solo_main");
  const backErr = await chart(0).locator('[data-role="pc-solo-back"]').click({ timeout: 4000 }).then(() => "", e => String(e).split("\n").slice(0, 6).join(" ¦ ")); await page.waitForTimeout(800);
  const h4 = await hs(), l4 = await look();
  say(l3.solo === "main" && h3[0] >= 0.97 * sum(h3) && l3.tags.length === 0 && !l3.legOff && l3.back === 1
      && l4.solo === "" && h4.every((v, i) => Math.abs(v - h0[i]) <= 3) && /\bstochrsi:00\b/.test(lines3) && /\bcvd:0+\b/.test(lines3),
      `${label}: ٣ النقرتان على الرسم نفسِه (بمؤشّر D7M) تكبّرانه وحده، وزرُّ العودة في رأسه يعيد الكلّ`, JSON.stringify({ h3, l3, h4, l4: l4.solo, backErr, lines3 }));
  if (calm) { say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || ""); await ctx.close(); continue; }

  // ── ٤ ‏D811: قائمةُ الشاشات — «ثلاث شاشات» وحدها و«إنشاء لوحة جديدة» ──
  const layBtn = page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first();
  await layBtn.click(); await page.waitForTimeout(300);
  const names = await page.locator('[data-role="troom-layout-menu"] [data-layout]').evaluateAll(bs => bs.map(b => b.textContent.trim()));
  const add = (await page.locator('[data-role="troom-preset-add"]').textContent() || "").trim();
  await shot("menu");
  await page.locator('[data-role="troom-layout-menu"] [data-layout="3"]').click(); await page.waitForTimeout(2000);
  const g = await page.evaluate(() => [...document.querySelectorAll('[data-role="troom-pane"]')].map(p => { const r = p.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.bottom)]; }));
  const cls = await page.locator('[data-role="troom-grid"]').getAttribute("class");
  const top3 = desk ? g.length === 3 && g[0][2] >= g[1][2] + g[2][2] - 2 && g[1][1] >= g[0][3] - 2 && Math.abs(g[1][1] - g[2][1]) < 2 : g.length === 3;
  say(JSON.stringify(names) === JSON.stringify(["شاشةٌ واحدة", "شاشتان", "ثلاث شاشات", "أربعُ شاشات"]) && add === "إنشاء لوحة جديدة" && top3 && /\bg3\b/.test(cls || ""),
      `${label}: ٤ القائمة: «ثلاث شاشات» وحدها و«إنشاء لوحة جديدة» — والثلاثُ ${desk ? "الكبيرةُ فوق بالعرض والصغيرتان تحتها بجانب بعض (ولو كان المحفوظُ ترتيباً قديماً)" : "متتاليةٌ على الجوال"}`,
      JSON.stringify({ names, add, g, cls }));
  await shot("three");

  // ── ٥ ‏D810 في أيّ شاشة: النقرتان على MACD في الشاشة الثانية تكبّرانه هناك وحدها، والأولى كما هي ──
  const pane1 = page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="pro-chart"]');
  const ph = async () => (await pane1.getAttribute("data-pane-h") || "").split(",").filter(Boolean).map(Number);
  const p0 = await ph();
  await pane1.scrollIntoViewIfNeeded().catch(() => {}); await page.waitForTimeout(300);
  const st1 = await pane1.locator('[data-role="pc-stage"]').boundingBox();
  const macdIdx = 2;
  await dbl({ x: st1.x + st1.width * 0.4, y: st1.y + sum(p0.slice(0, macdIdx)) + macdIdx + p0[macdIdx] / 2 });
  await page.waitForTimeout(800);
  const p1 = await ph(), s1 = await pane1.getAttribute("data-solo"), s0 = await chart(0).getAttribute("data-solo");
  await shot("solo_pane2");
  await pane1.locator('[data-role="pc-solo-back"]').click().catch(() => {}); await page.waitForTimeout(700);
  const s1b = await pane1.getAttribute("data-solo");
  say(p0.length === 3 && s1 === "macd" && p1[2] >= 0.95 * sum(p1) && s0 === "" && s1b === "",
      `${label}: ٥ في الشاشة الثانية: النقرتان على MACD تكبّرانه هناك وحده والشاشةُ الأولى كما هي، وزرُّ العودة يعيده`, JSON.stringify({ p0, p1, s1, s0, s1b }));

  // ── ٦ ‏D812: البحثُ في كلّ شاشة — المؤشّراتُ والسلعُ والسوقان ──
  const box = page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="troom-psearch"]');
  const typeQ = async t => {
    if (!(await box.locator("input").isVisible().catch(() => false))) { await box.locator(".inline-search-btn").click(); await page.waitForTimeout(250); }
    await box.locator("input").fill(t); await page.waitForTimeout(450);
  };
  const rows = () => page.evaluate(() => ({ mkt: [...document.querySelectorAll('[data-role="search-mkt"]')].map(b => b.dataset.symbol),
    us: [...document.querySelectorAll('[data-role="search-hit"]')].map(b => b.dataset.symbol), sa: document.querySelectorAll('[data-role="search-sa"]').length }));
  const seen = {};
  for (const [q, want] of [["تاسي", "^TASI.SR"], ["برنت", "BZ=F"], ["الذهب", "GC=F"], ["الفضة", "SI=F"], ["S&P", "^GSPC"], ["nasdaq", "^IXIC"], ["داو", "^DJI"], ["بتكوين", "BTC-USD"], ["نفط تكساس", "CL=F"]]) {
    await typeQ(q); const r = await rows(); seen[q] = r.mkt[0] === want ? "✓" : JSON.stringify(r.mkt);
  }
  await typeQ("الراجحي"); const rSa = await rows();
  await typeQ("ابل"); const rUs = await rows();
  await typeQ("الذهب"); await shot("search_gold");
  await page.locator('[data-role="search-mkt"][data-symbol="GC=F"]').click().catch(() => {}); await page.waitForTimeout(1200);
  const symG = await page.locator('[data-role="troom-pane"]').nth(1).getAttribute("data-symbol");
  const headG = (await page.locator('[data-role="troom-pane"]').nth(1).locator('[data-role="troom-phead"]').textContent() || "");
  await typeQ("تاسي"); await box.locator("input").press("Enter"); await page.waitForTimeout(1200);
  const symT = await page.locator('[data-role="troom-pane"]').nth(1).getAttribute("data-symbol");
  await page.locator('[data-role="troom-pane"]').nth(2).locator('[data-role="troom-psearch"] .inline-search-btn').click(); await page.waitForTimeout(250);
  await page.locator('[data-role="troom-pane"]').nth(2).locator('[data-role="troom-psearch"] input').fill("برنت"); await page.waitForTimeout(350);
  await page.locator('[data-role="troom-pane"]').nth(2).locator('[data-role="troom-psearch"] input').press("Enter"); await page.waitForTimeout(1200);
  const symB = await page.locator('[data-role="troom-pane"]').nth(2).getAttribute("data-symbol");
  say(Object.values(seen).every(v => v === "✓") && rSa.sa > 0 && rSa.mkt.length === 0 && rUs.us.includes("AAPL") && rUs.mkt.length === 0
      && symG === "GC=F" && /الذهب/.test(headG) && symT === "^TASI.SR" && symB === "BZ=F",
      `${label}: ٦ بحثُ كلّ شاشة يجد المؤشّراتِ والسلعَ بالعربية والإنجليزية (تاسي · برنت · الذهب · الفضّة · S&P · ناسداك · داو · بتكوين · غرب تكساس) `
        + "أوّلَ القائمة، والسعوديَّ والأمريكيَّ كما كانا — والاختيارُ أو Enter يفتحه في الشاشة نفسِها باسمه",
      JSON.stringify({ seen, rSa, rUs: rUs.us.slice(0, 3), symG, headG: headG.slice(0, 40), symT, symB }));

  const over = await page.evaluate(() => document.scrollingElement.scrollWidth - innerWidth);
  say(errs.length === 0 && over <= 1, `${label}: لا خطأ في الصفحة ولا فيضَ أفقيّ`, errs[0] || `${over}px`);
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
