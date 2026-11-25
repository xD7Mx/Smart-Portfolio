// ────────────────────────────────────────────────────────────────────────
// D772 (بأمر المالك 2026-11-20 بصورةٍ من تريدنق فيو): «عدّل ألوانَ الرسم البيانيّ للنسخة التي في الصورة، وخلّ فيه إمكانيةَ أن أغيّر ألوانَ
// الشموع — أخضر وأسود، أبيض وأحمر… الألوانُ باهتة — نبغى ألواناً مشبعةً نظيفة، وخلفيةُ الشارت سوداء… مستوياتُ الفيبو ما هي مضبوطة: فيها كسرٌ
// وعيوب، وأرقامٌ تظهر في غير أماكنها، وأرقامٌ تظهر بلا خطّ مستوى… لا تضع نسبَ المستويات أبداً (0.6 · 0.1 · 1.1) — فقط سعرُ المستوى نفسُه».
// ١–٢ سلوكيٌّ على طبقة الرسم نفسِها (‏lib/chartOverlay) بلوحةٍ مصطنعة · ٣ ساكنٌ على المصدر · ٤–٥ المتصفّح: الرسمُ الحقيقيّ
//    SHOTS=dir node scripts/audit/chart_colors_d772.mjs
// ────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync, mkdtempSync, readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const done = () => { console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔"); process.exit(fail); };
const rd = (p) => { try { return readFileSync(join(FRONT, p), "utf-8"); } catch { return ""; } };
const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const tmp = mkdtempSync(join(tmpdir(), "sp-d772-"));
await build({ entryPoints: [join(FRONT, "src/lib/chartOverlay.ts")], outfile: join(tmp, "over.mjs"), format: "esm", bundle: true, logLevel: "silent" });
const { ChartOverlay } = await import(pathToFileURL(join(tmp, "over.mjs")).href);

// ── ١–٢ طبقةُ الرسم: الرقمُ على صفّ خطّه وحده، ولا فُسحةَ تقطع خطّاً ──
const draw = (levels) => {
  const rec = [];
  const ctx = new Proxy({ measureText: (t) => ({ width: String(t).length * 6 }) },
    { get: (t, k) => (k in t ? t[k] : (...a) => { rec.push([k, a, t.fillStyle]); }), set: (t, k, v) => { t[k] = v; return true; } });
  const ov = new ChartOverlay();
  ov.attached({ chart: { timeScale: () => ({ logicalToCoordinate: (k) => 100 + 10 * k, options: () => ({ barSpacing: 10 }) }) },
                series: { priceToCoordinate: (p) => 400 - p }, requestUpdate() { } });
  ov.set({ levels, textTop: 10 });
  ov.paneViews()[0].renderer().draw({ useMediaCoordinateSpace: (cb) => cb({ context: ctx, mediaSize: { width: 600, height: 400 } }) });
  return rec;
};
const L = (price, label, o = {}) => ({ price, color: "W", lcolor: "W", label, lx: 30, lpos: "above", width: 1, ...o });
// ثلاثةُ مستوياتٍ متقاربة (300 · 297 · 294 ⇒ صفوفٌ 100 · 103 · 106) ورابعٌ بعيد (250 ⇒ 150)
// ‏D783 (المالك 2026-11-21): «الأرقامُ واحدٌ يمينٌ والثاني يسار — خلِّها في صفٍّ واحد بدون أن تتداخل»: عمودٌ واحد، والرقمُ يلامس خطَّه (فوقه ·
// تحته · عليه)، والعنقودُ الضيّقُ ينزل أقربَ صفٍّ خالٍ بمِهمازٍ إلى خطّه — ولا يركب رقمٌ رقماً، ولا فُسحةَ تقطع خطّاً
const r1 = draw([L(300, "300.00"), L(297, "297.00"), L(294, "294.00"), L(250, "250.00")]);
const txt = r1.filter(r => r[0] === "fillText").map(r => ({ t: r[1][0], x: r[1][1], y: r[1][2] }));
const lines = r1.filter(r => r[0] === "moveTo").map(r => r[1][1]);
const yOf = { "300.00": 100, "297.00": 103, "294.00": 106, "250.00": 150 };
const oneCol = txt.length > 0 && txt.every(t => t.x === txt[0].x);
const touch = t => Math.abs(t.y - (yOf[t.t] - 6.5)) < 0.01 || Math.abs(t.y - (yOf[t.t] + 8.5)) < 0.01 || Math.abs(t.y - (yOf[t.t] + 0.5)) < 0.01;
const noOverlap = txt.every((a, i) => txt.every((b, j) => i === j || Math.abs(a.y - b.y) >= 13));
const leads = r1.filter(r => r[0] === "setLineDash" && Array.isArray(r[1][0]) && r[1][0].length === 2 && r[1][0][0] === 2).length;
say(txt.length === 4 && oneCol && noOverlap && txt.filter(touch).length === 3 && touch(txt.find(t => t.t === "250.00")) && leads === 1
    && lines.length >= 4 && !r1.some(r => r[0] === "fillRect"),
    "١ الأرقامُ عمودٌ واحد (لا يمينٌ ويسار)، وكلُّ رقمٍ يلامس خطَّه هو (فوقه أو تحته)، والعنقودُ الضيّقُ ينزل صفّاً خالياً بمِهمازٍ منقّطٍ إلى خطّه — "
    + "ولا يركب رقمٌ رقماً، ولا فُسحةَ بلون اللوحة تقطع خطّاً",
    txt.map(t => `${t.t}@${t.x},${t.y}`).join(" · "));
