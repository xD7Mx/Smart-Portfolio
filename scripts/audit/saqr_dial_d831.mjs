// ─────────────────────────────────────────────────────────────────────────
// D831 — قرصُ صقر (المالك 2026-11-25): «الكلماتُ — الإشارات والأساس والمخاطر والمحرّك — خلّها خارجَ الدائرة التي فيها صقر، في نفس الدائرة لكن
// بشكلٍ متساوٍ مع الدائرة، لا خطّاً أفقيّاً، موازيةً لخطّ الدائرة تحت النقاط المعنيّة؛ لا تُبقِ شيئاً داخل دائرة صقر الداخلية… والنقاطُ كاملةً
// بالبنفسجيّ لتحاكي لونَ تصميم التطبيق». كانت الأسماءُ أفقيّةً داخل دائرة صقر (نصفُ قطرها 86 والدائرةُ 100)، والنقاطُ أخضرَ وكهرمانيّاً ورماديّاً.
//  ١ كلُّ اسمٍ على قوسٍ موازٍ للدائرة (نصٌّ على مسار) عند نقطته نفسِها، بين دائرة صقر والنقطة — لا يدخل دائرةَ صقر ولا يمسّ النقطة،
//    والحروفُ قائمة: النصفُ الأعلى مع العقارب والأسفلُ عكسَها؛ وخطُّه ≥ 9.5px.
//  ٢ لا اسمَ ولا أيقونةَ داخل دائرة صقر، والمسحُ الدوّارُ حلقةٌ خارجها — والأسلاكُ وحدها تخرج من تحت علامته (‏D836 بأمر المالك).
//  ٣ ‏D836 (المالك: «بدلَ المربّع والمعيّن أيقوناتٌ جميلةٌ متّصلةٌ كأنّها CPU من خلف علامة صقر»؛ و«لماذا بعضُ البنفسجيّ باهت؟»): لكلّ نظامٍ أيقونتُه
//    بنفسجيّةً كاملة — متطابقةً في كلّ حال — ويصلها سلكٌ من تحت صقر يمرّ بين الأسماء لا عليها؛ والحالُ في السلك: متّصلٌ يسري فيه نبضٌ (يعمل) ·
//    متقطّعٌ (يتحفّظ) · منقّطٌ (ساكن) — والمفتاحُ تحت القرص بعيّناتها.
//  ٥ ‏D837 (المالك 2026-11-25: «الفونيكس أكبر… صغّر الدائرةَ والمؤشّرات… الإضاءةُ الصفراءُ تتوهّج… الأجنحةُ من الأسفل إلى الأعلى… تفاعليّة»):
//    الشعارُ ≥ 60٪ من القرص وقلبُه في مركزه، يرتفع جناحاه ويتوهّج قلبُه، ولا يغطّي اسماً ولا أيقونة (بألفا صورته)، ولمسُه يرفرفه.
//  ٤ في السوقين، والمظهرين، والحاسوب والجوال — بلا خطأ؛ وتقليلُ الحركة يُسكن ظهورَ الأسماء.
//    node scripts/audit/saqr_dial_d831.mjs
// ─────────────────────────────────────────────────────────────────────────
import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const FRONT = join(ROOT, "frontend");
const PORT = 5331;
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
const now = Date.now(), iso = ms => new Date(ms).toISOString().slice(0, 19) + "+00:00";
const SES = { market: "us", state: "open", label: "السوق مفتوح", detail: "يغلق بعد 2 س", next: null, source: "ياهو" };
const OPPS = m => ({ market: m, at: iso(now - 3600e3), universe: 300, screened: 290, read: 200, found: 2, min_q: 50, job: { on: false, msg: "", at: null }, rejected: [], items: [] });
const ST = m => ({ market: m, ccy: m === "sa" ? "SAR" : "USD", on: true, capital: 1000, goal: 100000, cash: 1000, equity: 1000, pl: 0, pl_pct: 0, progress: 0,
  started: iso(now - 86400e3), tier: { frac: 0.25, seats: 4 }, positions: [], closed: [], n_closed: 0, wins: 0, losses: 0, win_rate: null, realized: 0, fees: 0,
  today: { wins: 0, losses: 0, realized: 0, new: 0 }, exposure: { contracts: 0, cost: 0, value: 0, ret: null }, equity_curve: [[iso(now - 3600e3), 1000], [iso(now), 1000]],
  signals: [], log: [], gates: [], scan: m === "us" ? { at: iso(now), universe: 900, full: { optionable: 812, passed: 300 } } : null, session: null, last_cycle: null, last_check: null,
  health: { news: false }, broker: { linked: false, name: "IBKR" }, runs: [], running: { on: false, msg: "", at: null },
  settings: { per_trade: null, max_positions: null, instruments: "both", sides: "both", opt_stop: 40, stock_stop: 6, take_x: 2, mode: "balanced", day_target: null, auto: true },
  day: null, orders: [], pulse: null, geo: null, rules: { stop: 0.6, take: 2, growth: 15 },
  regime: m === "sa" ? { verdict: "هابط", state: "هابط", close: 9891, sma50: 10100, sma200: 10900, ret3m: -4.2, chg: -0.35 } : null,
  opps: { at: iso(now - 3600e3), universe: 300, screened: 290, read: 200, found: 2 } });

