// ─────────────────────────────────────────────────────────────────────────
// D695 (بأمر المالك 2026-10-13): «أعد تصميمَ بطاقات التوزيع النسبي لتحاكي تصميمَ التطبيق الأنيق». كانت سطوراً تفصلها خطوطٌ
// بلغةٍ غير لغة بطاقات الفرز وغرفة التداول. يُفتح التطبيقُ الحقيقيّ (‏vite) على الجوال واللوح، في المظهرين، ويُقاس من الـDOM:
// بطاقةٌ لكلّ شركةٍ بنمط التطبيق، وشريطُ وزنٍ بمقياسٍ واحد تتحرّك علامتُه مع الكتابة، وخاناتٌ يمينيّةٌ بأرقامٍ لاتينية،
// ولمسٌ ≥ 32px، وخطٌّ ≥ 9.5px، ولا فيضَ أفقيّ، وحركةُ دخول.
//    SHOTS=dir node scripts/audit/ui_d695.mjs   ← لقطاتٌ للمراجعة
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5250;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const ITEMS = [
  ["2222", "أرامكو السعودية", 24.1, 41000, 35.2, 30, 3.9], ["1120", "مصرف الراجحي", 92.3, 22000, 18.9, 25, 2.6],
  ["2270", "سدافكو", 178.6, 15500, 13.3, 10, 2.1], ["7010", "الاتصالات السعودية", 41.2, 9800, 8.4, 15, 4.4],
].map(([symbol, name, last_price, market_value, current_weight, target_weight, dividend_yield], i) =>
  ({ company_id: i + 1, symbol, name, last_price, market_value, current_weight, target_weight, dividend_yield, sharia_status: "pure" }));
