// ─────────────────────────────────────────────────────────────────────────
// مؤشّرُ D7M (سكربت المالك) — حسابُ الفيبوناتشي والقناة يطابق منطق Pine (D463).
// يُترجَم `d7m.ts` بـesbuild ويُنادى على مسارٍ معلومِ القمم والقيعان:
// صعودٌ من 100 إلى 200 ثمّ تراجع — فمستوى 0 عند القمّة (200) و1 عند القاع
// (100) و0.5 عند 150 و0.618 عند 138.2، كما يحسبها السكربت بلا عكس.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdtempSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const ES = join(ROOT, "frontend/node_modules/esbuild/lib/main.js");
if (!existsSync(ES)) { console.log("… لم يُقَس: esbuild غيرُ مثبّت"); process.exit(0); }
const esbuild = await import(pathToFileURL(ES).href);
const out = join(mkdtempSync(join(tmpdir(), "d7m-")), "d7m.mjs");
await (esbuild.build || esbuild.default.build)({ entryPoints: [join(ROOT, "frontend/src/components/analysis/d7m.ts")],
  bundle: true, format: "esm", outfile: out, platform: "neutral", logLevel: "silent" });
const M = await import(pathToFileURL(out).href);
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };

// مسار: قاعٌ 100 عند 30 · قمّةٌ 200 عند 60 · تراجعٌ بعدها
const bars = [];
for (let i = 0; i < 80; i++) {
  const c = i <= 30 ? 130 - i : i <= 60 ? 100 + (i - 30) * (100 / 30) : 200 - (i - 60) * 2;
  const h = i === 60 ? 200 : c + 1, l = i === 30 ? 100 : c - 1;
  bars.push({ date: `d${i}`, open: c, high: Math.max(h, c), low: Math.min(l, c), close: c });
}
bars[30].high = 101; bars[60].low = 199;
const f = M.autoFib(bars, 1, 7);
const at = lv => f && f.lines.find(x => Math.abs(x.level - lv) < 1e-9)?.price;
say(!!f, "١ يُبنى فيبوناتشي من آخر ضلعٍ للزجزاج");
say(!!f && Math.abs(at(0) - 200) < 0.01 && Math.abs(at(1) - 100) < 0.01, "٢ المستوى 0 عند القمّة و1 عند القاع (بلا عكس)", `${at(0)} · ${at(1)}`);
say(!!f && Math.abs(at(0.5) - 150) < 0.01 && Math.abs(at(0.618) - 138.2) < 0.01, "٣ و0.5 = 150 و0.618 = 138.2", `${at(0.5)} · ${at(0.618)}`);
say(!!f && f.lines.find(x => x.level === 0.5)?.title === "دعــم قـوي" && f.lines.find(x => x.level === 0.618)?.title === "اتجاه معاكس",
    "٤ ونصّا المستويين كما في السكربت");
say(!!f && f.lines.length === 14, "٥ والمستوياتُ الظاهرةُ افتراضاً في السكربت أربعَ عشرة", String(f && f.lines.length));
say(!!f && f.zones.some(z => z.title === "الــمــقــاومــة") && f.zones.some(z => z.title === "الـــدعـــم"),
    "٦ ومناطقُ المقاومة والدعم بأسمائها");

