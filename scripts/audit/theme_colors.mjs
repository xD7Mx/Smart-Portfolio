// ─────────────────────────────────────────────────────────────────────────
// D238 — لكلِّ مظهرٍ لوحُه، ولا لونَ فاقعٍ في مساحةٍ ملوّنة.
//
// بأمرَي المالك:
//   · «ألوانُ الرسم في الداكن صحيحةٌ وطبيعية، والفاتح قبيحة» — واللوحُ
//     كان **واحداً للمظهرين**، وذاك سببُه: درجةٌ مضبوطةٌ على أرضيةٍ
//     داكنةٍ تلمع على الورق.
//   · «للداكن فقط: الشريطُ البصريّ فاقع، اجعله كألوان الفاتح» — فمقاييسُ
//     الداكن تأخذ درجاتِ الفاتح، وهي ملاحظةٌ مخصّصةٌ لا تعميم.
//
// ويُقاس ما يُنسى: أن يعود اللوحُ واحداً بعد ضبطٍ لاحقٍ لأحد المظهرين.
// ─────────────────────────────────────────────────────────────────────────
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const css = readFileSync(join(ROOT, "frontend/src/styles/globals.css"), "utf8");
let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

// آخرُ تعريفٍ للرمز داخل كتلةٍ يفوز — كما يفعل المتصفّح.
const blocks = [...css.matchAll(/(:root|html\.light)\s*\{([^}]*)\}/g)];
const val = (scope, name) => {
  let out = null;
  for (const b of blocks) {
    if (b[1] !== scope) continue;
    const m = [...b[2].matchAll(new RegExp(`--${name}\\s*:\\s*([^;]+);`, "g"))];
    if (m.length) out = m[m.length - 1][1].trim();
  }
  return out;
};

const charts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map(i => `chart-${i}`);
const same = charts.filter(c => val(":root", c) && val(":root", c) === val("html.light", c));
say(same.length === 0, "١ لوحُ الرسوم مختلفٌ بين المظهرين — لا لوحَ واحدٌ لأرضيتين",
    same.length ? `${same.length} رمزاً متطابقاً: ${same.slice(0, 3).join(" · ")}` : "عشرةُ رموزٍ منفصلة");

const missing = charts.filter(c => !val("html.light", c));
say(missing.length === 0, "٢ وكلُّ رمزٍ مُعرَّفٌ في الفاتح صراحةً — لا وراثةٌ صامتة",
    missing.join(" · "));

const gauges = ["gauge-pos", "gauge-warn", "gauge-neg"];
const diff = gauges.filter(g => val(":root", g) !== val("html.light", g));
say(diff.length === 0,
    "٣ ومقاييسُ الداكن بدرجات الفاتح — بأمر المالك المخصّص",
    diff.length ? `اختلف: ${diff.join(" · ")}`
      : gauges.map(g => val(":root", g)).join(" · "));

// وحبرُ النصّ لا يُهدَّأ معها: الحرفُ يحتاج عتبتَه (الميثاق).
say(val(":root", "pos-ink") !== val(":root", "gauge-pos"),
    "٤ وحبرُ الحكم مستقلٌّ عن حشو الشريط — العتبةُ للنصّ باقية",
    `${val(":root", "pos-ink")} ≠ ${val(":root", "gauge-pos")}`);

console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
