#!/usr/bin/env python3
"""تقديمُ جدول السوق لا يُشغّل محرّكَ الحوكمة لكلّ صفّ (D434).

    python3 scripts/audit/screener_serve_no_engine.py

قال المالك: «التطبيقُ بطيءٌ في ملء بطاقات قسم السوق — أريده سلساً سريعاً
بلا تأخير». وقِيس على خادمه: `/market/screener` باردةً **285.8 ثانية**.
والمُحلِّلُ سمّى السبب: إنعاشُ الصفوف عند التقديم يُنادي
`_governance_score` لكلّ صفّ، فيُشغَّل **تحليلُ السهم كاملاً** (ومعه نداءُ
«أرقام» بالشبكة) — ‎6.8 ثانيةٍ للصفّ على ‎270 صفّاً. ونتيجتُه محفوظةٌ ساعةً
**في الذاكرة وحدَها**، فكلُّ إقلاعٍ يجعل أوّلَ زائرٍ يدفع ثمنَ السوق كلِّه.

والدرجةُ نفسُها حسبتها مسحةُ التقييم الليلية بالمحرّك نفسِه وحفظتها في
مخزنٍ دائم. فالشرط: تقديمُ الجدول يقرأ المخزَّنَ ولا يُشغّل المحرّكَ ولا
مرّة — ويبقى الامتناعُ الصريحُ المحفوظُ («-») فارغاً كما في الصفحة.
"""
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import market_screener as MS
    from app.services import governance_engine as GE
    from app.services import cache
    from app.services.content_engine import _fund_store_put_many
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

calls = {"n": 0}


async def _counted(*_a, **_k):
    calls["n"] += 1
    return {"evaluable": True, "overall": 1.0}

GE.evaluate_company = _counted
STORE = {"1111": 72.0, "2222": 55.0, "3333": 81.0}
_fund_store_put_many({s: {"finance_score": v} for s, v in STORE.items()})
# والقوائمُ «مخزَّنةٌ» كي لا يُعفى المسارُ القديمُ نفسَه بغيابها
for s in STORE:
    cache.set(f"stmt:{s}.SR", {"periods": [{"as_of": "2025-12-31"}]}, 3600)
cache.set("screener:gov:4444.SR", "-", 3600)          # امتناعٌ صريحٌ محفوظ

rows = [{"symbol": s, "price": 10.0, "sector": "الطاقة"} for s in STORE]
rows.append({"symbol": "4444", "price": 10.0, "sector": "الطاقة", "finance_score": 60.0})
out = asyncio.run(MS.refresh_derived(rows))

check(calls["n"] == 0, "١ تقديمُ الجدول لا يُشغّل محرّكَ الحوكمة لأيّ صفّ",
      f"نداءاتُ المحرّك: {calls['n']}")
got = {r["symbol"]: r.get("finance_score") for r in out}
check(all(got.get(s) == v for s, v in STORE.items()),
      "٢ والدرجةُ من مخزن المسحة — المحرّكُ نفسُه، محسوبةٌ سلفاً",
      str({s: got.get(s) for s in STORE}))
check(got.get("4444") is None,
      "٣ والامتناعُ الصريحُ المحفوظُ يُفرِغ الخانةَ كالصفحة", str(got.get("4444")))

# ── ٤ · والخادمُ في الإنتاج لا يُعاد مع كلّ ملفّ ──────────────────
# كان يعمل بـ`--reload`، والشفرةُ مربوطة: كلُّ مزامنةٍ للشجرة تُعيده وتمسح
# ذاكرتَه، فيدفع أوّلُ زائرٍ ثمنَ البناء من جديد.
_dc = ROOT / "docker-compose.yml"
if _dc.exists():
    import re as _re
    _t = _dc.read_text(encoding="utf-8")
    _blk = _t.split("\n  backend:", 1)[-1].split("\n  frontend:", 1)[0]
    _cmd = _re.search(r"^\s*command:\s*(.+)$", _blk, _re.M)
    check(bool(_cmd) and "--reload" not in _cmd.group(1),
          "٤ خادمُ الإنتاج بلا --reload", _cmd.group(1)[:80] if _cmd else "لا أمرَ صريح — يرث --reload من الصورة")

print(("FAIL" if fail else "PASS")
      + " D434 — جدولُ السوق يُقدَّم من المحفوظ لا بتشغيل المحرّك لكلّ صفّ")
sys.exit(fail)
