// ─────────────────────────────────────────────────────────────────────────
// D736 (بأمر المالك 2026-11-15): «في غرفة التداول خلِّه الرسم البياني… الشركاتُ في اليمين والرسمُ على اليسار… سخّر كلَّ
// الإمكانيات لجعل الرسم وجمالِه وثباتِه وتحريكِ السهم ومؤشّرِ D7M والدعوم شبيهاً بتريدنق فيو سلاسةً ودقّةً وثباتاً… الشموعُ
// كأنها ديكور ليست حقيقية… المؤشّراتُ رسومُها فارغة… خيارُ تخصيصٍ في الأطر — مثلاً 6 ساعات… الرسمُ له أيقونةُ فرشة والمؤشّراتُ
// أيقونة… وخلّها الرسم البياني ومختبر الأبحاث وألغِ الشركات».
// الحالُ قبله (‏NativeChart في الغرفة): الشموعُ كلُّها تُحشر في عرض الشاشة (‏fitContent)، والعجلةُ معطَّلة، والرسمُ يُهدم ويُبنى مع
// كلّ تغيير، وتاريخٌ مكرَّرٌ من المصدر يُفرغه كلَّه، واللوحاتُ السفلى هوامشُ على مقياسٍ واحد، ولا إطارَ مخصَّصاً، والقائمةُ يسار الرسم.
// ١–٩ سلوكيٌّ على الدوالّ نفسِها (‏lib/chartData · lib/chartOverlay) وساكنٌ على المصدر · ١٠–… المتصفّح: التطبيقُ والمكتبةُ الحقيقيّان.
//    SHOTS=dir node scripts/audit/pro_chart_d736.mjs
// ─────────────────────────────────────────────────────────────────────────
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
const DATA = join(FRONT, "src/lib/chartData.ts"), OVER = join(FRONT, "src/lib/chartOverlay.ts");
if (!existsSync(DATA) || !existsSync(OVER)) { say(false, "١ دوالُّ بيانات الرسم وطبقتُه موجودة"); done(); }
const { build } = await import(pathToFileURL(join(FRONT, "node_modules/esbuild/lib/main.js")).href);
const tmp = mkdtempSync(join(tmpdir(), "sp-d736-"));
await build({ entryPoints: [DATA], outfile: join(tmp, "data.mjs"), format: "esm", bundle: false, logLevel: "silent" });
await build({ entryPoints: [OVER], outfile: join(tmp, "over.mjs"), format: "esm", bundle: true, logLevel: "silent" });
const D = await import(pathToFileURL(join(tmp, "data.mjs")).href);
await build({ entryPoints: [join(FRONT, "src/lib/indicators.ts")], outfile: join(tmp, "ind.mjs"), format: "esm", bundle: false, logLevel: "silent" });
const I = await import(pathToFileURL(join(tmp, "ind.mjs")).href);
const { ChartOverlay } = await import(pathToFileURL(join(tmp, "over.mjs")).href);

// ── ١–٤ البيانات والإطارات ──
const bar = (date, o, h, l, c, v = 100) => ({ date, open: o, high: h, low: l, close: c, volume: v });
const dirty = [bar("2026-11-08", 10, 11, 9, 10.5), bar("2026-11-01", 9, 10, 8, 9.5), bar("2026-11-08", 10, 12, 9, 11),
               bar("2026-10-25", 0, 5, 4, 4.5), bar("2026-10-18", 8, 8.2, 7, 9), { date: "2026-10-11", open: 7, high: 8, low: 6, close: NaN }];
const clean = D.sanitizeBars(dirty);
say(JSON.stringify(clean.map(b => b.time)) === JSON.stringify(["2026-10-18", "2026-11-01", "2026-11-08"]) && clean[2].close === 11 && clean[0].high === 9,
    "١ الشموعُ تُسلَّم للرسم مرتَّبةً بلا تاريخٍ مكرَّر ولا شمعةٍ مختلّة — وآخرُ المكرَّرَين يحكم، والقمّةُ تحوي الجسم",
    clean.map(b => b.time).join(" · "));
// ‏D739 (المالك: «توقيتٌ موحّدٌ مثل تريدنق فيو… أغيّره −3 −2 على توقيت غرينتش»): الشمعةُ بالتوقيت العالميّ الحقيقيّ، والعرضُ بالمنطقة المختارة
const t10 = D.barTime("2026-11-12 10:00");
const at = (tz) => D.tickLabel(D.displayTimes([{ time: t10 }], tz)[0], 3);
say(t10 === Date.UTC(2026, 10, 12, 7, 0) / 1000 && at("Asia/Riyadh") === "10:00" && at("UTC") === "07:00" && at("America/New_York") === "02:00"
    && at("America/Sao_Paulo") === "04:00" && D.barTime("2026-11-12") === "2026-11-12" && D.displayTimes([{ time: "2026-11-12" }], "America/New_York")[0] === "2026-11-12"
    && /12 .* 2026/.test(D.crossLabel("2026-11-12")) && !/[٠-٩]/.test(D.crossLabel(t10) + D.tickLabel("2026-11-12", 1)),
    "٢ الشمعةُ بالتوقيت العالميّ، وتُعرض بأيّ منطقة: افتتاحُ الرياض 10:00 = 07:00 UTC = 02:00 نيويورك = 04:00 (UTC−3) — واليوميةُ لا تتبع منطقة",
    ["Asia/Riyadh", "UTC", "America/New_York", "America/Sao_Paulo"].map(at).join(" · "));
const fb = Date.UTC(2026, 10, 1, 5, 30) / 1000;          // ساعةُ الرجوع عن الصيفيّ في نيويورك تتكرّر: 01:30 مرّتين
const ny = D.displayTimes([{ time: fb }, { time: fb + 3600 }, { time: fb + 7200 }], "America/New_York");
say(ny[0] < ny[1] && ny[1] < ny[2] && D.tickLabel(ny[0], 3) === "01:30" && D.tickLabel(ny[1], 3) === "01:30" && D.tickLabel(ny[2], 3) === "02:30"
    && D.fmtOffset(-180) === "UTC−3" && D.fmtOffset(330) === "UTC+5:30" && D.fmtOffset(0) === "UTC" && D.exchangeTz("1120.SR") === "Asia/Riyadh"
    && D.exchangeTz("AAPL") === "America/New_York" && D.exchangeTz("BTC-USD") === "UTC" && D.TZ_LIST.length >= 20,
    "٢ب والصيفيُّ والشتويُّ يُحسبان لحظتَهما، وساعةُ الرجوع المكرَّرة لا تكسر الرسم، ولكلّ رمزٍ منطقةُ بورصته", ny.map(t => D.tickLabel(t, 3)).join(" · "));
const tf = (s) => { const p = D.parseTf(s); return p ? `${p.n}${p.unit}` : null; };
say(tf("6h") === "6h" && tf("45m") === "45m" && tf("120m") === "2h" && tf("3d") === "3d" && tf("2w") === "2wk" && tf("1mo") === "1mo"
    && tf("25h") === null && tf("0d") === null && tf("13mo") === null && tf("abc") === null && tf("6") === null,
    "٣ الإطارُ المخصَّص «عددٌ + وحدة»: 6 ساعات و45 دقيقة و3 أيام تُقبل، وما خرج عن الحدّ أو اختلّ لا يُقبل", ["6h", "120m", "25h"].map(tf).join(" · "));
