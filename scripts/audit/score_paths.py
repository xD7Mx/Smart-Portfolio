#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# درجةُ الحوكمة: أربعةُ مسارات، ورقمٌ واحدٌ يجب أن يخرج منها جميعاً.
#
# رأى المالكُ الدرجةَ في **فرز السوق** و**خريطة أداء القطاعات** تخالف صفحةَ
# السهم. والمسارات:
#
#   ١ صفحةُ السهم        analyze_company(...)["score"]
#   ٢ محرّكُ الحوكمة بقرار evaluate_company(..., with_decision=True)
#   ٣ محرّكُ الحوكمة بلا   evaluate_company(..., with_decision=False)
#   ٤ عمودُ قاعدة البيانات Company.finance_score  ← يقرؤه الفرزُ والخريطة أوّلاً
#
# الرابعُ **نسخةٌ محفوظةٌ** من الثالث، يُحدَّث بمهمّةٍ دورية. فإن تغيّرت
# معايرةُ المحرّك (D162) ولم تُحدَّث النسخة، عُرض رقمٌ قديمٌ في شاشتين
# ورقمٌ حيٌّ في ثالثة — وهذا ما يراه المالك.
#
# ولا يُصلَح بالحدس: يُشغَّل على الخادم فيُطبع الأربعةُ لكلّ رمز، فيُعرف
# أيُّها الشاذّ قبل تغيير سطرٍ واحد.
#
#   docker exec sp_backend python /app/scripts/audit/score_paths.py
#   docker exec sp_backend python /app/scripts/audit/score_paths.py 1120 2222
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)


async def main() -> int:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Company
    from app.services.analysis import analyze_company
    from app.services.governance_engine import evaluate_company
    from app.api.v1.endpoints.holdings import yahoo_symbol

    want = [a.replace(".SR", "") for a in sys.argv[1:]]
    rows = []
    async with AsyncSessionLocal() as db:
        cs = (await db.execute(
            select(Company).where(Company.status != "ARCHIVED"))).scalars().all()
        for c in cs:
            sym = str(c.symbol).replace(".SR", "")
            if want and sym not in want:
                continue
            y = yahoo_symbol(c.symbol)
            stored = float(c.finance_score) if c.finance_score is not None else None

            async def _try(coro):
                try:
                    return await coro
                except Exception as e:                            # noqa: BLE001
                    return {"__err__": f"{type(e).__name__}: {e}"}

            a = await _try(analyze_company(y, c.company_name or sym, db=db))
            g1 = await _try(evaluate_company(y, db=db, sector=c.sector))
            g0 = await _try(evaluate_company(y, db=db, sector=c.sector,
                                             with_decision=False))
            pick = lambda d, k: (d or {}).get(k) if isinstance(d, dict) else None
            rows.append((sym, c.company_name, pick(a, "score"),
                         pick(g1, "finance_score"), pick(g0, "finance_score"), stored))

    print(f"{'الرمز':<7}{'صفحة السهم':>12}{'محرّك+قرار':>12}"
          f"{'محرّك بلا':>12}{'المخزَّن':>10}   الشركة")
    print("─" * 78)
    diff = 0
    for sym, name, a, g1, g0, st in rows:
        vals = [v for v in (a, g1, g0, st) if v is not None]
        bad = len({round(float(v), 1) for v in vals}) > 1
        if bad:
            diff += 1
        f = lambda v: "—" if v is None else f"{float(v):.1f}"
        mark = " ✖" if bad else "  "
        print(f"{sym:<7}{f(a):>12}{f(g1):>12}{f(g0):>12}{f(st):>10}{mark} {name}")

    print("─" * 78)
    print(f"اختلف في {diff} من {len(rows)} شركة.")
    print("العمودُ المخزَّن هو ما يعرضه الفرزُ وخريطةُ القطاعات؛ والأوّلُ ما تعرضه صفحةُ السهم.")
    return 1 if diff else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
