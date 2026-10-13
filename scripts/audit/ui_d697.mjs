// ─────────────────────────────────────────────────────────────────────────
// D697 (بأمر المالك 2026-10-13): «اجعل المستشارَ الآليّ تبويباً ثالثاً بجانب المختبر». كان بطاقةً في آخر «التحليل».
// يُفتح التطبيقُ الحقيقيّ (‏vite) على الجوال والحاسوب ويُقاس من الـDOM: الترتيبُ، والمستشارُ في تبويبه وحدَه، ورابطُه،
// والحركةُ عند التبديل، ولا فيضَ أفقيّ.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5251;
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
  const advisorShown = () => page.evaluate(() => [...document.querySelectorAll("h2")].some(h => h.textContent.trim() === "المستشار الآلي"));

  // ١ · ثلاثةُ تبويبات بالترتيب: التحليل · المختبر · المستشار — والتحليلُ بلا مستشار
  await go("/ai");
  const t1 = (await tabs()).map(x => x.t);
  say(t1.join("|") === "التحليل|المختبر|المستشار", `${label}: تحليلُ الذكاء ثلاثةُ تبويبات — «المستشار» ثالثاً بجانب المختبر`, t1.join(" · "));
  say(!(await advisorShown()), `${label}: «التحليل» بلا مستشار — لا تكرار`);

  // ٢ · «المستشار» يفتحه بحركةٍ ويحمل رابطَه
  await page.locator("nav button", { hasText: "المستشار" }).first().click({ timeout: 5000 }).catch(() => {});
  await sleep(60);
  const moving = await page.evaluate(() => {
    const nav = [...document.querySelectorAll("nav")].find(n => [...n.querySelectorAll("button")].some(b => b.textContent.trim() === "المستشار"));
    let n = 0;
    for (let el = nav?.nextElementSibling; el; el = el.nextElementSibling) n += el.getAnimations({ subtree: true }).length;
    return n;
  });
  await page.waitForTimeout(1200);
  const url = await page.evaluate(() => location.pathname + location.search);
  say(url === "/ai?tab=advisor" && (await advisorShown()) && moving > 0, `${label}: «المستشار» يفتح المستشارَ الآليّ بحركةٍ ويحمل رابطَه`, `${url} · ${moving} حركة`);
  const over = await page.evaluate(() => {
    const W = document.documentElement.clientWidth, m = document.querySelector(".app-main");
    return Math.max(document.documentElement.scrollWidth, m ? m.scrollWidth : 0) - W;
  });
  say(over <= 1, `${label}: المستشارُ في تبويبه بلا فيضٍ أفقيّ`, `${over}px`);

  // ٣ · الرابطُ يفتحه مباشرةً، والمختبرُ في مكانه لا يحمل المستشار
  await go("/ai?tab=advisor");
  say((await tabs()).find(x => x.t === "المستشار")?.on && (await advisorShown()), `${label}: /ai?tab=advisor يفتح المستشارَ مباشرة`);
  await go("/ai?tab=lab");
  say((await tabs()).find(x => x.t === "المختبر")?.on && !(await advisorShown()), `${label}: والمختبرُ في تبويبه بلا مستشار`);
  say(errs.length === 0, `${label}: لا خطأَ في الصفحات`, errs[0] || "");
  await ctx.close();
}
await browser.close();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
