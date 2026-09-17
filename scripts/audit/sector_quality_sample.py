#!/usr/bin/env python3
"""عيّنةٌ من كلّ قطاعٍ تُحاكم المحرّكَين — جودةً وسعراً عادلاً (D391).

    docker exec sp_backend python /app/scripts/audit/sector_quality_sample.py
    docker exec sp_backend python /app/scripts/audit/sector_quality_sample.py --n 4
    docker exec sp_backend python /app/scripts/audit/sector_quality_sample.py --sector البنوك

بأمر المالك: «ابنِ المحرّكَ ليتماشى مع كلّ قطاعٍ بخارطته، مع سحبِ
عيّناتِ شركاتٍ لكلّ قطاعٍ للتأكّد من جودة التقييم للمحرّكَين: الجودة
والعادل».

ومعيارُ الحكم ليس «خرج رقمٌ أم لا» — بل **أربعةٌ تُقاس لكلّ قطاع**:

  ١· **التغطية**: كم ورقةً خرجت لها درجةٌ وكم خرج لها سعرٌ عادل.
  ٢· **الخريطة**: أيُّ المسارات حُكِّمت فعلاً، وهل هي مساراتُ خريطة
     القطاع في `VALUATION` أم مساراتٌ عامّة تسلّلت (‏تدفّقٌ حرٌّ لبنك ·
     مضاعفُ ربحيةٍ لريتٍ بلا توزيع).
  ٣· **الصدق**: عمرُ الأرقام وثقتُها — فدرجةٌ على قوائمِ 2022 ليست
     كدرجةٍ على قوائم هذا الربع، ورقمٌ بثقةٍ منخفضةٍ يُعلَن.
  ٤· **سببُ الامتناع** حين يمتنع: يُطبَع بنصّه ويُجمَع بالتكرار — فأكثرُ
     سببٍ تكرّر هو العملُ التالي، لا الورقةُ الأولى في القائمة.

والعيّنةُ من **الدليل الرسميّ** (‏273 شركةً · 22 قطاعاً · بلا «نمو»)،
موزَّعةً على القطاعات كلِّها لا مقتطعةً من أوّل القائمة (‏D364).
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

N = 3
if "--n" in sys.argv:
    i = sys.argv.index("--n")
    try:
        N = max(1, min(8, int(sys.argv[i + 1])))
    except (IndexError, ValueError):
        N = 3
ONLY = None
if "--sector" in sys.argv:
    j = sys.argv.index("--sector")
    ONLY = sys.argv[j + 1] if j + 1 < len(sys.argv) else None
CONC = 4


async def main() -> int:
    from app.data.archetype_spec import VALUATION
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services.analysis import analyze_company
    from app.services.statement_merge import archetype_of

    mm = main_market(MARKET_UNIVERSE)
    by_sec: dict[str, list[str]] = {}
    for s, m in mm.items():
        by_sec.setdefault((m or {}).get("sector") or "—", []).append(s)
    for k in by_sec:
        by_sec[k].sort()
    secs = sorted(by_sec) if not ONLY else [k for k in by_sec if ONLY in k]
    if not secs:
        print(f"لا قطاعَ يوافق «{ONLY}» — القطاعاتُ: {' · '.join(sorted(by_sec))}")
        return 1
    pick = [(k, s) for k in secs for s in by_sec[k][:N]]
    print(f"═ محاكمةُ المحرّكَين بالقطاع ═ قطاعاتٌ={len(secs)}"
          f" · من كلٍّ {N} · أوراقٌ={len(pick)}"
          f" · الدليلُ الرسميُّ {len(mm)} شركة")

    sem = asyncio.Semaphore(CONC)
    rows: dict[str, list[dict]] = {}

    async def one(sec: str, sym: str) -> None:
        async with sem:
            try:
                a = await analyze_company(f"{sym}.SR", allow_supplement=False)
            except Exception as e:                                # noqa: BLE001
                rows.setdefault(sec, []).append(
                    {"sym": sym, "err": f"{type(e).__name__}"})
                return
            a = a or {}
            fv = a.get("fair_value_detail") or {}
            fin = a.get("financial") or {}
            prov = a.get("governance_provenance") or {}
            rows.setdefault(sec, []).append({
                "sym": sym,
                "arch": archetype_of(sym),
                "score": (fin or {}).get("score"),
                "stmt_asof": prov.get("تاريخ الأرقام"),
                "stmt_age": prov.get("عمر الأرقام أياماً"),
                "fv": a.get("fair_value"),
                "low": a.get("fair_value_low"),
                "high": a.get("fair_value_high"),
                "conf": a.get("fair_value_conf"),
                "disp": fv.get("dispersion"),
                "paths": [m.get("name") for m in (fv.get("methods") or [])],
                "why": (fv.get("unavailable_reason") or "")[:96],
                "price": a.get("price"),
            })

    await asyncio.gather(*(one(k, s) for k, s in pick),
                         return_exceptions=True)

    no_fv: Counter = Counter()
    tot = {"n": 0, "score": 0, "fv": 0, "stale": 0}
    for sec in secs:
        rs = rows.get(sec) or []
        spec = VALUATION.get(
            next((r.get("arch") for r in rs if r.get("arch")), "") or "", {})
        want = " · ".join((spec.get("weights") or {}).keys()) or "—"
        print(f"\n═════ {sec} ═════ خريطةُ الصنف: {want}")
        for r in rs:
            tot["n"] += 1
            if r.get("err"):
                print(f"  {r['sym']}: تعذّر — {r['err']}")
                continue
            if r.get("score") is not None:
                tot["score"] += 1
            if r.get("fv") is not None:
                tot["fv"] += 1
            if (r.get("stmt_age") or 0) > 200:
                tot["stale"] += 1
            age = (f"{r['stmt_asof']}({r['stmt_age']}ي)"
                   if r.get("stmt_asof") else "بلا تاريخ")
            print(f"  {r['sym']} · {r.get('arch') or '—'}"
                  f" · سعر={r.get('price')}"
                  f" · درجة={r.get('score') if r.get('score') is not None else '—'}"
                  f" · قوائمُ {age}")
            if r.get("fv") is not None:
                print(f"       عادلٌ={r['fv']} ({r.get('low')}–{r.get('high')})"
                      f" · ثقة={r.get('conf')}"
                      + (f" · تشتّت={r['disp']}×" if r.get("disp") else "")
                      + f" · مسارات: {' + '.join(str(p)[:26] for p in r['paths']) or '—'}")
            else:
                print(f"       عادلٌ=— · السبب: {r.get('why') or 'غير معلَن'}")
                no_fv[(r.get("arch") or "—") + " | " + (r.get("why") or "غير معلَن")[:70]] += 1

    n = tot["n"] or 1
    print("\n═ الحصيلةُ عبر القطاعات ═")
    print(f"  أوراقٌ مقيسة: {tot['n']}"
          f" · لها درجة: {tot['score']} ({100*tot['score']//n}%)"
          f" · لها سعرٌ عادل: {tot['fv']} ({100*tot['fv']//n}%)"
          f" · قوائمُها شائخة: {tot['stale']}")
    if no_fv:
        print("\n═ أسبابُ الامتناع مرتَّبةً بالتكرار — وهي ترتيبُ العمل ═")
        for k, c in no_fv.most_common(10):
            print(f"  {c:>3}  {k}")
    print("\nالحكم: كلُّ قطاعٍ يُقرأ بخريطته: مسارٌ خارجُ خريطةِ صنفه عطبٌ"
          " وإن أخرج رقماً، وامتناعٌ سببُه مدخلٌ غائبٌ عملٌ باقٍ لا حكمٌ"
          " نهائيّ. وأكثرُ سببٍ تكرّر يُعالَج أوّلاً — لا الورقةُ الأولى"
          " في القائمة.")
    return 0


raise SystemExit(asyncio.run(main()))
