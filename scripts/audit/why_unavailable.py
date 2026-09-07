#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# «غير متاح» و«بيانات غير كافية» — لماذا؟ ولماذا يظهر السهمُ في شاشةٍ
# ويغيب عن أخرى؟
#
# رأى المالكُ غازكو (‏2080) ممتنَعاً عنها في شاشة وحاضرةً في تحليل الذكاء،
# ورأى الريتات بلا سعرٍ عادل. والامتناعُ قد يكون صواباً — لكنّ صوابَه
# لا يُعرف إلا بذكر سببه.
#
# يُشغَّل على الخادم حيث البيانات:
#   docker exec sp_backend python /app/scripts/audit/why_unavailable.py 2080
#   docker exec sp_backend python /app/scripts/audit/why_unavailable.py --sector "المرافق العامة"
#   docker exec sp_backend python /app/scripts/audit/why_unavailable.py --reits
#
# لا يكتب شيئاً — يقرأ ويطبع.
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


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "نعم" if v else "لا"
    if isinstance(v, (int, float)):
        return f"{v:.{nd}f}"
    return str(v)


async def one(sym: str, db) -> None:
    from app.services.market_data import market_service
    from app.services.analysis import analyze_company
    from app.services.governance_engine import evaluate_company
    from app.api.v1.endpoints.holdings import yahoo_symbol
    from app.data.market_universe import MARKET_UNIVERSE

    meta = MARKET_UNIVERSE.get(sym) or {}
    y = yahoo_symbol(sym)
    name = meta.get("name_ar") or sym
    print(f"\n══ {sym} · {name} · {meta.get('sector') or 'بلا قطاع'} ══")

    fin = await market_service.get_financials(y)
    periods = (fin or {}).get("periods") or []
    print(f"  القوائم: {len(periods)} فترة" if periods else "  القوائم: لا شيء")
    if periods:
        p0 = periods[0]
        have = [k for k in ("revenue", "net_income", "operating_cash_flow",
                            "free_cash_flow", "equity", "total_assets",
                            "debt_ratio", "interest_coverage", "eps", "shares")
                if p0.get(k) is not None]
        miss = [k for k in ("revenue", "net_income", "operating_cash_flow",
                            "free_cash_flow", "equity", "debt_ratio",
                            "interest_coverage") if p0.get(k) is None]
        print(f"    آخرُ فترة: سنة {p0.get('year')} · متوفّر {len(have)} بند")
        if miss:
            print(f"    ناقص: {' · '.join(miss)}")

    info = await market_service.get_company_info(y) or {}
    tgt = info.get("target_mean_price")
    print(f"  هدفُ المحلّلين: {_fmt(tgt)}"
          f"  (عددُ المحلّلين: {info.get('number_of_analysts') or '—'})")
    print(f"  السعر: {_fmt(info.get('price'))} · مكرّر: {_fmt(info.get('pe_ratio'))}"
          f" · دفترية: {_fmt(info.get('price_to_book'))}"
          f" · توزيعات: {_fmt(info.get('dividend_yield'))}")

    try:
        a = await analyze_company(y, name, db=db)
    except Exception as e:                                        # noqa: BLE001
        a = None
        print(f"  صفحةُ السهم: سقطت — {type(e).__name__}: {e}")
    if a:
        d = (a.get("decision") or {})
        print(f"  صفحةُ السهم: أهليّة={_fmt(a.get('evaluable'))}"
              f" · درجة={_fmt(a.get('score'), 1)}"
              f" · قرار={d.get('raw') or '—'}"
              f" · سبب={ (d.get('reason') or '—')[:70] }")
        fv = a.get("fair_value")
        print(f"    القيمةُ المعروضة: {_fmt(fv)}"
              f" · مصدرُها: {a.get('fair_value_source') or '—'}")

    try:
        g = await evaluate_company(y, db=db, sector=meta.get("sector"))
    except Exception as e:                                        # noqa: BLE001
        g = None
        print(f"  محرّكُ الحوكمة: سقط — {type(e).__name__}: {e}")
    if g:
        print(f"  محرّكُ الحوكمة: أهليّة={_fmt(g.get('evaluable'))}"
              f" · درجة={_fmt(g.get('finance_score'), 1)}"
              f" · مجلس={len(g.get('expert_panel') or [])} قراءة")
        if not g.get("evaluable"):
            print(f"    سببُ عدم الأهليّة: {g.get('reason') or g.get('note') or '—'}")


async def main() -> int:
    from app.core.database import AsyncSessionLocal
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    args = [a for a in sys.argv[1:]]
    uni = main_market(MARKET_UNIVERSE)
    syms: list[str] = []
    if "--sector" in args:
        sec = args[args.index("--sector") + 1]
        syms = [s for s, m in uni.items() if (m.get("sector") or "") == sec]
        print(f"قطاع «{sec}»: {len(syms)} شركة")
    elif "--reits" in args:
        syms = [s for s, m in uni.items()
                if "عقاري" in (m.get("sector") or "") or "صناديق" in (m.get("sector") or "")]
        print(f"الصناديق العقارية: {len(syms)} شركة")
    else:
        syms = [a.replace(".SR", "") for a in args if a.isdigit() or a.endswith(".SR")]
    if not syms:
        print("استعمال: why_unavailable.py 2080 [رمزٌ آخر...] | --sector «اسم» | --reits")
        return 2

    async with AsyncSessionLocal() as db:
        for s in syms:
            try:
                await one(s, db)
            except Exception as e:                                # noqa: BLE001
                print(f"\n══ {s} ══\n  سقط الفحص: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
