// ─────────────────────────────────────────────────────────────────────────
// D828 — قارئُ التقرير على الجوال (المالك 2026-11-25): «عرضُ التقرير على الكمبيوتر ممتازٌ ولا غلطة، أمّا على الجوال فيحتاج توحيدَ المقاسات مع
// مراعاة صغر شاشة الجوال — لازم يكون واضحاً على الجوال». كانت الورقةُ (‏A4 بعرض الحاسوب) تُصغَّر إلى عرض الهاتف (‏≈39٪، خطٌّ نحو 4px).
//  ١ على الجوال شارةُ «اقرأ بملء الشاشة» فوق الورقة (ولا شارةَ على الحاسوب)، ولمسُها يفتح القارئَ بالورقة نفسِها بعرض الشاشة.
//  ٢ التكبير: زرٌّ يكبّر، ونقرتان تنقلان إلى مقاس الطباعة (100٪) حيث نُقر وتعيدان، وإصبعان يكبّران — والورقةُ تُسحب في الاتّجاهين.
//  ٣ الإغلاقُ يعيد الصفحة كما كانت، ولا تمريرَ أفقيٌّ للصفحة خلفه، ولا خطأ.
//    node scripts/audit/reader_d828.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync, mkdtempSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5328;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const devices = _pw.devices || _pw.default?.devices;
const out = join(mkdtempSync(join(tmpdir(), "sp_d828_")), "paper.html");
spawnSync("python3", [join(ROOT, "scripts/audit/research_desk_d816.py")], { env: { ...process.env, SP_PAPER_OUT: out }, encoding: "utf8", timeout: 240000 });
if (!existsSync(out)) { console.log("FAIL ٠ كتابةُ الورقة من الخادم"); process.exit(1); }
const PAPER = readFileSync(out, "utf8");
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
const sleep = ms => new Promise(r => setTimeout(r, ms));
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(0); }

let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const HEAD = { date: "2026-11-25", label: "الأربعاء 25 نوفمبر 2026", headline: "عنوان", close: 11227, pct: 0.62, view: "محايد", picks: 0 };
const browser = await chromium.launch({ executablePath: CHROME });
const open = async (ctxOpts) => {
  const ctx = await browser.newContext(ctxOpts);
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_active_portfolio", "1"); sessionStorage.setItem("sp:market:tab", "calendar"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const p = new URL(r.request().url()).pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/market/research-desk") return r.fulfill(body({ report: HEAD, dates: [{ date: HEAD.date, label: HEAD.label }], running: { on: false } }));
    if (p === "/market/research-desk/paper") return r.fulfill(body({ html: PAPER, date: HEAD.date }));
    if (p === "/portfolios") return r.fulfill(body([{ id: 1, name: "محفظتي", is_archived: false }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await sleep(1500);
  await page.locator('[data-role="ev-report"]').click({ timeout: 8000 }).catch(() => {});
  await sleep(2500);
  return { ctx, page, errs };
};
const zOf = async page => Number(await page.locator('[data-role="rl-reader"]').getAttribute("data-z").catch(() => "0"));

// ═ الحاسوب: لا شارة ═
{
  const { ctx, page } = await open({ viewport: { width: 1366, height: 900 }, deviceScaleFactor: 1 });
  const chips = await page.locator('[data-role="rl-read"]').count();
  say(chips === 0, "الحاسوب: الورقةُ بمقاسها كما هي — لا شارةَ قارئ (العرضُ ممتازٌ كما قال المالك)", `شارات ${chips}`);
  await ctx.close();
}

// ═ الجوال ═
{
  const { ctx, page, errs } = await open({ ...devices["iPhone 13"] });
  const chip = page.locator('[data-role="rl-read"]');
  const chipN = await chip.count(), chipTxt = (await chip.textContent().catch(() => "")) || "";
  await chip.tap().catch(() => {});
  await sleep(900);
  const shown = await page.locator('[data-role="rl-reader"]').getAttribute("data-shown").catch(() => null);
  const z0 = await zOf(page), fitZ = Math.min(1, (390 - 12) / 860);
  const fr = await page.evaluate(() => { const f = document.querySelector('[data-role="rl-reader"] iframe'); return f?.contentDocument?.querySelectorAll(".page").length || 0; });
  say(chipN === 1 && /اقرأ بملء الشاشة/.test(chipTxt) && shown === "1" && Math.abs(z0 - fitZ) < 0.01 && fr >= 4,
      "١ الجوال: شارةُ «اقرأ بملء الشاشة» فوق الورقة، ولمسُها يفتح القارئَ بالورقة نفسِها (صفحاتُها كلُّها) بعرض الشاشة", `z ${z0} · صفحات ${fr}`);

  await page.locator('[data-role="rl-zin"]').tap(); await sleep(450);
  const z1 = await zOf(page);
  await page.locator('[data-role="rl-zfit"]').tap(); await sleep(450);
  const zf = await zOf(page);
  const box = await page.locator('[data-role="rl-reader-box"]').boundingBox();
  await page.touchscreen.tap(box.x + box.width * 0.7, box.y + 220); await sleep(100); await page.touchscreen.tap(box.x + box.width * 0.7, box.y + 220); await sleep(600);
  const z2 = await zOf(page);
  const pan = await page.evaluate(() => { const b = document.querySelector('[data-role="rl-reader-box"]'); return { sw: b.scrollWidth, cw: b.clientWidth, sl: b.scrollLeft }; });
  await page.touchscreen.tap(box.x + box.width * 0.5, box.y + 220); await sleep(100); await page.touchscreen.tap(box.x + box.width * 0.5, box.y + 220); await sleep(600);
  const z3 = await zOf(page);
  const s = await ctx.newCDPSession(page);
  const cx = box.x + box.width / 2, cy = box.y + 320, tp = d => [{ x: cx - d, y: cy }, { x: cx + d, y: cy }];
  await s.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: tp(40) });
  for (let i = 1; i <= 6; i++) { await s.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: tp(40 + i * 18) }); await sleep(30); }
  await s.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] }); await sleep(300);
  const z4 = await zOf(page);
  const pct = await page.locator('[data-role="rl-zpct"]').textContent();
  say(z1 > z0 + 0.1 && Math.abs(zf - fitZ) < 0.01 && Math.abs(z2 - 1) < 0.01 && pan.sw > pan.cw * 1.5 && Math.abs(z3 - fitZ) < 0.01 && z4 > fitZ * 1.5
      && pct === `${Math.round(z4 * 100)}%`,
      "٢ التكبير: الزرُّ يكبّر ويعيد بعرض الشاشة، والنقرتان تنقلان إلى مقاس الطباعة (100٪) حيث نُقر وتعيدان، والإصبعان يكبّران — والورقةُ تُسحب في الاتّجاهين",
      JSON.stringify({ z0: +z0.toFixed(3), زر: +z1.toFixed(3), نقرتان: z2, رجوع: +z3.toFixed(3), إصبعان: +z4.toFixed(3), pct }));

  await page.locator('[data-role="rl-reader-close"]').tap(); await sleep(500);
  const gone = await page.locator('[data-role="rl-reader"]').count();
  const over = await page.evaluate(() => document.scrollingElement.scrollWidth - innerWidth);
  const ovf = await page.evaluate(() => document.body.style.overflow);
  say(gone === 0 && over <= 1 && ovf === "" && errs.length === 0, "٣ الإغلاقُ يعيد الصفحةَ كما كانت (تمريرُها عائد)، بلا تمريرٍ أفقيّ ولا خطأ", errs[0] || `تجاوز ${over}`);
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
