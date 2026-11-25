// ─────────────────────────────────────────────────────────────────────────
// D815 · D817 — ورقةُ التقرير اليوميّ كما أمر المالك (2026-11-24):
//  ‏D815 «التقريرُ اليوميّ على الجوال يجب أن يظهر كما يظهر على الكمبيوتر» — كانت الورقةُ تلتفّ عموداً واحداً تحت 820px.
//  ‏D817 (صورتا ملفّ 24/11): «العنوانُ في أعلى الصفحة مكانُه الصحيحُ تحليلُ السوق، وبدايةُ الصفحة بالأخبار — وتكرّر في محفظتنا مع أنّه
//        يخصّ السوق»، و«العملاتُ المشفّرة قلّلها — المهمّاتُ الرئيسية فقط»، و«إجراءاتُ الشركات السعودية لها نصيبُ الأسد وتأخذ مساحتَها
//        بعدم الاقتطاع»؛ ثمّ ‏D822: «لم أطلب سوى المساحة الكافية لا إعادةَ تصميمه» — فجدولٌ كأقرانه بلا اقتطاع.
// الورقةُ تُكتب من الخادم نفسِه (‏research_paper.render) بأقصى ما تحمله عادةً — جداولُها بصفوفها وثمانيةَ عشرَ إجراءً (‏research_desk_d816.py).
//    SHOTS=dir node scripts/audit/report_d815.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, readFileSync, mkdtempSync } from "node:fs";
import { spawn, spawnSync } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));

// ═ الورقةُ من الخادم ═
const out = join(mkdtempSync(join(tmpdir(), "sp_d815_")), "paper.html");
const py = spawnSync("python3", [join(ROOT, "scripts/audit/research_desk_d816.py")], { env: { ...process.env, SP_PAPER_OUT: out }, encoding: "utf8", timeout: 240000 });
if (!existsSync(out)) { say(false, "٠ كتابةُ الورقة من الخادم", (py.stderr || py.stdout || "").slice(-300)); process.exit(1); }
const HTML = readFileSync(out, "utf8");

// ═ ساكنٌ على المصدر ═
const rp = readFileSync(join(ROOT, "backend/app/services/research_paper.py"), "utf8");
say(!/XRP-USD/.test(rp) && /"BTC-USD"/.test(rp) && /"ETH-USD"/.test(rp) && /days: int = 7, limit: int = 18/.test(rp) && /"actions": acts\[:18\]/.test(rp),
    "٠ العملاتُ المشفّرةُ الرئيسيةُ وحدها (بتكوين · إيثريوم)، وإجراءاتُ الشركات لأسبوعٍ كما كانت — بلا حدِّ العشرة الذي يقصّها (‏D822)");

const PORT = 5303;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const browser = await chromium.launch({ executablePath: CHROME });