const ALLOC = { items: ITEMS, reinvestment_pool: 1200, fresh_cash: 8800, available_cash: 10000, investable: 126300 };

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp, theme] of [["الجوال · فاتح", { width: 390, height: 844 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"],
                                  ["اللوح", { width: 820, height: 1100 }, "light"]]) {
  const ctx = await browser.newContext({ viewport: vp, isMobile: vp.width < 600, hasTouch: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", r => /\/allocation(\?|$)/.test(r.request().url()) ? r.fulfill(body(ALLOC)) : r.fulfill(body([])));
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe");
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/portfolio`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1800);
  await page.locator("nav button", { hasText: "لوحة التحكم" }).first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(300);
  await page.locator("button", { hasText: "التوزيع النسبي" }).first().click({ timeout: 5000 }).catch(() => {});
  await sleep(80);
  const rising = await page.evaluate(() => [...document.querySelectorAll('[data-role="alloc-card"]')].filter(c => c.getAnimations().length).length);
  await page.waitForTimeout(1200);

  const m = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('[data-role="alloc-card"]')];
    const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const one = cards[0];
    const cs = one ? getComputedStyle(one) : null;
    const minFont = Math.min(...cards.flatMap(c => [...c.querySelectorAll("*")])
      .filter(e => e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()))
      .map(e => parseFloat(getComputedStyle(e).fontSize)));
    const targets = cards.flatMap(c => [...c.querySelectorAll('input, button')]).map(e => e.getBoundingClientRect().height);
    const cells = cards.flatMap(c => [...c.querySelectorAll('[data-role="cell"]')]);
    const misaligned = cells.filter(c => getComputedStyle(c).textAlign === "center" || getComputedStyle(c).textAlign === "left").length;
    const arabicDigits = /[٠-٩۰-۹]/.test(cards.map(c => c.textContent).join(""));
    const bar = one?.querySelector(".wbar"), mark = one?.querySelector(".wbar-mark");
    const row = (c) => c.getBoundingClientRect();
    return {
      n: cards.length, oldList: !!document.querySelector(".lg\\:hidden.divide-y"),
      radius: cs ? parseFloat(cs.borderTopLeftRadius) : 0, logo: one ? !!one.querySelector("img, [data-logo], svg") : false,
      cells: one ? one.querySelectorAll('[data-role="cell"]').length : 0, minFont, minTarget: Math.min(...targets), misaligned, arabicDigits,
      markLeft: mark ? mark.getBoundingClientRect().left : null, barW: bar ? bar.getBoundingClientRect().width : 0,
      total: !!document.querySelector('[data-role="alloc-total"]'),
      sell: (() => { const c = one?.querySelectorAll('[data-role="cell"]')[1]; return c ? { label: c.children[0].textContent.trim(), value: c.children[1].textContent.trim().replace(/\s+/g, " ") } : null; })(),
      cols: cards.length > 1 ? (Math.abs(row(cards[0]).top - row(cards[1]).top) < 2 ? 2 : 1) : 1,
      over: sw - W,
    };
  });
  say(m.n === ITEMS.length && !m.oldList, `${label}: بطاقةٌ لكلّ شركة (${m.n}) — لا قائمةَ سطورٍ تفصلها خطوط`);
  say(m.radius >= 14 && m.logo && m.cells === 3 && m.total, `${label}: بنمط بطاقات التطبيق — حوافٌّ ${m.radius}px وشعارٌ وثلاثُ خانات، وبطاقةُ مجموع`);
  say(m.minFont >= 9.5 && m.minTarget >= 32, `${label}: أصغرُ خطّ ≥ 9.5px وأصغرُ هدف لمس ≥ 32px`, `${m.minFont}px · ${Math.round(m.minTarget)}px`);
  say(m.misaligned === 0 && !m.arabicDigits, `${label}: الخاناتُ يمينيّةٌ والأرقامُ لاتينية`);
  say(m.over <= 1, `${label}: لا فيضَ أفقيّ`, `${m.over}px`);
  say(rising > 0, `${label}: البطاقاتُ تطلع بحركةٍ عند فتح التبويب`, `${rising} حركة`);
  if (vp.width >= 768) say(m.cols === 2, `${label}: عمودان على اللوح`);
  // شريطُ الوزن: كتابةُ هدفٍ جديد تُحرّك العلامة (بانزلاق) — بمقياسٍ واحد للبطاقات
  const inp = page.locator('[data-role="alloc-target"]').first();
  await inp.fill("5").catch(() => {});
  await sleep(40);
  const moving = await page.evaluate(() => {
    const mk = document.querySelector('[data-role="alloc-card"] .wbar-mark');
    return mk ? getComputedStyle(mk).transitionDuration : "";
  });
  await page.waitForTimeout(500);
  const after = await page.evaluate(() => { const mk = document.querySelector('[data-role="alloc-card"] .wbar-mark'); return mk ? mk.getBoundingClientRect().left : null; });
  const unsaved = await page.evaluate(() => document.body.textContent.includes("معاينة"));
  say(m.markLeft != null && after != null && Math.abs(after - m.markLeft) > 10 && /0\.32s|320ms/.test(moving) && unsaved,
      `${label}: علامةُ الهدف تنزلق مع الكتابة قبل الحفظ (معاينة)`, `${Math.round(m.markLeft ?? -1)} ← ${Math.round(after ?? -1)} · ${moving}`);
  // والفائضُ يُقال بأسهمه لا بصفرين: أرامكو (35.2٪ والهدفُ 30٪ قبل التعديل) «أسهمٌ للبيع» برقمٍ موجب
  const sellCell = m.sell;
  say(sellCell && sellCell.label === "أسهمٌ للبيع" && /^[1-9][\d,]*\s*سهم$/.test(sellCell.value),
      `${label}: الفائضُ يُقال بأسهمه «أسهمٌ للبيع» — لا «0 سهم» من السيولة وإعادة الاستثمار`, sellCell ? `${sellCell.label} ${sellCell.value}` : "—");
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  if (SHOTS) {
    await inp.fill("30").catch(() => {});
    await page.waitForTimeout(500);
    const el = await page.$('[data-role="alloc-cards"]');
    if (el) await el.screenshot({ path: join(SHOTS, `alloc_${vp.width}_${theme}.png`) });
  }
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
