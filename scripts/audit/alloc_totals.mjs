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
const { weightedDividendYield, retainedCashPct, rescaleWeights, rebalanceRow } =
  await import(pathToFileURL(out).href);

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

// ══ إعادةُ التوزيع تُحرّك الأرقام فعلاً ══
// أوّلُ صياغةٍ لهذه الميزة كانت **شكلاً بلا أثر**: الحقلُ يغيّر لونَ الوسم
// والأوزانُ ثابتةٌ على افتراض المئة، فلا يتحرّك مبلغٌ ولا سهم. فحصٌ يُثبت
// الأثرَ لا وجودَ الحقل.
{
  const before = [50, 30, 20];
  const after = rescaleWeights(before, 70);
  const sum = after.reduce((a, b) => a + b, 0);
  say(Math.abs(sum - 70) < 1e-9, "٨ المجموعُ بعد إعادة التوزيع يبلغ الهدف",
      `${before.join("+")} ⇐ ${after.join("+")} = ${sum}`);
  say(after.every((v, i) => Math.abs(v - before[i]) > 1e-9),
      "٩ وكلُّ وزنٍ تحرّك — لا رقمَ بقي على حاله");
  const ratio = after[0] / after[1], was = before[0] / before[1];
  say(Math.abs(ratio - was) < 0.02, "١٠ والنسبةُ بين الشركات محفوظة",
      `${was.toFixed(3)} ⇐ ${ratio.toFixed(3)}`);
}

// ١١ · والكسورُ لا تترك بقيّةً تُبقي الوسمَ برتقالياً بعد عملٍ صحيح.
{
  const bad = rescaleWeights([33.3, 33.3, 33.4], 70).reduce((a, b) => a + b, 0);
  say(Math.abs(bad - 70) < 1e-9, "١١ ولا بقيّةَ تقريبٍ تُفسد المجموع", String(bad));
}

// ١٢ · مجموعٌ حاليٌّ صفرٌ لا يُقسَم عليه.
say(rescaleWeights([0, 0], 70).every(v => v === 0),
    "١٢ ولا يُوزَّع شيءٌ بنسبةٍ من عدم");

// ١٣ · والمبلغُ يتبع الوزن — النصيبُ `وزن ÷ 100 × نقد`.
{
  const cash = 100000;
  const amt = (w) => w / 100 * cash;
  const b = rescaleWeights([50, 30, 20], 100).map(amt).reduce((a, c) => a + c, 0);
  const a70 = rescaleWeights([50, 30, 20], 70).map(amt).reduce((a, c) => a + c, 0);
  say(Math.abs(b - 100000) < 1 && Math.abs(a70 - 70000) < 1,
      "١٣ والمبلغُ الموزَّع ينزل معه", `${b} ⇐ ${a70}`);
}

// ١٤ · والمكوّنُ يستدعي هذه الدالّةَ بعينها — لا نسخةً محلّية.
{
  const page = readFileSync(join(ROOT, "frontend/src/pages/PortfolioPage.tsx"), "utf8");
  const imports = /import\s*\{[^}]*weightedDividendYield[^}]*\}\s*from\s*"\.\.\/lib\/allocMath"/.test(page);
  say(imports && page.includes("weightedDividendYield(") && page.includes("rescaleWeights("),
    "١٤ جدولُ التوزيع يستدعي الدوالَّ المفحوصة نفسَها");
}

// ١٥ · والخادمُ ينشر عائدَ كلّ شركة، وإلا فلا شيءَ يُرجَّح.
{
  const api = readFileSync(join(ROOT, "backend/app/api/v1/endpoints/allocation.py"), "utf8");
  say(/"dividend_yield":/.test(api), "١٥ نقطةُ التوزيع تنشر عائدَ كلّ شركة");
}


/* ══ D217 — المتضخّمةُ تُباع ولا تُشترى ══
   رأى المالكُ الجدولَ لا يتصرّف حين يتجاوز الوزنُ الحاليُّ المستهدفَ: لا رقمَ
   سالبٌ يقول «بِعْ». والأسوأُ من السكوت أنّ النصيبَ كان يُحسب بالوزن
   المستهدف وحدَه بلا نظرٍ إلى الحاليّ، فتأخذ المتضخّمةُ نقداً جديداً
   فيزداد اختلالُها — عطبٌ يعمل عكسَ غرض الجدول.
   وهذا الجدولُ قلبُ القرار الاستثماريّ لا بطاقةً تكميلية، فتُقاس حالاتُه
   بأرقامٍ معلومة الجواب سلفاً لا بالنظر. */
