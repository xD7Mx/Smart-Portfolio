#!/usr/bin/env python3
"""حارسُ D651 (ملاحظةُ المالك 2026-10-09): الحدثُ الواحد بندٌ واحد، ووسمٌ واحد.

العطب: استحواذُ «الغاز» على «جاكو» ظهر ثلاثَ مرّات — الإعلانُ ثمّ «آخرُ التطورات بشأن…» مرّتين — وبجانب كلٍّ وسمان:
نوعُ الحدث و«الإفصاح». الجذر: العرضُ ينقل قائمةَ الإفصاحات كما هي، وكلُّ إفصاحٍ عنده حدثٌ مستقلّ."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
import os, tempfile   # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services.events_view import dedupe   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

T0 = "تعلن شركة الغاز والتصنيع الأهلية القابضة عن توقيع اتفاقية شراء حصص للاستحواذ على ما نسبته 50% من رأس مال شركة جاكو للغازات بقيمة 125,000,000 ريال سعودي بعد زيادة رأس المال."
T1 = T0.replace("القابضة عن توقيع", "القابضة (غازكو) عن آخر التطورات بشأن توقيع")
ev = [{"kind": "acquisition", "date": "2026-06-24", "value": 125e6, "title": T1},
      {"kind": "acquisition", "date": "2026-04-29", "value": 125e6, "title": T1},
      {"kind": "acquisition", "date": "2026-03-24", "value": 125e6, "title": T0},
      {"kind": "contract", "date": "2026-05-01", "value": 30e6, "title": "تعلن الشركة عن توقيع عقد توريد مع أرامكو بقيمة 30 مليون ريال"},
      {"kind": "contract", "date": "2026-02-01", "value": 80e6, "title": "تعلن الشركة عن توقيع عقد توريد مع سابك بقيمة 80 مليون ريال"},
      {"kind": "regulator", "date": "2026-01-10", "title": T0}]
r = dedupe(ev)
acq = [x for x in r if x["kind"] == "acquisition"]
check(len(acq) == 1 and acq[0]["date"] == "2026-06-24" and acq[0]["filings"] == 3 and acq[0]["first_date"] == "2026-03-24",
      "١ إعلانُ الصفقة وتحديثاها بندٌ واحد: أحدثُها بتاريخه، ومعه تاريخُ أوّل إعلانٍ وعددُها", str(acq))
check(len([x for x in r if x["kind"] == "contract"]) == 2, "٢ وعقدان مختلفان (قيمتان وطرفان) يبقيان اثنين")
check(any(x["kind"] == "regulator" for x in r), "٣ ونوعٌ آخر بالنصّ نفسِه لا يُضمّ — النوعُ جزءٌ من الهويّة")
again = dedupe([{**x, "first_date": x["first_date"] if x["filings"] > 1 else None} for x in r])
check([x["filings"] for x in again] == [x["filings"] for x in r], "٤ والجمعُ الثاني (بالعنوان العربيّ) لا يُضيّع العدد")
ev_src = (ROOT / "backend/app/services/events_view.py").read_text(encoding="utf-8")
check("dedupe(ev.get(\"events\") or [])" in ev_src and "out = dedupe(out)" in ev_src and "events:view:v2" in ev_src,
      "٥ العرضُ يجمع قبل جلب العناوين وبعده، وكاشُه جديد")
me = (ROOT / "frontend/src/components/analysis/MaterialEvents.tsx").read_text(encoding="utf-8")
check(">الإفصاح</a>" not in me and "href={e.url}" in me, "٦ وسمٌ واحد: نوعُ الحدث — والعنوانُ نفسُه رابطُ الإفصاح")
check("أُعلن أوّلاً" in me, "٧ وتاريخُ أوّل إعلانٍ ظاهرٌ حين تتعدّد الإفصاحات")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
