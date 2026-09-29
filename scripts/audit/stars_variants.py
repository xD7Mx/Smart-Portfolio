"""كم نجماً تُخرج كلُّ صيغةٍ من القاعدة؟ (قراءةٌ فقط — لا تُكتب السلّة)

    docker exec sp_backend python /app/scripts/audit/stars_variants.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import tasi_stars as S
    from app.services.market_screener import get_cached_screener
    from app.services.tadawul_market import usable_rows
    rows = get_cached_screener() or []
    rec = S._load() or {}
    tasi = rec.get("tasi_ret_12m")
    snap = usable_rows()[0] or {}
    large = S.large_caps(snap)
    print("تاسي 12ش:", tasi, "· صفوف:", len(rows))

    def count(up=15, conf=True, score=70, stale=270, big=True, beat=True):
        out = []
        for r in rows:
            s = str(r.get("symbol"))
            u, fs, age, rt = r.get("fair_value_upside_pct"), r.get("finance_score"), r.get("stmt_age_days"), r.get("ret_12m")
            if not S._main_share(s) or (big and s not in large):
                continue
            if not (isinstance(u, (int, float)) and u >= up):
                continue
            if conf and r.get("fair_value_conf") in (None, "منخفضة"):
                continue
            if not (isinstance(fs, (int, float)) and fs >= score) or (r.get("red_lines") or 0):
                continue
            if not (isinstance(age, (int, float)) and age <= stale) or r.get("sharia") == "NON_COMPLIANT":
                continue
            if beat and not (isinstance(rt, (int, float)) and tasi is not None and rt > tasi):
                continue
            out.append(s)
        return out

    variants = [
        ("القاعدةُ الحالية", {}),
        ("بلا شرط ثقة التقييم", {"conf": False}),
        ("بلا ثقة · عادل ≥10٪", {"conf": False, "up": 10}),
        ("بلا ثقة · درجة ≥60", {"conf": False, "score": 60}),
        ("بلا ثقة · كلّ السوق الرئيسيّ", {"conf": False, "big": False}),
        ("بلا ثقة · عادل ≥10٪ · درجة ≥60", {"conf": False, "up": 10, "score": 60}),
        ("بلا ثقة · عادل ≥10٪ · درجة ≥60 · كلّ السوق", {"conf": False, "up": 10, "score": 60, "big": False}),
    ]
    for name, kw in variants:
        got = count(**kw)
        print(f"  {len(got):>3} ← {name}: {' '.join(got[:25])}")
    confs = {}
    for r in rows:
        confs[r.get("fair_value_conf")] = confs.get(r.get("fair_value_conf"), 0) + 1
    print("توزيعُ ثقة التقييم:", confs)


asyncio.run(main())
