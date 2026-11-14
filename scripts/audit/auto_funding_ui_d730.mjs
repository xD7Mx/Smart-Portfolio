// ─────────────────────────────────────────────────────────────────────────
// D730 في المتصفّح: نافذةُ المعاملة تقسم الشراءَ آليّاً — المالكُ يكتب العددَ والسعرَ وحدهما.
// يُفتح التطبيقُ الحقيقيّ (‏vite) والخادمُ مُحاكًى، ويُقاس: لا اختيارَ للتمويل، والتقسيمُ يظهر بسعر التنفيذ قبل التأكيد،
// والتأكيدُ معطَّلٌ حتى يصل، وما يُرسَل للحفظ هو ما عُرض (‏AUTO + العددُ نفسُه)، ورفضُ 409 يُعيد المعاينة.
//    SHOTS=dir node scripts/audit/auto_funding_ui_d730.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5252;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const body = (data, status = 200) => ({ status, contentType: "application/json", body: JSON.stringify(status === 200 ? { success: true, data } : { detail: data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

const CO = { id: 1, symbol: "1120", name_ar: "مصرف الراجحي", name: "Al Rajhi", sector: "البنوك", status: "ACTIVE" };
const HOLD = { id: 1, company_id: 1, company: CO, symbol: "1120", total_shares: 100, quantity: 100, last_price: 64, current_value: 6400,
  market_value: 6400, average_cost: 50, invested_amount: 5000, total_dividends_received: 0, unrealized_gain: 1400 };
const ALLOC = { items: [{ company_id: 1, symbol: "1120", name: "مصرف الراجحي", last_price: 64, quantity: 100, market_value: 6400,
  current_weight: 17.5, target_weight: 25, reinvest_share: 446.6, liquidity_share: 23300, sharia_status: "pure" }],
  reinvestment_pool: 1786.4, fresh_cash: 28213.6, available_cash: 30000, investable: 36400 };
const SHARE = 446.6;

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp] of [["الحاسوب", { width: 1366, height: 900 }], ["الجوال", { width: 390, height: 844 }]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [], posts = [], previews = [];
  let reject409 = true, slow = 0;
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/transactions/funding-preview") {
      const q = Number(u.searchParams.get("quantity")), px = Number(u.searchParams.get("price"));
      previews.push({ q, px, d: u.searchParams.get("transaction_date") });
      if (slow) await sleep(slow);
      const rq = Math.min(q, Math.floor(SHARE / px + 1e-9));
      return r.fulfill(body({ reinvest_qty: rq, liquidity_qty: q - rq, reinvest_amount: +(rq * px).toFixed(2),
        liquidity_amount: +((q - rq) * px).toFixed(2), company_share: SHARE, headroom: 1786.4 }));
    }
    if (p === "/transactions" && r.request().method() === "POST") {
      posts.push(JSON.parse(r.request().postData() || "{}"));
      if (reject409) { reject409 = false; return r.fulfill(body("تغيّر نصيبُ الشركة من إعادة الاستثمار منذ المعاينة — راجع المعاينة وأكّد من جديد. لم يُحفظ شيء.", 409)); }
      return r.fulfill(body({ id: 9, split: null }));
    }
    if (p === "/holdings") return r.fulfill(body([HOLD]));
    if (p === "/holdings/1") return r.fulfill(body(HOLD));
    if (p === "/allocation") return r.fulfill(body(ALLOC));
    if (p === "/cash") return r.fulfill(body({ available_cash: 30000, total_cash: 30000 }));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
  await page.goto(`http://localhost:${PORT}/portfolio`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2000);
  const open = page.locator('button[title="شراء/بيع"]:visible').first();
  await open.click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(700);
  const modal = page.locator(".modal-box, [role=dialog]").last();
  const txt = await modal.textContent().catch(() => "");
  say(/معاملة/.test(txt || "") && !/\bضخ\b/.test(txt || ""), `${label}: النافذةُ تُفتح بلا اختيارٍ للتمويل («ضخ» · «إعادة استثمار»)`);
  const nums = modal.locator('input[inputmode="decimal"], input[inputmode="numeric"]');
  slow = 900;
  await nums.nth(0).fill("372");
  await nums.nth(1).fill("63.8");
  await page.waitForTimeout(350);
  const confirm = modal.locator("button.btn-primary").first();
  const disabledWhileWaiting = await confirm.isDisabled();
  await page.waitForTimeout(1300);
  const split = await page.evaluate(() => {
    const g = (r) => document.querySelector(`[data-role="${r}"]`)?.textContent?.replace(/\s+/g, " ").trim() || "";
    return { rei: g("split-reinvest"), liq: g("split-liquidity") };
  });
  const last = previews[previews.length - 1] || {};
  say(disabledWhileWaiting && /7 سهم/.test(split.rei) && /365 سهم/.test(split.liq) && /446\.60/.test(split.rei),
      `${label}: التقسيمُ بسعر التنفيذ (63.8) يظهر قبل التأكيد — 7 من إعادة الاستثمار و365 من السيولة، والتأكيدُ معطَّلٌ حتى يصل`,
      `${split.rei} | ${split.liq} | معطّل أثناء الانتظار: ${disabledWhileWaiting}`);
  say(last.q === 372 && last.px === 63.8 && previews.length <= 3, `${label}: المعاينةُ تُطلب بعد توقّف الكتابة — لا طلبٌ لكلّ حرف`, `${previews.length} طلب`);
  if (SHOTS) await modal.screenshot({ path: join(SHOTS, `funding_${vp.width}.png`) }).catch(() => {});
  slow = 0;
  const before409 = previews.length;
  await confirm.click();
  await page.waitForTimeout(900);
  const errTxt = await modal.textContent().catch(() => "");
  say(posts.length === 1 && posts[0].funding_source === "AUTO" && posts[0].expect_reinvest_qty === 7 && posts[0].shares === 372
      && posts[0].price_per_share === 63.8 && /لم يُحفظ شيء/.test(errTxt || "") && previews.length > before409,
      `${label}: يُرسَل «AUTO» والعددُ المعروضُ نفسُه (7)؛ ورفضُ 409 يُقال ويُعيد المعاينة`, JSON.stringify(posts[0] || {}));
  await confirm.click();
  await page.waitForTimeout(800);
  say(posts.length === 2 && posts[1].expect_reinvest_qty === 7, `${label}: والتأكيدُ الثاني بعد المعاينة الجديدة يُحفظ`);
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
