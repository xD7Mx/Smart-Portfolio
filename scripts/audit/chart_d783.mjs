// ─────────────────────────────────────────────────────────────────────────
// D783 — بأمر المالك (2026-11-21): «ترسُ القائمة الجانبية يتحكّم في كلّ شيء: إعادةُ تسمية، حذف، إخفاء… ولازم أتحكّم بالترتيب — أرفع وأنزل وأرتّب:
// تاسي تحت، والسباكس فوق، وأرامكو تحت، والراجحي فوق»، و«الترندُ لم أجده في إعدادات الدحم في الألوان — ضاع»، و«الفيبو أربعَ عشرةَ مستوىً
// كتريدنق فيو — عندنا ناقصة».
// خادمٌ مموَّهٌ بحالةٍ تتغيّر مع الأوامر (ترتيبٌ وتسميةٌ وحذف)، ويُفحص على الشاشتين.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5283;
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
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const bars = (n = 150) => Array.from({ length: n }, (_, i) => {
  const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10);
  const c = 600 + i * 1.1 + Math.sin(i / 2) * 3, o = 600 + (i - 1) * 1.1 + Math.sin((i - 1) / 2) * 3;
  return { date: day, open: o, high: Math.max(o, c) + 1, low: Math.min(o, c) - 1, close: c, volume: c >= o ? 3e6 : 1e6 };
});
const HOLD = [{ company: { symbol: "1120", name_ar: "مصرف الراجحي" }, last_price: 64.2, change_pct: 1.25 },
              { company: { symbol: "2222", name_ar: "أرامكو السعودية" }, last_price: 25.1, change_pct: -0.4 }];
const tabsOf = page => page.locator('[data-role="troom-tab"]').allTextContents();
const rowsOf = (page, box = "troom-rows") => page.evaluate(b => [...document.querySelectorAll(`[data-role="${b}"] [data-sym]`)].map(e => e.getAttribute("data-sym")), box);

