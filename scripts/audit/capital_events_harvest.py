"""‏D674 — الحصادُ الأوّل لأحداث رأس المال (السوقُ الرئيسيّ كلُّه) ثمّ ما يغيّره في عدد الأسهم.

يكتب مخزنَ أحداث رأس المال وحده (‏capev:events) — ما يكتبه الحصّادُ الليليّ نفسُه؛ لا يمسّ أرقامَ المالك ولا تقييماً محفوظاً.
ثمّ يطبع لكلّ شركةٍ لها حدثٌ بعد آخر قوائمها: نوعَه وتاريخه، وعددَ القوائم والسوق، وحكمَ المحرّك (عددُ السوق · لا رقم · كما هو).

    docker exec sp_backend python /app/scripts/audit/capital_events_harvest.py
"""
import asyncio
import collections
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services import capital_events as CE, fair_value_models as F
    from app.services.tadawul_xbrl import for_symbol as X
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market, is_nomu
    syms = sorted(s for s in main_market(MU) if not is_nomu(s))
    rep = await CE.harvest(syms, max_age_days=7, pause=1.2)
    if rep.get("failed"):
        rep2 = await CE.harvest(syms, max_age_days=7, pause=2.5)     # ما تعذّر يُعاد مرّةً بتمهّلٍ أكبر
        rep = {**rep, "retry": rep2}
    print("@@HARVEST@@", rep)
    kinds = collections.Counter(e["k"] for s in syms for e in CE.events_of(s))
    print("@@KINDS@@", dict(kinds), "· شركاتٌ قُرئت", sum(CE.harvested(s) for s in syms), "من", len(syms))
    after = []
    for s in syms:
        a, q = X(s, "annual") or [], X(s, "quarterly") or []
        last = max((str(x.get("as_of") or f"{x.get('year')}-12-31")[:10] for x in (q[-1:] + a[-1:])), default=None)
        ev = CE.kind_after(s, last)
        if ev:
            after.append((s, last, ev))
    print(f"@@AFTER@@ لها حدثٌ بعد آخر قوائمها {len(after)}")
    for s, last, ev in after:
        try:
            i = await F.gather(s)
        except Exception as e:                                     # noqa: BLE001
            i = None
            print(f"   {s} · تعذّر: {type(e).__name__}")
        verdict = "—"
        if i is not None:
            if i.capital_pending:
                verdict = "لا رقم حتى تُنشر قوائمُ تشملها"
            elif any("إفصاحات «تداول»" in n for n in i.notes):
                verdict = f"عددُ السوق {i.shares / 1e6:,.1f} مليون"
            else:
                verdict = f"كما هو {i.shares / 1e6:,.1f} مليون (الفرقُ دون 5٪)"
        print(f"@@EV@@ {s} {(MU.get(s) or {}).get('name_ar')} · قوائم {last} · {ev['kind']} {ev['date']} · {verdict} · "
              f"{str(ev.get('title'))[:110]}")


asyncio.run(main())
