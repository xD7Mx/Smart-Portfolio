#!/usr/bin/env python3
"""حارسُ D659: قائمةُ إفصاحات «تداول» الفارغةُ في عمليّةٍ باردة تُعاد مرّةً قبل أن تُعدّ جواباً — قِيس: «الغاز» أوّلُ رمزٍ صفرٌ دائماً."""
import asyncio, os, pathlib, sys, tempfile
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

import json                                                         # noqa: E402
import app.services.tadawul_disclosure as TD, app.services.tadawul_http as TH   # noqa: E402
from app.services import cache                                      # noqa: E402
calls = {"n": 0}
async def _ep():
    return "https://example/ep"
async def _fetch(*a, **k):
    calls["n"] += 1
    if calls["n"] == 1:
        return 200, json.dumps({"announcementList": []})          # الطلبُ الباردُ الأوّل
    return 200, json.dumps({"announcementList": [{"SYMBOL": "2080", "announcementUrl": "/x?locale=en", "PR_DATE": "2026-06-24",
                                                  "SHORT_DESC": "Gas acquires Jaco"}]})
TD._endpoint, TH.smart_fetch = _ep, _fetch
rows = asyncio.run(TD.list_for("2080", 60))
check(len(rows) == 1 and calls["n"] == 2, "١ الفراغُ الأوّلُ يُعاد مرّةً فتصل الإفصاحات", f"طلبات {calls['n']} · صفوف {len(rows)}")
calls["n"] = 10
cache._store.pop("tadawul:annlist:v3:4013", None)
async def _empty(*a, **k):
    calls["n"] += 1
    return 200, json.dumps({"announcementList": []})
TH.smart_fetch = _empty
r2 = asyncio.run(TD.list_for("4013", 60))
check(r2 == [] and calls["n"] == 12, "٢ وفراغٌ بعد الإعادة يبقى فراغاً — مرّتان لا أكثر", str(calls["n"]))
# اكتشافُ النقطة يتعذّر أوّلَ مرّة في العمليّة الباردة
eps = {"n": 0}
async def _ep_cold():
    eps["n"] += 1
    return None if eps["n"] == 1 else "https://example/ep"
TD._endpoint, TH.smart_fetch = _ep_cold, _fetch
calls["n"] = 1
cache._store.pop("tadawul:annlist:v3:2080", None)
r3 = asyncio.run(TD.list_for("2080", 60))
check(len(r3) == 1 and eps["n"] >= 2, "٣ واكتشافُ النقطة المتعذّرُ أوّلَ مرّةٍ يُعاد — فأوّلُ شركةٍ بعد إعادة التشغيل لا تُحرم أحداثَها",
      f"اكتشاف {eps['n']} · صفوف {len(r3)}")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
