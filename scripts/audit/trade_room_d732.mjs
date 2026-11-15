// ─────────────────────────────────────────────────────────────────────────
// D732 (بأمر المالك 2026-11-14): «غرفة التداول… أضيف شركات في القائمة المفضّلة، وأضع قوائم للسوق الأمريكي وللسوق
// السعودي… إذا ضغطتُ على الشركة يظهر الشارت بخصائص: ستوكاستيك، RSI، الماكد، CVD… والمؤشّر حقّي».
// الحالُ قبله: الرسمُ تبويبٌ ثانٍ بلا قوائم، والقوائمُ بطاقاتٌ تفتح ورقةَ السهم لا رسمَه؛ ولا ستوكاستيك ولا CVD،
// واللوحتان السفليّتان (RSI · MACD) بهوامشَ ثابتةٍ لا تحتمل ثالثة.
// ١–٦ سلوكيّ على الدوالّ نفسِها (‏lib/indicators) · ٧–… المتصفّح: التطبيقُ الحقيقيّ والمكتبةُ الحقيقيّة.
//    SHOTS=dir node scripts/audit/trade_room_d732.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync, mkdtempSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const SRC = join(FRONT, "src/lib/indicators.ts");
if (!existsSync(SRC)) { say(false, "١ دوالُّ المؤشّرات موجودة"); console.log("\nالنتيجة: عطب ✖"); process.exit(1); }
const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const out = join(mkdtempSync(join(tmpdir(), "sp-d732-")), "ind.mjs");
await build({ entryPoints: [SRC], outfile: out, format: "esm", bundle: false, logLevel: "silent" });
const I = await import(pathToFileURL(out).href);
const near = (a, b, e = 1e-9) => a != null && Math.abs(a - b) < e;

// ستوكاستيك: سلسلةٌ صاعدةٌ بانتظام تُغلق عند قمّتها ⇒ ‏%K = 100
const up = Array.from({ length: 30 }, (_, i) => ({ high: 10 + i + 0.5, low: 10 + i - 0.5, close: 10 + i + 0.5, volume: 100 }));
const st = I.stochastic(up);
say(st.k[15] != null && near(st.k[29], 100) && near(st.d[29], 100) && st.k[14] == null && st.k[15] != null,
    "١ ستوكاستيك 14·3·3: إغلاقٌ عند أعلى قمّةٍ ⇒ ‏%K = ‏%D = 100، ولا قيمةَ قبل 14 + 3 − 1 شمعة", `${st.k[29]} · أوّل ${st.k.findIndex(v => v != null)}`);
const mixed = [{ high: 12, low: 8, close: 10 }, ...Array.from({ length: 15 }, () => ({ high: 12, low: 8, close: 9 }))];
const sm = I.stochastic(mixed);
say(near(sm.k[15], 25), "٢ وإغلاقٌ عند ربع المدى ⇒ 25", String(sm.k[15]));
const flat = Array.from({ length: 20 }, () => ({ high: 5, low: 5, close: 5 }));
say(I.stochastic(flat).k.every(v => v == null), "٣ ومدًى صفريّ (قمّةٌ = قاع) فراغٌ لا رقمٌ مختلَق");
// ‏CVD D7M — سكربتُ المالك بنصّه (2026-11-14): نسبةُ الاتّجاه = ½(فتيلان + (صاعدة ? 2×جسم : 0)) ÷ (فتيلان + جسم)، والصفرُ ½
const cb = [{ open: 10, high: 12, low: 9, close: 11, volume: 100 }, { open: 11, high: 11.5, low: 10, close: 10.2, volume: 200 },
            { open: 10, high: 10, low: 10, close: 10, volume: 50 }];
const c = I.cvdCum(cb).map(v => +v.toFixed(4));
say(JSON.stringify(c) === JSON.stringify([66.6667, -86.6667, -61.6667]),
    "٤ ‏CVD D7M بمعادلة السكربت: +66.67 (صاعدة · ⅔) ثمّ −153.33 (هابطة) ثمّ +25 (شمعةٌ بلا مدى ⇒ ½)", JSON.stringify(c));
const raw = I.cvdD7M(cb, { ...I.CVD_DEFAULTS, ha: false, scale: "volume", ema2: false });
say(raw.o[0] == null && +raw.o[2].toFixed(4) === -86.6667 && +raw.c[2].toFixed(4) === -61.6667 && +raw.h[1].toFixed(4) === 66.6667,
    "٤ب والشمعةُ: فتحُها تراكمُ الأمس وإغلاقُها تراكمُ اليوم، وقمّتُها وقاعُها أكبرُهما وأصغرُهما");