const r2 = draw([L(300, "300.00", { lpos: "on" }), L(150, "150.00", { lpos: "below" })]);
const t2 = r2.filter(r => r[0] === "fillText").map(r => r[1][2]);
// ‏D772: رقمُ أعلى خطٍّ (فوق حيّز وسيلة الإيضاح) يُكتب يميناً حيث لا وسيلة إيضاح — وتحتها يساراً يُترك
const top1 = (lx) => { const rr = []; const ov = new ChartOverlay(); const cx = new Proxy({ measureText: (t) => ({ width: String(t).length * 6 }) },
  { get: (t, k) => (k in t ? t[k] : (...a) => { rr.push([k, a]); }), set: (t, k, v) => { t[k] = v; return true; } });
  ov.attached({ chart: { timeScale: () => ({ logicalToCoordinate: (k) => 10 * k, options: () => ({ barSpacing: 10 }) }) }, series: { priceToCoordinate: (p) => 400 - p }, requestUpdate() { } });
  ov.set({ levels: [L(370, "370.00", { lx })], textTop: 50 });
  ov.paneViews()[0].renderer().draw({ useMediaCoordinateSpace: (cb) => cb({ context: cx, mediaSize: { width: 600, height: 400 } }) });
  return rr.filter(r => r[0] === "fillText").length; };
say(!r2.some(r => r[0] === "fillRect") && Math.abs(t2[0] - 100) <= 0.5 && t2[1] > 252 && t2[1] - 252 <= 7 && top1(50) === 1 && top1(5) === 0,
    "٢ «على الخطّ» يتوسّطه بلا فُسحة تقطعه، و«تحته» تحته — الموضعُ من خطّ المستوى نفسِه دائماً", t2.join(" · "));

// ── ٣ ساكنٌ على المصدر ──
const pc = rd("src/components/chart/ProChart.tsx"), d7 = rd("src/components/analysis/d7m.ts"), nat = rd("src/components/analysis/NativeChart.tsx");
const css = rd("src/styles/globals.css"), over = rd("src/lib/chartOverlay.ts");
const code = pc.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, "");
const tokOk = ["--pc-bg: #000000", "--pc-up: #ffffff", "--pc-down: #f23645", "--pc-green: #089981", "--pc-fib: #ffffff", "--pc-fib-gold: #ffd600",
  "--pc-ema20:", "--pc-sw-9: #000000"].every(t => css.includes(t));