say(D.tfLong("6h") === "6 ساعات" && D.tfLong("2h") === "ساعتان" && D.tfLong("1h") === "ساعة" && D.tfLong("15m") === "15 دقيقة" && D.tfLong("3d") === "3 أيام"
    && D.tfShort("6h") === "6س" && D.tfShort("1wk") === "أسبوع" && D.fmtPrice(0) === "0.00" && D.fmtPrice(1234.5) === "1,234.50",
    "٤ واسمُ الإطار بالفصحى (ساعة · ساعتان · 6 ساعات · 15 دقيقة) والسعرُ بهللتين", `${D.tfLong("6h")} · ${D.tfLong("2h")} · ${D.tfShort("6h")}`);

// ── ٤ب ‏D741: Stoch RSI بسكربت تريدنق فيو الذي أرسله المالك — يُعاد حسابُه هنا من نصّ السكربت مستقلّاً ويُطابَق ──
{
  const px = Array.from({ length: 160 }, (_, i) => 100 + 8 * Math.sin(i / 7) + 3 * Math.sin(i / 2.3) + ((i * 37) % 11 - 5) / 4);
  const rma = (a, n) => { const o = Array(a.length).fill(null); let s = null; for (let i = 0; i < a.length; i++) { if (a[i] == null) continue;
    if (s == null) { const w = a.slice(i - n + 1, i + 1); if (w.length === n && w.every(v => v != null)) { s = w.reduce((x, y) => x + y, 0) / n; o[i] = s; } }
    else { s = (s * (n - 1) + a[i]) / n; o[i] = s; } } return o; };
  const up = px.map((v, i) => (i ? Math.max(v - px[i - 1], 0) : null)), dn = px.map((v, i) => (i ? Math.max(px[i - 1] - v, 0) : null));
  const ru = rma(up, 14), rd = rma(dn, 14);
  const r = ru.map((u, i) => (u == null || rd[i] == null ? null : rd[i] === 0 ? 100 : u === 0 ? 0 : 100 - 100 / (1 + u / rd[i])));
  const st = r.map((v, i) => { if (i < 13) return null; const w = r.slice(i - 13, i + 1); if (w.some(x => x == null)) return null;
    const hh = Math.max(...w), ll = Math.min(...w); return hh > ll ? 100 * (v - ll) / (hh - ll) : null; });
  const smaR = (a, n) => a.map((_, i) => { if (i < n - 1) return null; const w = a.slice(i - n + 1, i + 1); return w.some(x => x == null) ? null : w.reduce((x, y) => x + y, 0) / n; });
  const K = smaR(st, 3), Dd = smaR(K, 3);
  const ours = I.stochRsi(px, I.STOCHRSI_DEFAULTS);
  const diff = Math.max(...K.map((v, i) => (v == null && ours.k[i] == null ? 0 : v == null || ours.k[i] == null ? 1e9 : Math.abs(v - ours.k[i]))),
                        ...Dd.map((v, i) => (v == null && ours.d[i] == null ? 0 : v == null || ours.d[i] == null ? 1e9 : Math.abs(v - ours.d[i]))));
  const flat = I.stochRsi(Array(60).fill(50));
  say(diff < 1e-9 && ours.k.findIndex(v => v != null) === 29 && ours.d.findIndex(v => v != null) === 31 && flat.k.every(v => v == null)
      && JSON.stringify(I.STOCHRSI_DEFAULTS) === JSON.stringify({ k: 3, d: 3, rsiLen: 14, stochLen: 14, src: "close", upper: 80, middle: 50, lower: 20 })
      && JSON.stringify(I.stochRsi(I.source(px.map(c => ({ open: c, high: c + 1, low: c - 1, close: c })), "close"), { ...I.STOCHRSI_DEFAULTS, k: 8, d: 8, rsiLen: 14, stochLen: 3 }).k.slice(-1)) !== JSON.stringify(ours.k.slice(-1)),
      "٤ب Stoch RSI بسكربت تريدنق فيو حرفاً: RSI 14 (وايلدر) ← ستوكاستيك 14 ← K 3 · D 3 — أوّلُ قيمةٍ عند الشمعة 30، ومدًى صفريٌّ فراغٌ لا رقم",
      `أكبرُ فرق ${diff.toExponential(1)} · آخرُ K ${ours.k[159].toFixed(4)} · D ${ours.d[159].toFixed(4)}`);
}

// ── ٤ج ‏D744: القناةُ السعرية ترتكز على الدعوم والمقاومات الحقيقية وتحوي الشموع — قناةٌ صاعدةٌ مصنوعةٌ بلمساتٍ معروفة ──
{
  await build({ entryPoints: [join(FRONT, "src/components/analysis/d7m.ts")], outfile: join(tmp, "d7m.mjs"), format: "esm", bundle: true, logLevel: "silent" });
  const M = await import(pathToFileURL(join(tmp, "d7m.mjs")).href);
  const bs = Array.from({ length: 220 }, (_, i) => { const mid = 100 + i * 0.25, w = 6 * Math.sin(i / 9), c = mid + w;
    return { date: `2026-01-${i}`, open: c - 0.2, high: c + 0.6, low: c - 0.6, close: c, volume: 1000 }; });
  const ch = M.autoChannel(bs, 2, 10);
  const lineAt = (seg, x) => seg[0][1] + (seg[1][1] - seg[0][1]) * (x - seg[0][0]) / (seg[1][0] - seg[0][0]);
  let out = 0;
  if (ch) for (let x = ch.base[0][0]; x < bs.length; x++) { const a = lineAt(ch.base, x), b = lineAt(ch.parallel, x), hi = Math.max(a, b), lo = Math.min(a, b);
    if (bs[x].close > hi + 0.8 || bs[x].close < lo - 0.8) out++; }
  const slope = ch ? (ch.base[1][1] - ch.base[0][1]) / (ch.base[1][0] - ch.base[0][0]) : 0;
  say(!!ch && (ch.touches ?? 0) >= 3 && out === 0 && slope > 0.15 && slope < 0.35,
      "٤ج القناةُ السعرية ترتكز على قمّتين أو قاعين حقيقيّين بأكثر اللمسات، وتحوي كلَّ الإغلاقات منذ بدايتها، وميلُها ميلُ السعر",
      ch ? `لمسات ${ch.touches} · خارجها ${out} · الميل ${slope.toFixed(3)}` : "لا قناة");
}