const big = Array.from({ length: 300 }, (_, i) => ({ open: 50 + Math.sin(i / 7), high: 51.5 + Math.sin(i / 7), low: 48.6 + Math.sin(i / 7),
  close: 50 + Math.sin(i / 7) + ((i * 37) % 11 - 5) / 10, volume: 1000 + (i * 53) % 400 }));
const lv = I.cvdD7M(big), pc = I.cvdD7M(big, { ...I.CVD_DEFAULTS, scale: "pct" });
const inR = (a, lo, hi) => a.every(v => v == null || (v >= lo - 1e-9 && v <= hi + 1e-9));
say(I.CVD_DEFAULTS.scale === "levels" && I.CVD_DEFAULTS.len === 200 && I.CVD_DEFAULTS.ha && I.CVD_DEFAULTS.ema2 && I.CVD_DEFAULTS.ema2Len === 200
    && inR(lv.h, 0, 100) && inR(lv.l, 0, 100) && inR(pc.h, -100, 100) && lv.ema2.filter(v => v != null).length > 250,
    "٤ج وافتراضاتُ السكربت: «مستويات» 0–100 على 200 شمعة، وهايكن آشي، وEMA 200 — و«نسبة» بين −100 و100");
let ok5 = true, worst = "";
for (let n = 1; n <= 4; n++) {
  const L = I.paneLayout(n);
  const tops = L.panes.map(p => p.top), bots = L.panes.map(p => 1 - p.bottom);
  for (let i = 0; i < n; i++) if (!(tops[i] < bots[i])) { ok5 = false; worst = `n=${n} i=${i}`; }
  for (let i = 1; i < n; i++) if (!(tops[i] >= bots[i - 1] - 1e-9)) { ok5 = false; worst = `تداخل n=${n} i=${i}`; }
  if (!(1 - L.price.bottom <= L.volume.top + 1e-9 && 1 - L.volume.bottom <= tops[0] + 1e-9)) { ok5 = false; worst = `سعر/حجم n=${n}`; }
}
say(ok5, "٥ اللوحاتُ السفلى (حتى أربع) لا يتداخل اثنتان منها، والحجمُ فوقها والسعرُ فوق الجميع", worst);
const nc = (await import("node:fs")).readFileSync(join(FRONT, "src/components/analysis/NativeChart.tsx"), "utf-8");
say(/\["stoch", "Stochastic"/.test(nc) && /\["cvd", "CVD D7M"/.test(nc) && /\["d7m", "D7M"/.test(nc) && /sp_chart_ind/.test(nc) && /sp_cvd_cfg/.test(nc)
    && /cvdD7M\(bars/.test(nc) && !/cvdApprox/.test(nc),
    "٦ الرسمُ يعرض ستوكاستيك وCVD D7M (سكربتُ المالك بإعداداته) بجانب RSI وMACD وD7M، والاختياران يُحفظان");

// حدودُ اللوحة تُضبط بعد إنشاء سلسلتها — مقياسٌ مُلحَقٌ لا يوجد قبل أوّل سلسلة، فضبطُه قبلها يضيع فتُرسم على الرسم كلّه
// (عطبٌ قِيس في لقطة CVD D7M: شموعُه فوق شموع السعر)
const order = ["rsi", "stoch", "macd", "cvd"].filter(k => {
  const make = nc.indexOf(`priceScaleId: "${k}"`), set = nc.indexOf(`chart.priceScale("${k}").applyOptions`);
  return !(make > 0 && set > make);
});
say(order.length === 0, "٦ب وكلُّ لوحةٍ سفلى تُحدُّ بعد إنشاء سلسلتها — لا مؤشّرَ يُرسم فوق شموع السعر", order.join(","));

const proSrc = (await import("node:fs")).readFileSync(join(FRONT, "src/components/chart/ProChart.tsx"), "utf-8");
say(/\["stoch", "Stochastic"/.test(proSrc) && /\["cvd", "CVD D7M"/.test(proSrc) && /\["d7m", "D7M"/.test(proSrc) && /sp_chart_ind/.test(proSrc) && /sp_cvd_cfg/.test(proSrc)
    && /cvdD7M\(bars/.test(proSrc) && /import ProChart from "\.\.\/chart\/ProChart"/.test((await import("node:fs")).readFileSync(join(FRONT, "src/components/market/TradeRoom.tsx"), "utf-8")),
    "٦ج والرسمُ الاحترافيّ في الغرفة (‏D736) يحمل المؤشّراتِ نفسَها بإعداداتها المحفوظة");

// ── المتصفّح ──
const PORT = 5255;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر فحصُ المتصفّح (المتصفّح غيرُ متاح) — لا حكم."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const bars = (n = 160) => Array.from({ length: n }, (_, i) => {
  const d = new Date(Date.UTC(2026, 0, 5) + i * 7 * 864e5).toISOString().slice(0, 10), b = 60 + 6 * Math.sin(i / 9) + i * 0.05;
  return { date: d, open: b, high: b + 1.2, low: b - 1.1, close: b + (i % 3 - 1) * 0.6, volume: 1e5 + (i % 7) * 1e4 };
});
const HOLD = [{ company: { symbol: "1120", name_ar: "مصرف الراجحي" }, last_price: 64.2, change_pct: 1.25 },
              { company: { symbol: "2222", name_ar: "أرامكو السعودية" }, last_price: 25.1, change_pct: -0.4 }];
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let upv = false;
for (let i = 0; i < 60 && !upv; i++) { await sleep(500); try { upv = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!upv) { console.log("… لم يقلع خادمُ التطوير."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [], calls = [], barsFor = [];
  let groups = [{ id: 1, name: "الرئيسية", color: "var(--chart-1)", is_default: true }];
  const lists = { 1: [] };
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(bars|history)\//.test(p)) { barsFor.push(decodeURIComponent(p.split("/").pop())); return r.fulfill(body(bars())); }
    if (p === "/holdings") return r.fulfill(body(HOLD));
    if (p === "/market/watchlist/groups" && m === "GET") return r.fulfill(body(groups));
    if (p === "/market/watchlist/groups" && m === "POST") {
      const b = JSON.parse(r.request().postData() || "{}"); const g = { id: groups.length + 1, name: b.name, is_default: false };
      groups = [...groups, g]; lists[g.id] = []; calls.push(["create", b.name]); return r.fulfill(body(g));
    }
    if (p === "/market/watchlist" && m === "POST") {
      const b = JSON.parse(r.request().postData() || "{}"); lists[b.group_id] = [...(lists[b.group_id] || []), { symbol: b.symbol, name: b.symbol, price: 191.2, change_pct: 0.8 }];
      calls.push(["add", b.symbol, b.group_id]); return r.fulfill(body(null));
    }
    if (/^\/market\/watchlist\//.test(p) && m === "DELETE") {
      const s = p.split("/").pop(), g = Number(u.searchParams.get("group_id")); lists[g] = lists[g].filter(x => x.symbol !== s);
      calls.push(["remove", s, g]); return r.fulfill(body(null));
    }
    if (p === "/market/watchlist") return r.fulfill(body(lists[Number(u.searchParams.get("group_id"))] || []));
    return r.fulfill(body([]));
  });
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe"); localStorage.removeItem("sp_room_symbol"); localStorage.removeItem("sp_room_list");
    localStorage.setItem("sp_chart_ind", JSON.stringify({ sma20: false, sma50: false, macd: false }));
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2600);
  const lay = await page.evaluate(() => {
    const c = document.querySelector('[data-role="troom-chart"]')?.getBoundingClientRect(), l = document.querySelector('[data-role="troom-list"]')?.getBoundingClientRect();
    return c && l ? { side: Math.abs(c.top - l.top) < 4 && c.width > l.width * 2, listRight: l.left >= c.right - 1, below: l.top >= c.bottom - 1 } : null;
  });
  // ‏D736 (المالك 2026-11-15): «المستخدم عربيّ — الشركاتُ في اليمين والرسمُ البيانيُّ على اليسار»
  say(!!lay && (desk ? lay.side && lay.listRight : lay.below), `${label}: ${desk ? "القوائمُ يمينَ الشاشة والرسمُ يسارَها" : "الرسمُ أوّلاً والقوائمُ تحته"} — افتراضُ الغرفة`, JSON.stringify(lay));
  const rowsTxt = await page.locator('[data-role="troom-row"]').allTextContents();
  say(rowsTxt.length === 2 && /مصرف الراجحي/.test(rowsTxt[0]) && /64\.20/.test(rowsTxt[0]) && /\+1\.25%/.test(rowsTxt[0]),
      `${label}: «محفظتي» قائمةٌ ثابتة بأسعارها وتغيّرها`, rowsTxt[0]?.replace(/\s+/g, " "));
  await page.locator('[data-role="troom-row"]').nth(1).click();
  await page.waitForTimeout(1400);
  const ident = await page.evaluate(() => document.querySelector('[data-role="troom-chart"]')?.textContent || "");
  say(/2222/.test(ident) && barsFor.includes("2222"), `${label}: الضغطُ على الشركة يفتح رسمَها`, barsFor.slice(-2).join(","));
  // المؤشّرات الأربعة معاً
  await page.locator('[data-role="pc-ind"]').click();
  for (const k of ["rsi", "stoch", "macd", "cvd"]) { await page.locator(`[data-role="pc-ind-menu"] [data-ind="${k}"]`).click(); await sleep(120); }
  await page.mouse.click(5, 5);
  await page.waitForTimeout(1500);
  const panes = await page.evaluate(() => [...document.querySelectorAll('[data-role="pane-tag"]')].map(e => ({ t: e.textContent, y: e.getBoundingClientRect().top })));
  const ys = panes.map(p => p.y);
  const nPanes = await page.evaluate(() => Number(document.querySelector('[data-role="pro-chart"]')?.dataset.panes || 0));
  say(panes.length === 4 && nPanes === 5 && ys.every((y, i) => i === 0 || y - ys[i - 1] > 40) && /CVD D7M · مستويات 200/.test(panes[3]?.t || "")
      && panes.every(p => /\d/.test(p.t.replace(/14 3 3|12 26 9|RSI 14|200/g, ""))),
      `${label}: RSI وستوكاستيك وMACD وCVD D7M معاً — أربعُ لوحاتٍ حقيقيةٍ لا تتداخل، ولكلٍّ قيمُه`, panes.map(p => `${p.t}@${Math.round(p.y)}`).join(" | "));
  if (SHOTS) { const el = await page.$('[data-role="troom"]'); if (el) await el.screenshot({ path: join(SHOTS, `room_${vp.width}_${theme}.png`) }); }
  // قائمةٌ للسوق الأمريكي، وAAPL بالبحث، ثمّ إزالتُها
  await page.locator('[data-role="troom-new"]').click();
  await page.waitForTimeout(250);
  await page.locator('[data-role="troom-preset"]', { hasText: "السوق الأمريكي" }).click();
  await page.waitForTimeout(900);
  const onUS = await page.locator('[data-role="troom-tab"][aria-selected="true"]').textContent();
  await page.locator('[data-role="troom-list"] button[aria-label="ابحث عن سهم"]').click();
  await page.locator('[data-role="troom-list"] .inline-search-input').fill("AAPL");
  await page.waitForTimeout(200);
  await page.locator('[data-role="troom-list"] .sp-menu button').first().click();
  await page.waitForTimeout(900);
  const usRows = await page.locator('[data-role="troom-row"]').allTextContents();
  say(onUS === "السوق الأمريكي" && calls.some(c => c[0] === "create" && c[1] === "السوق الأمريكي")
      && calls.some(c => c[0] === "add" && c[1] === "AAPL" && c[2] === 2) && usRows.length === 1 && /AAPL/.test(usRows[0]),
      `${label}: قائمةُ «السوق الأمريكي» تُنشأ بضغطة، وAAPL يُضاف إليها بحقل البحث`, JSON.stringify(calls));
  await page.locator('[data-role="troom-edit"]').click();
  await page.locator('[data-role="troom-remove"]').first().click();
  await page.waitForTimeout(800);
  say(calls.some(c => c[0] === "remove" && c[1] === "AAPL" && c[2] === 2) && (await page.locator('[data-role="troom-row"]').count()) === 0,
      `${label}: وتُزال من قائمتها وحدها في وضع التحرير`);
  const m = await page.evaluate(() => {
    const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const root = document.querySelector('[data-role="troom-list"]');
    const t = [...root.querySelectorAll("button, input")].filter(e => e.offsetParent).map(e => e.getBoundingClientRect().height);
    const f = [...root.querySelectorAll("*")].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
    return { over: sw - W, minT: Math.min(...t), minF: Math.min(...f) };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5, `${label}: لا فيضَ أفقيّ، ولمسٌ ≥ 32px، وخطٌّ ≥ 9.5px`, `${m.over}px · ${Math.round(m.minT)}px · ${m.minF}px`);
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