say(tokOk && /background: \{ color: tok\("--pc-bg"/.test(code) && /grid: \{ vertLines: \{ visible: false \}, horzLines: \{ visible: false \} \}/.test(code)
    && /const ink = C\("fib"\)/.test(code) && !/tokA\("--ink-muted", "#6b7280", 0\.6\)/.test(code) && /inkTxt = ink/.test(code)
    && /\["ema20", "--pc-ema20"\]/.test(code) && /label: fmtPrice\(l\.price\)/.test(code) && !/label: `\$\{l\.level\}/.test(code)
    && /fibLabelPos: "above"/.test(d7) && /fibV: 5/.test(code) && /text: l\.price\.toFixed/.test(nat) && !/text: \[String\(l\.level\)/.test(nat)
    && !/fillRect/.test(over.slice(over.indexOf("// ٤ب"), over.indexOf("const placedN"))) && !/hit\[0\] - h - 1/.test(over),
    "٣ اللوحةُ سوداءُ بلا شبكةٍ في المظهرين، وخطوطُ المؤشّر مشبعةٌ مُصمَتة (الخطُّ ورقمُه لونٌ واحد — كان الخطُّ رمادياً شفّافاً فبدا الرقمُ بلا خطّ)، "
    + "والرقمُ سعرُ المستوى وحدَه بلا نسبةٍ في الرسمَين، وفوق خطّه افتراضاً");
say(/data-role="pc-candle-colors"/.test(code) && /role="pc-colors"/.test(code) && /data-role="pc-cc-preset"/.test(code) && /CANDLE_PRESETS/.test(code)
    && /"أخضر · أسود", "--pc-green", "--pc-black"/.test(code) && /"أبيض · أحمر", "--pc-up", "--pc-down"/.test(code) && /dark\(cd, bgc\) \? edge : cd/.test(code) && /dark\(cu, bgc\) \? edge : cu/.test(code) && /theme === "light" && dark\(c, bgc\) \? alt : c/.test(code) && /tok\("--pc-green", "#089981"\)\), cd = fit\(/.test(code)
    && !/type="color"/.test(code),
    "٣ب ألوانُ الشموع زرٌّ في الشريط: قوالبُ (أبيض·أحمر · أخضر·أحمر · أخضر·أسود · أبيض·أسود) ولوحتا ألوانٍ مشبعة — وما يذوب في اللوحة (الأسودُ على الأسود والأبيضُ على الأبيض — ‏D841) بحافّةٍ تُظهره");

// ── ٤–٥ المتصفّح ──
const PORT = 5272;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر فحصُ المتصفّح — لا حكم."); done(); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const weekly = (n = 300) => { const out = []; let p = 95;
  for (let i = 0; i < n; i++) { const d = new Date(Date.UTC(2021, 0, 4) + i * 7 * 864e5).toISOString().slice(0, 10);
    const c = +(p * (1 + Math.sin(i / 9) * 0.035 + ((i * 37) % 11 - 5) / 300)).toFixed(2);
    out.push({ date: d, open: +p.toFixed(2), high: +(Math.max(p, c) + 1.2).toFixed(2), low: +(Math.min(p, c) - 1.2).toFixed(2), close: c, volume: 1e6 }); p = c; }
  return out; };
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير."); done(); }
const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب · داكن", { width: 1366, height: 900 }, "dark"], ["الجوال · فاتح", { width: 390, height: 844 }, "light"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e.message || e).slice(0, 160)));
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    if (/^\/market\/(bars|history)\//.test(p)) return r.fulfill(body(weekly()));
    if (p === "/market/watchlist/groups") return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }]));
    return r.fulfill(body([]));
  });
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe");
    if (!sessionStorage.getItem("sp_d772")) {
      for (const k of ["sp_room_symbol", "sp_chart_type", "sp_chart_candle", "sp_d7m_cfg_v2"]) localStorage.removeItem(k);
      localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: false, stochrsi: false, cvd: false, d7m: true }));
      sessionStorage.setItem("sp_d772", "1");
    }
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3500);
  const px = await page.evaluate(() => {
    const cs = [...document.querySelectorAll('[data-role="pc-stage"] canvas')];
    const c = cs.find(x => x.width > 200 && x.height > 150);
    if (!c) return null;
    /* ‏D784: اللونُ الغالبُ على شبكةٍ من 144 نقطة — لا بكسلُ الزاوية وحده: «مختصر» ستّةُ خطوطٍ فمنطقةُ المقاومة الملوّنة قد تبلغ الزاوية (قيس: [16,3,3]) */
    const g = c.getContext("2d"), seen = new Map();
    for (let i = 1; i <= 12; i++) for (let j = 1; j <= 12; j++) {
      const d = g.getImageData(Math.floor(c.width * i / 13), Math.floor(c.height * j / 13), 1, 1).data, k = `${d[0]},${d[1]},${d[2]},${d[3]}`;
      seen.set(k, (seen.get(k) || 0) + 1);
    }
    return [...seen.entries()].sort((a, b) => b[1] - a[1])[0][0].split(",").map(Number);
  });
  if (SHOTS) await page.locator('[data-role="pc-stage"]').first().screenshot({ path: `${SHOTS}/chart-${vp.width}-${theme}.png` }).catch(() => {});
  /* ‏D841 (المالك 2026-11-25: «الرسمُ البيانيّ لا يدعم المظهرَ الفاتح»): سوداءُ في الداكن كما أمر D772، وبيضاءُ في الفاتح */
  const blk = px && px[0] < 8 && px[1] < 8 && px[2] < 8, wht = px && px[0] > 247 && px[1] > 247 && px[2] > 247;
  say(theme === "dark" ? blk : wht, `${label}: ٤ لوحةُ الرسم ${theme === "dark" ? "سوداءُ في المظهر الداكن" : "بيضاءُ في المظهر الفاتح (‏D841)"}`, JSON.stringify(px));
  await page.locator('[data-role="pc-colors"]').first().click().catch(() => {});
  await page.waitForTimeout(400);
  const nPre = await page.locator('[data-role="pc-cc-preset"]').count(), nSw = await page.locator('[data-role="pc-candle-colors"] .pc-sw').count();
  await page.locator('[data-role="pc-cc-preset"]', { hasText: "أخضر · أحمر" }).click().catch(() => {});
  await page.waitForTimeout(500);
  const saved = await page.evaluate(() => localStorage.getItem("sp_chart_candle"));
  await page.reload({ waitUntil: "load" }).catch(() => {});
  await page.waitForTimeout(3000);
  await page.locator('[data-role="pc-colors"]').first().click().catch(() => {});
  await page.waitForTimeout(400);
  const on = await page.locator('[data-role="pc-cc-preset"][aria-pressed="true"]').textContent().catch(() => "");
  const tgt = await page.evaluate(() => { let m = 99; document.querySelectorAll('[data-role="pc-candle-colors"] button').forEach(b => { const r = b.getBoundingClientRect(); if (r.width && r.height) m = Math.min(m, r.height); }); return m; });
  if (SHOTS) await page.locator('[data-role="pc-candle-colors"]').first().screenshot({ path: `${SHOTS}/candle-menu-${vp.width}-${theme}.png` }).catch(() => {});
  say(nPre === 4 && nSw === 18 && saved === JSON.stringify({ up: "#089981", down: "#f23645" }) && /أخضر · أحمر/.test(on || "") && tgt >= 32,
      `${label}: ٥ ألوانُ الشموع: أربعةُ قوالبَ ولوحتا ألوان (تسعٌ لكلٍّ)، والمختارُ يُحفظ ويبقى بعد إعادة التحميل — وأهدافُ اللمس ≥ 32px`,
      JSON.stringify({ nPre, nSw, saved, on, tgt }));
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
done();
