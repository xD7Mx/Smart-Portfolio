// ─────────────────────────────────────────────────────────────────────────
// D761 — حيويّةُ السوق الأمريكيّ وسلسلةُ «إنتراكتف بروكرز» والتحليلُ الذكيّ والأحداثُ الاقتصادية (بأمر المالك 2026-11-17).
// «علامةٌ بجانب اسم الشركة كتريدنق فيو: مفتوح، قبل الماركت، بعد الماركت، مغلق، عطلة… أريد الأرقام تتحرّك… البحثُ يدعم جميعَ الشركات
// وألصق العقدَ المنسوخ فيظهر… السلسلةُ مثل إنتراكتف بروكر… زرُّ تحليلٍ ذكيّ يعرف اليونانيات ويمتنع عن الخاطئ… وأيُّ حدثٍ كالفيدرالي وأثرُه».
// خادمٌ مموَّهٌ بأشكال الردود الحقيقية (‏live_quote · option_advisor · econ_calendar)، ويُفحص على الشاشتين.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5261;
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
const SES = { open: { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" },
  holiday: { market: "us", state: "holiday", label: "عطلة", detail: "يفتح بعد يوم و1 س", next: null, holiday: "عيد الشكر", source: "schedule" } };
const occ = (k, cp) => `SPY261120${cp}${String(Math.round(k * 1000)).padStart(8, "0")}`;
const G = (k, call) => ({ iv: 14.2, delta: call ? 0.52 : -0.48, gamma: 0.031, theta: -21.5, vega: 33.1, itm: 48, pop: 41, px: 3.7, src: "ask", spread: 2.7, be: call ? k + 3.7 : k - 3.7 });
const legs = cp => Array.from({ length: 30 }, (_, i) => { const k = 740 + i; return { contract: occ(k, cp), strike: k, last: 3.69, bid: 3.6, ask: 3.7,
  change: -1, pct: -5.2, volume: 1000 + i, oi: 400 + i, iv: 10.3, itm: cp === "C" ? k < PRICE : k > PRICE, last_trade: null, g: G(k, cp === "C") }; });
const CHAIN = { symbol: "SPY", name: "SPDR S&P 500", price: PRICE, currency: "USD", delayed: true, session: SES.open,
  expirations: [{ t: 1795132800, date: "2026-11-20", dte: 3 }], expiry: 1795132800, calls: legs("C"), puts: legs("P"),
  stats: { atm_iv: 14.2, move: 10.9, move_pct: 1.4, pcr_vol: 1.12, pcr_oi: 0.94, max_pain: 750, vol: { call: 30435, put: 30435 }, oi: { call: 12435, put: 12435 } } };
const CARD = (k, v) => ({ contract: occ(k, "P"), type: "put", strike: k, expiry: "2026-11-20", dte: 3, cost: 370, px_src: "ask", g: G(k, false), oi: 900, volume: 50,
  verdict: v, verdict_ar: { ok: "مناسب", warn: "بحذر", no: "أمتنع" }[v], pros: ["مع الاتجاه: المسارُ هابط."], cons: v === "no" ? ["احتمالُ الربح عند الانتهاء نحو 8٪ فقط — أقربُ إلى اليانصيب."] : [], need_pct: 1.2 });
const ADVICE = { symbol: "SPY", price: PRICE, trend: { state: "هابط" }, news: { impact: "سلبي", event: "تراجعٌ بعد بيانات التجزئة" }, hv: 12.1, earnings: null,
  lean: "put", lean_note: "", events: [{ id: "e1", title: "FOMC Meeting Minutes", day: "غداً", riyadh: "2026-11-18 22:00" }],
  best: [CARD(752, "ok"), CARD(748, "warn")], refused: [CARD(720, "no")], budget: 150,
  fit: { ok: false, min_cost: 370, text: "ميزانيةُ 150 دولار لا تكفي لعقدٍ معقولٍ على ^SPX.", alt: { symbol: "SPY", text: "تأخذه على SPY: SPY261120P00752000 بكلفة 140 دولار (مناسب)." } },
  summary: "الاتجاهُ هابطٌ والأنسبُ عقدُ بيعٍ قريبٌ من السعر؛ والخطرُ الأهمّ محضرُ الفيدرالي غداً." };
const EVENTS = { read_ok: true, events: [
  { id: "e0", title: "Retail Sales m/m", ar: "مبيعات التجزئة", impact: "High", impact_ar: "عالٍ", at: "2026-11-17T13:30:00+00:00", riyadh: "2026-11-17 16:30", day: "اليوم", past: true, forecast: "0.1%", previous: "0.8%" },
  { id: "e1", title: "FOMC Meeting Minutes", ar: "محضر اجتماع الفيدرالي", impact: "High", impact_ar: "عالٍ", at: "2026-11-18T19:00:00+00:00", riyadh: "2026-11-18 22:00",
    day: "غداً", past: false, forecast: null, previous: null, what: "يكشف نقاشَ أعضاء الفيدرالي حول الفائدة.", above: "نبرةٌ متشدّدة ترفع العوائد وتضغط الأسهم — ميلٌ لعقود البيع.",
    below: "نبرةٌ متيسّرة تدعم الأسهم — ميلٌ لعقود الشراء.", lean: "neutral" }] };
const bars = (n = 120) => Array.from({ length: n }, (_, i) => { const day = new Date(Date.UTC(2026, 6, 1) + i * 864e5).toISOString().slice(0, 10), b = 700 + i * 0.4;
  return { date: day, open: b, high: b + 2, low: b - 2, close: b + 1, volume: 1e6 }; });

const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [], hist = [], posts = [], adv = [];
  let px = PRICE, ses = SES.open;
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "SPY"); localStorage.setItem("sp_room_list", "g2"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(history|bars)\//.test(p)) { hist.push(decodeURIComponent(p.split("/").pop())); return r.fulfill(body(bars())); }
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "SPY", price: px, change: -7.1, change_pct: -0.94, time: new Date().toISOString(), delayed: 0,
      source: "ياهو", session: ses, ext: null }));
    if (p.startsWith("/market/options/")) return r.fulfill(body(CHAIN));
    if (p === "/market/options-advice") {
      adv.push(Object.fromEntries(u.searchParams));
      return r.fulfill(body(u.searchParams.get("contract") ? { ...ADVICE, contract: CARD(720, "no") } : ADVICE));
    }
    if (p === "/market/econ-events") return r.fulfill(body(EVENTS));
    if (p === "/market/symbol-search") return r.fulfill(body((u.searchParams.get("q") || "").toLowerCase().startsWith("nio")
      ? [{ symbol: "NIO", name: "NIO Inc.", type: "سهم", exchange: "نيويورك", us: true, options: true }] : []));
    if (p === "/market/watchlist/groups") return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }, { id: 2, name: "السوق الأمريكي", is_default: false }]));
    if (p === "/market/watchlist" && m === "POST") { posts.push(JSON.parse(r.request().postData() || "{}")); return r.fulfill(body({ ok: true })); }
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);

  // ١ شارةُ حالة السوق والسعرُ الحيّ بجانب الاسم — والسعرُ يتحرّك ويومض
  const badge = page.locator('[data-role="troom-chart"] [data-role="lq-session"]').first();
  const st1 = await badge.getAttribute("data-state").catch(() => null), lb1 = await badge.textContent().catch(() => "");
  const p1 = await page.locator('[data-role="lq-price"]').first().textContent().catch(() => "");
  px = 755.12;
  await page.waitForTimeout(6200);
  const p2 = await page.locator('[data-role="lq-price"]').first().textContent().catch(() => "");
  say(st1 === "open" && /السوق مفتوح/.test(lb1 || "") && p1 === "754.37" && p2 === "755.12",
      `${label}: ١ شارةُ «السوق مفتوح» بجانب الاسم، والسعرُ يتحرّك وحدَه (754.37 ⇐ 755.12 بلا تحديث صفحة)`, `${st1} · ${p1} ⇐ ${p2}`);

  const shot = async n => { if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/${n}-${vp.width}.png` }).catch(() => {}); };
  await shot("chart");
  // ٢ الأحداثُ الاقتصادية: زرٌّ بعدد عالية الأثر القادمة، ولوحةٌ بالأثر والسيناريوهين
  const cnt = await page.locator('[data-role="troom-chart"] [data-role="ee-count"]').first().textContent().catch(() => "");
  await page.locator('[data-role="troom-chart"] [data-role="ee-btn"]').first().click(); await page.waitForTimeout(500);
  const items = await page.locator('[data-role="ee-item"]').allTextContents();
  await shot("events");
  say(cnt === "1" && items.length === 2 && /محضر اجتماع الفيدرالي/.test(items[1]) && /أعلى من المتوقّع/.test(items[1]) && /عقود البيع/.test(items[1]) && /22:00/.test(items[1]),
      `${label}: ٢ الأحداثُ الاقتصادية — عددُ العالية القادمة، والحدثُ بوقت الرياض وما يقيسه وسيناريوهاه وميلُ الخيارات`, `${cnt} · ${items.length}`);
  await page.keyboard.press("Escape"); await page.waitForTimeout(400);

  // ٣ السلسلة بطريقة «إنتراكتف بروكرز»: الشراءُ يساراً والتنفيذُ وسطاً والبيعُ يميناً، ورأسُها
  await page.locator('[data-role="troom-options"]').click(); await page.waitForTimeout(900);
  const pos = await page.evaluate(() => {
    const r = document.querySelector('[data-role="oc-row"]'); if (!r) return null;
    const x = s => r.querySelector(s).getBoundingClientRect().left;
    return { c: x(".ocx-c"), k: x(".ocx-k"), p: x(".ocx-p") };
  });
  const stats = await page.locator('[data-role="oc-stats"]').textContent().catch(() => "");
  await shot("chain");
  const ocBadge = await page.locator('[data-role="oc"] [data-role="lq-session"]').count();
  say(pos && pos.c < pos.k && pos.k < pos.p && /تذبذب النقود/.test(stats || "") && /14.2%/.test(stats || "") && /±10.90/.test(stats || "") && /750.00/.test(stats || "") && ocBadge === 1,
      `${label}: ٣ الشراءُ يساراً والتنفيذُ وسطاً والبيعُ يميناً، وفي الرأس حالةُ السوق وتذبذبُ النقود والحركةُ المتوقّعة وألمُ الحدّ الأقصى`, JSON.stringify(pos));

  // ٤ بطاقةُ العقد: اليونانياتُ كاملة، ورأيُ التحليل الذكيّ «أمتنع» بسببه
  await page.locator('[data-role="oc-cell"][data-side="put"]').first().click(); await page.waitForTimeout(300);
  const det = await page.locator('[data-role="oc-detail"]').textContent().catch(() => "");
  await page.locator('[data-role="oc-judge"]').click(); await page.waitForTimeout(700);
  const vd = await page.locator('[data-role="oc-detail"] [data-role="oc-verdict"]').getAttribute("data-verdict").catch(() => null);
  const vt = await page.locator('[data-role="oc-detail"] [data-role="oc-verdict"]').textContent().catch(() => "");
  await page.locator('[data-role="oc-detail"]').scrollIntoViewIfNeeded().catch(() => {}); await shot("detail");
  say(/الدلتا/.test(det || "") && /الغاما/.test(det || "") && /الثيتا/.test(det || "") && /الفيغا/.test(det || "") && /-0.480/.test(det || "")
      && vd === "no" && /أمتنع/.test(vt || "") && /اليانصيب/.test(vt || "") && adv.some(a => /^SPY261120P/.test(a.contract || "")),
      `${label}: ٤ بطاقةُ العقد باليونانيات كاملة، و«رأي التحليل الذكي» يمتنع عن العقد الخاطئ بسببه`, `${vd}`);

  // ٥ التحليلُ الذكيّ بالميزانية: الخلاصة والأنسبُ والممتنَعُ عنه، والبديلُ حين لا تكفي الميزانية
  await page.locator('[data-role="oc-budget"]').fill("150");
  await page.locator('[data-role="oc-smart"]').click(); await page.waitForTimeout(900);
  const ai = await page.locator('[data-role="oc-ai"]').textContent().catch(() => "");
  const best = await page.locator('[data-role="oc-best"]').count();
  await shot("smart");
  say(best === 2 && /رأي التحليل الذكي/.test(ai || "") && /الاتجاهُ هابط/.test(ai || "") && /تأخذه على SPY/.test(ai || "") && /أمتنع عنها/.test(ai || "")
      && adv.some(a => a.budget === "150" && !a.contract),
      `${label}: ٥ «تحليل ذكي» بميزانية 150: الخلاصةُ والأنسبُ بأحكامه والممتنَعُ عنه، و«تأخذه على SPY» حين لا تكفي`, `${best}`);
  const m = await page.evaluate(() => {
    const sh = document.querySelector(".oc-sheet"); const W = document.documentElement.clientWidth;
    let minT = 99, minF = 99;
    sh.querySelectorAll("button, summary, input").forEach(b => { const r = b.getBoundingClientRect(); if (r.width && r.height) minT = Math.min(minT, r.height); });
    sh.querySelectorAll("*").forEach(e => { if (e.childElementCount === 0 && e.textContent.trim()) minF = Math.min(minF, parseFloat(getComputedStyle(e).fontSize)); });
    return { over: document.documentElement.scrollWidth - W, minT: Math.round(minT * 100) / 100, minF };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5, `${label}: ٦ لا فيض، وأهدافُ اللمس ≥ 32px، والخطُّ ≥ 9.5px`, JSON.stringify(m));
  await page.keyboard.press("Escape"); await page.waitForTimeout(200); await page.keyboard.press("Escape"); await page.waitForTimeout(400);

  // ٧ البحث: «nio» يُظهر الأمريكيّ، والاختيارُ يُضيف ويفتح رسمَه؛ والعقدُ المنسوخُ من المختبر يُفتح عقداً باسمه
  await page.locator(".troom-bar .inline-search-btn").click(); await page.waitForTimeout(300);
  await page.locator(".troom-bar .inline-search-input").fill("nio"); await page.waitForTimeout(900);
  const hit = await page.locator('[data-role="search-hit"]').first().textContent().catch(() => "");
  await page.locator('[data-role="search-hit"]').first().click().catch(() => {}); await page.waitForTimeout(900);
  const nioOpen = hist.includes("NIO");
  await page.locator(".troom-bar .inline-search-btn").click(); await page.waitForTimeout(300);
  await page.locator(".troom-bar .inline-search-input").fill("NIO280121P00003000"); await page.waitForTimeout(500);
  await page.locator('[data-role="search-option"]').click().catch(() => {}); await page.waitForTimeout(1000);
  const idt = await page.locator('[data-role="troom-chart"]').first().textContent().catch(() => "");
  say(/NIO/.test(hit || "") && posts.some(p => p.symbol === "NIO") && nioOpen && posts.some(p => p.symbol === "NIO280121P00003000" && /NIO 3 بيع/.test(p.name || ""))
      && hist.includes("NIO280121P00003000") && /NIO 3 بيع/.test(idt || ""),
      `${label}: ٧ البحثُ يُظهر NIO ويضيفه ويفتح رسمَه، والعقدُ المنسوخُ يُفتح عقداً باسمه («NIO 3 بيع»)`, (hit || "").slice(0, 40));

  // ٨ العطلة: الشارةُ «عيد الشكر»
  ses = SES.holiday;
  await page.waitForTimeout(6200);
  await page.evaluate(() => window.dispatchEvent(new Event("focus")));
  await page.waitForTimeout(1500);
  const hb = page.locator('[data-role="troom-chart"] [data-role="lq-session"]').first();
  const hs = await hb.getAttribute("data-state").catch(() => null), ht = await hb.textContent().catch(() => "");
  say(hs === "holiday" && /عيد الشكر/.test(ht || ""), `${label}: ٨ والعطلةُ باسمها («عيد الشكر»)`, `${hs} · ${ht}`);
  say(errs.length === 0, `${label}: ٩ لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
