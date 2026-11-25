// ─────────────────────────────────────────────────────────────────────────
// D823 · D824 — ملاحظتا المالك (2026-11-24):
//  ‏D830 «تحذيرُ كروم عند التنزيل»: الملفُّ يُفتح في قارئ المتصفّح برابطٍ موقَّع (العرضُ ليس تنزيلاً).
//  ‏D823 «أنيميشنُ زرّ حفظ التقرير لم يعجبني — لا أريده أن يدور، خلِّ السهمَ ينزل للأسفل أو أنيميشناً أجملَ وأكثرَ احترافية».
//  ‏D824 «عند تحليل الرسم والضغطِ عليه سطرُ الكلام وعدّادُ الثواني مكسّران وليسا مرتّبين» — كان العدّادُ بصنف «cr-sec» الذي تحمله أقسامُ
//        التحليل نفسُها (عمودٌ مرن) فينكسر سطرُه.
//  ١ زرُّ PDF وقتَ الإعداد: سهمُ الأيقونة يهبط (لا شيءَ يدور)، والزرُّ بلونه كاملاً (يعمل لا معطّل)، ثمّ علامةُ تمامٍ لحظةً — ويسكن مع تقليل الحركة.
//  ٢ انتظارُ تحليل الرسم: النصُّ يميناً والعدّادُ شارةٌ يساراً في صفٍّ واحدٍ لا ينكسر، والعدّادُ يعدّ ولا يتراقص عرضُه — في الشاشتين.
//    node scripts/audit/ui_d823_d824.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5323;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّحُ أو playwright غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
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
const PAPER = '<!doctype html><html dir="rtl"><body><div class="page"><div class="pb"><p>ورقة</p></div><div class="pf">1</div></div></body></html>';
const bars = (n = 160) => Array.from({ length: n }, (_, i) => { const day = new Date(Date.UTC(2026, 3, 1) + i * 864e5).toISOString().slice(0, 10), b = 30 + i * 0.05;
  return { date: day, open: b, high: b + 0.4, low: b - 0.4, close: b + 0.1, volume: 1e6 }; });