const RB = { investable: 1_000_000, lastPrice: 50, freshCash: 100_000, reinvestPool: 0 };

// ١٦ · تجاوزٌ بنقطتين على مليون ⇒ بيعُ ‎20,000 ريالاً (‏400 سهم).
{
  const r = rebalanceRow({ ...RB, currentWeight: 12, targetWeight: 10 });
  say(r.side === "sell" && near(r.totalAmount, -20000) && near(r.totalShares, -400),
      "١٦ الوزنُ الحاليُّ فوق المستهدف ⇒ مبلغٌ سالبٌ بيعاً",
      `${r.side} · ${r.totalAmount} · ${r.totalShares} سهم`);
}

// ١٧ · ولا تأخذ المتضخّمةُ نصيباً من النقد الجديد — وإلّا زاد اختلالُها.
{
  const r = rebalanceRow({ ...RB, currentWeight: 12, targetWeight: 10 });
  say(r.liquidityShare === null && r.reinvestShare === null,
      "١٧ ولا نصيبَ لها من النقد الجديد", `${r.liquidityShare} · ${r.reinvestShare}`);
}

// ١٨ · دون المستهدف ⇒ شراءٌ بنصيب وزنه من النقد (‏10٪ × 100,000).
{
  const r = rebalanceRow({ ...RB, currentWeight: 6, targetWeight: 10 });
  say(r.side === "buy" && near(r.totalAmount, 10000),
      "١٨ دون المستهدف ⇒ شراءٌ بنصيب وزنه", `${r.side} · ${r.totalAmount}`);
}

// ١٩ · فائضٌ لا يبلغ سعرَ سهمٍ واحد لا يُقترح — رقمٌ لا يُنفَّذ ليس نصيحة.
{
  const r = rebalanceRow({ ...RB, currentWeight: 10.001, targetWeight: 10 });
  say(r.side === "none" && r.totalAmount === null,
      "١٩ فائضٌ دون سهمٍ واحدٍ لا يُقترح", `${r.side} · فائض ${r.excessPct.toFixed(4)} نقطة`);
}

// ٢٠ · بلا وزنٍ مستهدفٍ لا حكمَ أصلاً — لا شراءَ ولا بيع.
{
  const r = rebalanceRow({ ...RB, currentWeight: 30, targetWeight: 0 });
  say(r.side === "none" && r.totalAmount === null,
      "٢٠ بلا وزنٍ مستهدفٍ لا شراءَ ولا بيع", r.side);
}

// ٢١ · عند التساوي يبقى نصيبُ النقد الجديد — التوازنُ لا يمنع التوظيف.
{
  const r = rebalanceRow({ ...RB, currentWeight: 10, targetWeight: 10 });
  say(r.side === "buy" && r.totalAmount > 0,
      "٢١ عند التساوي يبقى نصيبُ النقد الجديد", `${r.side} · ${r.totalAmount}`);
}

// ٢٢ · حجمُ البيع يتناسب مع حجم التجاوز — لا رقمَ ثابت.
{
  const a = rebalanceRow({ ...RB, currentWeight: 12, targetWeight: 10 });
  const b = rebalanceRow({ ...RB, currentWeight: 14, targetWeight: 10 });
  say(near(b.totalAmount, 2 * a.totalAmount),
      "٢٢ ضِعفُ التجاوز ⇒ ضِعفُ البيع", `${a.totalAmount} ⇐ ${b.totalAmount}`);
}

// ٢٣ · بطاقةُ التوزيع تستدعي الدالّةَ المفحوصة نفسَها — لا نسخةً في المكوّن.
{
  const page = readFileSync(join(ROOT, "frontend/src/pages/PortfolioPage.tsx"), "utf8");
  say(/rebalanceRow\(/.test(page) && /from "\.\.\/lib\/allocMath"/.test(page),
      "٢٣ الجدولُ يستدعي `rebalanceRow` المفحوصة");
}

console.log("\nالنتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
