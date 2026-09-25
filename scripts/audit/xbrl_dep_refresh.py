#!/usr/bin/env python3
"""المرحلةُ الأولى (D489): إعادةُ قراءة قوائم «تداول» ليُحفظ بندُ الإهلاك، ثمّ قياسُ التغطية.

    docker exec sp_backend python /app/scripts/audit/xbrl_dep_refresh.py

شرطُ الإنهاء المعلَن للمالك: الإهلاكُ حاضرٌ لـ90٪ فأكثر من شركات السوق الرئيسة
غير المالية، ويُطبع الناقصُ بالاسم. ثمّ عددُ النماذج العاملة لرموزه الـ22
مقابل عددها في InvestingPro.
"""
import asyncio, sys, time
sys.path.insert(0, "/app")

REPS = {"2222": 14, "2010": 14, "1302": 7, "1831": 13, "4030": 14, "2340": 10, "1810": 12,
        "4072": 13, "4003": 13, "4001": 15, "2280": 15, "4165": 15, "4013": 14, "4164": 14,
        "1120": 3, "1111": 15, "8210": 4, "7010": 15, "2082": 13, "4330": 3, "4300": 11, "7203": 14}
FIN = {"البنوك", "التأمين", "الخدمات المالية", "الصناديق العقارية المتداولة"}


async def main():
    from app.data.universe import main_market, is_etf
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.services import tadawul_xbrl as X
    from app.services import fair_value_models as F
    syms = [s for s, m in main_market(U).items()
            if not is_etf(s) and (m or {}).get("sector") not in FIN]
    t0 = time.time()
    rep = await X.refresh(syms, conc=3)
    print(f"═ إعادةُ القراءة: {len(syms)} ورقة في {time.time()-t0:.0f} ث · {rep}")
    have, miss = [], []
    for s in syms:
        an = X.for_symbol(s, "annual") or []
        (have if an and an[-1].get("depreciation") is not None else miss).append(s)
    pct = 100 * len(have) / max(len(syms), 1)
    print(f"\n═ الإهلاكُ في أحدث سنة: {len(have)} من {len(syms)} = {pct:.1f}٪ "
          f"({'✔ الشرطُ متحقّق' if pct >= 90 else '✖ دون 90٪'})")
    for s in miss:
        print(f"   ناقص: {s} {(U.get(s) or {}).get('name_ar') or ''}")
    print("\n═ النماذجُ العاملة لرموز المالك مقابل InvestingPro:")
    for s, n in REPS.items():
        try:
            r = await F.for_symbol(s)
        except Exception as e:                                     # noqa: BLE001
            print(f"   {s}: تعذّر — {type(e).__name__}"); continue
        keys = sorted(m["key"] for m in (r or {}).get("models") or [])
        print(f"   {s}: {len(keys)} من {n} · قيمة {(r or {}).get('value')} · {', '.join(keys)}")


async def sanity():
    """معيارُ المالك: قرينٌ من كلّ قطاعٍ له هدفُ محللين في ياهو — سعرُنا العادلُ
    بجانبه. هدفٌ 5 وسعرُنا 8 (أو العكس) غيرُ منطقيّ: يُوسَم ما خرج عن ±30٪."""
    from app.data.universe import main_market
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.services import fair_value_models as F
    from app.services.market_data import market_service
    by_sec: dict[str, list[str]] = {}
    for s, m in main_market(U).items():
        by_sec.setdefault((m or {}).get("sector") or "—", []).append(s)
    rows = []
    for sec, syms in sorted(by_sec.items()):
        order = [x for x in REPS if x in syms] + [x for x in syms if x not in REPS]
        pick = None
        for s in order[:12]:
            try:
                info = await market_service.get_company_info(s + ".SR") or {}
            except Exception:                                      # noqa: BLE001
                continue
            tgt = info.get("target_mean_price")
            if tgt:
                pick = (s, float(tgt), info.get("price") or info.get("current_price")); break
        if not pick:
            print(f"   {sec}: لا هدفَ محللين لأيّ ورقةٍ مفحوصة"); continue
        s, tgt, px = pick
        try:
            r = await F.for_symbol(s) or {}
        except Exception:                                          # noqa: BLE001
            r = {}
        fv = r.get("value")
        ratio = (fv / tgt) if fv and tgt else None
        flag = "—" if ratio is None else ("✔" if 0.7 <= ratio <= 1.3 else "✖")
        rows.append((sec, s, px, tgt, fv, ratio, flag, r.get("count")))
    print("\n═ معيارُ المالك: سعرُنا العادل مقابل هدف المحللين (ياهو)، ورقةٌ لكلّ قطاع")
    print(f"   {'القطاع':<34} {'الرمز':<5} {'السعر':>8} {'المحللون':>9} {'سعرُنا':>9} {'النسبة':>7}  نماذج")
    for sec, s, px, tgt, fv, ratio, flag, n in rows:
        print(f"   {sec:<34} {s:<5} {px or 0:>8.2f} {tgt:>9.2f} {fv or 0:>9.2f} "
              f"{(ratio or 0):>6.2f}× {flag}  {n}")
    ok = sum(1 for r in rows if r[6] == "✔")
    print(f"\n   ضمن ±30٪: {ok} من {len(rows)} قطاعاً")


async def all_():
    await main()
    await sanity()

asyncio.run(all_())
