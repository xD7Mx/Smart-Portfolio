"""كاشفُ البلاغات المفتوحة (قراءةٌ فقط): ثمانيةٌ وعشرون بلاغاً قديماً (‏D270–D415) حالتُها «مفتوح — يُقاس على الخادم».
يقيس كلَّ همٍّ منها في الإنتاج اليوم بالدالّة التي يعرضها التطبيق، فيُغلق ما حلّته أعمالٌ لاحقةٌ بشاهدٍ مقيس، ويُسمّى ما بقي.

    docker exec sp_backend python /app/scripts/audit/open_items_door.py
"""
import asyncio
import collections
import sys
from datetime import date

sys.path.insert(0, "/app")


def _age(p):
    try:
        return (date.today() - date.fromisoformat(str(p.get("as_of") or f"{p.get('year')}-12-31")[:10])).days
    except Exception:                                              # noqa: BLE001
        return None


async def main():
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market, is_nomu
    from app.services.statement_merge import archetype_of
    from app.services.tadawul_xbrl import for_symbol as X
    from app.services.content_engine import fund_store_load
    syms = sorted(s for s in main_market(MU) if not is_nomu(s))
    arch = {s: archetype_of(s) for s in syms}
    st = fund_store_load() or {}

    # ── القوائم: من لا ملفّاتَ له، وعمرُ أحدثها (‏D356 · D359 · D365–D368 · D410) ──
    no_annual, ages, ttm_ok, ie_ok, ie_n, ins_rev, ins_n = [], [], 0, 0, 0, 0, 0
    for s in syms:
        a, q = X(s, "annual") or [], X(s, "quarterly") or []
        if not a and not q:
            no_annual.append(s)
            continue
        last = max((a[-1:] + q[-1:]), key=lambda p: str(p.get("as_of") or ""))
        ages.append(_age(last) or 0)
        a_end = str((a[-1] if a else {}).get("as_of") or "")
        if len([p for p in q if str(p.get("as_of") or "") > a_end]) >= 1 or len(q) >= 4:
            ttm_ok += 1
        if arch[s] not in ("bank", "insurance", "financial", "reit"):
            ie_n += 1
            if any(isinstance(p.get("interest_expense"), (int, float)) for p in (a[-2:] + q[-4:])):
                ie_ok += 1
        if arch[s] == "insurance":
            ins_n += 1
            if isinstance(last.get("revenue"), (int, float)) and last["revenue"] > 0 and (_age(last) or 999) <= 274:
                ins_rev += 1
    print(f"@@STMT@@ بلا قوائمَ أصلاً {len(no_annual)} من {len(syms)} {no_annual[:8]}")
    print(f"@@AGE@@ أحدثُ القوائم: ≤ 200 يوم {sum(a <= 200 for a in ages)} · ≤ 274 {sum(a <= 274 for a in ages)} · "
          f"أقدمُ من 274 {sum(a > 274 for a in ages)} · أقدمُ من 456 {sum(a > 456 for a in ages)} من {len(ages)}")
    print(f"@@TTM@@ أرباعٌ بعد آخر سنة أو أربعةٌ فأكثر {ttm_ok} من {len(syms) - len(no_annual)}")
    print(f"@@IE@@ تكلفةُ التمويل منشورةٌ لغير الماليّة {ie_ok} من {ie_n}")
    print(f"@@INS@@ التأمين: إيرادٌ موجبٌ في أحدث قوائمَ دون 274 يوماً {ins_rev} من {ins_n}")

    # ── السعرُ العادل: التغطية، والمدى يحوي القيمة (‏D334 · D371 · D393) ──
    have = [s for s in syms if isinstance((st.get(s) or {}).get("fair_value"), (int, float))]
    bad_rng = [s for s in have if isinstance((st.get(s) or {}).get("fair_value_low"), (int, float))
               and isinstance((st.get(s) or {}).get("fair_value_high"), (int, float))
               and not (st[s]["fair_value_low"] <= st[s]["fair_value"] <= st[s]["fair_value_high"])]
    a2222 = st.get("2222") or {}
    print(f"@@FV@@ بسعرٍ عادل {len(have)} من {len(syms)} · مدى لا يحوي قيمتَه {len(bad_rng)} {bad_rng[:6]} · "
          f"أرامكو {a2222.get('fair_value')} ({a2222.get('fair_value_low')}–{a2222.get('fair_value_high')}) "
          f"ثقة {a2222.get('fair_value_conf')}")

    # ── الريتاتُ والصناديق (‏D338 · D341 · D345) ──
    reits = sorted(s for s in MU if archetype_of(s) == "reit")
    try:
        from app.services.reit_advisor import cached as reit_cached
        rv = [s for s in reits if reit_cached(s)]
    except Exception as e:                                         # noqa: BLE001
        rv = []
        print("   الريت: تعذّر", type(e).__name__)
    rfv = [s for s in reits if isinstance((st.get(s) or {}).get("fair_value"), (int, float))]
    print(f"@@REIT@@ ريتات {len(reits)} · بمستشارٍ محفوظ {len(rv)} · بسعرٍ عادل {len(rfv)}")

    # ── كبارُ الملّاك (‏D270 · D275) — المحفوظُ كما تعرضه الصفحة، وقراءةٌ حيّةٌ لأرامكو بلا حفظ ──
    try:
        from app.services import tadawul_ownership as TO
        rd = {s: TO.reading(s) for s in syms}
        kinds = collections.Counter(k for r in rd.values() if r for k in TO.KINDS if r.get(k))
        print(f"@@OWN@@ ملكيةٌ محفوظة {sum(1 for r in rd.values() if r)} من {len(syms)} · بنودُها {dict(kinds)}")
        live = await TO.read_symbol("2222")
        print(f"@@OWN2222@@ بنودٌ حيّة {[k for k in TO.KINDS if k in live]} · {str({k: live.get(k) for k in TO.KINDS if k in live})[:240]}"
              f" · خطأ {live.get('error')}")
    except Exception as e:                                         # noqa: BLE001
        print("@@OWN@@ تعذّر", type(e).__name__, str(e)[:160])

    # ── الصفقاتُ الخاصة (‏D273 · D292 · D293 · D303 · D305 · D310–D317) — المحفوظُ كما تعرضه الشاشة ──
    try:
        from app.services import special_deals as SD
        rec = SD.reading() or {}
        deals = rec.get("deals") or []
        real = [d for d in deals if str(d.get("symbol") or "") in MU]
        print(f"@@DEALS@@ محفوظة {len(deals)} · برموزٍ حقيقية {len(real)} · بتاريخ {rec.get('as_of') or rec.get('at')} · "
              f"المصدر {rec.get('source')}")
        for d in deals[:4]:
            print("   ", {k: d.get(k) for k in ("date", "symbol", "name", "price", "volume", "value") if k in d})
    except Exception as e:                                         # noqa: BLE001
        print("@@DEALS@@ تعذّر", type(e).__name__, str(e)[:160])

    why = collections.Counter(str((st.get(s) or {}).get("fair_value_unavailable"))[:60] for s in syms if s not in have)
    for w, n in why.most_common(6):
        print(f"   {n:>3} × {w}")


asyncio.run(main())
