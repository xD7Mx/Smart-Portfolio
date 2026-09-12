#!/usr/bin/env python3
"""جاهزيةُ القرار — ثلاثةُ أرقامٍ تُقاس من داخل الحاوية (D284).

    docker exec sp_backend python /app/scripts/audit/readiness.py
    docker exec sp_backend python /app/scripts/audit/readiness.py 60   # عيّنة

يقرأ المخزنَ والمحرّكاتِ مباشرةً: لا مصادقة، ولا نداءَ شبكةٍ خارجيّ.
(ومسارُ `/market/fair-value-coverage` محميٌّ بمصادقة المالك — فطلبُه
بـcurl بلا رمزٍ يردّ «Not authenticated»، وهو خطأٌ في أمري لا في التطبيق.)

ويُطبع الصفرُ صفراً: هذا مقياسُ حالٍ لا لوحةُ مديح.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

ORDER = ["مرتفعة", "متوسطة", "منخفضة"]


def line(k: str, v) -> None:
    print(f"  {k:<34} {v}")


async def main() -> int:
    n_sample = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0

    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    uni = list(main_market(MARKET_UNIVERSE))
    total = len(uni)
    print(f"\nالسوق الرئيسة: {total} شركة\n")

    # ── ١ · القوائم الرسمية ─────────────────────────────────────────────
    print("١) القوائم الرسمية (XBRL من تداول)")
    try:
        from app.services.tadawul_xbrl import for_symbol
        with_stmt = [s for s in uni if for_symbol(s)]
        four_plus = [s for s in with_stmt if len(for_symbol(s) or []) >= 4]
        line("شركاتٌ لها قوائمُ رسمية", f"{len(with_stmt)} من {total}")
        line("منها بأربع فتراتٍ فأكثر", f"{len(four_plus)} — شرطُ الثقة المرتفعة")
    except Exception as e:                                        # noqa: BLE001
        line("تعذّر", f"{type(e).__name__}: {e}")
        with_stmt = []

    # ── ٢ · معايير المحرّك ──────────────────────────────────────────────
    print("\n٢) معايير المحرّك")
    try:
        from app.services.risk_free import reading as rf_reading
        rf = rf_reading() or {}
        line("المعدَّل الخالي من المخاطر",
             f"{(rf.get('value') or 0) * 100:.3f}٪ · {rf.get('as_of') or 'غير متوفّر'}"
             if rf.get("value") else "غير متوفّر — المحرّكُ يمتنع")
    except Exception as e:                                        # noqa: BLE001
        line("المعدَّل الخالي من المخاطر", f"تعذّر: {type(e).__name__}")
    try:
        from app.services.sector_betas import reading as b_reading
        b = b_reading() or {}
        secs = (b.get("sectors") or {})
        line("قطاعاتٌ لها بيتا مقيسة", f"{len(secs)} · {b.get('as_of') or '—'}")
    except Exception as e:                                        # noqa: BLE001
        secs = {}
        line("قطاعاتٌ لها بيتا مقيسة", f"تعذّر: {type(e).__name__}")
    try:
        from app.services.fair_value_engine.params import load_params
        p = load_params()
        line("ملفُّ المعايير", f"موثَّقٌ · {p.raw['as_of']}")
    except Exception as e:                                        # noqa: BLE001
        line("ملفُّ المعايير", f"مرفوضٌ — المحرّكُ يمتنع: {str(e)[:60]}")

    # ── ٣ · نطقُ المحرّك ────────────────────────────────────────────────
    print("\n٣) السعر العادل — كم شركةً ينطق لها المحرّك")
    from app.services.fair_value_engine.serve import value_for_symbol
    from app.services.tadawul_market import row_for

    pool = with_stmt or uni
    if n_sample:
        pool = pool[:n_sample]
    counts = {c: 0 for c in ORDER}
    spoke = abst = nopx = 0
    for sym in pool:
        price = (row_for(sym) or {}).get("price")
        if not price:
            nopx += 1
            continue
        try:
            out = await value_for_symbol(f"{sym}.SR", price=float(price))
        except Exception:                                         # noqa: BLE001
            out = None
        if out and out.get("value"):
            spoke += 1
            counts[out.get("confidence") or "منخفضة"] = \
                counts.get(out.get("confidence") or "منخفضة", 0) + 1
        else:
            abst += 1
    line("قِيست", f"{len(pool)} شركة")
    line("نطق المحرّك", f"{spoke}")
    for c in ORDER:
        line(f"  منها ثقةٌ {c}", counts.get(c, 0))
    line("امتنع", abst)
    line("بلا سعرٍ في اللقطة", nopx)

    usable = counts.get("مرتفعة", 0) + counts.get("متوسطة", 0)
    print("\nالخلاصة")
    line("يحمل اسمَ «السعر العادل»", f"{usable} من {len(pool)} — ثقةٌ متوسطةٌ فأعلى")
    if not with_stmt:
        print("\n  القوائمُ الرسميةُ لم تُقرأ بعد. الدفعةُ تعمل 22:15 و01:30 —"
              "\n  وتكتمل التغطيةُ في نحو أربع ليالٍ من التركيب.")
    # ── ٤ · ولماذا فرغ ما فرغ ───────────────────────────────────────────
    # صفرٌ بلا سببٍ يُطلب له مسبارٌ آخر — ودورةُ المسابر أنهكت المالك.
    # فيُقاس السببُ هنا: تُجرَّب قراءةٌ واحدةٌ ويُطبع ما ردّته.
    if "--why" in sys.argv or not with_stmt or not secs:
        print("\n٤) لماذا فرغ ما فرغ — قراءةٌ واحدةٌ تُجرَّب الآن")
        rows, live, at = _rows_state()
        line("لقطةُ السوق", f"{len(rows)} رمزاً · "
                            f"{'حيّة' if live else 'آخرُ إغلاق'} · {at or '—'}")
        try:
            from app.services.tadawul_xbrl import refresh as x_refresh
            r = await x_refresh(["1010"])
            line("قراءةُ XBRL لـ1010", str(r)[:110])
        except Exception as e:                                    # noqa: BLE001
            line("قراءةُ XBRL لـ1010", f"{type(e).__name__}: {str(e)[:90]}")
        try:
            from app.services.sector_betas import refresh as b_refresh
            r = await b_refresh(uni[:12])
            line("محاولةُ بيتا (12 شركة)", str(r)[:110])
        except Exception as e:                                    # noqa: BLE001
            line("محاولةُ بيتا", f"{type(e).__name__}: {str(e)[:90]}")

    print(f"\nقِيس في {dt.datetime.now():%Y-%m-%d %H:%M}\n")
    return 0


def _rows_state():
    try:
        from app.services.tadawul_market import usable_rows
        return usable_rows()
    except Exception:                                             # noqa: BLE001
        from app.services.tadawul_market import snapshot
        return snapshot(), True, None


raise SystemExit(asyncio.run(main()))
