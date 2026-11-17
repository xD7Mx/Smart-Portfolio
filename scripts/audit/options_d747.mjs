// ─────────────────────────────────────────────────────────────────────────
// D747 — البحثُ في السوق الأمريكي كلِّه وعقودُ الخيارات في غرفة التداول (بأمر المالك 2026-11-15).
// «قائمةُ البحث تشمل جميعَ أسهم السوق الأمريكي… وأضف الخيارات — أختار عقدي من هنا، اللي بعد أسبوع ولا بعد يومين».
// يُقلَع خادمُ التطوير بخادمٍ مموَّهٍ بأشكال الردود الحقيقية (‏options_chain.shape_chain / shape_search)، ويُفحص: زرُّ الخيارات
// للسهم الأمريكي، والآجالُ بأيامها، وقربُ السعر والكلّ، والشراءُ والبيع، وفتحُ رسم العقد باسمه العربيّ، وإضافتُه للقائمة،
// والبحثُ في السوق كلِّه — بلا خطأٍ ولا فيضٍ وبأهدافِ لمسٍ ≥ 32px وخطٍّ ≥ 9.5px.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5247;
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
const occ = (k, cp, d = "261116") => `SPY${d}${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
const legs = (cp, d) => Array.from({ length: 30 }, (_, i) => { const k = 740 + i; return { contract: occ(k, cp, d), strike: k, last: 3.69, bid: 3.6, ask: 3.7,
  change: -1, pct: -5.2, volume: 1000 + i, oi: 400 + i, iv: 10.3, itm: cp === "C" ? k < PRICE : k > PRICE, last_trade: null }; });
const CHAIN = d => ({ symbol: "SPY", name: "SPDR S&P 500", price: PRICE, currency: "USD", delayed: true,
  expirations: [{ t: 1794787200, date: "2026-11-16", dte: 1 }, { t: 1794873600, date: "2026-11-17", dte: 2 }, { t: 1795392000, date: "2026-11-23", dte: 8 }],
  expiry: d || 1794787200, calls: legs("C", d === 1794873600 ? "261117" : "261116"), puts: legs("P", d === 1794873600 ? "261117" : "261116") });
const bars = (n = 120) => Array.from({ length: n }, (_, i) => { const day = new Date(Date.UTC(2026, 6, 1) + i * 864e5).toISOString().slice(0, 10), b = 700 + i * 0.4;
  return { date: day, open: b, high: b + 2, low: b - 2, close: b + 1, volume: 1e6 }; });

const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [], hist = [], posts = [], chains = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try {
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "SPY"); localStorage.setItem("sp_room_list", "g2");
    const s = JSON.parse(localStorage.getItem("sp-auth") || "{}");
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(history|bars)\//.test(p)) { hist.push(decodeURIComponent(p.split("/").pop())); return r.fulfill(body(bars())); }
    if (p.startsWith("/market/options/")) { const d = Number(u.searchParams.get("date")) || null; chains.push([decodeURIComponent(p.split("/").pop()), d]); return r.fulfill(body(CHAIN(d))); }
    if (p === "/market/symbol-search") return r.fulfill(body((u.searchParams.get("q") || "").toLowerCase().startsWith("nvd")
      ? [{ symbol: "NVDA", name: "NVIDIA Corporation", type: "سهم", exchange: "ناسداك", us: true, options: true }] : []));
    if (p === "/market/watchlist/groups") return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }, { id: 2, name: "أوبشن", is_default: false }]));
    if (p === "/market/watchlist" && m === "POST") { posts.push(JSON.parse(r.request().postData() || "{}")); return r.fulfill(body({ ok: true })); }
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const btn = page.locator('[data-role="troom-options"]');
  say(await btn.count() === 1, `${label}: ١ لسهمٍ أمريكيّ زرُّ «الخيارات» بجانب اسمه`);
  await btn.click().catch(() => {});
  await page.waitForTimeout(900);
  const exps = await page.locator('[data-role="oc-exp"]').allTextContents();
  say(exps.length === 3 && exps[0].includes("16 نوفمبر") && exps[0].includes("غداً") && exps[1].includes("بعد يومين") && exps[2].includes("بعد 8 أيام")
      && chains[0]?.[0] === "SPY", `${label}: ٢ الآجالُ بتواريخها وأيامها الباقية — غداً · بعد يومين · بعد 8 أيام`, JSON.stringify(exps));
  /* ‏D761: الجدولُ بطريقة «إنتراكتف بروكرز» — صفٌّ لكلّ سعر تنفيذٍ بعقدَيه، والسعرُ الحاليُّ خطٌّ بين سعرَي التنفيذ */
  const near = await page.locator('[data-role="oc-row"]').count();
  const pxl = await page.locator('[data-role="oc-pxline"]').first().textContent().catch(() => "");
  const atm = await page.locator('[data-role="oc-pxline"] + [data-role="oc-row"] .ocx-k b').first().textContent().catch(() => "");
  await page.locator('[data-role="oc-range"]').click(); await page.waitForTimeout(250);
  const allN = await page.locator('[data-role="oc-row"]').count();
  await page.locator('[data-role="oc-range"]').click(); await page.waitForTimeout(250);
  say(near === 24 && allN === 30 && pxl === "754.37" && atm === "755.00", `${label}: ٣ ما قربَ السعر أوّلاً (24 سعرَ تنفيذٍ حوله) والسعرُ خطٌّ قبل أقرب تنفيذ، والكلُّ بضغطة`, `${near}/${allN} · ${pxl} · ${atm}`);
  await page.locator('[data-role="oc-exp"]').nth(1).click(); await page.waitForTimeout(600);
  await page.locator('[data-role="oc-cell"][data-side="put"]').first().click(); await page.waitForTimeout(300);
  const putTitle = await page.locator('[data-role="oc-detail"] .ocx-dhead b').first().textContent().catch(() => "");
  say(chains.some(c => c[1] === 1794873600) && /بيع/.test(putTitle || "") && /17 نوفمبر/.test(putTitle || ""),
      `${label}: ٤ تغييرُ الأجل يطلب سلسلتَه، وعقدُ البيع (Put) يُفتح ببطاقته باسمه`, putTitle || "");
  const m = await page.evaluate(() => {
    const sh = document.querySelector(".oc-sheet"); const W = document.documentElement.clientWidth;
    let minT = 99, minF = 99;
    sh.querySelectorAll("button").forEach(b => { const r = b.getBoundingClientRect(); if (r.width && r.height) minT = Math.min(minT, r.height); });
    sh.querySelectorAll("*").forEach(e => { if (e.childElementCount === 0 && e.textContent.trim()) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    return { over: document.documentElement.scrollWidth - W, minT, minF };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5, `${label}: ٥ لا فيضَ في الصفحة، وأهدافُ اللمس ≥ 32px، والخطُّ ≥ 9.5px`, JSON.stringify(m));
  await page.locator('[data-role="oc-add"]').first().click(); await page.waitForTimeout(400);
  const added = posts[0] || {};
  say(/^SPY261117P\d{8}$/.test(added.symbol || "") && /SPY \d+ بيع · 17 نوفمبر/.test(added.name || "") && added.group_id === 2,
      `${label}: ٦ «أضف للقائمة» في بطاقة العقد يضيفه إلى القائمة المفتوحة باسمه`, JSON.stringify(added));
  await page.locator('[data-role="oc-open"]').first().click(); await page.waitForTimeout(1200);
  const ident = await page.locator('[data-role="troom-chart"]').first().textContent().catch(() => "");
  say(await page.locator('[data-role="oc"]').count() === 0 && hist.some(h => /^SPY261117P\d{8}$/.test(h)) && /SPY \d+ بيع/.test(ident || ""),
      `${label}: ٧ «الرسم» في بطاقة العقد يغلق السلسلة ويفتح رسمَه باسمه العربيّ`, (ident || "").slice(0, 60));
  await page.locator('[data-role="troom-options"]').click(); await page.waitForTimeout(600);
  const reopened = chains[chains.length - 1]?.[0];
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);
  say(reopened === "SPY" && await page.locator('[data-role="oc"]').count() === 0, `${label}: ٨ ومن رسم العقد تُفتح سلسلةُ أصله، و«Esc» يغلقها`);
  await page.locator(".troom-bar .inline-search-btn").click(); await page.waitForTimeout(300);
  await page.locator(".troom-bar .inline-search-input").fill("nvd"); await page.waitForTimeout(900);
  const hit = await page.locator('[data-role="search-hit"]').first().textContent().catch(() => "");
  await page.locator('[data-role="search-hit"]').first().click().catch(() => {}); await page.waitForTimeout(400);
  say(/NVDA/.test(hit || "") && /سهم · ناسداك/.test(hit || "") && posts.some(p => p.symbol === "NVDA"),
      `${label}: ٩ البحثُ يشمل السوقَ الأمريكيَّ كلَّه — الرمزُ واسمُه ونوعُه وبورصتُه، ويُضاف بضغطة`, (hit || "").slice(0, 60));
  say(errs.length === 0, `${label}: ١٠ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