// ── ٥ طبقةُ الرسم: موضعٌ كسريٌّ بين شمعتين (المكتبةُ تعيد صفراً لرقم شمعةٍ كسريّ ⇒ خطٌّ على حافّة الرسم) ──
const rec = [];
const ctx2d = new Proxy({}, { get: (t, k) => (k in t ? t[k] : (...a) => { rec.push([k, a]); }), set: (t, k, v) => { t[k] = v; return true; } });
const target = { useMediaCoordinateSpace: (cb) => cb({ context: ctx2d, mediaSize: { width: 600, height: 400 } }) };
const ov = new ChartOverlay();
ov.attached({ chart: { timeScale: () => ({ logicalToCoordinate: (k) => (Number.isInteger(k) ? 100 + 10 * k : 0), options: () => ({ barSpacing: 10 }) }) },
              series: { priceToCoordinate: (p) => 400 - p }, requestUpdate() { } });
ov.set({ segments: [{ x1: 2.5, y1: 100, x2: 7.25, y2: 150, color: "C" }], paths: [{ pts: [{ x: 1.2, y: 50 }, { x: 1.7, y: 60 }], color: "C" }] });
ov.paneViews()[0].renderer().draw(target);
const mv = rec.filter(r => r[0] === "moveTo" || r[0] === "lineTo").map(r => r[1].map(v => +v.toFixed(2)).join(","));
say(JSON.stringify(mv) === JSON.stringify(["125,300", "172.5,250", "112,350", "117,340"]),
    "٥ خطُّ الاتجاه والفرشاةُ بموضعهما الكسريّ بين الشموع — لا يُرسمان على حافّة الرسم ولا سلالمَ", mv.join(" → "));

// ── ٦–٩ ساكنٌ على المصدر ──
const pc = rd("src/components/chart/ProChart.tsx"), room = rd("src/components/market/TradeRoom.tsx"), wp = rd("src/pages/WatchlistPage.tsx");
const pkg = JSON.parse(rd("package.json") || "{}");
const code = pc.replace(/\/\*[\s\S]*?\*\/|\/\/[^\n]*/g, "");
say(/from "lightweight-charts"/.test(pc) && /^\d+\.\d+\.\d+$/.test(pkg.dependencies?.["lightweight-charts"] || "") && !/unpkg\.com/.test(code),
    "٦ مكتبةُ الرسم مع التطبيق بإصدارٍ مثبَّت — لا تُنزَّل من الشبكة عند فتح الرسم", pkg.dependencies?.["lightweight-charts"] || "غير مثبَّتة");
