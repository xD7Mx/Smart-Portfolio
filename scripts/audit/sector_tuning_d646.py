#!/usr/bin/env python3
"""حارسُ D646: وزنُ النماذج المعايَر للقطاعين اللذين اجتازا القاعدةَ المسجّلة قبل القياس — بالقيم المقيسة نفسِها، لا غيرُهما."""
import re, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services import fair_value_models as F       # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

check(F.SECTOR_TUNING == {"التأمين": {"k": 0.3, "drop_family": "multiples"},
                          "الخدمات الاستهلاكية": {"k": 0.4, "drop_key": "epv"}},
      "١ القطاعان المعتمدان بقيمهما المقيسة (sector_shrink_door) — ولا ثالثَ بلا قياس", str(F.SECTOR_TUNING))
check(F._tuning("8010") == F.SECTOR_TUNING["التأمين"] and F._tuning("2222") == {},
      "٢ التعاونيةُ تأخذ وزنَ التأمين، وأرامكو (قطاعٌ لم يجتز) على الوزن العامّ")
src = (ROOT / "backend/app/services/fair_value_models.py").read_text()
i_tune, i_agg = src.find("_tune = _tuning(i.symbol)"), src.find("agg = aggregate(models, i.price, i.archetype)")
check(0 < i_tune < i_agg and '_k = _tune.get("k", MARKET_BLEND_K)' in src,
      "٣ الإسقاطُ قبل التجميع والوزنُ في المزج — كما حُوكي في القياس")
_cv = re.search(r'fvm:v(\d+):', src)
check(_cv and int(_cv.group(1)) >= 38, "٤ وكاشُ النماذج بإصدارٍ جديد فلا تبقى قيمةٌ قبل التعديل", _cv and _cv.group(0))
doc = (ROOT / "docs/ENGINES_V2.md").read_text()
check("بنقطةٍ مئويةٍ كاملةٍ على الأقلّ" in doc, "٥ القاعدةُ مسجَّلةٌ في الميثاق قبل القياس")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