const READING = { ok: true, at: "2026-11-25T10:00:00", reading: { bias: "صاعد", headline: "المسارُ صاعدٌ فوق المتوسّطات.", frames: [], levels: [], indicators: [] } };

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, reduce] of [["الحاسوب", { width: 1366, height: 900 }, false], ["الجوال", { width: 390, height: 844 }, false], ["تقليلُ الحركة", { width: 1366, height: 900 }, true]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, reducedMotion: reduce ? "reduce" : "no-preference", acceptDownloads: true });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_active_portfolio", "1"); localStorage.setItem("sp_room_symbol", "2222.SR");
    localStorage.setItem("sp_room_layout", "1"); sessionStorage.setItem("sp:market:tab", "calendar"); } catch { /* */ } });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (p === "/market/research-desk") return r.fulfill(body({ report: HEAD, dates: [{ date: HEAD.date, label: HEAD.label }], running: { on: false } }));
    if (p === "/market/research-desk/paper") return r.fulfill(body({ html: PAPER, date: HEAD.date }));
    if (p === "/market/research-desk/pdf") { await sleep(2200); return r.fulfill({ status: 200, contentType: "application/pdf", body: Buffer.from("%PDF-1.4\n%%EOF") }); }
    /* ‏D830: الملفُّ يُفتح في قارئ المتصفّح برابطٍ موقَّع — العرضُ ليس تنزيلاً فلا يحذّر كروم */
    if (p === "/market/research-desk/pdf-link") { await sleep(2200); return r.fulfill(body({ path: "/market/research-desk/pdf-view?k=1&day=2026-11-25&mo=0&exp=9999999999&sig=t", date: HEAD.date })); }
    if (p === "/market/research-desk/pdf-view") return r.fulfill({ status: 200, contentType: "application/pdf", headers: { "Content-Disposition": 'inline; filename="daily-report-2026-11-25.pdf"' }, body: Buffer.from("%PDF-1.4\n%%EOF") });
    if (p === "/market/chart-read") { await sleep(3300); return r.fulfill(body(READING)); }
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p === "/portfolios") return r.fulfill(body([{ id: 1, name: "محفظتي", is_archived: false }]));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });

  // ═ ١ زرُّ PDF ═
  {
    await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(1500);
    await page.locator('[data-role="ev-report"]').click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(1500);
    const btn = page.locator('[data-role="rl-pdf"]');
    const popP = ctx.waitForEvent("page", { timeout: 8000 }).catch(() => null);
    await btn.click().catch(() => {});
    await page.waitForTimeout(500);
    if (process.env.SHOTS && !reduce) await page.locator('[data-role="rl-pdf"]').screenshot({ path: join(process.env.SHOTS, `d823_${vp.width}.png`) }).catch(() => {});
    const busy = await page.evaluate(() => {
      const b = document.querySelector('[data-role="rl-pdf"]'), svg = b?.querySelector('[data-role="rl-dl"]'), arrow = svg?.querySelector(".rl-dl-arrow");
      const spins = [...(b?.querySelectorAll("*") || [])].filter(e => /spin/i.test(getComputedStyle(e).animationName) || e.classList.contains("rl-spin")).length;
      return { aria: b?.getAttribute("aria-busy"), on: svg?.getAttribute("data-busy"), anim: arrow ? getComputedStyle(arrow).animationName : null,
               op: b ? Number(getComputedStyle(b).opacity) : 0, spins };
    });
    await page.waitForTimeout(2300);
    const done = await page.locator('[data-role="rl-pdf-done"]').count();
    await page.waitForTimeout(1900);
    const back = await page.locator('[data-role="rl-pdf"] [data-role="rl-dl"]').count();
    const pop = await popP;
    const view = pop ? pop.url() : "";
    if (pop) await pop.close().catch(() => {});
    const anim = reduce ? busy.anim === "none" : busy.anim === "rlDrop";
    say(busy.aria === "true" && busy.on === "1" && anim && busy.spins === 0 && busy.op === 1 && done === 1 && back === 1 && /\/market\/research-desk\/pdf-view\?k=1&day=2026-11-25/.test(view),
        `${label}: ١ زرُّ PDF وقتَ الإعداد — ${reduce ? "ساكنٌ مع تقليل الحركة" : "سهمُه يهبط إلى الصينية"} ولا شيءَ يدور، والزرُّ بلونه كاملاً، ثمّ علامةُ تمامٍ لحظةً — `
        + "والملفُّ يُفتح في قارئ المتصفّح برابطه الموقَّع (‏D830: العرضُ ليس تنزيلاً فلا يحذّر كروم)",
        JSON.stringify({ ...busy, done, back, view: view.slice(-90) }));
  }

  // ═ ٢ انتظارُ تحليل الرسم ═
  if (!reduce) {
    await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2500);
    await page.locator('[data-role="chart-read-btn"]').first().click({ timeout: 8000 }).catch(() => {});
    await page.waitForTimeout(400);
    const read = () => page.evaluate(() => {
      const row = document.querySelector('[data-role="chart-read-wait"] .cr-wait-row'), t = row?.querySelector(".cr-wait-t"), c = document.querySelector('[data-role="chart-read-timer"]');
      if (!row || !t || !c) return null;
      const a = t.getBoundingClientRect(), b = c.getBoundingClientRect(), n = c.querySelector('[data-role="chart-read-sec"]');
      return { sec: Number(n.textContent), mid: Math.abs((a.top + a.bottom) / 2 - (b.top + b.bottom) / 2), textRight: a.left > b.right - 1, rowH: row.getBoundingClientRect().height,
               lines: Math.round(a.height / parseFloat(getComputedStyle(t).lineHeight || "18")), w: Math.round(b.width), disp: getComputedStyle(n).display,
               fs: parseFloat(getComputedStyle(c).fontSize) };
    });
    const r1 = await read();
    if (process.env.SHOTS) await page.screenshot({ path: join(process.env.SHOTS, `d824_${vp.width}.png`) });
    await page.waitForTimeout(2100);
    const r2 = await read();
    await page.waitForTimeout(1600);
    const body2 = await page.locator('[data-role="chart-read-body"]').count();
    say(r1 && r2 && r2.sec >= 2 && r2.sec > r1.sec && r1.mid <= 3 && r2.mid <= 3 && r1.textRight && r1.rowH <= 40 && r1.disp !== "flex" && r1.w === r2.w && r1.fs >= 9.5 && body2 === 1,
        `${label}: ٢ انتظارُ تحليل الرسم — النصُّ يميناً والعدّادُ شارةٌ يساراً في صفٍّ واحدٍ لا ينكسر، يعدّ ولا يتراقص عرضُه، ثمّ تظهر القراءة`,
        JSON.stringify({ r1, r2, body2 }));
  }
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
