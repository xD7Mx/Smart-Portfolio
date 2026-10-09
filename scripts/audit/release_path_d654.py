#!/usr/bin/env python3
"""حارسُ D654: طريقُ النشر يشمل مزامنةَ القرار بعد كلّ نشرٍ يبدّل إصدارَ المحرّك، والمزامنةُ لا تكتب إلا للمخالِف."""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
doc = (ROOT / "docs/ENGINES_V2.md").read_text(encoding="utf-8")
src = (ROOT / "scripts/audit/decision_page_sync_door.py").read_text(encoding="utf-8")
check("decision_page_sync_door.py" in doc and "parity_gate.py" in doc, "١ طريقُ النشر يسمّي مزامنةَ القرار ثمّ بوابةَ رقم اليوم")
i_off = src.find("cache.set, lastgood.save = (lambda *a, **k: None), (lambda *a, **k: None)")
i_diff = src.find("if pl and dl and pl != dl:")
i_on = src.find("cache.set, lastgood.save = _set, _save")
i_loop = src.find("for s, pl, dl in diff:")
check(0 < i_off < i_diff < i_on < i_loop, "٢ الصفحاتُ تُحسب أوّلاً بلا كتابة، ولا يُكتب إلا حكمُ المخالِفة بعد ذلك")
check("fair_value" not in src.split("cache.set, lastgood.save = _set, _save")[1], "٣ ولا تمسّ المزامنةُ رقماً — حكمُ الصفحة وحده")
check('cache.expire_prefix(f"analysis:{s}.SR:")' in src, "٤ والمخالِفةُ يُبطَل كاشُها أوّلاً — التحليلُ المخزَّن لا يكتب حكمَه")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
body = mk[mk.index("async def get_company_analysis"):mk.index("async def get_company_analysis") + 2600]
check("sync_page_verdict(ysym, data)" in body, "٥ وفتحُ صفحة السهم يكتب حكمَها في الفرز ولو جاء التحليلُ من الكاش")
import os, tempfile                                                  # noqa: E401
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
sys.path.insert(0, str(ROOT / "backend"))
from app.services import lastgood                                   # noqa: E402
from app.api.v1.endpoints.market import sync_page_verdict            # noqa: E402
lastgood.save("governance:deep", {"7202": {"decision": {"raw": "انتظار", "label": "انتظار"}, "source": "sweep", "quality": 70}})
w1 = sync_page_verdict("7202.SR", {"evaluable": True, "decision": {"raw": "شراء", "label": "شراء"}})
row = lastgood.load("governance:deep")["7202"]
check(w1 and row["decision"]["raw"] == "شراء" and row["source"] == "page" and row.get("quality") == 70,
      "٦ حكمُ الصفحة يُكتب، وبقيّةُ الصفّ باقية، ومصدرُه «الصفحة» فتحميه المسحةُ (D578)")
w2 = sync_page_verdict("7202.SR", {"evaluable": True, "decision": {"raw": "شراء", "label": "شراء"}})
w3 = sync_page_verdict("7202.SR", {"evaluable": False, "decision": {"raw": "بيع", "label": "بيع"}})
check(not w2 and not w3, "٧ ولا كتابةَ إن اتّفقا، ولا حكمَ من صفحةٍ لم تكتمل بياناتُها")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
