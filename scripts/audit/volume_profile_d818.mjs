// ─────────────────────────────────────────────────────────────────────────
// D818 (الواجهة) — الفوليوم بروفايل في سلسلة العقود (بأمر المالك 2026-11-24): «السترايكاتُ المناسبةُ للدخول بتصميمٍ بصريٍّ واضح…
// أضيفُ أحدَ معايير الاختيار: الفوليوم بروفايل».
//  ١ مفتاحٌ فوق الجدول: نقطةُ التحكّم ومنطقةُ القيمة بأرقامها، ومعنى «حجمٌ كثيف» و«فراغ»، ونافذةُ البروفايل.
//  ٢ كلُّ سعر تنفيذٍ يحمل عمودَ حجمه، ويُوسَم إن وقع على مستوى: تحكّم · أعلى القيمة · أدنى القيمة · حجمٌ كثيف · فراغ — بخطٍّ ≥ 9.5px وتباينٍ
//    ≥ 4.5:1 في المظهرين، وعلى الجوال بلا تمريرٍ أفقيٍّ للصفحة.
//  ٣ والسيولةُ الضعيفة: المفتاحُ يقول ذلك ولا وسمَ ولا أعمدة — لا يُبنى على بروفايلٍ قليل الدلالة.
//    node scripts/audit/volume_profile_d818.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5318;
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
const PRICE = 754.37;
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const occ = (k, cp) => `SPY261120${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
const G = (k, call) => ({ iv: 14.2, delta: call ? 0.52 : -0.48, gamma: 0.031, theta: -21.5, vega: 33.1, itm: 48, pop: 41, px: 3.7, src: "ask", spread: 2.7, be: call ? k + 3.7 : k - 3.7 });
const legs = cp => Array.from({ length: 30 }, (_, i) => { const k = 740 + i; return { contract: occ(k, cp), strike: k, last: 3.69, bid: 3.6, ask: 3.7,
  change: -1, pct: -5.2, volume: 1000 + i, oi: 400 + i, iv: 10.3, itm: cp === "C" ? k < PRICE : k > PRICE, last_trade: null, g: G(k, cp === "C") }; });
const BINS = Array.from({ length: 40 }, (_, i) => { const p = 735.5 + i; return +(0.15 + Math.exp(-(((p - 752) / 2.5) ** 2)) + 0.8 * Math.exp(-(((p - 763) / 2) ** 2))).toFixed(3); });
const mx = Math.max(...BINS);
const VPX = { poc: 752, val: 747, vah: 758, hvn: [{ p: 752, w: 1 }, { p: 763, w: 0.8 }, { p: 744, w: 0.3 }], lvn: [760], lo: 735, hi: 775, step: 1,
  bins: BINS.map(b => +(b / mx).toFixed(3)), window: "شموعُ 15 دقيقة لنحو عشرين جلسة", thin: false };
const chainOf = vp => ({ symbol: "SPY", name: "SPDR S&P 500", price: PRICE, currency: "USD", delayed: true, session: SES,
  expirations: [{ t: 1795132800, date: "2026-11-20", dte: 3 }], expiry: 1795132800, calls: legs("C"), puts: legs("P"), vp,
  stats: { atm_iv: 14.2, move: 10.9, move_pct: 1.4, pcr_vol: 1.12, pcr_oi: 0.94, max_pain: 750, vol: { call: 30435, put: 30435 }, oi: { call: 12435, put: 12435 } } });
const bars = (n = 120) => Array.from({ length: n }, (_, i) => { const day = new Date(Date.UTC(2026, 6, 1) + i * 864e5).toISOString().slice(0, 10), b = 700 + i * 0.4;
  return { date: day, open: b, high: b + 2, low: b - 2, close: b + 1, volume: 1e6 }; });

/* التباين: لونُ النصّ على أوّلِ خلفيةٍ غير شفّافةٍ تحته (مزجٌ بالشفافية) */
const contrastOf = el => {
  const parse = s => { const m = s.match(/[\d.]+/g) || []; return { r: +m[0], g: +m[1], b: +m[2], a: m[3] == null ? 1 : +m[3] }; };
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const layers = [];
  for (let n = el; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c.a > 0) { layers.push(c); if (c.a >= 1) break; } }
  let bg = { r: 255, g: 255, b: 255 };
  for (const c of layers.reverse()) bg = { r: c.r * c.a + bg.r * (1 - c.a), g: c.g * c.a + bg.g * (1 - c.a), b: c.b * c.a + bg.b * (1 - c.a) };
  const fg = parse(getComputedStyle(el).color);
  const a = lum(fg), b = lum(bg);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
};

const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  let thin = false;
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "SPY"); localStorage.setItem("sp_room_layout", "1"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "SPY", price: PRICE, change: -7.1, change_pct: -0.94, time: new Date().toISOString(), delayed: 0,
      source: "ياهو", session: SES, ext: null }));
    if (p.startsWith("/market/options/")) return r.fulfill(body(chainOf(thin ? { ...VPX, thin: true } : VPX)));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { market: "sa", state: "closed", label: "السوق مغلق", detail: "", next: null } }));
    if (p === "/market/watchlist/groups") return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }]));
    if (p === "/market/watchlist") return r.fulfill(body([{ symbol: "SPY", name: "SPDR S&P 500" }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await page.locator('[data-role="troom-options"]').first().click().catch(() => {});
  await page.waitForTimeout(1200);
  const shot = async n => { if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/vp-${n}-${vp.width}.png` }).catch(() => {}); };

  const read = () => page.evaluate(() => {
    const leg = document.querySelector('[data-role="oc-vpleg"]');
    const ks = [...document.querySelectorAll('[data-role="oc-row"] .ocx-k')].map(k => {
      const bar = k.querySelector(".ocx-vpbar"), tag = k.querySelector('[data-role="oc-vptag"]');
      return { k: +(k.querySelector("b")?.textContent || "").replace(/,/g, ""), vp: k.getAttribute("data-vp"), tag: tag?.textContent || "",
        w: bar ? bar.getBoundingClientRect().width / k.getBoundingClientRect().width : 0, fs: tag ? parseFloat(getComputedStyle(tag).fontSize) : null };
    });
    return { leg: leg?.textContent || "", ks, over: document.documentElement.scrollWidth - window.innerWidth };
  });
  const r1 = await read();
  await shot("chain");
  const at = k => r1.ks.find(x => x.k === k) || {};
  const tags = { 752: at(752).vp, 758: at(758).vp, 747: at(747).vp, 763: at(763).vp, 760: at(760).vp, 744: at(744).vp };
  say(/الفوليوم بروفايل/.test(r1.leg) && /752\.00/.test(r1.leg) && /747\.00–758\.00/.test(r1.leg) && /حجمٌ كثيف/.test(r1.leg) && /فراغ/.test(r1.leg)
      && /شموعُ 15 دقيقة/.test(r1.leg),
      `${label}: ١ مفتاحُ البروفايل فوق الجدول: نقطةُ التحكّم ومنطقةُ القيمة بأرقامها، ومعنى «حجمٌ كثيف» و«فراغ»، ونافذتُه`, r1.leg.slice(0, 120));
  const tagged = r1.ks.filter(x => x.vp);
  say(JSON.stringify(tags) === JSON.stringify({ 752: "poc", 758: "vah", 747: "val", 763: "hvn", 760: "lvn", 744: "" })
      && at(752).tag === "تحكّم" && at(763).tag === "حجمٌ كثيف" && at(760).tag === "فراغ" && at(752).w > 0.9 && at(760).w < at(752).w
      && tagged.every(x => x.fs >= 9.5) && r1.over <= 1,
      `${label}: ٢ كلُّ سعر تنفيذٍ بعمود حجمه، والموسومُ على مستواه (تحكّم · حدّا القيمة · حجمٌ كثيف · فراغ — والخفيفُ بلا وسم)، بخطٍّ ≥ 9.5px وبلا تمريرٍ أفقيّ`,
      `${JSON.stringify(tags)} · عرضُ عمود التحكّم ${at(752).w?.toFixed(2)} · تجاوز ${r1.over}`);
  const cons = [];
  for (const theme of ["dark", "light"]) {
    await page.evaluate(t => { document.documentElement.classList.toggle("light", t === "light"); document.documentElement.classList.toggle("dark", t === "dark"); }, theme);
    await page.waitForTimeout(250);
    cons.push(...(await page.evaluate(src => { const f = eval(src); return [...document.querySelectorAll('[data-role="oc-vptag"]')]
      .map(e => ({ c: +f(e).toFixed(2), t: e.textContent, fg: getComputedStyle(e).color })); }, `(${contrastOf.toString()})`)).map(x => ({ ...x, theme })));
    await shot(`chain-${theme}`);
  }
  const low = cons.filter(x => x.c < 4.5);
  say(cons.length >= 10 && !low.length, `${label}: ٢ب الوسومُ مقروءةٌ في المظهرين (تباين ≥ 4.5:1)`,
      low.length ? JSON.stringify(low.slice(0, 4)) : `أدنى ${Math.min(...cons.map(x => x.c))}`);

  thin = true;
  await page.keyboard.press("Escape").catch(() => {}); await page.waitForTimeout(400);
  await page.reload({ waitUntil: "load" }).catch(() => {}); await page.waitForTimeout(2500);
  await page.locator('[data-role="troom-options"]').first().click().catch(() => {}); await page.waitForTimeout(1200);
  const r2 = await read();
  say(/السيولةُ ضعيفة/.test(r2.leg) && r2.ks.length > 5 && r2.ks.every(x => !x.tag && x.w === 0),
      `${label}: ٣ السيولةُ الضعيفة: المفتاحُ يقول ذلك، ولا وسمَ ولا أعمدة`, r2.leg.slice(0, 80));
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
