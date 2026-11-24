// ─────────────────────────────────────────────────────────────────────────
// D790 — المالك (2026-11-24): «التكبيرُ لا يعمل بشكلٍ صحيح — فيه أخطاءٌ وبقايا صفحةٍ ظاهرة».
// قِيس: الشاشاتُ المكبَّرة شفّافة — ‏.troom-chart بطاقةٌ، وقاعدةُ «دمج البطاقات» ‏`html.light .card { background: transparent !important }`
// (‏0,2,1) تغلب خلفيةَ التكبير (‏0,2,0) — فيظهر من خلفها شريطُ التطبيق (الجرس والساعة) متداخلاً مع رأس الشاشات، وزرُّ المحادثة،
// وحدُّ القائمة. وارتفاعُها من موضعٍ مخمَّن لأعلى الشبكة (104 وهو ~67) فتنتهي قبل قاع النافذة بـ81–87px، وعمودا الثلاث غيرُ متساويين.
//   ١ لوحةُ التكبير معتمةٌ في المظهرين (‏alpha = 1) — ولا شيءَ خارجها مرسومٌ فوقها.
//   ٢ الشاشاتُ تملأ النافذة على الحاسوب بلا فيضٍ (ثلاثٌ وأربع)، وعمودا الثلاث ينتهيان معاً.
//   ٣ والجوالُ شاشاتٌ متتاليةٌ تُمرَّر داخل اللوحة المعتمة.
//    SHOTS=dir node scripts/audit/troom_wide_d790.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const PORT = 5290;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const pw = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js", "/usr/local/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!pw || !existsSync(CHROME)) { console.log("… تعذّر فحصُ المتصفّح: المتصفّحُ أو playwright غيرُ متاح."); process.exit(fail); }
const _pw = await import(pathToFileURL(pw).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { /* */ } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { /* */ } }
if (!up) { console.log("… تعذّر إقلاعُ خادم التطوير — لا حكم."); stop(); process.exit(fail); }

const body = data => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const SHOTS = process.env.SHOTS;
const bars = (n = 160, base = 90) => Array.from({ length: n }, (_, i) => {
  const t = Math.floor(Date.UTC(2026, 3, 17) / 1000) + i * 86400, w = Math.sin(i / 6) * 3 + i * 0.07;
  const o = base + w, c = o + Math.sin(i / 2) * 0.8;
  return { time: t, open: +o.toFixed(2), high: +(Math.max(o, c) + 0.6).toFixed(2), low: +(Math.min(o, c) - 0.6).toFixed(2), close: +c.toFixed(2), volume: 1e6 };
});

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme, n] of [["الحاسوب · فاتح · ثلاث", { width: 1366, height: 900 }, "light", 3], ["الحاسوب · داكن · أربع", { width: 1440, height: 900 }, "dark", 4],
                                      ["الجوال · فاتح · ثلاث", { width: 390, height: 844 }, "light", 3]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(([n]) => { try {
    if (sessionStorage.getItem("d790-init")) return;
    sessionStorage.setItem("d790-init", "1");
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_room_symbol", "2222.SR"); localStorage.setItem("sp_room_list", "mine");
    localStorage.setItem("sp_room_layout", String(n)); localStorage.removeItem("sp_room_panes");
  } catch { /* */ } }, [n]);
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(history|bars)\//.test(p)) return r.fulfill(body(bars()));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.locator('[data-role="troom-wide"]').first().click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(2200);                                          // حركةُ الظهور ثمّ المعايرة
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `d790_wide_${vp.width}_${theme}_${n}.png`) }).catch(() => {});
  const m = await page.evaluate(() => {
    const panel = document.querySelector('[data-role="troom-chart"]');
    if (!panel || panel.dataset.wide !== "1") return null;
    const bg = getComputedStyle(panel).backgroundColor;
    const a = (bg.match(/rgba?\(([^)]+)\)/)?.[1] || "").split(/[,\s/]+/).filter(Boolean).map(Number);
    const alpha = a.length > 3 ? a[3] : (a.length ? 1 : 0);
    // ما خارج اللوحة مرسومٌ فوقها: عنصرٌ ثابتٌ أو لاصقٌ بطبقةٍ أعلى يتقاطع معها
    const pz = Number(getComputedStyle(panel).zIndex) || 0;
    const over = [...document.querySelectorAll("body *")].filter(e => {
      if (panel.contains(e) || e.contains(panel)) return false;
      const cs = getComputedStyle(e); if (cs.position !== "fixed" && cs.position !== "sticky") return false;
      const z = Number(cs.zIndex); if (!(z > pz)) return false;
      const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
    }).map(e => e.className && String(e.className).slice(0, 40));
    const ps = [...panel.querySelectorAll('[data-role="troom-pane"]')];
    const bottoms = ps.map(p => { let t = 0; for (let e = p; e && e !== panel; e = e.offsetParent) t += e.offsetTop; return t + p.offsetHeight; });
    return { alpha, over, H: panel.clientHeight, sh: panel.scrollHeight, bottoms, n: ps.length };
  });
  if (!m) { say(false, `${label}: لوحةُ التكبير لم تُفتح`); await ctx.close(); continue; }
  say(m.alpha === 1 && m.over.length === 0,
      `${label}: ١ لوحةُ التكبير معتمةٌ (لا يظهر من خلفها شريطُ التطبيق ولا زرُّ المحادثة) ولا شيءَ خارجها فوقها`, JSON.stringify({ alpha: m.alpha, over: m.over }));
  if (desk) {
    const last = Math.max(...m.bottoms);
    const cols = n === 3 ? Math.abs(m.bottoms[0] - m.bottoms[2]) : 0;
    say(Math.abs(m.H - last) <= 3 && m.sh <= m.H + 1 && cols <= 3,
        `${label}: ٢ الشاشاتُ تملأ النافذة إلى قاعها بلا فيض${n === 3 ? "، وعمودا الثلاث ينتهيان معاً" : ""}`,
        JSON.stringify({ H: m.H, bottoms: m.bottoms, scroll: m.sh }));
  } else {
    say(m.n === n && m.sh > m.H, `${label}: ٣ الجوالُ شاشاتٌ متتاليةٌ تُمرَّر داخل اللوحة المعتمة`, JSON.stringify({ n: m.n, H: m.H, scroll: m.sh }));
  }
  say(errs.length === 0, `${label}: لا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
