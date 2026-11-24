// ─────────────────────────────────────────────────────────────────────────
// D801–D805 — الشاشاتُ المتعدّدة كما أمر المالك (2026-11-24، الرسالةُ الثانية):
//  ‏D801 «زرُّ تقسيم الشاشات بجانب الإطارات — لا آخرَ شيءٍ على اليسار»، و«الإطارُ الأزرقُ حول الشاشة المختارة مقصوصٌ من جهة — هل متعمَّد؟
//        وبدلَه أيقونةٌ بجانب الشركة أجمل»، و«ألغِ كلمة تتبع الأولى».
//  ‏D802 «كتبتُ أبل وأبغى العقد يطلع معي — ما وجدته».
//  ‏D803 «أمدّد واحدةً وأنقص — مرونة»، و«الثلاثُ: واحدةٌ بالعرض فوق واثنتان تحت بجانب بعض».
//  ‏D804 «أحفظ تخصيصاً (ثلاثُ شاشاتٍ لشركاتٍ معيّنة) في المفضّلة — في شاشة الإطارات نفسِها مع زرّ مسح».
//  ‏D805 «النقاطُ المتّصلةُ بالأرقام ظهرت على الكمبيوتر أيضاً بعد ثلاث شاشات».
//  ‏D811 (بعدها): «احذف الخيارَ الذي تكون الكبيرةُ فيه على اليمين — ثلاث شاشات وحدها»: للثلاث ترتيبٌ واحد، والتخصيصُ لا يحمل ترتيباً،
//        وقيمةُ «side» المحفوظةُ من قبل (في تهيئة هذا الحارس) لا أثرَ لها.
//    SHOTS=dir node scripts/audit/troom_d801.mjs
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
const nc = t => t.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\{\/\*[\s\S]*?\*\/\}/g, "").replace(/(^|[^:])\/\/[^\n]*/g, "$1");   // بلا تعليقات
const tr = nc(readFileSync(join(FRONT, "src/components/market/TradeRoom.tsx"), "utf8")), css = nc(readFileSync(join(FRONT, "src/styles/globals.css"), "utf8"));
say(!/تتبع الأولى/.test(tr) && !/\.troom-pane\.on \{ box-shadow/.test(css) && !/troom-pane\.on\s*\{[^}]*box-shadow/.test(css),
    "٠ لا «تتبع الأولى»، ولا ظلَّ داخليّاً حول الشاشة المختارة (كان يُرسم تحت محتواها فيُقصّ)");

const PORT = 5301;
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
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "", next: null, source: "ياهو" };
const EXPS = [[1, "2026-12-18", 25], [2, "2027-01-15", 53]].map(([t, date, dte]) => ({ t, date, dte }));
const occ = (root, date, cp, k) => `${root}${date.slice(2, 4)}${date.slice(5, 7)}${date.slice(8, 10)}${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
const chain = (sym, t) => { const e = EXPS.find(x => x.t === t) || EXPS[0];
  const row = (k, cp) => ({ contract: occ(sym, e.date, cp, k), strike: k, last: 3, bid: 2.9, ask: 3.1, pct: 1, volume: 500, oi: 2000, iv: 40, itm: cp === "C" ? k < 100 : k > 100,
    g: { iv: 40, delta: cp === "C" ? 0.5 : -0.5, gamma: 0.02, theta: -0.03, vega: 0.1, itm: 0.5, pop: 0.4, px: 3.1, src: "ask", spread: 2, be: k + 3.1 } });
  const ks = [90, 95, 100, 105, 110];
  return { symbol: sym, name: sym, price: 100, expirations: EXPS, expiry: e.t, calls: ks.map(k => row(k, "C")), puts: ks.map(k => row(k, "P")),
    stats: { atm_iv: 40, move: 6, move_pct: 6, pcr_vol: 0.8, pcr_oi: 0.9, max_pain: 100, vol: { call: 1000, put: 800 }, oi: { call: 5000, put: 4000 } }, session: SES }; };

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب · داكن", { width: 1440, height: 900 }, "dark"], ["الحاسوب · فاتح", { width: 1366, height: 860 }, "light"], ["الجوال · فاتح", { width: 390, height: 844 }, "light"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d801-init")) return;
    sessionStorage.setItem("d801-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_room_layout", "3"); localStorage.setItem("sp_room_var3", "side"); localStorage.removeItem("sp_room_sizes"); localStorage.removeItem("sp_room_presets");
    localStorage.setItem("sp_room_panes", JSON.stringify([null, null, "1120", null])); localStorage.setItem("sp_chart_tf", "1d");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/options/")) return r.fulfill(body(chain(decodeURIComponent(p.split("/").pop()), Number(u.searchParams.get("date")) || 1)));
    if (p === "/market/symbol-search") return r.fulfill(body([]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2800);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  const shot = async n => { if (SHOTS) await page.screenshot({ path: join(SHOTS, `d801_${n}_${vp.width}_${theme}.png`) }).catch(() => {}); };
  const syms = () => page.locator('[data-role="troom-pane"]').evaluateAll(ps => ps.map(p => p.dataset.symbol));

  // ── ١ ‏D801: الأيقونةُ بجانب الشركة، لا إطارٌ مقصوص، ولا «تتبع الأولى»، وزرُّ الشاشات بجانب الإطارات ──
  const sel = await page.evaluate(() => [...document.querySelectorAll('[data-role="troom-pane"]')].map(p => {
    const h = p.querySelector('[data-role="troom-phead"]'), b = h?.querySelector('[data-role="troom-sel"]'), logo = b?.nextElementSibling;
    return { on: b?.getAttribute("aria-pressed"), first: h?.firstElementChild === b, nextLogo: !!logo && !!logo.querySelector?.("img, svg, span") , bg: h ? getComputedStyle(h).backgroundColor : "",
      shadow: getComputedStyle(p).boxShadow, w: b ? Math.round(b.getBoundingClientRect().width) : 0, txt: p.textContent?.includes("تتبع الأولى") };
  }));
  const layAdj = await page.locator('[data-role="troom-pane"]').first().locator('[data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').count();
  await page.locator('[data-role="troom-pane"]').nth(2).locator('[data-role="troom-sel"]').click(); await page.waitForTimeout(300);
  const sel2 = await page.locator('[data-role="troom-sel"]').evaluateAll(bs => bs.map(b => b.getAttribute("aria-pressed")));
  say(sel.length === 3 && sel[0].on === "true" && sel[1].on === "false" && sel.every(x => x.first && x.w >= 32 && (x.shadow === "none" || !x.shadow) && !x.txt)
      && sel[0].bg !== sel[1].bg && layAdj === 1 && JSON.stringify(sel2) === '["false","false","true"]',
      `${label}: ١ الشاشةُ المختارة أيقونةٌ بجانب شركتها ورأسٌ بلونٍ خفيف — لا إطارٌ مقصوص ولا «تتبع الأولى»، والأيقونةُ تختار غيرها، وزرُّ «الشاشات» بجانب الإطارات`,
      JSON.stringify({ sel: sel.map(x => [x.on, x.first, x.w, x.shadow]), layAdj, sel2 }));
  await shot("panes");

  // ── ٢ ‏D802: «أبل» في بحث الشاشة الثالثة ⇐ AAPL و«العقود»؛ والعقدُ المختارُ يُفتح في الشاشة نفسِها ──
  const box = page.locator('[data-role="troom-pane"]').nth(2).locator('[data-role="troom-psearch"]');
  await box.locator(".inline-search-btn").click(); await page.waitForTimeout(250);
  await box.locator("input").fill("أبل"); await page.waitForTimeout(500);
  const hit = await page.locator('[data-role="search-hit"][data-symbol="AAPL"]').count();
  const chBtn = page.locator('[data-role="search-chain"][data-symbol="AAPL"]');
  const chN = await chBtn.count();
  await chBtn.click().catch(() => {}); await page.waitForTimeout(1200);
  const ocOpen = await page.locator('[data-role="oc-cell"]').count();
  await page.locator('[data-role="oc-cell"][data-side="call"]').nth(2).click().catch(() => {}); await page.waitForTimeout(400);
  await page.locator('[data-role="oc-open"]').first().click().catch(() => {}); await page.waitForTimeout(1200);
  const s2 = await syms();
  say(hit === 1 && chN === 1 && ocOpen > 0 && /^AAPL\d{6}C\d{8}$/.test(s2[2] || "") && s2[0] === "2222.SR",
      `${label}: ٢ «أبل» بالعربية تجد AAPL وبجانبها «العقود» — والعقدُ المختارُ من السلسلة يُفتح في الشاشة التي بُحث فيها`, JSON.stringify({ hit, chN, ocOpen, s2 }));

  // ── ٣ ‏D803: «كبيرةٌ فوق واثنتان تحت»، والفواصلُ تُسحب وتُحفظ، والنقرتان تعيدانها ──
  const layBtn = page.locator('[data-role="troom-chart"] [data-role="pc-tfs"] + .troom-layw [data-role="troom-layout"]').first();
  await layBtn.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-layout-menu"] [data-layout="3"]').click(); await page.waitForTimeout(1800);
  const geo = () => page.evaluate(() => { const g = document.querySelector('[data-role="troom-grid"]').getBoundingClientRect();
    return [...document.querySelectorAll('[data-role="troom-pane"]')].map(p => { const r = p.getBoundingClientRect(); return [Math.round(r.left - g.left), Math.round(r.top - g.top), Math.round(r.width), Math.round(r.height)]; }); });
  const g0 = await geo();
  const top3 = desk ? g0[0][2] >= g0[1][2] + g0[2][2] - 2 && g0[1][1] > g0[0][1] + 50 && g0[1][1] === g0[2][1] && g0[1][0] > g0[2][0] : true;
  let dragOk = true, det = "";
  if (desk) {
    const v = page.locator('[data-role="troom-split-v"]'), h = page.locator('[data-role="troom-split-h"]');
    const vb = await v.boundingBox(), hb = await h.boundingBox();
    // الفاصلُ الرأسيُّ بين السفليّتين يُسحب يساراً ⇒ اليمنى (الثانية) تكبر
    await page.mouse.move(vb.x + vb.width / 2, vb.y + vb.height / 2); await page.mouse.down();
    await page.mouse.move(vb.x + vb.width / 2 - 160, vb.y + vb.height / 2, { steps: 8 }); await page.mouse.up(); await page.waitForTimeout(700);
    const g1 = await geo();
    // الفاصلُ الأفقيُّ يُسحب إلى أسفل ⇒ العليا تطول
    await page.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2); await page.mouse.down();
    await page.mouse.move(hb.x + hb.width / 2, hb.y + hb.height / 2 + 120, { steps: 8 }); await page.mouse.up(); await page.waitForTimeout(900);
    const g2 = await geo();
    const saved = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_room_sizes") || "{}"));
    await shot("resized");
    await page.locator('[data-role="troom-split-v"]').dblclick(); await page.waitForTimeout(700);
    const g3 = await geo();
    const kv0 = Number(await page.locator('[data-role="troom-split-h"]').getAttribute("aria-valuenow"));
    await page.locator('[data-role="troom-split-h"]').focus(); await page.keyboard.press("ArrowDown"); await page.waitForTimeout(500);
    const kv1 = Number(await page.locator('[data-role="troom-split-h"]').getAttribute("aria-valuenow"));
    dragOk = g1[1][2] > g0[1][2] + 100 && g1[2][2] < g0[2][2] - 100 && g2[0][3] > g1[0][3] + 25 && saved["3t"] && saved["3t"].a > 0.55 && saved["3t"].b > 0.6
      && Math.abs(g3[1][2] - g0[1][2]) <= 3 && kv1 === kv0 + 5;
    det = JSON.stringify({ g0, g1: g1.map(x => x[2]), top: [g1[0][3], g2[0][3]], saved, reset: g3[1][2], kv: [kv0, kv1] });
  } else {
    dragOk = await page.locator('[data-role^="troom-split"]').count() === 0;
    det = JSON.stringify({ g0 });
  }
  say(top3 && dragOk,
      `${label}: ٣ ${desk ? "«كبيرةٌ فوق بالعرض واثنتان تحت بجانب بعض»، والفاصلُ الرأسيُّ والأفقيُّ يُسحبان فتكبر الشاشةُ وتصغر جارتُها ويُحفظ، والنقرتان تعيدانه، والأسهمُ تحرّكه"
        : "على الجوال الشاشاتُ متتاليةٌ بلا فواصل"}`, det);

  // ── ٤ ‏D804: تخصيصٌ في المفضّلة — يُحفظ باسمه ويُطبَّق ويُمسح ──
  await layBtn.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-preset-add"]').click(); await page.waitForTimeout(250);
  const sug = await page.locator('[data-role="troom-preset-name"]').inputValue();
  await page.locator('[data-role="troom-preset-name"]').fill("عقدُ أبل تحت أرامكو");
  await page.locator('[data-role="troom-preset-save"]').click(); await page.waitForTimeout(300);
  const ps1 = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_room_presets") || "[]"));
  await page.locator('[data-role="troom-layout-menu"] [data-layout="1"]').click(); await page.waitForTimeout(1500);
  const one = await page.locator('[data-role="troom-one"]').count();
  await layBtn.click(); await page.waitForTimeout(300);
  const items = await page.locator('[data-role="troom-preset"]').count();
  await page.locator('[data-role="troom-preset-go"]').first().click(); await page.waitForTimeout(2200);
  const s4 = await syms(), var4 = await page.locator('[data-role="troom-grid"]').getAttribute("class");
  await layBtn.click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-preset-del"]').first().click(); await page.waitForTimeout(300);
  const after = await page.locator('[data-role="troom-preset"]').count(), ps2 = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_room_presets") || "[]"));
  await page.keyboard.press("Escape"); await page.waitForTimeout(300);
  say(sug.length > 0 && ps1.length === 1 && ps1[0].name === "عقدُ أبل تحت أرامكو" && ps1[0].n === 3 && one === 1 && items === 1
      && s4.length === 3 && /\bg3\b/.test(var4 || "") && /^AAPL\d{6}C/.test(s4[2] || "") && s4[0] === "2222.SR" && after === 0 && ps2.length === 0,
      `${label}: ٤ «إنشاء لوحة جديدة» في قائمة الشاشات يحفظ الحاليّةَ باسمٍ في المفضّلة، وضغطتُه تعيد الثلاثَ بترتيبها ورموزها، وزرُّ المسح يزيلها`,
      JSON.stringify({ sug, ps1: ps1.map(p => [p.name, p.n, p.v3, p.syms]), one, items, s4, var4, after }));

  // ── ٥ ‏D805: لا مِهمازَ منقّطاً في أيّ شاشة ──
  const lead = await page.locator('[data-role="pro-chart"]').evaluateAll(cs => cs.map(c => c.dataset.leaders));
  say(lead.length >= 3 && lead.every(x => x === "0"), `${label}: ٥ لا نقاطَ منقّطةً متّصلةً بالأرقام في أيّ شاشة (الكبيرةُ في الثلاث كذلك)`, lead.join(","));

  const over = await page.evaluate(() => document.scrollingElement.scrollWidth - innerWidth);
  say(errs.length === 0 && over <= 1, `${label}: لا خطأ في الصفحة ولا فيضَ أفقيّ`, errs[0] || `${over}px`);
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