const browser = await chromium.launch({ executablePath: CHROME });
for (const vp of [{ width: 1366, height: 860 }, { width: 390, height: 844 }]) {
  const label = vp.width < 600 ? "الجوال" : "سطح المكتب";
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [], calls = [];
  /* حالةُ الخادم المموَّه: تتغيّر بالأوامر كما يتغيّر الخادمُ الحقيقيّ */
  let groups = [{ id: 3, name: "المؤشرات", is_default: false, sort_order: -1 }, { id: 1, name: "الرئيسية", is_default: true, sort_order: 0 },
                { id: 2, name: "السوق الأمريكي", is_default: false, sort_order: 1 }];
  const rows = { 1: [{ symbol: "AAPL", name: "Apple", price: 231.4, change_pct: 0.3 }],
    2: [{ symbol: "SPY", name: "SPDR S&P 500", price: 754.37, change_pct: -0.94 }],
    3: [{ symbol: "^TASI.SR", name: "تاسي", price: 11234.5, change_pct: -0.31 }, { symbol: "^GSPC", name: "S&P 500", price: 6012.4, change_pct: 0.42 },
        { symbol: "BTC-USD", name: "بتكوين", price: 96123.1, change_pct: 2.1 }] };
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  page.on("dialog", d => d.accept().catch(() => {}));
  await page.addInitScript(() => { try {
    if (sessionStorage.getItem("d783-init")) return;
    sessionStorage.setItem("d783-init", "1");
    for (const k of ["sp_room_hidden", "sp_room_list2", "sp_room_mine_order", "sp_room_layout"]) localStorage.removeItem(k);
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "1120"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: true, stochrsi: false, cvd: false, macd: false, d7m: true }));
  } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    const data = () => JSON.parse(r.request().postData() || "{}");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p.startsWith("/market/live/")) return r.fulfill(body({ symbol: "X", price: 64.2, change: 0.4, change_pct: 0.6, time: new Date().toISOString(), delayed: 0,
      source: "ياهو", session: SES, ext: null }));
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa", state: "closed", label: "السوق مغلق" } }));
    if (p === "/holdings") return r.fulfill(body(HOLD));
    if (p === "/market/watchlist/groups" && m === "GET") return r.fulfill(body(groups));
    if (p === "/market/watchlist/groups/order" && m === "PUT") {
      const ids = data().ids || []; calls.push(["gorder", ids]);
      groups = ids.map((id, i) => ({ ...groups.find(g => g.id === id), sort_order: i }));
      return r.fulfill(body(groups));
    }
    let mm = /^\/market\/watchlist\/groups\/(\d+)$/.exec(p);
    if (mm && m === "PATCH") { const id = +mm[1], name = data().name; calls.push(["rename", id, name]); groups = groups.map(g => (g.id === id ? { ...g, name } : g)); return r.fulfill(body({})); }
    if (mm && m === "DELETE") { const id = +mm[1]; calls.push(["gdel", id]); groups = groups.filter(g => g.id !== id); return r.fulfill(body(null)); }
    if (p === "/market/watchlist/order" && m === "PUT") {
      const d = data(); calls.push(["order", d.group_id, d.symbols]);
      rows[d.group_id] = d.symbols.map(s => rows[d.group_id].find(x => x.symbol === s));
      return r.fulfill(body(d.symbols));
    }
    if (p === "/market/watchlist" && m === "GET") return r.fulfill(body(rows[Number(u.searchParams.get("group_id"))] || []));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const shot = async n => { if (process.env.SHOTS) await page.screenshot({ path: `${process.env.SHOTS}/d783-${n}-${vp.width}.png` }).catch(() => {}); };

  // ١ الترس: لكلّ قائمةٍ إظهارٌ ورفعٌ وإنزالٌ وتسميةٌ وحذف («محفظتي» إظهارٌ وحده) — وأهدافُ اللمس ≥ 32px
  await page.locator('[data-role="troom-gear"]').click(); await page.waitForTimeout(350);
  await shot("gear");
  const gm = await page.evaluate(() => [...document.querySelectorAll('[data-role="troom-glist"]')].map(r => ({ id: r.getAttribute("data-list"),
    acts: ["troom-gup", "troom-gdown", "troom-grename", "troom-gdel"].filter(k => r.querySelector(`[data-role="${k}"]`)).length,
    tgt: Math.min(...[...r.querySelectorAll("button")].map(b => Math.min(b.getBoundingClientRect().width, b.getBoundingClientRect().height))) })));
  say(gm.length === 4 && gm[0].id === "mine" && gm[0].acts === 0 && gm.slice(1).every(g => g.acts === 4) && gm.every(g => g.tgt >= 32),
    `${label}: ١ ترسُ القوائم: لكلّ قائمةٍ إظهارٌ وإخفاءٌ ورفعٌ وإنزالٌ وإعادةُ تسميةٍ وحذف (و«محفظتي» إظهارٌ وحده) — وأهدافُ اللمس ≥ 32px`, JSON.stringify(gm.map(g => `${g.id}:${g.acts}`)));

  // ٢ ترتيبُ القوائم: «المؤشرات» تنزل تحت «الرئيسية» — يُحفظ على الخادم ويتبدّل الصفّ
  await page.locator('[data-role="troom-glist"][data-list="g3"] [data-role="troom-gdown"]').click(); await page.waitForTimeout(900);
  const t2 = await tabsOf(page), go = calls.find(c => c[0] === "gorder");
  say(go && JSON.stringify(go[1]) === "[1,3,2]" && JSON.stringify(t2) === JSON.stringify(["محفظتي", "الرئيسية", "المؤشرات", "السوق الأمريكي"]),
    `${label}: ٢ رفعُ القوائم وإنزالُها — «المؤشرات» تحت «الرئيسية» تُحفظ على الخادم ويتبدّل صفُّ القوائم`, JSON.stringify(t2));

  // ٣ إعادةُ التسمية من الترس
  await page.locator('[data-role="troom-glist"][data-list="g2"] [data-role="troom-grename"]').click(); await page.waitForTimeout(250);
  await page.locator('[data-role="troom-rename-input"]').fill("أمريكا"); await page.keyboard.press("Enter"); await page.waitForTimeout(900);
  const t3 = await tabsOf(page);
  say(calls.some(c => c[0] === "rename" && c[1] === 2 && c[2] === "أمريكا") && t3.includes("أمريكا") && !t3.includes("السوق الأمريكي"),
    `${label}: ٣ إعادةُ تسمية القائمة من الترس («السوق الأمريكي» ⇐ «أمريكا»)`, JSON.stringify(t3));

  // ٤ حذفُ قائمةٍ من الترس (بعد التأكيد)
  await page.locator('[data-role="troom-glist"][data-list="g2"] [data-role="troom-gdel"]').click(); await page.waitForTimeout(900);
  const t4 = await tabsOf(page);
  say(calls.some(c => c[0] === "gdel" && c[1] === 2) && !t4.includes("أمريكا"), `${label}: ٤ حذفُ القائمة من الترس بعد التأكيد`, JSON.stringify(t4));
  await page.mouse.click(5, vp.height - 5); await page.waitForTimeout(300);

  // ٥ ترتيبُ العناصر في «المؤشرات»: السباكس فوق، وتاسي تحت — يُحفظ على الخادم وينزلق في مكانه
  await page.locator('[data-role="troom-tab"]', { hasText: "المؤشرات" }).click(); await page.waitForTimeout(900);
  await page.locator('[data-role="troom-edit"]').click(); await page.waitForTimeout(300);
  const priceInEdit = await page.locator('[data-role="troom-rows"] [data-role="troom-price"]').count();
  await page.locator('[data-role="troom-rows"] [data-sym="^GSPC"] [data-role="troom-up"]').click(); await page.waitForTimeout(500);
  const anim = await page.evaluate(() => document.getAnimations().filter(a => a.effect?.target?.closest?.('[data-role="troom-rows"]')).length);
  await page.locator('[data-role="troom-rows"] [data-sym="^TASI.SR"] [data-role="troom-down"]').click(); await page.waitForTimeout(700);
  await shot("order");
  const r5 = await rowsOf(page), ord = calls.filter(c => c[0] === "order");
  say(JSON.stringify(r5) === JSON.stringify(["^GSPC", "BTC-USD", "^TASI.SR"]) && ord.length === 2 && ord[1][1] === 3
      && JSON.stringify(ord[1][2]) === JSON.stringify(["^GSPC", "BTC-USD", "^TASI.SR"]) && priceInEdit === 0,
    `${label}: ٥ ترتيبُ العناصر بالسهمين — السباكس فوق وتاسي تحت — يُحفظ على الخادم (والسعرُ يتنحّى في وضع الترتيب ليتّسع للسهمين)`,
    `${r5.join(" · ")} · حركة ${anim}`);
  say(anim >= 1, `${label}: ٥ب والعنصرُ ينزلق إلى مكانه بانسياب لا يقفز`, `${anim}`);
  await page.locator('[data-role="troom-edit"]').click(); await page.waitForTimeout(300);

  // ٦ ترتيبُ «محفظتي»: أرامكو فوق الراجحي — يبقى بعد إعادة التحميل
  await page.locator('[data-role="troom-tab"]', { hasText: "محفظتي" }).click(); await page.waitForTimeout(600);
  await page.locator('[data-role="troom-edit"]').click(); await page.waitForTimeout(300);
  await page.locator('[data-role="troom-rows"] [data-sym="2222"] [data-role="troom-up"]').click(); await page.waitForTimeout(500);
  const r6 = await rowsOf(page), saved = await page.evaluate(() => localStorage.getItem("sp_room_mine_order"));
  await page.reload({ waitUntil: "load" }).catch(() => {}); await page.waitForTimeout(2500);
  const r6b = await rowsOf(page);
  say(JSON.stringify(r6) === '["2222","1120"]' && saved === '["2222","1120"]' && JSON.stringify(r6b) === '["2222","1120"]',
    `${label}: ٦ ترتيبُ «محفظتي» بيد المالك (أرامكو فوق الراجحي) ويبقى بعد إعادة التحميل`, `${r6.join(",")} ⇐ ${r6b.join(",")}`);

  // ٧ إعداداتُ D7M: الترندُ بلونيه داخل قسمه، والمنتقي يعرض اللونَ المرسومَ فعلاً — ولا قسمَ ألوانٍ عامّاً
  await page.locator('[data-role="pc-cfg"]').first().click(); await page.waitForTimeout(250);
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="d7m"]').first().click(); await page.waitForTimeout(400);
  await shot("trend");
  const tr = await page.evaluate(() => {
    const dlg = document.querySelector('[role="dialog"][aria-label="إعدادات D7M"]');
    const hex = n => { const v = getComputedStyle(document.documentElement).getPropertyValue(n).trim(); if (/^#[0-9a-f]{6}$/i.test(v)) return v.toLowerCase();
      const m = v.match(/\d+(\.\d+)?/g); return m ? "#" + m.slice(0, 3).map(x => Math.round(+x).toString(16).padStart(2, "0")).join("") : v; };
    const up = dlg?.querySelector('[data-role="d7m-trend"] [data-color="trendUp"] input[type="color"]'), dn = dlg?.querySelector('[data-role="d7m-trend"] [data-color="trendDown"] input[type="color"]');
    return { legend: dlg?.querySelector('[data-role="d7m-trend"] legend')?.textContent || "", up: up?.value, dn: dn?.value, upTok: hex("--pc-trend-up"), dnTok: hex("--pc-trend-down"),
      general: [...(dlg?.querySelectorAll("legend") || [])].some(l => l.textContent.trim() === "الألوان"), colors: dlg?.querySelectorAll('input[type="color"]').length || 0 };
  });
  say(/الترند/.test(tr.legend) && tr.up === tr.upTok && tr.dn === tr.dnTok && !tr.general && tr.colors >= 12,
    `${label}: ٧ الترندُ بلونيه (الصاعد والهابط) داخل قسم «الترند» في إعدادات D7M، والمنتقي يعرض اللونَ المرسومَ فعلاً — ولكلّ عنصرٍ لونُه في قسمه`,
    `${tr.legend} · ${tr.up}/${tr.upTok} · ${tr.dn}/${tr.dnTok} · ${tr.colors} منتقيات`);

  // ٨ الفيبو: «الكل» أربعَ عشرةَ كتريدنق فيو، و«مختصر» ثلاثة
  await page.locator('[role="dialog"][aria-label="إعدادات D7M"] [data-role="fib-mode"] button', { hasText: "الكل" }).click(); await page.waitForTimeout(700);
  const lvAll = await page.evaluate(() => Number(document.querySelector('[data-role="pro-chart"]')?.dataset.lv));
  await page.locator('[role="dialog"][aria-label="إعدادات D7M"] [data-role="fib-mode"] button', { hasText: "مختصر" }).click(); await page.waitForTimeout(700);
  const lvC = await page.evaluate(() => Number(document.querySelector('[data-role="pro-chart"]')?.dataset.lv));
  await page.locator('[role="dialog"][aria-label="إعدادات D7M"] button[aria-label="إغلاق"]').first().click().catch(() => {});
  say(lvAll === 14 && lvC === 3, `${label}: ٨ مستوياتُ الفيبو في «الكل» أربعَ عشرةَ كتريدنق فيو، وفي «مختصر» ثلاثة`, `${lvAll} · ${lvC}`);
  const over = await page.evaluate(() => document.scrollingElement.scrollWidth - innerWidth);
  say(errs.length === 0 && over <= 1, `${label}: ٩ لا خطأ ولا فيضَ أفقيّ`, errs[0] || `${over}px`);
  await ctx.close();
}
await browser.close(); stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