// ٧–١٠ (D464): المتوسط الأسّي والاتجاه ولوحة القرار وإعداداتٌ لكلّ مدخل
const e = M.ema([1, 2, 3, 4, 5], 3);
say(e[1] === null && Math.abs(e[2] - 2) < 1e-9 && Math.abs(e[4] - 4) < 1e-9, "٧ EMA يبدأ بمتوسط أوّل len كما في Pine", JSON.stringify(e));
const up = [], dn = [];
for (let i = 0; i < 300; i++) {
  const u = 100 + i * 0.5 + Math.sin(i / 6) * 4, d = 300 - i * 0.5 + Math.sin(i / 6) * 4;
  up.push({ date: new Date(Date.UTC(2024, 0, 1 + i)).toISOString().slice(0, 10), open: u - 0.3, high: u + 1, low: u - 1, close: u, volume: 1000 });
  dn.push({ date: up[i].date, open: d + 0.3, high: d + 1, low: d - 1, close: d, volume: 1000 });
}
// مسارٌ صاعدٌ بقيعانٍ حادّة (V) وشموعٍ بلا ذيول — كتاسي اليوميّ: الإغلاقُ = القمّة عند المحور
const vb = []; let pv = 100;
for (let i = 0; i < 600; i++) { const ph = i % 60, c = 100 + i * 0.3 + 10 * Math.abs(ph - 30) / 30;
  vb.push({ date: `v${i}`, open: pv, high: Math.max(pv, c), low: Math.min(pv, c), close: c }); pv = c; }
const t = M.autoTrend(vb, 15);
say(t.lines.some(l => l.up), "٨ يرسم الاتجاهُ التلقائيّ خطَّ القيعان الصاعدة ولو بلا ذيول", String(t.lines.length));
// ٩ (D465): صفوفُ اللوحة كما في السكربت — 1D (EMA200 يومي) و4H · 1H · 15M (VWAP الجلسة من شموع 15د)
const m15Up = [], m15Dn = [];
for (let k = 0; k < 20; k++) { const u = 10 + k * 0.1, d = 12 - k * 0.1;
  m15Up.push({ date: "s", open: u - 0.05, high: u + 0.02, low: u - 0.06, close: u, volume: 100 });
  m15Dn.push({ date: "s", open: d + 0.05, high: d + 0.06, low: d - 0.02, close: d, volume: 100 }); }
const du = M.dashboard(up, { daily: up, m15: m15Up }), dd = M.dashboard(dn, { daily: dn, m15: m15Dn });
const mix = M.dashboard(dn, { daily: dn, m15: m15Up });
say(!!du && du.rows.map(r => r.tf).join() === "1D,4H,1H,15M" && du.score === 10 && dd.score === -10 && mix.score === -4 + 3 + 2 + 1,
    "٩ اللوحة: 1D · 4H · 1H · 15M بأوزان 4 · 3 · 2 · 1 كما في السكربت", du && dd && mix ? `${du.score} · ${dd.score} · ${mix.score}` : "null");
say(M.D7M_DEFAULTS.bull === 6 && M.D7M_DEFAULTS.bear === -6 && mix.summary === "محايد" && mix.decision !== undefined,
    "٩ب وحدّا الاتجاه 6 / −6 من عشرة (قيمةُ السكربت)", `${M.D7M_DEFAULTS.bull} · ${M.D7M_DEFAULTS.bear}`);
const keys = Object.keys(M.D7M_DEFAULTS);
const { readFileSync } = await import("node:fs");
const panel = readFileSync(join(ROOT, "frontend/src/components/analysis/D7MPanel.tsx"), "utf8");
const miss = keys.filter(k => !new RegExp(`["']${k}["']`).test(panel));
say(miss.length === 0, "١٠ لوحةُ الإعدادات تتحكّم في كلّ مدخلٍ للمؤشّر", miss.join(","));
const nc = readFileSync(join(ROOT, "frontend/src/components/analysis/NativeChart.tsx"), "utf8");
const usedColors = M.D7M_COLORS.map(c => c[0]).filter(k => !new RegExp(`C\\("${k}"\\)|colors\\?\\.${k}\\b|colors\\?\\.\\[k\\]`).test(nc));
say(/type="color"/.test(panel) && usedColors.length === 0, "١١ ألوانُ المؤشّر تُختار من الإعدادات وتصل إلى الرسم", usedColors.join(","));
console.log((fail ? "FAIL" : "PASS") + " D463/D464 — مؤشّرُ D7M يطابق سكربتَ المالك");
process.exit(fail);
