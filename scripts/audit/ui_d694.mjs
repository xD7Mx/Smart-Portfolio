// ─────────────────────────────────────────────────────────────────────────
// D694 (بأمر المالك 2026-10-13): «استبدل الحوكمةَ مكانَ مختبر الأبحاث داخل المحفظة، ثمّ انقل مختبرَ الأبحاث تبويباً داخل
// تحليل الذكاء». يُفتح التطبيقُ الحقيقيّ (‏vite) على الجوال والحاسوب ويُقاس من الـDOM: ترتيبُ التبويبات، والروابطُ القديمة،
// والقائمةُ الجانبية، والحركةُ عند التبديل، ولا فيضَ أفقيّ.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5249;
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

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp, mobile] of [["الجوال", { width: 390, height: 844 }, true], ["الحاسوب", { width: 1280, height: 900 }, false]]) {
  const ctx = await browser.newContext({ viewport: vp, isMobile: mobile, hasTouch: mobile });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  await page.route("**/api/v1/**", r => r.fulfill(body([])));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); } catch { } });
  const go = async (path, wait = 2200) => {
    await page.goto(`http://localhost:${PORT}${path}`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(wait);
  };
  const tabs = () => page.evaluate(() => [...document.querySelectorAll("nav button[aria-pressed]")]
    .map(b => ({ t: b.textContent.trim(), on: b.getAttribute("aria-pressed") === "true" })));
  const overflow = () => page.evaluate(() => {
    const W = document.documentElement.clientWidth, m = document.querySelector(".app-main");
    return Math.max(document.documentElement.scrollWidth, m ? m.scrollWidth : 0) - W;
  });

  // ١ · المحفظة: «الحوكمة» في موضع «المختبر» (الثالث) — ولا «مختبر»
  await go("/portfolio");
  const pt = (await tabs()).map(x => x.t);
  say(pt[2] === "الحوكمة" && !pt.includes("المختبر"), `${label}: تبويبُ «الحوكمة» في المحفظة مكانَ «المختبر» — لا مختبرَ فيها`, pt.join(" · "));

  // ٢ · الرابطُ القديم /governance يفتح تبويبَها، ومحتواها حاضرٌ بلا عنوانٍ كبيرٍ مكرَّر، والقائمةُ بلا بندٍ لها
  await go("/governance");
  const gv = await page.evaluate(() => ({
    url: location.pathname + location.search,
    h1: [...document.querySelectorAll("h1")].some(h => h.textContent.trim() === "الحوكمة"),
    seg: [...document.querySelectorAll(".seg-btn")].map(b => b.textContent.trim()).join("|"),
    navLink: !!document.querySelector('a[href="/governance"]'),
  }));
  const gtab = (await tabs()).find(x => x.t === "الحوكمة");
  say(gv.url === "/portfolio?tab=governance" && gtab?.on && gv.seg.includes("محفظتي") && gv.seg.includes("السوق") && !gv.h1,
      `${label}: /governance يفتح تبويبَ الحوكمة في المحفظة بمبدّلها «محفظتي · السوق» — بلا عنوانٍ كبيرٍ مكرَّر`, `${gv.url} · ${gv.seg}`);
  say(!gv.navLink, `${label}: ولا بندَ «الحوكمة» في القائمة الجانبية — هي في المحفظة`);
  say((await overflow()) <= 1, `${label}: الحوكمةُ في المحفظة بلا فيضٍ أفقيّ`);

  // ٣ · تحليلُ الذكاء: تبويبان «التحليل · المختبر»، والتبديلُ بحركةٍ لا قفزة، والمختبرُ يحمل رابطَه
  await go("/ai");
  const at = await tabs();
  say(at.map(x => x.t).join("|").includes("التحليل|المختبر") && at.find(x => x.t === "التحليل")?.on,
      `${label}: تحليلُ الذكاء يفتح على «التحليل» وبجانبه «المختبر»`, at.map(x => x.t).join(" · "));
  await page.locator("nav button", { hasText: "المختبر" }).first().click({ timeout: 5000 }).catch(() => {});
  await sleep(60);
  const moving = await page.evaluate(() => {
    const nav = [...document.querySelectorAll("nav")].find(n => [...n.querySelectorAll("button")].some(b => b.textContent.trim() === "المختبر"));
    let n = 0;
    for (let el = nav?.nextElementSibling; el; el = el.nextElementSibling) n += el.getAnimations({ subtree: true }).length;
    return n;
  });
  await page.waitForTimeout(1500);
  const lab = await page.evaluate(() => ({ url: location.pathname + location.search, title: document.body.textContent.includes("مختبر الأبحاث") }));
  say(lab.url === "/ai?tab=lab" && lab.title && moving > 0, `${label}: «المختبر» يفتح مختبرَ الأبحاث بحركةٍ ويحمل رابطَه`, `${lab.url} · ${moving} حركة`);
  say((await overflow()) <= 1, `${label}: المختبرُ في تحليل الذكاء بلا فيضٍ أفقيّ`);

  // ٤ · الروابطُ القديمة للمختبر تصل مكانَه الجديد
  for (const old of ["/stars", "/portfolio?tab=lab"]) {
    await go(old, 2600);
    const u = await page.evaluate(() => location.pathname + location.search);
    const on = (await tabs()).find(x => x.t === "المختبر")?.on;
    say(u === "/ai?tab=lab" && on, `${label}: الرابطُ القديم ${old} يفتح المختبرَ في تحليل الذكاء`, u);
  }
  say(errs.length === 0, `${label}: لا خطأَ في الصفحات`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