say(!/fitContent\(/.test(code) && /setVisibleLogicalRange\(/.test(code) && /mouseWheel: true/.test(code) && /pinch: true/.test(code) && /vertTouchDrag: false/.test(code)
    && (code.match(/createChart\(/g) || []).length === 1,
    "٧ الرسمُ يُنشأ مرّةً، ومشهدُه آخرُ الشموع بعرضٍ مقروء (لا الكلُّ محشوراً)، والعجلةُ والقرصُ يكبّران والإصبعُ العموديُّ للصفحة");
say(!/subscribeClick\(/.test(code) && /onPointerDown=\{drawDown\}/.test(code) && /<Brush /.test(code) && /<Activity /.test(code) && /data-role="pc-draw"/.test(code),
    "٨ أدواتُ الرسم تلتقط الإصبعَ بنفسها (نقرةُ المكتبة تبتلع الثانيةَ السريعة)، وللرسم أيقونةُ فرشاةٍ وللمؤشّرات أيقونة");
say(/import ProChart from "\.\.\/chart\/ProChart"/.test(room) && !/key=\{symbol\}/.test(room) && !/NativeChart/.test(room)
    && /\["chart", "الرسم البياني", CandlestickChart\], \["lab", "مختبر الأبحاث", FlaskConical\]/.test(wp) && !/WatchlistTab|الشركات"/.test(wp),
    "٩ الغرفةُ على الرسم الاحترافيّ يبقى قائماً حين يتبدّل الرمز، وتبويباها «الرسم البياني» و«مختبر الأبحاث» بلا «الشركات»");
const css = rd("src/styles/globals.css");
say(/\.pc-btn, \.pc-tf \{ min-width: 32px; min-height: 32px;/.test(css) && /prefers-reduced-motion: reduce\) \{\s*\.pc-btn/.test(css)
    && /\.troom \{ grid-template-columns: 300px minmax\(0, 1fr\); \}/.test(css) && /\.troom-chart \{ order: -1; \}/.test(css),
    "٩ب أزرارُ الشريط هدفُ لمسٍ ≥ 32px، والحركةُ تحترم تقليلَها، والقائمةُ أوّلُ عمودٍ (يمينَ الشاشة) والرسمُ أوّلاً على الجوال");

// ── المتصفّح ──
const PORT = 5256;
const SHOTS = process.env.SHOTS || "";
if (SHOTS) mkdirSync(SHOTS, { recursive: true });
const CHROME = ["/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium"].find(p => existsSync(p));
const PW = [join(FRONT, "node_modules", "playwright", "index.js"), "/opt/node22/lib/node_modules/playwright/index.js", "/usr/lib/node_modules/playwright/index.js"].find(p => existsSync(p));
if (!PW || !CHROME) { console.log("… تعذّر فحصُ المتصفّح (المتصفّح غيرُ متاح) — لا حكم."); done(); }
const _pw = await import(pathToFileURL(PW).href);
const chromium = _pw.chromium || _pw.default?.chromium;
const body = (data) => ({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
const sleep = (ms) => new Promise(r => setTimeout(r, ms));
const fmt = (v) => v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
// 420 أسبوعاً متعرّجاً — وآخرُها مكرَّرُ التاريخ كما كان المصدرُ يفعل (العطبُ الذي كان يُفرغ الرسم)
const weekly = (n = 420, seed = 3) => {
  const out = []; let p = 60;
  for (let i = 0; i < n; i++) {
    const d = new Date(Date.UTC(2018, 10, 4) + i * 7 * 864e5).toISOString().slice(0, 10);
    const c = +(p * (1 + Math.sin(i / 6 + seed) * 0.02 + ((i * 37 + seed) % 11 - 5) / 400)).toFixed(2);
    out.push({ date: d, open: +p.toFixed(2), high: +(Math.max(p, c) + 0.6).toFixed(2), low: +(Math.min(p, c) - 0.6).toFixed(2), close: c, volume: 1e6 + (i % 9) * 1e5 });
    p = c;
  }
  const l = out[out.length - 1];
  out.push({ ...l, close: +(l.close + 0.4).toFixed(2), high: +(l.high + 0.4).toFixed(2) });
  return out;
};
// ساعاتٌ بختم الخادم (ساعةُ الرياض): 10:00–13:00 لخمسين يوماً
const hourly = () => { const out = []; for (let d = 0; d < 50; d++) for (const h of [10, 11, 12, 13]) {
  const day = new Date(Date.UTC(2026, 8, 1) + d * 864e5).toISOString().slice(0, 10), b = 60 + Math.sin(d + h) * 2;
  out.push({ date: `${day} ${h}:00`, open: b, high: b + 0.5, low: b - 0.5, close: b + 0.2, volume: 1e5 }); } return out; };
// ‏D746: قسمُ الأبحاث ورقةٌ يكتبها الخادم (‏services/research_paper) — والصفحةُ تعرضها بتاريخها، والمصادرُ لا تُعرض
const RD_HEAD = { date: "2026-11-15", label: "الأحد 15 نوفمبر 2026", headline: "تراجعٌ بقيادة البنوك", close: 10258.22, pct: -0.66, view: "محايد", picks: 1 };
const RD_DATES = [{ date: "2026-11-15", label: "الأحد 15 نوفمبر 2026" }, { date: "2026-11-12", label: "الخميس 12 نوفمبر 2026" },
  { date: "2026-10-29", label: "الخميس 29 أكتوبر 2026" }];
const RD_PAPER = part => `<!doctype html><html lang="ar" dir="rtl"><body style="margin:0"><section class="page" style="min-height:1100px">
  <h1>التقرير اليومي</h1><table><tr><td>تاسي</td><td>10,258.22</td></tr></table></section>${part === "all"
  ? `<section class="page"><h1>محفظتنا واختياراتنا</h1></section>` : ""}</body></html>`;
const HOLD = [{ company: { symbol: "1120", name_ar: "مصرف الراجحي" }, last_price: 64.2, change_pct: 1.25 },
              { company: { symbol: "2222", name_ar: "أرامكو السعودية" }, last_price: 25.1, change_pct: -0.4 }];
const vite = spawn("npx", ["vite", "--port", String(PORT), "--strictPort"], { cwd: FRONT, stdio: "ignore" });
process.on("exit", () => { try { vite.kill("SIGKILL"); } catch { } });
let upv = false;
for (let i = 0; i < 60 && !upv; i++) { await sleep(500); try { upv = (await fetch(`http://localhost:${PORT}/`)).ok; } catch { } }
if (!upv) { console.log("… لم يقلع خادمُ التطوير."); done(); }
const browser = await chromium.launch({ executablePath: CHROME });
for (const [label, vp, theme] of [["الحاسوب", { width: 1366, height: 900 }, "dark"], ["الجوال", { width: 390, height: 844 }, "light"]]) {
  const desk = vp.width >= 1024;
  const ctx = await browser.newContext({ viewport: vp, isMobile: !desk, hasTouch: !desk });
  const page = await ctx.newPage();
  const errs = [], reqs = [], saves = [], ext = [];
  page.on("pageerror", e => errs.push(String(e.message || e)));
  const logoReq = [];
  page.on("request", r => { if (/unpkg\.com|jsdelivr|cdnjs/.test(r.url())) ext.push(r.url()); if (/\/market\/logo\//.test(r.url())) logoReq.push(decodeURIComponent(r.url().split("/market/logo/")[1])); });
  await page.route("**/api/v1/**", async r => {
    const u = new URL(r.request().url()), p = u.pathname.replace(/^.*\/api\/v1/, ""), m = r.request().method();
    if (/^\/market\/(bars|history)\//.test(p)) {
      const s = decodeURIComponent(p.split("/").pop()), tfq = u.searchParams.get("tf") || "";
      reqs.push(`${s}?${tfq}`);
      if (/^\d+(m|h)$/.test(tfq)) return r.fulfill(body(hourly()));
      const w = weekly(420, s.length);
      return r.fulfill(body(s === "^GSPC" ? w.map(x => ({ ...x, volume: 0 })) : w));
    }
    if (/^\/market\/drawings\//.test(p)) { if (m !== "GET") saves.push([decodeURIComponent(p.split("/").pop()), JSON.parse(r.request().postData() || "{}")]); return r.fulfill(body(m === "GET" ? [] : null)); }
    if (p === "/holdings") return r.fulfill(body(HOLD));
    if (p === "/market/research-desk") return r.fulfill(body({ report: RD_HEAD, dates: RD_DATES, running: { on: false } }));
    if (p === "/market/research-desk/paper") return r.fulfill(body({ html: RD_PAPER(u.searchParams.get("part")), date: "2026-11-15" }));
    if (p === "/market/watchlist/groups") return r.fulfill(body([{ id: 1, name: "الرئيسية", is_default: true }]));
    return r.fulfill(body([]));
  });
  await page.addInitScript((th) => { try {
    localStorage.setItem("sp_token", "probe");
    for (const k of ["sp_room_symbol", "sp_room_list", "sp_chart_tf", "sp_chart_tf_custom", "sp_chart_type"]) localStorage.removeItem(k);
    if (!sessionStorage.getItem("sp_d736_seeded")) { localStorage.setItem("sp_chart_ind_v3", JSON.stringify({ vol: true, stochrsi: false, cvd: false, d7m: false })); sessionStorage.setItem("sp_d736_seeded", "1"); }
    const s = JSON.parse(localStorage.getItem("sp-app-store") || "{}");
    localStorage.setItem("sp-app-store", JSON.stringify({ ...s, state: { ...(s.state || {}), theme: th }, version: s.version ?? 0 }));
  } catch { } }, theme);
  await page.goto(`http://localhost:${PORT}/watchlist`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(3000);
  const st = () => page.evaluate(() => {
    const r = document.querySelector('[data-role="pro-chart"]'), q = (k) => document.querySelector(`[data-k="${k}"]`)?.textContent || "";
    return r ? { ...r.dataset, o: q("o"), c: q("c"), chg: q("chg"), canv: document.querySelectorAll('[data-role="pc-stage"] canvas').length,
                 cover: !!document.querySelector('[data-role="pc-cover"]') } : null;
  });
  const box = async (sel) => page.locator(sel).first().boundingBox();

  // ١٠ الترتيب والتبويبان
  const lay = await page.evaluate(() => {
    const c = document.querySelector('[data-role="troom-chart"]')?.getBoundingClientRect(), l = document.querySelector('[data-role="troom-list"]')?.getBoundingClientRect();
    const tabs = [...document.querySelectorAll('[data-role="room-tab"]')].map(b => b.textContent.trim());
    return c && l ? { listRight: l.left >= c.right - 1 && Math.abs(c.top - l.top) < 4, below: l.top >= c.bottom - 1, tabs, stageBottom: document.querySelector('[data-role="pc-foot"]').getBoundingClientRect().bottom, H: innerHeight } : null;
  });
  say(!!lay && (desk ? lay.listRight : lay.below) && JSON.stringify(lay.tabs) === JSON.stringify(["الرسم البياني", "مختبر الأبحاث"]),
      `${label}: ${desk ? "الشركاتُ يمينَ الشاشة والرسمُ يسارَها" : "الرسمُ أوّلاً والقوائمُ تحته"}، والتبويبان «الرسم البياني» و«مختبر الأبحاث»`, JSON.stringify(lay?.tabs));
  if (desk) say(lay.stageBottom <= lay.H + 1, `${label}: الرسمُ كلُّه داخل الشاشة بشريطه السفليّ — لا لوحةَ ولا شريطَ تحت الطيّ`, `${Math.round(lay.stageBottom)} ≤ ${lay.H}`);

  // ١١ شموعٌ حقيقيةٌ مقروءة: 421 شمعةً من المصدر (آخرُها مكرَّر) ⇒ 420 على الرسم، والمعروضُ آخرُها لا الكلُّ محشوراً
  const s0 = await st();
  const want = weekly(420, 4), lastW = want[want.length - 1];
  say(!!s0 && s0.bars === "420" && !s0.cover && s0.canv >= 6 && s0.c === fmt(lastW.close) && s0.o === fmt(lastW.open) && s0.last === fmt(lastW.close),
      `${label}: تاريخٌ مكرَّرٌ من المصدر لا يُفرغ الرسم — 420 شمعةً، ووسيلةُ الإيضاح ووسمُ آخر سعرٍ بقيم آخر شمعةٍ حقيقية`, s0 ? `${s0.bars} شمعة · ${s0.o} / ${s0.c}` : "لا رسم");
  say(!!s0 && Number(s0.vis) > 20 && Number(s0.vis) <= (desk ? 170 : 80) && Number(s0.spacing) >= 3 && Number(s0.to) >= 419,
      `${label}: المعروضُ آخرُ الشموع بعرضٍ مقروء — لا 420 شمعةً خيوطاً في عرض الشاشة`, s0 ? `${s0.vis} معروضة · عرضُ الشمعة ${s0.spacing}px` : "");
  say(ext.length === 0, `${label}: لا مكتبةَ تُجلب من الشبكة عند فتح الرسم`, ext[0] || "");

  // ١٢ لوحاتٌ حقيقيةٌ للمؤشّرات بقيمها
  await page.locator('[data-role="pc-ind"]').click();
  for (const k of ["stochrsi", "cvd"]) { await page.locator(`[data-role="pc-ind-menu"] [data-ind="${k}"]`).click(); await sleep(150); }
  await page.mouse.click(5, 5);
  await page.waitForTimeout(1200);
  const panes = await page.evaluate(() => {
    const sb = document.querySelector('[data-role="pc-stage"]').getBoundingClientRect();
    return { n: Number(document.querySelector('[data-role="pro-chart"]').dataset.panes), stage: [sb.top, sb.bottom],
             tags: [...document.querySelectorAll('[data-role="pane-tag"]')].map(e => ({ k: e.dataset.ind, t: e.textContent, y: e.getBoundingClientRect().top,
               v: [...e.querySelectorAll("b")].map(b => b.textContent.trim()),
               f: Math.min(...[...e.querySelectorAll("*")].map(x => parseFloat(getComputedStyle(x).fontSize))) })) };
  });
  const nums = (t) => t.v.filter(x => /^-?\d+\.\d+$/.test(x)).length;
  const srTag = panes.tags.find(t => t.k === "stochrsi");
  say(panes.n === 3 && panes.tags.length === 2 && [...panes.tags].sort((a, b) => a.y - b.y).every((t, i, arr) => !i || t.y - arr[i - 1].y > 40) && panes.tags.every(t => t.y > panes.stage[0] + 100 && t.y < panes.stage[1])
      && nums(panes.tags.find(t => t.k === "cvd") || { v: [] }) >= 1 && !!srTag && nums(srTag) === 2
      && /Stoch RSI 3 3 14 14/.test(srTag.t) && panes.tags.every(t => t.f >= 9.5),
      `${label}: Stoch RSI وCVD D7M لكلٍّ لوحتُه الحقيقيةُ بقيمه — لا رسمٌ فارغ ولا تداخل، والخطُّ ≥ 9.5px`, panes.tags.map(t => `${t.k} ${t.v.join(" ")} @${Math.round(t.y)}`).join(" | "));

  // ١٢ب ‏D744: نافذةُ إعدادات المؤشّر كتريدنق فيو — Stoch RSI يصير 8 8 14 3 ويُحفظ، و«الافتراضي» يعيده
  await page.locator('[data-role="pc-cfg"]').click();
  await page.locator('[data-role="pc-cfg-menu"] [data-cfg="stochrsi"]').click();
  await page.waitForTimeout(250);
  const setNum = async (label, v) => { const i = page.locator(`[data-role="ind-settings"] input[aria-label="${label}"]`); await i.fill(String(v)); await sleep(120); };
  await setNum("K", 8); await setNum("D", 8); await setNum("طولُ الستوكاستيك", 3);
  await page.waitForTimeout(500);
  const srT = await page.locator('[data-role="pane-tag"][data-ind="stochrsi"]').textContent();
  const srSaved = await page.evaluate(() => JSON.parse(localStorage.getItem("sp_stochrsi_cfg") || "{}"));
  await page.locator('[data-role="ind-reset"]').click(); await page.waitForTimeout(400);
  const srBack = await page.locator('[data-role="pane-tag"][data-ind="stochrsi"]').textContent();
  await page.keyboard.press("Escape").catch(() => {});
  await page.locator('[data-role="ind-settings"] button[aria-label="إغلاق"]').click().catch(() => {});
  await page.waitForTimeout(250);
  say(/Stoch RSI 8 8 14 3 close/.test(srT || "") && srSaved.k === 8 && srSaved.stochLen === 3 && /Stoch RSI 3 3 14 14 close/.test(srBack || ""),
      `${label}: إعداداتُ المؤشّر قابلةٌ للتعديل كتريدنق فيو — 8 8 14 3 تُطبَّق فوراً وتُحفظ، و«الافتراضي» يعيد 3 3 14 14`, `${srT} ← ${srBack}`);
  // ١٢ج ‏D744: شريطُ D7M رفيعٌ فوق الرسم (لا جداول فوق الشموع)، والمستوياتُ «مختصر» ستةٌ و«الكل» أكثر، ولا نصَّ على الرسم إلا أرقامُ المستويات
  await page.locator('[data-role="pc-ind"]').click();
  await page.locator('[data-role="pc-ind-menu"] [data-ind="d7m"]').click();
  await page.mouse.click(5, 5);
  await page.waitForTimeout(1200);
  const strip = await page.evaluate(() => { const e = document.querySelector('[data-role="d7m-strip"]'); const r = e?.getBoundingClientRect();
    return { h: r ? Math.round(r.height) : 0, tiles: e ? e.querySelectorAll(".d7s-tile").length : 0, tables: document.querySelectorAll(".d7m-table").length,
             minF: e ? Math.min(...[...e.querySelectorAll("*")].filter(x => [...x.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(x => parseFloat(getComputedStyle(x).fontSize))) : 0 }; });
  const lvCompact = Number((await st()).lv);
  await page.locator('[data-role="pc-fibmode"] button', { hasText: "الكل" }).click(); await page.waitForTimeout(500);
  const lvAll = Number((await st()).lv);
  await page.locator('[data-role="pc-fibmode"] button', { hasText: "مختصر" }).click(); await page.waitForTimeout(300);
  say(strip.tiles >= 4 && strip.h > 0 && strip.h <= 52 && strip.tables === 0 && strip.minF >= 9.5 && lvCompact === 3 && lvAll > 6,
      `${label}: شريطُ D7M بحجم الإصبع (${strip.h}px · ${strip.tiles} شاشات) بلا جداول، والمستوياتُ مختصرةٌ ثلاثةً (‏D756: 1.1 و0.618 و0.5 مخفيّة) و«الكل» ${lvAll}`, `خطٌّ ≥ ${strip.minF}px`);

  // ١٢د ‏D756 (المالك 2026-11-16): عينُ الإخفاء تُخفي مستويات D7M وتعيدها، و‏MACD مؤشّرٌ بلوحته وقيمه، وأرقامُ فيبوناتشي حبّاتٌ أمام آخر شمعة
  const lvOn = Number((await st()).lv);
  await page.locator('[data-role="pc-eye"][data-eye="d7m"]').click(); await page.waitForTimeout(500);
  const lvOff = Number((await st()).lv);
  await page.locator('[data-role="pc-eye"][data-eye="d7m"]').click(); await page.waitForTimeout(500);
  const lvBack = Number((await st()).lv);
  const pz0 = Number((await st()).panes);
  await page.locator('[data-role="pc-ind"]').click();
  await page.locator('[data-role="pc-ind-menu"] [data-ind="macd"]').click();
  await page.mouse.click(5, 5); await page.waitForTimeout(1200);
  const mTag = await page.locator('[data-role="pane-tag"][data-ind="macd"]').textContent().catch(() => "");
  const mVals = (await page.locator('[data-role="pane-tag"][data-ind="macd"] b').allTextContents().catch(() => [])).filter(x => /\d/.test(x));
  const pz1 = Number((await st()).panes);
  say(lvOn >= 3 && lvOff === 0 && lvBack === lvOn && pz1 === pz0 + 1 && /MACD 12 26 close 9/.test(mTag || "") && mVals.length === 3,
      `${label}: ‏D756 العينُ تُخفي مؤشّرَ D7M وتعيده، و‏MACD لوحةٌ بقيمه الثلاث`, `مستويات ${lvOn}→${lvOff}→${lvBack} · لوحات ${pz0}→${pz1} · ${mVals.join(" · ")}`);
  await page.locator('[data-role="pc-ind"]').click();
  await page.locator('[data-role="pc-ind-menu"] [data-ind="macd"]').click();
  await page.mouse.click(5, 5); await page.waitForTimeout(700);

  // ١٣ الإطارُ المخصَّص: 6 ساعات
  await page.locator('[data-role="pc-tf-more"]').click();
  await page.waitForTimeout(250);
  const inp = page.locator('[data-role="pc-custom"] input');
  await inp.fill("6");
  await page.locator('[data-role="pc-custom"] .seg-btn', { hasText: "ساعة" }).click();
  const applyTxt = (await page.locator('[data-role="pc-custom-apply"]').textContent() || "").trim();
  await page.locator('[data-role="pc-custom-apply"]').click();
  await page.waitForTimeout(1300);
  const s6 = await st();
  const saved6 = await page.evaluate(() => [localStorage.getItem("sp_chart_tf"), localStorage.getItem("sp_chart_tf_custom")]);
  const onBar = await page.locator('[data-role="pc-tfs"] .pc-tf.on').first().textContent();
  say(applyTxt === "اعرض 6 ساعات" && reqs.some(x => /\?6h$/.test(x)) && s6.tf === "6h" && saved6[0] === "6h" && /6h/.test(saved6[1] || "") && onBar.trim() === "6س" && !s6.cover,
      `${label}: إطارٌ مخصَّص «6 ساعات» يُطلب من الخادم ويُعرض ويُحفظ ويبقى زرّاً في الشريط`, `${reqs.filter(x => /6h/.test(x))[0]} · ${onBar}`);
  await page.locator('[data-role="pc-tfs"] .pc-tf', { hasText: desk ? "أسبوع" : "6س" }).first().click().catch(() => {});
  if (!desk) { await page.locator('[data-role="pc-tf-more"]').click(); await page.locator('[data-role="pc-tf-more-menu"] .pc-tf', { hasText: "أسبوع" }).click(); }
  await page.waitForTimeout(1200);

  // ١٣ب المنطقةُ الزمنية كتريدنق فيو: «توقيتُ البورصة» افتراضاً، والساعةُ تعمل، وكلُّ اختيارٍ يُعيد كتابةَ أوقات الشموع ويُحفظ
  await page.locator('[data-role="pc-tfs"] .pc-tf', { hasText: "1س" }).first().click().catch(async () => {
    await page.locator('[data-role="pc-tf-more"]').click(); await page.locator('[data-role="pc-tf-more-menu"] .pc-tf', { hasText: /^ساعة$/ }).click(); });
  await page.waitForTimeout(1200);
  const tzRead = () => page.evaluate(() => ({ last: document.querySelector('[data-role="pro-chart"]').dataset.lastT,
    btn: document.querySelector('.pc-btn[data-role="pc-tz"]')?.textContent || "", clock: document.querySelector('[data-role="pc-clock"]')?.textContent || "" }));
  const tz0 = await tzRead();
  const pickTz = async (k) => { await page.locator('.pc-btn[data-role="pc-tz"]').click(); await page.locator(`[data-role="pc-tz-menu"] [data-tz="${k}"]`).click(); await page.waitForTimeout(700); return tzRead(); };
  const tzU = await pickTz("UTC"), tzS = await pickTz("America/Sao_Paulo"), tzN = await pickTz("America/New_York");
  const keptTz = await page.evaluate(() => localStorage.getItem("sp_chart_tz"));
  say(/ 13:00$/.test(tz0.last) && /\(UTC\+3\)/.test(tz0.btn) && /^\d{2}:\d{2}:\d{2}$/.test(tz0.clock) && / 10:00$/.test(tzU.last) && /\(UTC\)/.test(tzU.btn)
      && / 07:00$/.test(tzS.last) && /UTC−3/.test(tzS.btn) && / 06:00$/.test(tzN.last) && keptTz === "America/New_York",
      `${label}: المنطقةُ الزمنية كتريدنق فيو — البورصة (UTC+3) ثمّ UTC ثمّ UTC−3 ثمّ نيويورك (صيفيٌّ في 20 أكتوبر: UTC−4) تُعيد أوقاتَ الشموع، والساعةُ تعمل، والاختيارُ يُحفظ`,
      `${tz0.last} · ${tzU.last} · ${tzS.last} · ${tzN.last} · ${tz0.clock}`);
  await pickTz("exchange");
  // ١٣ج أزرارُ المدى تختار إطارَها وتعرض مدّتَها، والمقياسُ النسبيُّ واللوغاريتميّ
  await page.locator('[data-role="pc-ranges"] .pc-tf', { hasText: "5 سنوات" }).click();
  await page.waitForTimeout(1300);
  const r5 = await st();
  await page.locator('[data-role="pc-pct"]').click(); await page.waitForTimeout(250);
  const sPct = (await st()).scale;
  await page.locator('[data-role="pc-log"]').click(); await page.waitForTimeout(250);
  const sLog = (await st()).scale;
  await page.locator('[data-role="pc-log"]').click(); await page.waitForTimeout(250);
  say(r5.tf === "1wk" && Math.abs(Number(r5.vis) - 263) <= 6 && sPct === "2" && sLog === "1" && (await st()).scale === "0",
      `${label}: «5 سنوات» يختار الأسبوعيَّ ويعرض خمسَ سنوات، و% وlog يبدّلان مقياسَ السعر`, `${r5.tf} · ${r5.vis} شمعة (${r5.to} من ${r5.bars}) · ${sPct}/${sLog}`);

  // ١٤ خطُّ التقاطع والتكبير والسحب (الحاسوب) — «تحريك السهم»
  const sb = await box('[data-role="pc-stage"]');
  if (desk) {
    const a0 = await st();
    await page.mouse.move(sb.x + sb.width * 0.3, sb.y + 150);
    await page.waitForTimeout(250);
    const a1 = await st();
    say(a1.c !== a0.c && /\d/.test(a1.c) && /%\)$/.test(a1.chg), `${label}: خطُّ التقاطع يقرأ شمعتَه — وسيلةُ الإيضاح تتبعه بقيمها وتغيّرها`, `${a0.c} ← ${a1.c} ${a1.chg}`);
    for (let i = 0; i < 4; i++) { await page.mouse.wheel(0, -240); await sleep(70); }
    await page.waitForTimeout(400);
    const a2 = await st();
    say(Number(a2.vis) < Number(a0.vis) && a2.canv === a0.canv, `${label}: العجلةُ تكبّر حول المؤشّر — واللوحةُ نفسُها`, `${a0.vis} ← ${a2.vis} معروضة`);
    await page.mouse.move(sb.x + 200, sb.y + 180); await page.mouse.down(); await page.mouse.move(sb.x + 620, sb.y + 185, { steps: 10 }); await page.mouse.up();
    await page.waitForTimeout(900);
    const a3 = await st();
    const live = page.locator('[data-role="pc-live"]');
    say(Number(a3.to) < Number(a2.to) - 5 && (await live.count()) === 1, `${label}: السحبُ يحرّك الشموعَ إلى الماضي ويظهر زرُّ العودة`, `${a2.to} ← ${a3.to}`);
    await live.click();
    await page.waitForTimeout(500);
    const a4 = await st();
    say(Number(a4.to) >= 419 && (await live.count()) === 0, `${label}: وزرُّ العودة يعيد آخرَ شمعة`, a4.to);
  }

  // ١٥ أدواتُ الرسم: خطُّ اتجاهٍ بنقرتين سريعتين، وأفقيّ، وفرشاة — تُحفظ على الرمز المعروض
  await page.locator('[data-role="pc-draw"]').click();
  await page.waitForTimeout(350);
  const s2 = await box('[data-role="pc-stage"]');
  const sym = (await st()).symbol;
  const tap = async (x, y) => { if (desk) await page.mouse.click(x, y); else await page.touchscreen.tap(x, y); };
  await page.locator('[data-tool="trend"]').click();
  await tap(s2.x + s2.width * 0.25, s2.y + 150);
  await sleep(120);                                              // دون نصف ثانية: كانت المكتبةُ تبتلع الثانية
  await tap(s2.x + s2.width * 0.6, s2.y + 100);
  await page.waitForTimeout(350);
  await page.locator('[data-tool="hline"]').click();
  await tap(s2.x + s2.width * 0.4, s2.y + 170);
  await page.waitForTimeout(350);
  if (desk) {
    await page.locator('[data-tool="brush"]').click();
    await page.mouse.move(s2.x + 150, s2.y + 90); await page.mouse.down();
    for (let i = 1; i <= 24; i++) await page.mouse.move(s2.x + 150 + i * 7, s2.y + 90 + 20 * Math.sin(i / 3));
    await page.mouse.up();
    await page.waitForTimeout(350);
    await page.locator('[data-tool="null"]').click();
  }
  const lastSave = saves[saves.length - 1] || [null, {}];
  const items = lastSave[1].items || [];
  const tr = items.find(x => x.a && x.b), hl = items.find(x => typeof x.h === "number"), fr = items.find(x => Array.isArray(x.free));
  say(lastSave[0] === sym && !!tr && tr.v === 3 && tr.a.t !== tr.b.t && !!hl && (!desk || (fr && fr.free.length > 10 && fr.free.some(q => q.o > 0 && q.o < 1))),
      `${label}: خطُّ الاتجاه (نقرتان سريعتان) والأفقيُّ${desk ? " والفرشاةُ بمواضعها الكسريّة" : ""} تُحفظ على الرمز المعروض ${sym}`,
      `${lastSave[0]} · ${items.map(x => (x.a ? "اتجاه" : x.h != null ? "أفقيّ" : "فرشاة")).join(" · ")}`);
  const dr = await st();
  say(Number(dr.draws) === items.length && Number(dr.segs) >= 1, `${label}: والرسمُ على اللوحة نفسِها`, `${dr.draws} رسماً · ${dr.segs} خطّاً`);
  await page.locator('[data-role="pc-undo"]').click();
  await page.waitForTimeout(250);
  say(Number((await st()).draws) === items.length - 1, `${label}: والتراجعُ يزيل آخرَ رسم`);

  // ١٦ تبديلُ الشركة: الرسمُ نفسُه يبقى، والمشهدُ على آخر شموعها
  await page.evaluate(() => { document.querySelector('[data-role="pc-stage"] canvas').__same = 1; });
  if (!desk) await page.locator('[data-role="troom-list"]').scrollIntoViewIfNeeded();
  await page.locator('[data-role="troom-row"]').nth(1).click();
  await page.waitForTimeout(1500);
  const sw = await st();
  const same = await page.evaluate(() => document.querySelector('[data-role="pc-stage"] canvas')?.__same === 1);
  say(same && sw.symbol === "2222" && reqs.some(x => /^2222\?/.test(x)) && Number(sw.to) >= 419 && Number(sw.draws) === 0 && !sw.cover,
      `${label}: الضغطُ على شركةٍ يبدّل شموعَ الرسم نفسِه (لا يُهدم ويُبنى) ورسومُ كلّ شركةٍ لها`, `${sw.symbol} · ${sw.bars} شمعة`);
  await page.locator('[data-role="troom-tab"]', { hasText: "المؤشرات" }).click();
  await page.locator('[data-role="troom-row"]', { hasText: "S&P 500" }).click();
  await page.waitForTimeout(1500);
  const ix = await st();
  const volTxt = await page.locator('[data-role="pc-legend"] [data-ind="vol"]').textContent().catch(() => "");
  say(logoReq.includes("^GSPC") && logoReq.some(x => x === "^TASI"), `${label}: شعاراتُ الرموز غير السعودية والمؤشّرات تُطلب من خادمنا (شعاراتُ تريدنق فيو الرسمية)`, [...new Set(logoReq)].slice(0, 5).join(" · "));
  say(ix.symbol === "^GSPC" && ix.bars === "420" && /\d/.test(ix.c) && !ix.cover && /غير متوفّر/.test(volTxt || ""),
      `${label}: والمؤشّراتُ (S&P 500) تُرسم بشموعها — وحجمٌ لا يسلّمه المصدر «غير متوفّر» لا أعمدةٌ صفرية`, `${ix.symbol} · ${ix.bars} شمعة · ${volTxt}`);

  // ١٧ ملءُ الشاشة، والقياسات
  if (!desk) await page.evaluate(() => scrollTo(0, 0));
  await page.locator('[data-role="pc-full"]').click();
  await page.waitForTimeout(600);
  const fb = await page.evaluate(() => { const r = document.querySelector('[data-role="pro-chart"]').getBoundingClientRect(); return [r.left, r.top, r.width, r.height, innerWidth, innerHeight]; });
  say(fb[0] === 0 && fb[1] === 0 && fb[2] === fb[4] && Math.abs(fb[3] - fb[5]) <= 1, `${label}: ملءُ الشاشة يغطّيها كلَّها`, fb.slice(2).join("×"));
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `pro_full_${vp.width}_${theme}.png`) });
  await page.locator('[data-role="pc-full"]').click();
  await page.waitForTimeout(500);
  const m = await page.evaluate(() => {
    const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    const sw = Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0);
    const root = document.querySelector('[data-role="pro-chart"]');
    const t = [...root.querySelectorAll("button")].filter(e => e.offsetParent).map(e => { const r = e.getBoundingClientRect(); return Math.min(r.width, r.height); });
    const f = [...root.querySelectorAll("*")].filter(e => e.offsetParent && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())).map(e => parseFloat(getComputedStyle(e).fontSize));
    const icons = ["pc-draw", "pc-ind", "pc-type", "pc-full"].every(k => !!root.querySelector(`[data-role="${k}"] svg`));
    return { over: sw - W, minT: Math.min(...t), minF: Math.min(...f), icons, tfs: [...root.querySelectorAll('[data-role="pc-tfs"] .pc-tf')].filter(e => e.offsetParent).length };
  });
  say(m.over <= 1 && m.minT >= 32 && m.minF >= 9.5 && m.icons, `${label}: لا فيضَ أفقيّ، وأزرارُ الرسم ≥ 32px، وخطٌّ ≥ 9.5px، وللرسم والمؤشّرات والنوع وملء الشاشة أيقونات`,
      `${m.over}px · ${Math.round(m.minT)}px · ${m.minF}px`);
  if (!desk) say(m.tfs === 1, `${label}: الإطارُ الجاري وحده في الشريط وبقيّتُها في قائمته — كتطبيق تريدنق فيو`, `${m.tfs}`);
  if (SHOTS) await page.screenshot({ path: join(SHOTS, `pro_${vp.width}_${theme}.png`) });

  // ١٨ مختبرُ الأبحاث تبويبٌ هنا (‏D763: عقودُ الخيارات · المحفظة · صقر)، وروابطُه القديمة تصله — والتقريرُ اليوميّ انتقل إلى مفكرة السوق
  await page.locator('[data-role="room-tab"]', { hasText: "مختبر الأبحاث" }).click();
  await page.waitForTimeout(1200);
  const labHere = await page.evaluate(() => ({ url: location.pathname + location.search, chart: !!document.querySelector('[data-role="pro-chart"]'), lab: !!document.querySelector('[data-role="research-lab"]'),
    tabs: [...document.querySelectorAll('[data-role="rl-views"] [role="tab"]')].map(b => b.textContent.trim()), doc: !!document.querySelector('[data-role="rl-doc"]') }));
  // ‏D746: التقريرُ ورقةٌ واحدة (التقرير اليومي · التوصيات)، وأيامٌ مؤرّخة، وملفّ PDF، ولا مكتبةَ ولا مصادر — في مفكرة السوق بجانب التوقعات (‏D763)
  await page.evaluate(() => { try { sessionStorage.setItem("sp:market:tab", "calendar"); } catch { /* */ } });
  await page.goto(`http://localhost:${PORT}/market`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.locator('[data-role="ev-report"]').click({ timeout: 8000 }).catch(() => {});
  await page.waitForTimeout(1800);
  const paperOf = () => page.evaluate(() => { const f = document.querySelector('[data-role="rl-doc"] iframe');
    return { h1: f?.contentDocument?.querySelector("h1")?.textContent || null, h: f ? f.getBoundingClientRect().height : 0 }; });
  const doc = await page.evaluate(() => { const W = document.documentElement.clientWidth, main = document.querySelector(".app-main");
    return { tabs: [...document.querySelectorAll('[data-role="rl-tab"]')].map(b => b.textContent.trim()),
             days: [...document.querySelectorAll('[data-role="rl-day"]')].map(b => b.textContent.trim()),
             months: [...document.querySelectorAll('[data-role="rl-days"] .rl-mname')].map(b => b.textContent.trim()),
             pdf: !!document.querySelector('[data-role="rl-pdf"]'), lib: !!document.querySelector('[data-role="rl-lib"]'),
             srcs: (document.querySelector('[data-role="daily-report"]')?.textContent || "").includes("المصادر"),
             over: Math.max(document.documentElement.scrollWidth, main ? main.scrollWidth : 0) - W }; });
  const p1 = await paperOf();
  const all = await page.evaluate(() => [...(document.querySelector('[data-role="rl-doc"] iframe')?.contentDocument?.querySelectorAll("h1") || [])].map(h => h.textContent));
  say(doc.tabs.length === 0 && JSON.stringify(doc.days) === JSON.stringify(["15", "12", "29"])
      && JSON.stringify(doc.months) === JSON.stringify(["نوفمبر 2026", "أكتوبر 2026"]) && doc.pdf && !doc.lib && !doc.srcs
      && p1.h1 === "التقرير اليومي" && p1.h >= 1000 && JSON.stringify(all) === JSON.stringify(["التقرير اليومي", "محفظتنا واختياراتنا"]) && doc.over <= 1,
      `${label}: التقريرُ اليوميّ (في مفكرة السوق) تقريرٌ واحدٌ بتاريخه — السوقُ ثمّ محفظتُنا واختياراتُنا في الورقة نفسِها، وملفّ PDF، ولا مكتبةَ ولا مصادر`, JSON.stringify({ ...doc, p1, all }));
  let olds = 0;
  for (const old of ["/stars", "/ai?tab=lab"]) {
    await page.goto(`http://localhost:${PORT}${old}`, { waitUntil: "load", timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(1800);
    if ((await page.evaluate(() => location.pathname + location.search)) === "/watchlist?tab=lab") olds++;
  }
  say(labHere.url === "/watchlist?tab=lab" && labHere.lab && !labHere.chart && !labHere.doc && JSON.stringify(labHere.tabs) === JSON.stringify(["عقود الخيارات", "المحفظة", "صقر"]) && olds === 2,
      `${label}: «مختبر الأبحاث» تبويبٌ في الغرفة (عقودُ الخيارات · المحفظة · صقر — بلا التقرير)، ورابطاه القديمان يفتحانه`, `${labHere.url} · ${labHere.tabs.join("/")} · ${olds}/2`);
  say(errs.length === 0, `${label}: لا خطأ`, errs[0] || "");
  await ctx.close();
}
await browser.close();
done();