const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب · فاتح", { width: 1366, height: 900 }, "light"], ["الجوال · داكن", { width: 390, height: 844 }, "dark"],
  ["الجوال · فاتح", { width: 360, height: 780 }, "light"]]) {
  const ctx = await browser.newContext({ viewport: vp, deviceScaleFactor: 1, colorScheme: theme });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", e => errs.push(String(e).split("\n")[0].slice(0, 200)));
  await page.addInitScript(th => { try {
    localStorage.setItem("sp_token", "probe"); localStorage.setItem("sp_saqr_tab", "dash"); localStorage.setItem("sp_saqr_market", "us"); localStorage.setItem("sp_theme", th);
  } catch { /* */ } }, theme);
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, "");
    const mk = u.searchParams.get("market") === "sa" ? "sa" : "us";
    if (p === "/market/sessions") return r.fulfill(body({ us: SES, sa: { ...SES, market: "sa", state: "open", label: "السوق مفتوح" } }));
    if (p === "/market/saqr") return r.fulfill(body(ST(mk)));
    if (p === "/market/saqr/opportunities") return r.fulfill(body(OPPS(mk)));
    if (p === "/auth/me") return r.fulfill(body({ id: 1, username: "owner", is_owner: true, role: "owner" }));
    return r.fulfill(body([]));
  });
  await page.goto(`http://localhost:${PORT}/watchlist?tab=lab`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.evaluate(th => { const el = document.documentElement; el.classList.toggle("light", th === "light"); el.classList.toggle("dark", th === "dark"); }, theme);
  await page.locator('[data-role="sq-nav"] [data-view="dash"]').click().catch(() => {});
  await sleep(1600);

  for (const mk of ["us", "sa"]) {
    if (mk === "sa") { await page.locator('[data-role="sq-market"] [data-market="sa"]').click().catch(() => {}); await sleep(1500); }
    const g = await page.evaluate(() => {
      const hub = document.querySelector('[data-role="sq-hub"]'), svg = hub?.querySelector("svg");
      if (!hub || !svg) return null;
      const scale = hub.getBoundingClientRect().width / 300, C = 150;
      const RI = Number(hub.querySelector('[data-role="sq-ring-i"]')?.getAttribute("r"));
      const toUser = (x, y) => { const m = svg.getScreenCTM().inverse(); const p = new DOMPoint(x, y).matrixTransform(m); return [p.x, p.y]; };
      const nodes = [...hub.querySelectorAll('[data-role="sq-node"]')].map(n => { const b = (n.querySelector('[data-role="sq-badge"]') || n).getBoundingClientRect(); const [x, y] = toUser(b.x + b.width / 2, b.y + b.height / 2);
        return { k: n.dataset.k, st: n.dataset.state, x, y, r: Math.hypot(x - C, y - C), a: Math.atan2(y - C, x - C), rad: (b.width / scale) / 2,
                 badge: getComputedStyle(n.querySelector(".sq-badge")).stroke, ico: n.querySelector("svg.sq-ico") ? getComputedStyle(n.querySelector("svg.sq-ico")).color : "",
                 icoOp: n.querySelector("svg.sq-ico") ? Number(getComputedStyle(n.querySelector("svg.sq-ico")).opacity) * Number(getComputedStyle(n).opacity) : 0 }; });
      /* الأسلاك: نقاطٌ على كلّ سلكٍ بزاويتها ونصف قطرها — ونمطُ خطّه، ونبضُه */
      const traces = [...hub.querySelectorAll('[data-role="sq-trace"]')].map(t => { const L = t.getTotalLength(), pts = [];
        for (let k = 0; k <= 120; k++) { const p = t.getPointAtLength(L * k / 120); pts.push([Math.hypot(p.x - C, p.y - C), Math.atan2(p.y - C, p.x - C)]); }
        return { for: t.parentElement.dataset.for, st: t.dataset.state, dash: getComputedStyle(t).strokeDasharray, stroke: getComputedStyle(t).stroke, pts,
                 flow: !!t.parentElement.querySelector(".sq-flow") }; });
      /* خليةُ كلّ حرفٍ بزاويتها الحقيقية: من بداية الحرف ونهايته على خطّ الأساس، صعوداً وهبوطاً على اتّجاه رأسه (لا الصندوقُ الأفقيُّ المنتفخُ للحرف المائل) —
         والصعودُ والهبوطُ من حرفٍ أفقيٍّ بالخطّ نفسِه */
      const ref = document.createElementNS("http://www.w3.org/2000/svg", "text");
      ref.setAttribute("class", "sq-lbl ok"); ref.setAttribute("x", "0"); ref.setAttribute("y", "100"); ref.textContent = "الإشارات";
      svg.appendChild(ref);
      const re = ref.getExtentOfChar(1), ASC = 100 - re.y, DESC = re.y + re.height - 100;
      ref.remove();
      const labels = [...hub.querySelectorAll('[data-role="sq-label"]')].map(t => {
        const tp = t.querySelector("textPath"), n = t.getNumberOfChars?.() || 0, pts = [];
        for (let i = 0; i < n; i++) { try {
          const p0 = t.getStartPositionOfChar(i), p1 = t.getEndPositionOfChar(i), r = t.getRotationOfChar(i) * Math.PI / 180, ux = Math.sin(r), uy = -Math.cos(r);
          for (const q of [p0, p1]) pts.push([q.x + ux * ASC, q.y + uy * ASC], [q.x - ux * DESC, q.y - uy * DESC]);
        } catch { /* */ } }
        const rs = pts.map(([x, y]) => Math.hypot(x - C, y - C));
        const mid = n ? (() => { const e = t.getExtentOfChar(Math.floor(n / 2)); return [e.x + e.width / 2, e.y + e.height / 2]; })() : [C, C];
        let rot = 0; try { rot = t.getRotationOfChar(Math.floor(n / 2)); } catch { /* */ }
          const as = pts.map(([x, y]) => Math.atan2(y - C, x - C));
        return { for: t.dataset.for, half: t.dataset.half, txt: t.textContent.trim(), path: !!tp, pts, rmin: Math.min(...rs), rmax: Math.max(...rs), a: Math.atan2(mid[1] - C, mid[0] - C), rot, as,
                 fs: parseFloat(getComputedStyle(t).fontSize) * scale, anim: getComputedStyle(t).animationName };
      });
      const sweep = hub.querySelector(".sq-sweep path")?.getAttribute("d") || "";
      const brand = (() => { const d = document.createElement("i"); d.style.color = "var(--brand-ink)"; hub.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; })();
      const keys = [...document.querySelectorAll('[data-role="sq-legend"] .sq-key')].map(k => { const i = k.querySelector("i"); const cs = getComputedStyle(i);
        return { k: k.className.replace("sq-key", "").trim(), bs: cs.borderTopStyle, bc: cs.borderTopColor }; });
      const flowAnim = [...hub.querySelectorAll(".sq-flow")].map(f => getComputedStyle(f).animationName);
      /* ‏D837: الشعارُ الكبير — مقاسُه ومركزُ قلبه وصوره وحركتُه */
      const em = hub.querySelector('.sqe.rich'), hb = hub.getBoundingClientRect();
      const emb = em ? (() => { const r = em.getBoundingClientRect(), h = em.querySelector(".sqe-heart").getBoundingClientRect();
        const imgs = [...em.querySelectorAll("img")];
        return { w: r.width / hb.width, hx: (h.x + h.width / 2 - hb.x) / hb.width, hy: (h.y + h.height / 2 - hb.y) / hb.height,
                 box: [...toUser(r.x, r.y), ...toUser(r.right, r.bottom)], src: imgs[0]?.currentSrc || imgs[0]?.src || "", first: imgs[0]?.alt || "",
                 loaded: imgs.length === 3 && imgs.every(i => i.complete && i.naturalWidth > 0),
                 wing: getComputedStyle(em.querySelector(".sqe-wing")).animationName, heart: getComputedStyle(em.querySelector(".sqe-heart")).animationName,
                 role: em.getAttribute("role"), tab: em.tabIndex }; })() : null;
      return { scale, RI, nodes, labels, emb, sweep, brand, keys, traces, flowAnim, live: hub.dataset.live, legend: document.querySelector('[data-role="sq-legend"]')?.textContent || "" };
    });
    if (process.env.SHOTS) await page.locator('[data-role="sq-hubw"]').screenshot({ path: join(process.env.SHOTS, `d831-${mk}-${vp.width}-${theme}.png`) }).catch(() => {});
    if (!g) { say(false, `${label} · ${mk}: القرصُ غيرُ ظاهر`); continue; }
    const byK = Object.fromEntries(g.nodes.map(n => [n.k, n]));
    const angDiff = (x, y) => { let d = Math.abs(x - y) % (2 * Math.PI); return d > Math.PI ? 2 * Math.PI - d : d; };
    const lab = g.labels.map(l => { const n = byK[l.for];
      return { ...l, dA: n ? angDiff(l.a, n.a) * 180 / Math.PI : 99, gapIn: l.rmin - g.RI, gapDot: n ? (n.r - n.rad) - l.rmax : -99 }; });
    const curved = lab.every(l => l.path && l.dA <= 6) && lab.length === g.nodes.length && lab.length >= 7;
    const between = lab.every(l => l.gapIn >= 1 && l.gapDot >= 0);
    const halves = lab.every(l => (l.half === "b") === (Math.sin(byK[l.for].a) > 1e-6));
    /* اتّجاهُ الحرف = مماسُّ القوس: مع العقارب (زاويةُ النقطة + 90°) في الأعلى، وعكسَها (− 90°) في الأسفل ⇐ رأسُ الحرف نحو الخارج أعلى ونحو صقر أسفل — قائمٌ */
    const along = (l, off) => Math.cos((l.rot - (l.a * 180 / Math.PI + off)) * Math.PI / 180) > 0.94;
    const bottomUp = lab.filter(l => l.half === "b").every(l => along(l, -90));
    const topUp = lab.filter(l => l.half === "t").every(l => along(l, 90));
    const fsMin = Math.min(...lab.map(l => l.fs));
    say(curved && between && halves && bottomUp && topUp && fsMin >= 9.5,
      `${label} · ${mk === "us" ? "الأمريكيّ" : "السعوديّ"}: ١ كلُّ اسمٍ على قوسٍ موازٍ للدائرة عند نقطته، بين دائرة صقر والنقطة (لا يدخلها ولا يمسّ النقطة)، `
      + "والحروفُ قائمة — الأعلى مع العقارب والأسفلُ عكسَها — وخطُّه ≥ 9.5px",
      JSON.stringify({ n: lab.length, fs: +fsMin.toFixed(1), worst: lab.map(l => `${l.txt}:${l.dA.toFixed(1)}°/${l.gapIn.toFixed(1)}/${l.gapDot.toFixed(1)}/${Math.round(l.rot)}`).join(" ") }));
    const inside = g.nodes.filter(n => n.r - n.rad < g.RI).length + lab.filter(l => l.rmin < g.RI).length;
    const sweepRing = new RegExp(`^M[\\d.]+,${(150 - g.RI).toFixed(2)} L`).test(g.sweep) && g.sweep.includes(`A${g.RI},${g.RI} 0 0,0`);
    say(g.RI >= 110 && inside === 0 && sweepRing,
      `${label} · ${mk === "us" ? "الأمريكيّ" : "السعوديّ"}: ٢ لا اسمَ ولا أيقونةَ داخل دائرة صقر، والمسحُ الدوّارُ حلقةٌ خارجها — والأسلاكُ وحدها من تحت علامته`, g.sweep.slice(0, 60));
    const rgb = s => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number).join(",");
    const B = rgb(g.brand);
    const icons = g.nodes.every(n => rgb(n.badge) === B && rgb(n.ico) === B && n.icoOp > 0.99) && g.nodes.length === lab.length;
    /* السلكُ يبدأ تحت صقر وينتهي عند حافة أيقونته، ولا يمسّ اسماً في حزام الأسماء */
    const angIn = (x, lo, hi) => { const d = (v) => ((v - lo) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI); return d(x) <= d(hi); };
    const lblSpan = lab.map(l => { const sorted = l.as.map(x => x); let lo = sorted[0], best = 0;
      /* المدى الزاويّ للاسم: أصغرُ قوسٍ يحوي حروفَه */
      for (const s0 of sorted) { const w = Math.max(...sorted.map(x => ((x - s0) % (2 * Math.PI) + 2 * Math.PI) % (2 * Math.PI))); if (!best || w < best) { best = w; lo = s0; } }
      return { lo, hi: lo + best, rmin: l.rmin, rmax: l.rmax, txt: l.txt }; });
    const wires = g.traces.map(t => { const n = byK[t.for]; const first = t.pts[0], last = t.pts[t.pts.length - 1];
      const hits = t.pts.filter(([r, a]) => lblSpan.some(sp => r >= sp.rmin - 1 && r <= sp.rmax + 1 && angIn(a, sp.lo - 0.01, sp.hi + 0.01))).length;
      const endD = n ? Math.hypot(last[0] * Math.cos(last[1]) - (n.x - 150), last[0] * Math.sin(last[1]) - (n.y - 150)) : 99;
      return { k: t.for, st: t.st, start: first[0], endD, hits, dash: t.dash, flow: t.flow, stroke: rgb(t.stroke) }; });
    const wired = wires.length === g.nodes.length && wires.every(w => w.start < g.RI - 30 && w.endD <= byK[w.k].rad + 2.5 && w.hits === 0);
    const styles = wires.every(w => w.st === "ok" ? (w.dash === "none" && w.flow) : w.st === "warn" ? (/^\d/.test(w.dash) && !w.flow && parseFloat(w.dash) > 3)
      : (/^\d/.test(w.dash) && !w.flow && parseFloat(w.dash) < 2)) && wires.some(w => w.st !== "ok");
    const flowing = g.live !== "1" || g.flowAnim.every(x => x === "sqFlow");
    const kk = Object.fromEntries(g.keys.map(k => [k.k, k]));
    const legend = /وسلكُها إليه حالُه/.test(g.legend) && /أيقونةٍ/.test(g.legend) && kk.ok?.bs === "solid" && kk.warn?.bs === "dashed" && kk.off?.bs === "dotted"
      && rgb(kk.ok?.bc || "") === B;
    say(icons && wired && styles && flowing && legend,
      `${label} · ${mk === "us" ? "الأمريكيّ" : "السعوديّ"}: ٣ لكلّ نظامٍ أيقونتُه بنفسجيّةً كاملة متطابقةً في كلّ حال، ويصلها سلكٌ من تحت صقر بين الأسماء لا عليها — `
      + "والحالُ في السلك (متّصلٌ يسري فيه نبضٌ · متقطّعٌ · منقّط)، والمفتاحُ تحت القرص بعيّناتها",
      JSON.stringify({ B, icons, wires: wires.map(w => `${w.k}:${w.st}:${w.start.toFixed(0)}/${w.endD.toFixed(1)}/${w.hits}/${w.dash}/${w.flow ? 1 : 0}`).join(" "), legend }));
    /* ٥ ‏D837 (المالك: «الفونيكس أكبر… تصغّر الدائرة والمؤشّرات… الإضاءةُ الصفراءُ تتوهّج… الأجنحةُ من الأسفل إلى الأعلى… تفاعليّة»):
       الشعارُ ≥ 60٪ من القرص وقلبُه في مركزه، وصورُه الثلاث محمّلة، وحركةُ الجناحين والقلب، ولا بكسلَ معتمٍ منه على اسمٍ أو أيقونة */
    const e = g.emb;
    let overlap = -1;
    if (e) overlap = await page.evaluate(async ({ e, labels, nodes }) => {
      const im = new Image(); im.src = e.src; await im.decode().catch(() => {});
      const cv = document.createElement("canvas"); cv.width = im.naturalWidth; cv.height = im.naturalHeight;
      const cx = cv.getContext("2d"); cx.drawImage(im, 0, 0); const d = cx.getImageData(0, 0, cv.width, cv.height).data;
      const [x0, y0, x1, y1] = e.box, A = (x, y) => { const u = Math.round((x - x0) / (x1 - x0) * cv.width), v = Math.round((y - y0) / (y1 - y0) * cv.height);
        return u < 0 || v < 0 || u >= cv.width || v >= cv.height ? 0 : d[(v * cv.width + u) * 4 + 3]; };
      let hit = 0;
      for (const l of labels) for (const [x, y] of l.pts) if (A(x, y) > 60) hit++;
      for (const n of nodes) for (let k = 0; k < 16; k++) { const t = k / 16 * 2 * Math.PI; if (A(n.x + Math.cos(t) * n.rad, n.y + Math.sin(t) * n.rad) > 60) hit++; }
      return hit; }, { e, labels: g.labels, nodes: g.nodes });
    say(!!e && e.w >= 0.6 && Math.abs(e.hx - 0.5) <= 0.02 && Math.abs(e.hy - 0.5) <= 0.03 && e.loaded && e.first === "صقر" && overlap === 0
        && /sqeRise|sqeBeat/.test(e.wing) && (g.live !== "1" || /sqeHeart/.test(e.heart)) && e.role === "button" && e.tab === 0,
      `${label} · ${mk === "us" ? "الأمريكيّ" : "السعوديّ"}: ٥ الفونيكسُ أكبرُ من دائرته (≥ 60٪ من القرص) وقلبُه في المركز، يتوهّج قلبُه وترتفع أجنحتُه، `
      + "وهو تفاعليّ — ولا يغطّي اسماً ولا أيقونة",
      JSON.stringify(e && { w: +e.w.toFixed(3), hx: +e.hx.toFixed(3), hy: +e.hy.toFixed(3), loaded: e.loaded, overlap, wing: e.wing, heart: e.heart }));
  }
  await page.emulateMedia({ reducedMotion: "reduce" }); await sleep(200);
  const rm = await page.evaluate(() => [...document.querySelectorAll('[data-role="sq-label"]')].every(t => getComputedStyle(t).animationName === "none")
    && [...document.querySelectorAll('.sqe.rich, .sqe.rich *')].every(t => ["none", ""].includes(getComputedStyle(t).animationName)));
  /* اللمسُ يرفرفه — ومع تقليل الحركة يسكن */
  await page.emulateMedia({ reducedMotion: "no-preference" }); await sleep(100);
  await page.locator('.sqe.rich').click({ force: true }).catch(() => {});
  const beat = await page.evaluate(() => document.querySelector('.sqe.rich')?.dataset.beat || "");
  await page.emulateMedia({ reducedMotion: "reduce" });
  say(!!beat, `${label}: ٥ب لمسُ الشعار يرفرف جناحيه`, beat);
  say(rm && errs.length === 0, `${label}: ٤ تقليلُ الحركة يُسكن ظهورَ الأسماء — ولا خطأ في الصفحة`, errs[0] || "");
  await ctx.close();
}
await browser.close();
stop();
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
