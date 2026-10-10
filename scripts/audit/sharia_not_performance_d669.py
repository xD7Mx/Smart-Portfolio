#!/usr/bin/env python3
"""حارسُ D669 (المالك 2026-10-10): «لا تجعل شرعيةَ الشركة معياراً لقياس أدائها — فلا علاقة لذلك».

الحالُ قبل الإصلاح: لا يقرأ أيُّ ملفٍّ من ملفّات المحرّك المجمَّدة الشرعيةَ (لا درجةَ ولا قرارَ ولا سعرَ عادلاً) — لكنّها
ظهرت بصفة الأداء في ثلاثة مواضع: تنبيهٌ عالي الخطورة «غير متوافقة شرعياً» بين تنبيهات السلامة المالية في حوكمة المحفظة
(ويصير إشعاراً)، وسطرٌ في وصف حالة المحفظة، وسطرٌ بين الدرجة والقرار فيما يقرؤه «رأي الذكاء» تحت «المتانة والالتزام».
فالحارسُ يمنع الثلاثة، ويمنع أن يقرأ المحرّكُ الشرعيةَ يوماً.
"""
import os, pathlib, re, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services.engine_identity import FILES   # noqa: E402
import io, tokenize   # noqa: E402
# الشيفرةُ وحدها تُقرأ (لا التعليقُ ولا وثيقةُ الدالّة): و`scores.py` يحفظ حقلَ العرض `sharia_status` بعد حساب الدرجة —
# مزامنةُ بيانٍ يُعرض لا مُدخَلٌ في الحساب — فيُسمح بسطورها الثلاثة وحدها، وأيُّ ذكرٍ آخر عطب.
ALLOWED = {"backend/app/services/scores.py": ("r = maqasid.rating(c.symbol)", 'c.sharia_status = r["status"]',
                                               "from app.services import maqasid")}
DOC = ('"' * 3, "'" * 3)
hits = []
for rel in FILES:
    f = ROOT / rel
    if not f.exists() or not rel.endswith(".py"):
        continue
    keep = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(f.read_text(encoding="utf-8")).readline):
            if tok.type == tokenize.NAME and re.search(r"sharia|maqasid", tok.string, re.I):
                keep.setdefault(tok.start[0], tok.line.strip())
            elif (tok.type == tokenize.STRING and not tok.string.startswith(DOC)
                  and re.search(r"NON_COMPLIANT|COMPLIANT|شرعي", tok.string)):
                keep.setdefault(tok.start[0], tok.line.strip())
    except tokenize.TokenError:
        continue
    bad = [ln for ln in keep.values() if not any(a in ln for a in ALLOWED.get(rel, ()))]
    if bad:
        hits.append(f"{rel}: {bad[:2]}")
check(not hits, "١ لا يقرأ ملفٌّ من ملفّات المحرّك الشرعيةَ في حساب — لا درجةَ ولا قرارَ ولا سعرَ عادلاً يتأثّر بها", str(hits))
gv = (ROOT / "backend/app/services/governance.py").read_text(encoding="utf-8")
att = gv[gv.index("for h in holdings:"):gv.index("overall_score = round(")]
check('"غير متوافقة شرعياً"' not in att and not re.search(r'if sharia == "NON_COMPLIANT":\s*\n\s*attention', att),
      "٢ ولا تنبيهَ أداءٍ أو سلامةٍ مالية في حوكمة المحفظة بسبب الشرعية (ولا إشعارَ منه)")
nar = gv[gv.index("def _rule_governance_narrative"):gv.index("async def get_portfolio_governance")]
check("متوافقة شرعياً" not in nar.split('"""', 2)[-1], "٣ ولا يدخل وصفَ حالة المحفظة")
ac = (ROOT / "backend/app/services/ai_content.py").read_text(encoding="utf-8")
seg = ac[ac.index("def governance_narrative"):][:3000] if "def governance_narrative" in ac else ac
check("التوافق الشرعي:" not in seg, "٤ ولا موجِّهَ وصف الحوكمة للذكاء")
an = (ROOT / "backend/app/services/ai_analyst.py").read_text(encoding="utf-8")
blk = an[an.index("gov_lines = []") if "gov_lines = []" in an else 0:an.index('parts.append(_sec("المتانة والالتزام:", gov_lines))')]
check("sharia" not in blk and "لا تدخل في الحكم على أداء الشركة" in an,
      "٥ ورأيُ الذكاء يقرؤها قسماً مستقلّاً معلَّماً — لا سطراً بين الدرجة والقرار")
eg = (ROOT / "scripts/audit/engines_gate_v1.py").read_text(encoding="utf-8")
check("لا يدخل أداءَ الشركة" in eg, "٦ وبوابةُ الإصدار تفحص سلامةَ عرضها وحدَها وتقول إنها لا تقيس الأداء")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
