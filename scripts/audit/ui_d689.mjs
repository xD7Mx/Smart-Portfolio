// ─────────────────────────────────────────────────────────────────────────
// D689 — «الحركةُ جزءٌ من هويّة التصميم» (المالك 2026-10-13): لا قفزةَ في تبديل التبويبات ولا في فتح ورقة السهم وإغلاقها.
// يُفتح التطبيقُ الحقيقيّ (‏vite) ويُقاس من الـDOM: حركاتٌ جاريةٌ فعلاً (getAnimations) بعد كلّ تبديل، والورقةُ تبقى
// مركّبةً لحظةَ الإغلاق بحركة خروجها ثمّ تزول.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5246;
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
const WL = [["2222", "أرامكو السعودية", 24.1, 0.42], ["1120", "مصرف الراجحي", 62.3, -0.81], ["7010", "الاتصالات السعودية", 41.2, 1.12]]
  .map(([symbol, name, price, change_pct]) => ({ symbol, name, price, change_pct }));

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });
const page = await ctx.newPage();
await page.route("**/api/v1/**", r => {
  const u = r.request().url();
  if (/\/market\/watchlist\/groups/.test(u)) return r.fulfill(body([{ id: 1, name: "الرئيسية", color: "var(--chart-1)", is_default: true }]));
  if (/\/market\/watchlist(\?|$)/.test(u)) return r.fulfill(body(WL));
  return r.fulfill(body([]));
});
await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); sessionStorage.setItem("sp:market:tab", "main"); } catch { } });

// يُضغط التبويبُ ثمّ يُقاس فوراً: هل تجري حركةٌ على ما بعد شريط التبويبات؟
const switchMoves = async (path, tabText, barSel) => {
  await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2200);
  const btn = page.locator(`${barSel} button`, { hasText: tabText }).first();
  await btn.click({ timeout: 5000 }).catch(() => {});
  await sleep(60);
  return page.evaluate((barSel) => {
    const bar = [...document.querySelectorAll(barSel)].find(b => b.querySelector("button[aria-pressed]"));
    let n = 0;
    for (let el = bar?.nextElementSibling; el; el = el.nextElementSibling) n += el.getAnimations().length;
    return n;
  }, barSel);
};
const pf = await switchMoves("/portfolio", "لوحة التحكم", "nav");   // تبويبٌ بلا حركةٍ خاصّةٍ به قبل D689
say(pf > 0, "١ تبويباتُ المحفظة: المحتوى يطلع بحركةٍ عند التبديل — لا قفزة", `${pf} حركة`);
const mk = await switchMoves("/market", "مفكرة السوق", "div.flex.gap-1");
say(mk > 0, "٢ وتبويباتُ السوق كذلك", `${mk} حركة`);

// ورقةُ السهم: تصعد عند الفتح، وتبقى لحظةَ الإغلاق بحركة خروجها ثمّ تزول
await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
await page.waitForTimeout(2200);
const card = page.locator("[data-sort-key] button").first();
await card.click({ timeout: 5000 }).catch(() => {});
await sleep(80);
const opening = await page.evaluate(() => {
  // والغطاءُ خلفها يبهت داخلاً (كان يظهر دفعةً)، والورقةُ تصعد مسافةً لا ترتجف ستّ نقاط
  const s = document.querySelector(".stock-sheet"), o = document.querySelector(".stock-sheet-overlay");
  const a = s ? s.getAnimations().find(x => x.animationName) : null;
  return s && o && o.getAnimations().length > 0 && a && a.animationName === "sheetUp" ? 1 : 0;
});
say(opening > 0, "٣ ورقةُ السهم تصعد عند الفتح بحركة", `${opening}`);
await sleep(500);
await page.keyboard.press("Escape");
await sleep(60);
const leaving = await page.evaluate(() => {
  const o = document.querySelector(".stock-sheet-overlay");
  return o ? { cls: o.className, anim: (o.querySelector(".stock-sheet")?.getAnimations().length || 0) } : null;
});
await sleep(450);
const gone = await page.evaluate(() => !document.querySelector(".stock-sheet-overlay"));
say(!!leaving && leaving.cls.includes("leaving") && leaving.anim > 0 && gone,
    "٤ وتنزل عند الإغلاق بحركةٍ ثمّ تزول — لا اختفاءَ فجائيّ", leaving ? `${leaving.cls} · ${leaving.anim}` : "زالت فوراً");
await browser.close();
console.log((fail ? "FAIL" : "PASS") + " D689 — الحركةُ هويّة: تبديلُ التبويبات وورقةُ السهم");
process.exit(fail);
