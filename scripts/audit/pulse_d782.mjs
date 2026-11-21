// ─────────────────────────────────────────────────────────────────────────
// D782 — حسابُ لوحتي القوّة (بأمر المالك 2026-11-21): «نحتاج نعرف حاجتين: الاتجاه والسيولة — هل الاتجاهُ ذاهبٌ للصعود أو للهبوط، وهل
// السيولةُ ذاهبةٌ للصعود أو للهبوط». يُترجَم ‏analysis/pulse.ts بـesbuild ويُنادى على مساراتٍ معلومة: صعودٌ نظيفٌ بحجمٍ في الأيام الصاعدة،
// وهبوطٌ مثلُه، وتذبذبٌ بلا وجهة، وصعودٌ يُباع فيه بحجمٍ ثقيل (تصريف)، ومصدرٌ بلا أحجام.
// ─────────────────────────────────────────────────────────────────────────
import { existsSync, mkdtempSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath, pathToFileURL } from "node:url";
const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const ES = join(ROOT, "frontend/node_modules/esbuild/lib/main.js");
if (!existsSync(ES)) { console.log("… لم يُقَس: esbuild غيرُ مثبّت"); process.exit(0); }
const esbuild = await import(pathToFileURL(ES).href);
const out = join(mkdtempSync(join(tmpdir(), "pulse-")), "pulse.mjs");
await (esbuild.build || esbuild.default.build)({ entryPoints: [join(ROOT, "frontend/src/components/analysis/pulse.ts")],
  bundle: true, format: "esm", outfile: out, platform: "neutral", logLevel: "silent" });
const P = await import(pathToFileURL(out).href);
let fail = 0;
const say = (ok, l, d = "") => { if (!ok) fail = 1; console.log(`${ok ? "PASS" : "FAIL"} ${l}${d ? " — " + d : ""}`); };

/* مسارٌ بخطوةٍ يومية: ‏step للاتجاه، وموجةٌ صغيرةٌ فوقه، والحجمُ أثقلُ في الشموع الصاعدة (أو الهابطة) بحسب ‏heavyUp */
const path = (n, step, wave, heavyUp, vol = true) => Array.from({ length: n }, (_, i) => {
  const base = 100 + i * step + Math.sin(i / 2) * wave, prev = 100 + (i - 1) * step + Math.sin((i - 1) / 2) * wave;
  const up = base >= prev, o = prev, c = base;
  return { date: `d${i}`, open: o, high: Math.max(o, c) + 0.4, low: Math.min(o, c) - 0.4, close: c,
    volume: vol ? (up === heavyUp ? 3e6 : 1e6) : 0 };
});
const up = path(160, 0.6, 1.2, true), dn = path(160, -0.6, 1.2, false), chop = path(160, 0, 3, true), dist = path(160, 0.35, 1.2, false);
const tU = P.trendForce(up), lU = P.liquidityForce(up, true), tD = P.trendForce(dn), lD = P.liquidityForce(dn, true);
say(tU.side === "up" && tU.strength >= 55 && lU.side === "up" && /للصعود/.test(lU.word) && tD.side === "down" && tD.strength >= 55 && lD.side === "down" && /للهبوط/.test(lD.word),
  "١ صعودٌ نظيفٌ بحجمٍ في الأيام الصاعدة ⇒ الاتجاهُ صاعدٌ قويّ والسيولةُ داخلةٌ للصعود؛ والهبوطُ مثلُه بعكسه",
  `${tU.word} ${tU.level} ${tU.strength} · ${lU.word} ${lU.strength} | ${tD.word} ${tD.strength} · ${lD.word} ${lD.strength}`);
const tC = P.trendForce(chop);
say(tC.side === "flat" && tC.strength <= 34 && tC.word === "عرضيّ", "٢ التذبذبُ بلا وجهة ⇒ «عرضيّ» بقوّةٍ ضعيفة (≤ 34)", `${tC.word} ${tC.strength}`);
const tS = P.trendForce(dist), lS = P.liquidityForce(dist, true);
say(tS.side === "up" && lS.side === "down", "٣ اللوحتان مستقلّتان: صعودٌ يُباع فيه بحجمٍ ثقيل ⇒ الاتجاهُ صاعدٌ والسيولةُ خارجةٌ للهبوط (تصريف) — إنذارٌ لا يراه من ينظر إلى السعر وحده",
  `${tS.word} · ${lS.word}`);
const na = P.liquidityForce(path(160, 0.6, 1.2, true, false), true), na2 = P.liquidityForce(up, false);
say(na.side === "na" && na.word === "غير متوفّر" && na2.side === "na" && P.trendForce(up.slice(0, 20)) === null,
  "٤ بلا أحجامٍ من المصدر «غير متوفّر» لا رقمٌ مختلَق، وبلا شموعٍ كافية (دون 30) لا لوحة", `${na.word} · ${na2.stat}`);
say(P.levelWord(80) === "قويٌّ جدّاً" && P.levelWord(60, true) === "قويّة" && P.levelWord(40) === "متوسّط" && P.levelWord(10, true) === "ضعيفة"
  && tU.why.length >= 5 && tU.stat.startsWith("ADX") && lU.stat.startsWith("الحجم"),
  "٥ الدرجةُ بالفصحى (مذكّرةٌ للاتجاه مؤنّثةٌ للسيولة) والشواهدُ معها (ستةٌ للاتجاه · ثلاثةٌ للسيولة) وأوّلُها ‏ADX والحجمُ النسبيّ", tU.why.map(w => w[1]).join(" · "));
console.log("\nالنتيجة:", fail ? "عطب ✖" : "نظيف ✔");
process.exit(fail);
