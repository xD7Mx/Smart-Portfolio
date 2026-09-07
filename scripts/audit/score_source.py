#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D198 — درجةُ الحوكمة تُقرأ من المحرّك، والمخزَّنُ يملأ الفراغَ ولا يغلبه.
#
# رأى المالكُ الدرجةَ في فرز السوق وفي خريطة أداء القطاعات تخالف صفحةَ
# السهم. والسببُ ترتيبُ المصادر: العمودُ `Company.finance_score` **نسخةٌ
# محفوظة** يكتبها مسحٌ دوريّ، وكان يُقرأ أوّلاً — فمتى تغيّرت معايرةُ
# المحرّك أو تجدّدت القوائمُ ولم يُعَد المسح، عُرض رقمٌ قديمٌ في شاشتين
# ورقمٌ حيٌّ في ثالثة.
#
# فحصٌ سلوكيّ لا قراءةَ نصّ: يُشغَّل مسارُ الفرز على صفٍّ واحد بمحرّكٍ
# **مموَّهٍ** يُخرج رقماً معلوماً، وبعمودٍ مخزَّنٍ يُخرج رقماً آخر — ثم
# يُنظر أيَّهما ظهر. ولو عاد الترتيبُ القديم لظهر المخزَّن فيسقط الفحص.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _p in ("/app", str(ROOT / "backend"), str(ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

fail = 0


def say(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


async def main() -> int:
    from app.services import market_screener as ms

    ENGINE, STORED = 88.0, 41.0

    async def _engine(_ysym, _sector):
        return ENGINE

    # قاعدةُ البيانات لا تُلمَس: يُموَّه الجزءُ الذي يقرؤها فيُعيد صفّاً
    # واحداً بدرجةٍ مخزّنةٍ مخالفة.
    class _Res:
        def all(self):
            return [("2222", "COMPLIANT", STORED)]

    class _DB:
        async def execute(self, *_a, **_k):
            return _Res()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_a):
            return False

    real_engine = ms._governance_score
    real_session = getattr(ms, "AsyncSessionLocal", None)
    ms._governance_score = _engine
    import app.core.database as _dbmod
    real_local = _dbmod.AsyncSessionLocal
    _dbmod.AsyncSessionLocal = lambda: _DB()

    rows = [{"symbol": "2222", "sector": "الطاقة", "price": 30.0}]
    try:
        await ms._enrich_fundamentals(rows)
    finally:
        ms._governance_score = real_engine
        _dbmod.AsyncSessionLocal = real_local
        if real_session is not None:
            ms.AsyncSessionLocal = real_session

    got = rows[0].get("finance_score")
    say(got == ENGINE,
        "١ الفرزُ يعرض درجةَ المحرّك لا النسخةَ المخزَّنة",
        f"المحرّك {ENGINE} · المخزَّن {STORED} · المعروض {got}")

    # ٢ · وخريطةُ القطاعات لا تكتب المخزَّنَ فوق ما وصل من المسح الحيّ.
    src = (ROOT / "backend/app/services/governance.py").read_text(encoding="utf-8")
    # الموضعُ التنفيذيّ لا ذِكرُ الاسم في شرحٍ أعلى الملفّ.
    blk = src[src.index("_select(Company.symbol, Company.finance_score)"):][:400]
    say("not in score" in blk or "key not in score" in blk,
        "٢ خريطةُ القطاعات: المخزَّنُ يملأ الفراغَ ولا يمسح الحيّ")

    print()
    print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
    return fail


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
