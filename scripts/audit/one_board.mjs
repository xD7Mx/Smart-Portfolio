/**
 * D171 — ميزانُ خبراء الحوكمة يُرسَم من مكوّنٍ واحد.
 *
 * كان يُرسَم مرّتين بشيفرتين مستقلّتين: نافذةُ قسم الحوكمة (النجمة)
 * وتبويبُ التقييم في صفحة السهم. فأُعيد تصميمُ إحداهما وبقيت الأخرى،
 * فرأى المالكُ بطاقتين مختلفتين لِميزانٍ واحد — وهو عينُ عطبِ D164 في
 * صفّ التبويبات وD166 في القرار: **شيءٌ واحدٌ يُبنى في موضعين**.
 *
 * فحصٌ بنيويّ: لا شاشةَ ترسم `expert_panel` بيدها؛ من يعرضه يستدعي
 * `ExpertPanelBoard`. ويُقرأ النصُّ بحثاً عن الرسم اليدويّ لا عن وجود
 * الاستيراد — فالاستيرادُ قد يوجد ويبقى الرسمُ اليدويُّ إلى جانبه.
 */
import { readFileSync, readdirSync, statSync } from "fs";
import { join } from "path";

const ROOT = new URL("../../frontend/src", import.meta.url).pathname;
const BOARD = "ExpertPanelBoard";
let fail = 0;
const say = (ok, label, detail = "") => {
  if (!ok) fail = 1;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? " — " + detail : ""}`);
};

function walk(dir, out = []) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) walk(p, out);
    else if (p.endsWith(".tsx")) out.push(p);
  }
  return out;
}

const files = walk(ROOT);
const users = [];
const handRolled = [];
for (const f of files) {
  const src = readFileSync(f, "utf8");
  if (f.endsWith(`${BOARD}.tsx`)) continue;
  if (!src.includes("expert_panel")) continue;
  users.push(f.replace(ROOT, "src"));
  // رسمٌ يدويّ: تكرارٌ على المصفوفة داخل الشاشة نفسِها
  if (/expert_panel[^\n]*\.map\s*\(/.test(src) || /expert_panel\s*\.\s*map/.test(src))
    handRolled.push(f.replace(ROOT, "src"));
}

say(users.length >= 2, "١ الميزانُ يُعرض في شاشتين على الأقلّ",
    users.join(" · "));
for (const f of handRolled) console.log(`     ${f}: يرسم expert_panel بيده`);
say(handRolled.length === 0, "٢ لا شاشةَ ترسم الميزانَ بيدها",
    `${handRolled.length} شاشة`);

const missing = users.filter(f => !readFileSync(join(ROOT, f.slice(4)), "utf8").includes(BOARD));
for (const f of missing) console.log(`     ${f}: لا يستدعي ${BOARD}`);
say(missing.length === 0, `٣ كلُّ عارضٍ يستدعي ${BOARD}`, `${missing.length} مخالفاً`);

console.log();
console.log("النتيجة:", fail ? "فيه ملاحظات ✘" : "نظيف ✔");
process.exit(fail);