// ═ ١ الورقةُ نفسُها بعرض الحاسوب ═
{
  const page = await browser.newPage({ viewport: { width: 860, height: 1200 } });
  await page.setContent(HTML, { waitUntil: "load" }); await page.waitForTimeout(900);
  const pg = await page.evaluate(() => { if (window.__fit) window.__fit(document); return [...document.querySelectorAll(".page")].map(p => {
    const pb = p.querySelector(".pb"), lim = p.querySelector(".pf").getBoundingClientRect().top;
    let bot = 0; pb.querySelectorAll("*").forEach(c => { const r = c.getBoundingClientRect(); if (r.height) bot = Math.max(bot, r.bottom); });
    return { t: p.querySelector("h1")?.textContent || "", fit: Number(p.getAttribute("data-fit") || 1), over: Math.round(bot - lim),
             first: p.querySelector(".pb .blk h2, .pb h2, .pb .band")?.textContent || "", head: !!p.querySelector(".pb p.headline") }; }); });
  const p1 = pg[0] || {}, p4 = pg[3] || {};
  const lead = await page.evaluate(() => { const a = document.querySelector('[data-k="analysis"]'); const b = a?.querySelector('[data-k="headline"]');
    return { inAna: !!b, first: a?.firstElementChild === b }; });
  say(pg.length === 4 && p1.first.includes("الأخبار المحلية") && !p1.head && lead.inAna && lead.first && !p4.head,
      "١ الصفحةُ الأولى تبدأ بالأخبار المحلية، وعنوانُ اليوم يفتتح «تحليل السوق» — ولا يتكرّر في صفحة «محفظتنا»", JSON.stringify({ p1: p1.first, lead, p4: p4.head }));
  /* ‏D822 (المالك): «غيّرتَ تصميمَ إجراءات الشركات فصار مختلفاً عن أقرانه — أرجِعه كما كان شكلاً ومحتوى، لم أطلب إلّا المساحةَ الكافية» */
  const acts = await page.evaluate(() => {
    const band = [...document.querySelectorAll(".band")].find(b => b.textContent.trim() === "إجراءات الشركات السعودية"); if (!band) return null;
    const tw = band.nextElementSibling, rows = [...tw.querySelectorAll("tbody tr")], lim = band.closest(".page").querySelector(".pf").getBoundingClientRect().top;
    const fxb = [...document.querySelectorAll(".band")].find(b => /العملات والعملات المشفّرة/.test(b.textContent)), fxt = fxb?.nextElementSibling;
    return { n: rows.length, cut: rows.filter(r => r.getBoundingClientRect().bottom > lim).length, head: [...tw.querySelectorAll("th")].map(x => x.textContent).join(),
             same: tw.className === fxt?.className && tw.querySelector("table")?.className === fxt?.querySelector("table")?.className,
             afterFx: band.previousElementSibling === fxt, old: !!document.querySelector(".acts, .act, .acts-grid, [data-k=actions]") }; });
  const fx = await page.evaluate(() => [...document.querySelectorAll("td")].some(td => /ريبل/.test(td.textContent)));
  say(acts && acts.n === 18 && acts.cut === 0 && acts.head === "التاريخ,الشركة,نوع الحدث" && acts.same && acts.afterFx && !acts.old && !fx,
      "٢ ‏D822 إجراءاتُ الشركات السعودية جدولٌ كأقرانه في مكانه تحت العملات — كما كان شكلاً ومحتوى (لا قسمَ بتصميمٍ خاصّ)، وإجراءاتُ الأسبوع كلُّها "
      + "بلا اقتطاع (ثمانيةَ عشرَ هنا)، ولا «ريبل» في العملات", JSON.stringify({ acts, fx }));
  say(pg.every(p => p.over <= 0 && p.fit >= 0.8), "٣ كلُّ صفحةٍ تسع محتواها بأقصى صفوفه — لا شيءَ يُقصّ تحت تذييلها (والتصغيرُ ≥ 0.8)",
      pg.map(p => `${p.t}: ${p.over}px · ${p.fit}`).join(" | "));
  if (process.env.SHOTS) await page.screenshot({ path: join(process.env.SHOTS, "d815_paper.png"), fullPage: true });
  await page.close();
}

// ═ ٢ في التطبيق: الجوالُ كالحاسوب ═
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }
const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const HEAD = { date: "2026-11-25", label: "الأربعاء 25 نوفمبر 2026", headline: "عنوان", close: 11227, pct: 0.62, view: "محايد", picks: 0 };
for (const [label, vp, theme] of [["الحاسوب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_active_portfolio", "1"); sessionStorage.setItem("sp:market:tab", "calendar"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/market/research-desk") return r.fulfill(body({ report: HEAD, dates: [{ date: HEAD.date, label: HEAD.label }], running: { on: false } }));
    if (p === "/market/research-desk/paper") return r.fulfill(body({ html: HTML, date: HEAD.date }));
    if (p === "/portfolios") return r.fulfill(body([{ id: 1, name: "محفظتي", is_archived: false }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.locator('[data-role="ev-report"]').click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(2600);
  const m = await page.evaluate(() => {
    const doc = document.querySelector('[data-role="rl-doc"]'), f = doc?.querySelector("iframe"), d = f?.contentDocument;
    if (!d) return null;
    const pg = d.querySelector(".page"), cols = d.querySelector(".cols");
    const fr = f.getBoundingClientRect(), wr = doc.getBoundingClientRect(), fit = doc.querySelector(".rl-fit");
    return { inner: f.contentWindow.innerWidth, pageW: Math.round(pg.getBoundingClientRect().width), tracks: getComputedStyle(cols).gridTemplateColumns.split(" ").length,
             scale: Number(doc.dataset.scale), vis: Math.round(fr.width), box: Math.round(wr.width), left: Math.round(fr.left - wr.left),
             tail: Math.round(fit.getBoundingClientRect().height - fr.height), over: document.scrollingElement.scrollWidth - innerWidth };
  });
  const phone = vp.width < 820;
  say(!!m && m.inner >= 821 && m.pageW >= 780 && m.tracks === 2 && Math.abs(m.tail) <= 2 && m.over <= 1 && (phone ? m.scale < 1 && Math.abs(m.vis - m.box) <= 3 && m.left >= -1 : m.scale === 1),
      `${label}: ٤ الورقةُ ${phone ? "على الجوال كما على الحاسوب — بعرضها وأعمدتها مصغَّرةً لتسع الشاشة، بلا تمريرٍ أفقيّ ولا فراغٍ تحتها" : "بعرضها كما كانت"}`,
      JSON.stringify(m));
  if (process.env.SHOTS) await page.screenshot({ path: join(process.env.SHOTS, `d815_app_${vp.width}_${theme}.png`) });
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
