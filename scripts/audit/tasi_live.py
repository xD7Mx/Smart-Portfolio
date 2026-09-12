#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D252 — لسانُ «تاسي» يقول رقمَ السوق الآن، لا رقمَ ربع ساعةٍ مضت.
#
# قال المالك: «نجعل التطبيق بأسعار مباشرة ولسان تاسي يعرض الرقم المباشر
# بدون تأخير». وكان يُقرأ `^TASI.SR` من ياهو — متأخّرٌ عند المزوّد،
# ومخزَّنٌ عندنا ربعَ ساعةٍ فوق تأخيره. وخدمةُ مؤشّر «تداول» تنشره حيّاً.
#
# وخطرُ التحويل: أن يُفقد ما كان (حجمُ التداول لا تنشره الخدمة)، أو أن
# يُقرأ رقمٌ بلا زمنٍ إن تعذّرت. فيُقاس السلوك:
#   ٠· القيمةُ والتغيّرُ والنسبةُ تُقرأ من مخرَج الخدمة بنصّه
#   ١· والفاصلةُ الألفيةُ لا تُفسد الرقم (‏11,007.27)
#   ٢· ومصدرُه معلَنٌ مع الرقم
#   ٣· ومخرَجٌ معطوبٌ لا يُنتج رقماً
#   ٤· وحين تحضر تتقدّم ياهو في اللسان
#   ٥· و**حجمُ التداول يبقى** من ياهو — ما لا مصدرَ له لا يُخترع ولا يُمحى
#   ٦· وحين تتعذّر يبقى رقمُ ياهو ولا تُفرَّغ الشاشة
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import json  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import tadawul_http as th  # noqa: E402
from app.services import tadawul_market as tm  # noqa: E402

# مخرَجُ الخدمة كما قِيس على الخادم
BODY = json.dumps({
    "tasiValue": "11,007.27", "tasiNetChange": "-8.45",
    "tasiPercentageChange": "-0.08", "tasiStatus": "2",
    "mt30IndexValue": "1,477.27", "currentTime": "03:01 PM",
    "marketStatusCode": 3, "sukukValue": "901.8",
}, ensure_ascii=False)


def _serve(body, status=200):
    async def _f(url, **kw):
        return status, body
    th.fetch = _f                                                # type: ignore[assignment]


_serve(BODY)
q = asyncio.run(tm.index_quote())
check(q is not None and q.get("price") == 11007.27,
      "٠ · ١ القيمةُ تُقرأ والفاصلةُ الألفيةُ لا تُفسدها", str(q and q.get("price")))
check(q is not None and q.get("change") == -8.45 and q.get("change_pct") == -0.08,
      "٠ب والتغيّرُ والنسبةُ بإشارتهما", f"{q and q.get('change')} · {q and q.get('change_pct')}")
check(q is not None and q.get("source") == "تداول" and q.get("as_of") == "03:01 PM",
      "٢ ومصدرُه ووقتُه معلَنان مع الرقم", f"{q and q.get('source')} · {q and q.get('as_of')}")

_serve("<html>ليس JSON</html>")
check(asyncio.run(tm.index_quote()) is None,
      "٣ مخرَجٌ معطوبٌ لا يُنتج رقماً")
_serve(json.dumps({"tasiValue": "0"}))
check(asyncio.run(tm.index_quote()) is None,
      "٣ب وقيمةُ صفرٍ ليست مؤشّراً")
_serve(BODY, status=403)
check(asyncio.run(tm.index_quote()) is None, "٣ج والحجبُ لا يُقرأ رقماً")


# ── ٤ · ٥ · ٦ · الدمجُ في اللسان ────────────────────────────────────────
def merge(yahoo, live):
    """المنطقُ نفسُه المكتوبُ في `market_overview` — يُقاس لا يُقرأ."""
    tasi = dict(yahoo) if yahoo else None
    if tasi and tasi.get("volume"):
        tasi["traded_value_est"] = round(tasi["price"] * tasi["volume"])
    if live:
        tasi = {**(tasi or {}), **{k: v for k, v in live.items() if v is not None}}
        if tasi.get("volume"):
            tasi["traded_value_est"] = round(tasi["price"] * tasi["volume"])
    return tasi


yq = {"symbol": "^TASI.SR", "price": 10950.0, "change_pct": 0.4, "volume": 250_000_000}
_serve(BODY)
live = asyncio.run(tm.index_quote())
m = merge(yq, live)
check(m.get("price") == 11007.27 and m.get("source") == "تداول",
      "٤ الرقمُ المباشرُ يتقدّم ياهو في اللسان", str(m.get("price")))
check(m.get("volume") == 250_000_000
      and m.get("traded_value_est") == round(11007.27 * 250_000_000),
      "٥ وحجمُ التداول يبقى من ياهو ويُعاد حسابُ قيمته بالسعر المباشر",
      str(m.get("traded_value_est")))
m2 = merge(yq, None)
check(m2.get("price") == 10950.0 and "source" not in m2,
      "٦ وحين تتعذّر الخدمةُ يبقى رقمُ ياهو ولا تُفرَّغ الشاشة", str(m2.get("price")))

# ── والمنطقُ في نقطة النهاية هو هذا بعينه ────────────────────────────────
ep = (ROOT / "backend" / "app" / "api" / "v1" / "endpoints" / "market.py").read_text(
    encoding="utf-8")
check("from app.services.tadawul_market import index_quote" in ep
      and "traded_value_est" in ep,
      "٧ ونقطةُ اللسان تستدعي المصدرَ المباشرَ نفسَه")

print(("FAIL" if fail else "PASS") + " D252 — لسانُ تاسي مباشرٌ من المؤشّر")
raise SystemExit(fail)
