// ─────────────────────────────────────────────────────────────────────────
// D182 — صفُّ المجموع في جدول التوزيع: مجموعٌ يُكتب، وعائدٌ يُرجَّح.
//
// طلبان من المالك: أن يكون المجموعُ المستهدف رقماً يكتبه (سبعون بالمئة
// للمحفظة والباقي نقداً) بدل مئةٍ مفروضة، وأن يظهر تحت عمود «الوزن
// المستهدف» في صفّ المجموع **معدّلُ عائد التوزيعات** بهذه الأوزان.
//
// والخطرُ في الثاني حسابيّ: شركةٌ لا يصلنا عائدُها إن عُدّت صفراً خفضت
// المعدّل — رقمٌ مختلَق بصيغة حساب. فتخرج من البسط والمقام معاً.
//
// فحصٌ سلوكيّ: تُستورد الدالّةُ **نفسُها** التي يستدعيها المكوّن وتُشغَّل،
// لا نسخةٌ منها في هذا الملفّ — فنسخةُ الفحص تنجح ولو تعطّلت الشيفرة.
// ─────────────────────────────────────────────────────────────────────────
import { readFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const SRC = join(ROOT, "frontend/src/lib/allocMath.ts");

// esbuild يسكن في اعتماديات الواجهة — يُستورد بمساره لا باسمه.
const { build } = await import(
  pathToFileURL(join(ROOT, "frontend/node_modules/esbuild/lib/main.js")).href);

let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

const out = join(mkdtempSync(join(tmpdir(), "sp-alloc-")), "allocMath.mjs");
await build({ entryPoints: [SRC], outfile: out, format: "esm", bundle: false, logLevel: "silent" });
const { weightedDividendYield, retainedCashPct } = await import(pathToFileURL(out).href);

const near = (a, b) => a != null && Math.abs(a - b) < 1e-9;
const W = (r) => r.w;

// ١ · الترجيحُ بالوزن لا المتوسّطُ الحسابيّ.
//    ٧٠×٦ + ٣٠×٢ = ٤٨٠ ÷ ١٠٠ = ٤٫٨٪ (والمتوسّطُ الساذج ٤٫٠٪).
say(near(weightedDividendYield(
  [{ w: 70, dividend_yield: 6 }, { w: 30, dividend_yield: 2 }], W).value, 4.8),
  "١ المعدّلُ مرجّحٌ بالوزن المستهدف", "٤٫٨٪ لا ٤٫٠٪");

// ٢ · والمجموعُ دون المئة لا يغيّر المعدّل — النسبةُ بين الأوزان هي الحاكمة.
say(near(weightedDividendYield(
  [{ w: 49, dividend_yield: 6 }, { w: 21, dividend_yield: 2 }], W).value, 4.8),
  "٢ ولا يتأثّر بكون المجموع سبعين لا مئة");

// ٣ · المجهولُ يخرج من الطرفين — لا يُعدّ صفراً.
{
  const r = weightedDividendYield(
    [{ w: 50, dividend_yield: 6 }, { w: 50, dividend_yield: null }], W);
  say(near(r.value, 6) && r.unknown === 1,
    "٣ الشركةُ بلا عائدٍ معلوم تخرج من البسط والمقام",
    `المعدّل ${r.value} · مجهولة ${r.unknown}`);
}

// ٤ · وزنٌ صفرٌ لا يدخل أصلاً.
say(near(weightedDividendYield(
  [{ w: 0, dividend_yield: 99 }, { w: 10, dividend_yield: 3 }], W).value, 3),
  "٤ الوزنُ صفرٌ خارج الحساب");

// ٥ · لا عائدَ معلوماً ⇒ null لا صفر.
say(weightedDividendYield([{ w: 10, dividend_yield: null }], W).value === null,
  "٥ بلا عائدٍ معلومٍ ⇒ «غير متوفّر» لا صفر");

// ٦ · وقيمةٌ غيرُ محدودةٍ تُعامَل معاملةَ المجهول.
say(weightedDividendYield([{ w: 10, dividend_yield: Infinity }], W).value === null,
  "٦ والقيمةُ غيرُ المحدودة مجهولةٌ كذلك");

// ٧ · الباقي نقداً.
say(retainedCashPct(70) === 30 && retainedCashPct(100) === 0 && retainedCashPct(0) === 0,
  "٧ الباقي نقداً = 100 − المجموع المستهدف");

// ٨ · والمكوّنُ يستدعي هذه الدالّةَ بعينها — لا نسخةً محلّية.
{
  const page = readFileSync(join(ROOT, "frontend/src/pages/PortfolioPage.tsx"), "utf8");
  const imports = /import\s*\{[^}]*weightedDividendYield[^}]*\}\s*from\s*"\.\.\/lib\/allocMath"/.test(page);
  say(imports && page.includes("weightedDividendYield("),
    "٨ جدولُ التوزيع يستدعي الدالّةَ المفحوصة نفسَها");
}

// ٩ · والخادمُ ينشر عائدَ كلّ شركة، وإلا فلا شيءَ يُرجَّح.
{
  const api = readFileSync(join(ROOT, "backend/app/api/v1/endpoints/allocation.py"), "utf8");
  say(/"dividend_yield":/.test(api), "٩ نقطةُ التوزيع تنشر عائدَ كلّ شركة");
}

console.log("\nالنتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
