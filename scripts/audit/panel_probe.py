"""عتباتُ مجلس الخبراء — تُقاس على السوق قبل أن تُصدَّق.

## السؤال

لكلّ نمطٍ ثلاثةُ مؤشّراتٍ أو خمسة، ولكلٍّ عتبتان: «جيّد» و«ضعيف».
وهي ثمانون رقماً. فأيُّها يفرّق فعلاً؟

  · عتبةٌ **لا يبلغها أحد** في السوق عتبةٌ خاطئة — لا مسطرةٌ عالية.
  · وعتبةٌ **يبلغها الجميع** لا تفرّق — فوجودُها كعدمه.
  · ومؤشّرٌ **لا تصل بياناتُه أصلاً** عمودٌ ميّتٌ في المجلس: يُعرض
    فارغاً أو يسقط الرأيُ الذي بُني عليه.

فيُقاس كلٌّ منها على شركات السوق الحقيقية، ويُحكم بالأرقام.

## ما لا يفعله

لا يغيّر عتبةً ولا يقترح بديلاً. **قياسٌ فقط** — والتعديلُ قرارٌ يُتّخذ
بعد قراءة الجدول، لا يُدسّ فيه.

## لا يستهلك حصّة

يقرأ القوائمَ المخزَّنة وحدها، فمن لا قوائمَ له يُترك ولا يُطلب.

    docker exec sp_backend python /app/scripts/audit/panel_probe.py
"""

from __future__ import annotations

import os
import statistics as st
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

MIN_N = 5          # دون خمسِ شركاتٍ لا يُحكم على عتبة
ALL_PASS = 0.95    # يبلغها الجميع
NONE_PASS = 0.0    # لا يبلغها أحد


def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data import universe as uni
    from app.services import cache, lastgood, spec_score
    from app.services.four_scores import build_company_features
    from app.services.expert_panel import _ARCH_PILLARS, _val

    # ── جمعُ السمات لكلّ نمط ──
    by_arch: dict[str, list[dict]] = defaultdict(list)
    read = 0
    for sym, meta in MARKET_UNIVERSE.items():
        if not uni.is_main(sym):
            continue
        sec = meta.get("sector")
        if not sec:
            continue
        ck = f"stmt:{sym}.SR"
        data = cache.get(ck) or lastgood.load(
            ck, max_age_seconds=cache.FUNDAMENTALS_TTL)
        periods = (data or {}).get("periods") if isinstance(data, dict) else data
        if not periods or len(periods) < 2:
            continue
        arch, solved = spec_score.resolve_archetype_ex(sec, {})
        if not solved:
            continue
        try:
            feats, _i, _q = build_company_features(periods, sector=sec)
        except Exception:                                         # noqa: BLE001
            continue
        read += 1
        by_arch[arch].append(feats)

    if not read:
        print("✖ لا قوائمَ مخزَّنة. شغّل مسحَ السوق أوّلاً:")
        print("    docker exec sp_backend python /app/scripts/audit/market_sweep.py --market")
        return 2

    print("═" * 84)
    print("  عتباتُ مجلس الخبراء — هل تفرّق؟")
    print("═" * 84)
    print(f"  شركاتٌ مقروءة {read} · أنماطٌ ممثَّلة {len(by_arch)}\n")
    print(f"  {'النمط/المؤشّر':40} {'ع':>3} {'وسيط':>8} "
          f"{'جيّد':>6} {'ضعيف':>6} {'%جيّد':>6} الحكم")

    dead, never, always = [], [], []
    for arch in sorted(_ARCH_PILLARS, key=lambda a: -len(by_arch.get(a, []))):
        rows = by_arch.get(arch) or []
        print(f"\n  ── {arch}  ({len(rows)} شركة) ──")
        for pillar in _ARCH_PILLARS[arch]:
            key, label, _unit, direction, good, weak = pillar[:6]
            vals = [v for v in (_val(f, key) for f in rows)
                    if isinstance(v, (int, float))]
            if not vals:
                print(f"  {key[:38]:40} {'—':>3} "
                      f"{'لا تصل بياناتُه':>34}")
                if rows:
                    dead.append(f"{arch}/{key}")
                continue
            if direction == "lower":
                ok = sum(1 for v in vals if v <= good)
            elif direction == "band":
                lo, hi = min(good, weak), max(good, weak)
                ok = sum(1 for v in vals if lo <= v <= hi)
            else:
                ok = sum(1 for v in vals if v >= good)
            share = ok / len(vals)
            verdict = ""
            if len(vals) >= MIN_N:
                if share <= NONE_PASS:
                    verdict = "✖ لا يبلغها أحد"
                    never.append(f"{arch}/{key} (وسيط {st.median(vals):.1f} · "
                                 f"جيّد {good})")
                elif share >= ALL_PASS:
                    verdict = "✖ يبلغها الجميع"
                    always.append(f"{arch}/{key} ({share:.0%})")
                else:
                    verdict = "✔ تفرّق"
            else:
                verdict = "· عيّنةٌ صغيرة"
            print(f"  {key[:38]:40} {len(vals):>3} "
                  f"{st.median(vals):>8.1f} {good:>6} {weak:>6} "
                  f"{share:>5.0%} {verdict}")

    print("\n" + "═" * 84)
    if not (dead or never or always):
        print("  ✔ كلُّ عتبةٍ تفرّق، وكلُّ مؤشّرٍ تصل بياناتُه.")
        return 0
    if dead:
        print(f"\n  مؤشّراتٌ لا تصل بياناتُها ({len(dead)}) — أعمدةٌ ميّتة:")
        for x in dead:
            print(f"    · {x}")
    if never:
        print(f"\n  عتباتٌ لا يبلغها أحد ({len(never)}):")
        for x in never:
            print(f"    · {x}")
    if always:
        print(f"\n  عتباتٌ يبلغها الجميع ({len(always)}) — لا تفرّق:")
        for x in always:
            print(f"    · {x}")
    print("\n  قياسٌ فقط: لم تُغيَّر عتبةٌ ولا اتّجاه.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
