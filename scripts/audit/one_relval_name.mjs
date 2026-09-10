// ─────────────────────────────────────────────────────────────────────────
// D235 · D237 — اسمٌ واحدٌ لمحرّك التقييم في كلّ شاشة: «السعر العادل».
//
// بأمر المالك: «جملة القيمة النسبية إلى القطاع غيّرها في كل مكان إلى
// التقييم النسبي». وكانت الميزةُ الواحدة تُسمّى بأربعة أسماء — «القيمة
// النسبية إلى القطاع» · «قيمة نسبية إلى القطاع» · «نسبية للقطاع» ·
// «القيمة النسبية للسهم» — بحسب الشاشة والتلميح. وتعدُّدُ الاسم يجعل
// المستخدمَ يظنّ الأرقامَ أرقاماً مختلفة، وهو عطبٌ تكرّر في هذا التطبيق
// (‏D147 · D174 · D224).
//
// فالحارسُ يفتّش نصوصَ الواجهة كلَّها عن الأسماء المهجورة، ويشترط أن يكون
// اسمُ المحرّك في مخرَجه هو الاسمَ المعروضَ نفسَه — فلا تُصلَح الشاشاتُ
// ويبقى الخادمُ يقول اسماً آخر.
// ─────────────────────────────────────────────────────────────────────────
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

// كلُّ اسمٍ حمله المحرّكُ قبل «السعر العادل» — والأخيرُ بأمر المالك
// (‏D237): «المحرّكُ يستحقّ اللقب بسبب شموليته». فما سبقه مهجورٌ يُمنع
// رجوعُه، وتاريخُه يبقى في السجلّ لا في الشاشة.
const RETIRED = ["القيمة النسبية إلى القطاع", "قيمة نسبية إلى القطاع",
                 "نسبية للقطاع", "القيمة النسبية للسهم", "التقييم النسبي"];

const walk = (dir) => readdirSync(dir).flatMap(n => {
  const p = join(dir, n);
  return statSync(p).isDirectory() ? walk(p)
    : /\.(tsx?|ts)$/.test(n) ? [p] : [];
});

const hits = [];
for (const f of walk(join(ROOT, "frontend/src"))) {
  const src = readFileSync(f, "utf8");
  // تُستثنى أسطرُ التعليق: التاريخُ يُروى بأسمائه، والمعروضُ وحدَه يُحكَم.
  src.split("\n").forEach((ln, i) => {
    const t = ln.trim();
    if (t.startsWith("//") || t.startsWith("*") || t.startsWith("/*")) return;
    for (const r of RETIRED) if (ln.includes(r)) hits.push(`${f.replace(ROOT + "/", "")}:${i + 1} «${r}»`);
  });
}
say(hits.length === 0, "١ لا اسمَ مهجوراً في نصوص الواجهة",
    hits.slice(0, 4).join(" · "));

const eng = readFileSync(join(ROOT, "backend/app/services/relative_value.py"), "utf8");
say(/"basis": "السعر العادل"/.test(eng),
    "٢ واسمُ المحرّك في مخرَجه هو الاسمُ المعروض نفسُه");

// وحيث يُعرض التقييمُ يُعرض بالاسم — لا خانةٌ بلا عنوان.
const panel = readFileSync(join(ROOT, "frontend/src/components/analysis/AnalysisPanel.tsx"), "utf8");
say(panel.includes('<div className="kpi-lbl">السعر العادل</div>'),
    "٣ وخانةُ «البيانات المالية» تحمل الاسمَ الجديد");

console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
