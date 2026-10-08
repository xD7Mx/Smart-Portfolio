#!/usr/bin/env python3
"""حارسُ D620: حدثُ المفكرة (صرفٌ · أحقية · جمعية) يجد إعلانَه في «تداول» وإن سبقه بأسابيع."""
import datetime as dt, os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")   # ‏D630: مخزنُ الحالة مؤقّتٌ قبل استيراد المحرّك
os.environ["SP_STATE_DIR"] = _SB
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
from app.services.tadawul_disclosure import kind_fallback
rows = [{"date": "2026-09-20", "title": "إعلان مصرف الراجحي عن توزيع أرباح نقدية على المساهمين", "url": "a"},
        {"date": "2026-09-25", "title": "إعلان النتائج المالية الأولية", "url": "b"},
        {"date": "2026-03-01", "title": "توزيع أرباح العام الماضي", "url": "c"},
        {"date": "2026-08-01", "title": "دعوة لحضور اجتماع الجمعية العامة العادية", "url": "d"}]
d0 = dt.date(2026, 10, 1)
check((kind_fallback(rows, "صرف أرباح نقدية", d0) or {}).get("url") == "a", "١ «صرف أرباح» يجد إعلانَ التوزيع قبله بأحد عشر يوماً")
check((kind_fallback(rows, "اجتماع الجمعية العامة", dt.date(2026, 8, 20)) or {}).get("url") == "d", "٢ والجمعيةُ تجد دعوتَها")
check(kind_fallback(rows, "نتائج الربع الثالث", d0) is None, "٣ وما ليس من هذه الأنواع لا يُلصق بإعلانٍ قريب (لا اختلاق)")
check(kind_fallback(rows, "صرف أرباح نقدية", dt.date(2026, 2, 1)) is None, "٤ ولا إعلانَ بعد الحدث أو أقدمَ من خمسة أشهر")
sh = (ROOT / "frontend/src/components/common/ShareOpen.tsx").read_text()
check("<ExternalLink" not in sh and "argaam" not in sh.lower() and "window.location.href" not in sh, "٥ لا زرَّ «أرقام»، ولا يُشارَك رابطُ التطبيق")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
