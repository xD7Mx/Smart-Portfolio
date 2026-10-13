// ─────────────────────────────────────────────────────────────────────────
// D683 · D684 — ملاحظاتُ المالك (2026-10-11) تُقاس في المتصفّح على الجوال (390) والحاسوب (1280):
//   «المراقبة غيّر اسمها إلى الشاشة، واجعل البطاقات قابلةً للتحريك بلا أزرار — ضغطٌ مطوّل ثمّ تحريك — واجعل حكمَ القرار
//    على الجوال أسفلَ منتصف نسبة التغيّر، وثلاثُ أعمدةٍ بنفس المحتوى» · «وبطاقاتُ فرز السوق بهويّة التطبيق: اللي فوق مشابهٌ
//    للي تحت، ولا شذوذَ نصّيّ ولا تشتّت».
// يُفتح التطبيقُ الحقيقيّ (‏vite) ويُقاس من الـDOM: مواضعُ الخانات، ثمّ السحبُ نفسُه بالفأرة وباللمس (‏CDP).
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdirSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5243;
const CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
const PW = [join(FRONT, "node_modules", "playwright", "index.js"),
  "/opt/node22/lib/node_modules/playwright/index.js",
  "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !existsSync(CHROME)) { console.log("… تعذّر الفحص: المتصفّح غيرُ متاح."); process.exit(0); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const SHOTS = process.env.SP_SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });

let fail = 0;
const say = (ok, label, detail = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`); };
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const WL = [["2222", "أرامكو السعودية", 24.1, 0.42], ["1120", "مصرف الراجحي", 62.3, -0.81], ["7010", "الاتصالات السعودية", 41.2, 1.12],
  ["2280", "المراعي", 44.44, 0], ["4190", "جرير للتسويق", 13.9, -0.3], ["1150", "مصرف الإنماء", 26.5, 0.6],
  ["4013", "د. سليمان الحبيب للخدمات الطبية", 268, 1.4], ["2010", "سابك", 1234.5, -2.15]]
  .map(([symbol, name, price, change_pct]) => ({ symbol, name, price, change_pct }));
const DEC = ["شراء", "انتظار", "احتفاظ", "تجنب", "شراء قوي", "انتظار", "شراء", null];
const ROWS = WL.map((w, i) => ({ symbol: `${w.symbol}.SR`, name: w.name, sector: ["الطاقة", "البنوك", "الاتصالات", "إنتاج الأغذية", "تجزئة وتوزيع السلع الكمالية", "البنوك", "الرعاية الصحية", "المواد الأساسية"][i],
  sharia: i === 1 ? "NON_COMPLIANT" : "COMPLIANT", price: w.price, change_pct: w.change_pct,
  dist_sma50: [2.1, -3.4, 5.6, null, -1.2, 0.4, 8.9, -12.3][i], dist_sma200: [-4.2, 6.1, 12.4, -0.5, null, 3.3, 15.2, -20.1][i], rsi: [48, 31, 67, 55, null, 44, 72, 24][i],
  fair_value: i === 7 ? null : +(w.price * (1 + (i - 3) / 20)).toFixed(2), fair_value_upside_pct: i === 7 ? null : (i - 3) * 5, upside_pct: (i - 3) * 5,
  finance_score: [78, 85, 64, null, 52, 81, 90, 33][i], stmt_asof: "2026-06-30", stmt_age_days: [100, 100, 100, 100, 250, 100, 100, 100][i],
  verdict: ["cheap", "fair", "expensive", "loss", "insufficient", "cheap", "fair", null][i], value_gap_pct: [12, 1, -8, null, null, 9, -2, null][i],
  dividend_yield: [5.2, 3.1, 4.4, null, 6.8, 2.9, 1.2, null][i], macd_cross: [null, "up", null, "down", null, null, "up", null][i], decision: DEC[i] }));

const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
const stop = () => { try { vite.kill("SIGKILL"); } catch { } };
process.on("exit", stop);
let up = false;
for (let i = 0; i < 60 && !up; i++) { await sleep(500); try { up = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!up) { console.log("… لم يقلع خادمُ التطوير — لا حكم."); process.exit(0); }
const browser = await chromium.launch({ executablePath: CHROME });

for (const [label, vp] of [["الجوال", { width: 390, height: 844, isMobile: true, hasTouch: true }], ["الحاسوب", { width: 1280, height: 900 }]]) {
  const mob = !!vp.isMobile;
  const ctx = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: mob, hasTouch: mob, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  let wl = WL.map(x => ({ ...x }));
  const orders = [];
  await page.route("**/api/v1/**", r => {
    const u = r.request().url(), m = r.request().method();
    if (/\/market\/watchlist\/order/.test(u) && m === "PUT") {
      const syms = JSON.parse(r.request().postData() || "{}").symbols || [];
      orders.push(syms);
      wl = syms.map(s => wl.find(x => x.symbol === s)).filter(Boolean);
      return r.fulfill(body(syms));
    }
    if (/\/market\/watchlist\/groups/.test(u)) return r.fulfill(body([{ id: 1, name: "الرئيسية", color: "var(--chart-1)", is_default: true }]));
    if (/\/market\/watchlist(\?|$)/.test(u)) return r.fulfill(body(wl));
    if (/\/market\/screener/.test(u)) return r.fulfill(body({ rows: ROWS, state: "ready" }));
    return r.fulfill(body([]));
  });
  await page.addInitScript(() => { try { localStorage.setItem("sp_token", "probe"); sessionStorage.setItem("sp:market:tab", "screener"); } catch { } });

  // ═══ ١ · «الشاشة» ═══
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(2500);
  const g = await page.evaluate(() => {
    const W = document.documentElement.clientWidth;
    const main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const cards = [...document.querySelectorAll("[data-sort-key]")];
    const tops = cards.map(c => Math.round(c.getBoundingClientRect().top));
    const perRow = tops.filter(t => t === tops[0]).length;
    const off = [], clip = [], tall = [], rowMis = [];
    const byRow = {};
    for (const c of cards) {
      const k = c.dataset.sortKey;
      const chg = c.querySelector('[data-role="chg"]'), dec = c.querySelector('[data-role="dec"]');
      const price = c.querySelector('[data-role="price"]'), name = c.querySelector('[data-role="name"]');
      if (chg && dec) {
        const a = chg.getBoundingClientRect(), b = dec.getBoundingClientRect();
        const d = Math.abs((a.left + a.width / 2) - (b.left + b.width / 2));
        if (d > 1.5 || b.top <= a.bottom) off.push(`${k}:${d.toFixed(1)}`);
      }
      if (price && price.scrollWidth > price.clientWidth + 0.5) clip.push(k);
      if (name) { const lh = parseFloat(getComputedStyle(name).lineHeight) || 15; if (name.getBoundingClientRect().height > 2 * lh + 2) tall.push(k); }
      const t = Math.round(c.getBoundingClientRect().top);
      (byRow[t] ||= []).push(Math.round(price.getBoundingClientRect().top));
    }
    for (const [t, ps] of Object.entries(byRow)) if (Math.max(...ps) - Math.min(...ps) > 1) rowMis.push(t);
    const h1 = [...document.querySelectorAll("h1")].some(h => h.textContent.trim() === "غرفة التداول");   // ‏D687
    const navTxt = [...document.querySelectorAll('a[href="/watchlist"]')].map(a => a.textContent + " " + (a.getAttribute("title") || "") + " " + (a.getAttribute("aria-label") || "")).join(" ");
    const visible = document.body.innerText;
    return { W, sw, n: cards.length, perRow, off, clip, tall, rowMis, h1, nav: navTxt.includes("المراقبة") ? "قديم" : "ok", old: visible.includes("المراقبة"),
             btns: cards.some(c => [...c.querySelectorAll("button")].some(b => /تحريك|نقل|أعلى|أسفل/.test(b.getAttribute("aria-label") || ""))) };
  });
  say(g.h1 && !g.old && g.nav === "ok", `${label}: «غرفة التداول» اسمُ القسم (‏D687) — لا «المراقبة» في عنوانٍ ولا قائمةٍ ولا نصّ`);
  say(g.n === 8 && g.perRow === (mob ? 3 : 4), `${label}: ${mob ? "ثلاثُ" : "أربعُ"} بطاقاتٍ في الصفّ (‏D685)`, `${g.n} بطاقات · ${g.perRow} في الصفّ`);
  say(g.off.length === 0, `${label}: القرارُ تحت منتصف نسبة التغيّر في كلّ بطاقة (فرقُ المركزين ≤ 1.5px)`, g.off.join(" ") || "8/8");
  say(g.clip.length === 0 && g.tall.length === 0, `${label}: السعرُ كاملٌ لا مقصوص، والاسمُ سطران على الأكثر`, [...g.clip, ...g.tall].join(" "));
  say(g.rowMis.length === 0, `${label}: الخاناتُ تصطفّ بين بطاقات الصفّ الواحد (السعرُ على خطٍّ واحد)`);
  say(g.sw <= g.W + 1 && !g.btns, `${label}: لا فيضَ أفقيّ، ولا زرَّ تحريكٍ ظاهر`, `محتوى ${g.sw} · شاشة ${g.W}`);
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `screen_${vp.width}.png`), fullPage: true });

  const keys = () => page.evaluate(() => [...document.querySelectorAll("[data-sort-key]")].map(c => c.dataset.sortKey));
  const center = (i) => page.evaluate((i) => { const r = document.querySelectorAll("[data-sort-key]")[i].getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; }, i);
  const sheetOpen = () => page.evaluate(() => !!document.querySelector(".stock-sheet-overlay"));

  // ═══ ٢ · الترتيبُ بالضغط المطوّل ثمّ السحب ═══
  const k0 = await keys();
  if (!mob) {
    const a = await center(0), b = await center(2);
    await page.mouse.move(a.x, a.y); await page.mouse.down(); await sleep(650);
    for (let s = 1; s <= 10; s++) await page.mouse.move(a.x + (b.x - a.x) * s / 10, a.y + (b.y - a.y) * s / 10);
    await sleep(250);
    // ‏D687: البطاقةُ المرفوعة تحت الإصبع نفسِه (لا تقفز بين الخانات) — مركزُها عند المؤشّر، ثمّ تهبط بانزلاق
    const mid = await page.evaluate(({ x, y }) => {
      const el = [...document.querySelectorAll("[data-sort-key]")].find(e => (e.style.transform || "").includes("translate"));
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { d: Math.hypot(r.left + r.width / 2 - x, r.top + r.height / 2 - y), tr: el.style.transform };
    }, b);
    say(!!mid && mid.d < 14, `${label}: البطاقةُ المرفوعة تتبع الإصبع — مركزُها عند المؤشّر (‏D687)`, mid ? `${mid.d.toFixed(1)}px` : "لا إزاحة");
    await page.mouse.up(); await sleep(500);
    const landed = await page.evaluate(() => [...document.querySelectorAll("[data-sort-key]")].every(e => !(e.style.transform || "").includes("translate")));
    say(landed, `${label}: وتهبط في موضعها بعد الإفلات — لا إزاحةَ عالقة`);
  } else {
    const cdp = await ctx.newCDPSession(page);
    const a = await center(0), b = await center(2);
    const sc0 = await page.evaluate(() => (document.querySelector(".app-main") || document.scrollingElement).scrollTop);
    await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: a.x, y: a.y }] });
    await sleep(650);
    for (let s = 1; s <= 10; s++) await cdp.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: a.x + (b.x - a.x) * s / 10, y: a.y + (b.y - a.y) * s / 10 }] });
    await sleep(250);
    await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await sleep(500);
    const sc1 = await page.evaluate(() => (document.querySelector(".app-main") || document.scrollingElement).scrollTop);
    say(sc1 === sc0, `${label}: السحبُ باللمس لا يمرّر الصفحة`, `${sc0} → ${sc1}`);
  }
  const k1 = await keys();
  const want = [k0[1], k0[2], k0[0], ...k0.slice(3)];
  say(JSON.stringify(k1) === JSON.stringify(want), `${label}: ضغطٌ مطوّلٌ ثمّ سحبٌ ينقل البطاقةَ إلى موضع ما تُفلَت عليه`, k1.slice(0, 4).join(" "));
  say(orders.length === 1 && JSON.stringify(orders[0]) === JSON.stringify(k1), `${label}: والترتيبُ يُحفظ على الخادم بنداءٍ واحد بالترتيب الظاهر نفسِه`, `${orders.length} نداء`);
  say(!(await sheetOpen()), `${label}: والضغطةُ المطوّلة لا تفتح ورقةَ السهم`);

  // حركةٌ قاصدةٌ قبل المهلة (تمرير) لا ترفع شيئاً
  if (!mob) {
    const a = await center(3), b = await center(5);
    await page.mouse.move(a.x, a.y); await page.mouse.down(); await page.mouse.move(a.x, a.y + 30); await sleep(650);
    await page.mouse.move(b.x, b.y); await page.mouse.up(); await sleep(400);
    say(JSON.stringify(await keys()) === JSON.stringify(k1) && orders.length === 1, `${label}: حركةٌ قبل المهلة تمريرٌ لا سحب — لا يتغيّر ترتيبٌ ولا يُحفظ`);
  }
  // والنقرةُ العاديّة تفتح الورقة كما كانت
  const c = await center(0);
  if (mob) await page.touchscreen.tap(c.x, c.y); else await page.mouse.click(c.x, c.y);
  await sleep(700);
  say(await sheetOpen(), `${label}: والنقرةُ العاديّة تفتح ورقةَ السهم كما كانت`);
  await page.keyboard.press("Escape").catch(() => {});

  // ═══ ٣ · بطاقاتُ فرز السوق (الجوال) ═══
  if (mob) {
    await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2500);
    const s = await page.evaluate(() => {
      const W = document.documentElement.clientWidth;
      const main = document.querySelector(".app-main");
      const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
      const cards = [...document.querySelectorAll('[data-role="scr-card"]')];
      const misAlign = [], multi = [], colMis = [], badSign = [], bareChip = [], sr = [];
      const visualOrder = (el) => {         // أوّلُ محرفٍ مرئيّاً يساراً يجب أن يكون الإشارة (+/−) في الرقم الموقَّع
        const t = el.textContent.trim();
        if (!/^[+-]/.test(t) || !t.endsWith("%")) return true;
        const node = [...el.querySelectorAll("*"), el].map(e => [...e.childNodes].find(n => n.nodeType === 3 && /[+-]/.test(n.textContent))).find(Boolean);
        if (!node) return true;
        const i = node.textContent.search(/[+-]/), j = node.textContent.lastIndexOf("%");
        if (j < 0) return true;
        const R = (k) => { const r = document.createRange(); r.setStart(node, k); r.setEnd(node, k + 1); return r.getBoundingClientRect(); };
        return R(i).left < R(j).left;
      };
      for (const c of cards) {
        const cells = [...c.querySelectorAll('[data-role="cell"]')];
        for (const cell of cells) {
          const cr = cell.getBoundingClientRect();
          const l = cell.querySelector('[data-role="label"]'), v = cell.querySelector('[data-role="value"]');
          const lr = l.getBoundingClientRect(), vr = v.getBoundingClientRect();
          // كلُّ خانةٍ يمين: نهايةُ نصِّ التسمية ونصِّ الرقم عند حافّتها اليمنى
          const tr = (el) => { const r = document.createRange(); r.selectNodeContents(el); return r.getBoundingClientRect().right; };
          if (Math.abs(tr(l) - cr.right) > 1.5 || Math.abs(tr(v) - cr.right) > 1.5) misAlign.push(c.querySelector("img,svg") ? cells.indexOf(cell) : "?");
          if (vr.height > parseFloat(getComputedStyle(v).fontSize) * 1.9) multi.push(cell.textContent.trim().slice(0, 20));
          const sv = v.querySelector('[dir="ltr"]');
          if (sv && !visualOrder(sv)) badSign.push(sv.textContent.trim());
        }
        // الصفّ الأعلى والأسفل على أعمدةٍ واحدة
        if (cells.length === 6) for (let k = 0; k < 3; k++) {
          const a = cells[k].getBoundingClientRect(), b = cells[k + 3].getBoundingClientRect();
          if (Math.abs(a.left - b.left) > 1 || Math.abs(a.right - b.right) > 1) colMis.push(k);
        }
        const ch = c.querySelector('[data-role="chg"] [dir="ltr"]');
        if (ch && !visualOrder(ch)) badSign.push(ch.textContent.trim());
        for (const chip of c.querySelectorAll('[data-role="chip"]')) {
          const bg = getComputedStyle(chip).backgroundColor;
          if (!bg || bg === "rgba(0, 0, 0, 0)" || bg === "transparent") bareChip.push(chip.textContent.trim());
        }
        if (/\.SR|SR\./.test(c.innerText)) sr.push(c.innerText.slice(0, 20));
      }
      return { W, sw, n: cards.length, misAlign, multi, colMis, badSign, bareChip, sr };
    });
    say(s.n === 8, `${label}: بطاقاتُ الفرز ظاهرة`, `${s.n}`);
    say(s.misAlign.length === 0 && s.colMis.length === 0, `${label}: الفرز — كلُّ خانةٍ يمين، والصفُّ الأعلى والأسفل على الأعمدة نفسِها`,
        `${s.misAlign.length} خانةً منحرفة · ${s.colMis.length} عموداً مختلفاً`);
    say(s.multi.length === 0, `${label}: الفرز — كلُّ رقمٍ سطرٌ واحد (تاريخُ القوائم لا ينكسر)`, s.multi.join(" | "));
    say(s.badSign.length === 0, `${label}: الفرز — الإشارةُ قبل الرقم والنسبةُ بعده مرئيّاً («+5%» لا «5%+»)`, s.badSign.join(" "));
    say(s.bareChip.length === 0, `${label}: الفرز — الوسومُ بنمطٍ واحدٍ وأرضيةٍ ظاهرة`, s.bareChip.join(" "));
    say(s.sr.length === 0 && s.sw <= s.W + 1, `${label}: الفرز — الرمزُ بلا «.SR» مقلوب، ولا فيضَ أفقيّ`, `محتوى ${s.sw} · شاشة ${s.W}`);
    if (SHOTS) await page.screenshot({ path: join(SHOTS, `screener_${vp.width}.png`), fullPage: true });

    // ═══ ٤ · غرفة التداول (‏D687): الرسمُ تبويبٌ داخلها، وإيماءةُ السحب تُخرج القائمة ═══
    await page.goto(`http://localhost:${PORT}/chart`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2500);
    const room = await page.evaluate(() => ({
      url: location.pathname + location.search,
      h1: [...document.querySelectorAll("h1")].map(h => h.textContent.trim()),
      tab: [...document.querySelectorAll("nav button")].some(b => b.textContent.trim() === "الرسم البياني" && b.getAttribute("aria-pressed") === "true"),
      chart: [...document.querySelectorAll("button")].some(b => b.textContent.includes("المؤشرات")),
      chartNav: !!document.querySelector('a[href="/chart"]'),
      roomNav: [...document.querySelectorAll('a[href="/watchlist"]')].length > 0,
    }));
    say(room.url === "/watchlist?tab=chart" && room.tab && room.chart && room.h1.includes("غرفة التداول") && !room.h1.includes("الرسم البياني"),
        `${label}: الرسمُ البيانيّ تبويبٌ داخل «غرفة التداول» — ورابطُه القديم يفتحه هناك بعنوانٍ واحد`, `${room.url} · ${room.h1.join("|")}`);
    say(!room.chartNav && room.roomNav, `${label}: ولا بندَ مستقلّاً للرسم في القائمة — «غرفة التداول» وحدها`);
    const cdp2 = await ctx.newCDPSession(page);
    const swipe = async (x0, y0, x1, y1) => {
      await cdp2.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: x0, y: y0 }] });
      for (let s = 1; s <= 6; s++) await cdp2.send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: x0 + (x1 - x0) * s / 6, y: y0 + (y1 - y0) * s / 6 }] });
      await cdp2.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
      await sleep(450);
    };
    const drawerOn = () => page.evaluate(() => !!document.querySelector(".mobile-drawer"));
    await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(2200);
    const rise = await page.evaluate(() => document.querySelectorAll("[data-sort-key] > .card-rise").length);
    say(rise === 8, `${label}: البطاقاتُ تطلع متتابعةً عند الظهور (حركةٌ لا قفزة)`, `${rise}/8`);
    await swipe(200, 640, 190, 300);
    const v = await drawerOn();
    await swipe(330, 640, 120, 650);
    const opened = await drawerOn();
    await swipe(80, 640, 330, 640);
    const closed = !(await drawerOn());
    say(!v && opened && closed, `${label}: سحبُ الإصبع من اليمين إلى اليسار يُخرج القائمة، والعكسُ يُعيدها، والتمريرُ الرأسيّ لا يفتحها`,
        `رأسيّ ${v ? "فتح" : "لا"} · يمين→يسار ${opened ? "فتح" : "لا"} · عكسُه ${closed ? "أغلق" : "لا"}`);
  }
  await ctx.close();
}
await browser.close();
console.log((fail ? "FAIL" : "PASS") + " D683 · D684 · D687 — «غرفة التداول» بثلاثة أعمدة على الجوال وأربعة على الحاسوب وترتيبٌ بالضغط المطوّل · بطاقاتُ الفرز بهويّة التطبيق");
process.exit(fail);
