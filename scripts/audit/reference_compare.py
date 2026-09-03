"""معايرةُ محرّكنا على مرجعٍ خارجيّ — درجتُنا مقابل InvestingPro.

## السؤال الذي يجيبه

هل ترتّب درجتُنا الشركاتِ كما يرتّبها مرجعٌ مستقلّ؟ فإن اتّفق الترتيبُ
على عيّنةٍ متنوّعةِ القطاعات، وثِقنا بالمحرّك على السوق كلِّها — ولا
حاجةَ إلى إدخالٍ يدويٍّ دائم.

وإن اختلف، فالاختلافُ نفسُه هو الفائدة: يسمّي الشركاتِ التي نبتعد فيها
فنعرف **أين** ينحرف المحرّك بدل أن نجتهد في الفراغ.

## ما لا يفعله

لا يغيّر درجةً ولا وزناً ولا عتبة. **قياسٌ فقط.** ودرجةُ المرجع لا
تدخل الحوكمةَ ولا تُعرض للمستخدم.

    docker exec sp_backend python /app/scripts/audit/reference_compare.py
"""

from __future__ import annotations

import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _spearman(pairs: list[tuple[float, float]]) -> float | None:
    """ارتباطُ الرتب — يقيس اتّفاقَ الترتيب لا تطابقَ الأرقام.

    وهو المقياسُ الصحيح هنا: مقياسُنا ومقياسُهم قد يختلفان في المدى
    والمركز، والمهمُّ أن تتّفق الشركةُ الأقوى عندنا مع الأقوى عندهم.
    """
    n = len(pairs)
    if n < 4:
        return None

    def ranks(vals):
        order = sorted(range(n), key=lambda i: vals[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    a = ranks([p[0] for p in pairs])
    b = ranks([p[1] for p in pairs])
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    da = sum((x - ma) ** 2 for x in a) ** 0.5
    db = sum((y - mb) ** 2 for y in b) ** 0.5
    return round(num / (da * db), 3) if da and db else None


def _med(v):
    s = sorted(v)
    return None if not s else (s[len(s) // 2] if len(s) % 2
                               else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2)


async def main() -> int:
    from app.services import reference_scores as ref
    from app.services.governance_engine import evaluate_company
    from app.data.saudi_directory import name_of
    from app.data.market_universe import MARKET_UNIVERSE

    syms = ref.all_symbols()
    if not syms:
        print("✖ لا مراجعَ مُدخَلة. أنشئ القالب ثم املأه:")
        print("    python scripts/reference_entry.py --template > ref.csv")
        return 2

    rows = []
    for s in syms:
        r = ref.get(s) or {}
        sec = (MARKET_UNIVERSE.get(s) or {}).get("sector")
        try:
            gov = await evaluate_company(f"{s}.SR", sector=sec)
        except Exception:                                         # noqa: BLE001
            gov = None
        rows.append({
            "sym": s, "name": (name_of(s) or "")[:22], "sector": sec or "—",
            "ours": (gov or {}).get("overall"),
            "theirs": r.get("health_100"),
            "their_fv": r.get("fair_value"),
        })

    print("═" * 74)
    print("  معايرةُ درجة السلامة — محرّكُنا مقابل المرجع")
    print("═" * 74)
    print(f"  {'الرمز':6} {'الشركة':24} {'لنا':>6} {'المرجع':>8} {'الفرق':>7}")
    both = []
    for r in sorted(rows, key=lambda x: -(x["theirs"] or -1)):
        o, t = r["ours"], r["theirs"]
        d = round(o - t, 1) if isinstance(o, (int, float)) and \
            isinstance(t, (int, float)) else None
        if d is not None:
            both.append((o, t))
        print(f"  {r['sym']:6} {r['name']:24} "
              f"{('—' if o is None else round(o,1)):>6} "
              f"{('—' if t is None else t):>8} "
              f"{('—' if d is None else f'{d:+.1f}'):>7}")

    print("\n" + "─" * 74)
    if len(both) < 4:
        print(f"  شركاتٌ للمقارنة {len(both)} — لا تكفي لحكم. "
              f"يلزم عشرون فأكثر لتنوّعٍ معتبَر.")
        return 0
    rho = _spearman(both)
    diffs = [abs(o - t) for o, t in both]
    bias = _med([o - t for o, t in both])
    print(f"  شركاتٌ مقارَنة        {len(both)}")
    print(f"  ارتباطُ الرتب (‏ρ)     {rho}")
    print(f"  وسيطُ الفارق المطلق   {_med(diffs):.1f} نقطة")
    print(f"  الميلُ المنهجيّ        {bias:+.1f} نقطة "
          f"({'نحن أعلى' if bias > 0 else 'نحن أدنى'})")

    far = sorted(((abs(o - t), r) for (o, t), r in
                  zip(both, [x for x in rows
                             if isinstance(x['ours'], (int, float))
                             and isinstance(x['theirs'], (int, float))])),
                 key=lambda x: -x[0])[:5]
    if far:
        print(f"\n  أبعدُ خمسٍ — هنا يُبحث عن سبب الانحراف:")
        for d, r in far:
            print(f"    {r['sym']} {r['name']:22} {r['sector'][:18]:18} "
                  f"فارق {d:.0f}")

    print("\n" + "═" * 74)
    if rho is not None and rho >= 0.70:
        print("  ✔ الترتيبُ متّفق — المحرّكُ موثوقٌ على السوق كلِّها.")
    elif rho is not None and rho >= 0.40:
        print("  ~ اتّفاقٌ جزئيّ — راجِع «أبعدُ خمس» قبل التعميم.")
    else:
        print("  ✖ الترتيبُ لا يتّفق — لا يُعمَّم المحرّكُ قبل تفسير الفارق.")
    print("  (‏قياسٌ فقط: لم تُغيَّر درجةٌ ولا وزنٌ ولا عتبة.)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
