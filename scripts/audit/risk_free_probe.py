#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D249 · D250 — مسبارُ المعدَّل الخالي من المخاطر، على الخادم حيث الشبكة.
#
# يقرأ سوقَ الصكوك من «تداول» (بعبور الحماية) ويطبع **ما فُهم بنصّه**:
# عددَ الأدوات، والمرشَّحاتِ السياديةَ الثابتةَ بالريال بأجلِها وعائدِها
# ومصدرِ العائد، والمختارَ ولماذا.
#
#   docker exec sp_backend python /app/scripts/audit/risk_free_probe.py
#   docker exec sp_backend python /app/scripts/audit/risk_free_probe.py --apply
#
# بلا `--apply` لا يُكتب شيء. ولا يُعدَّل ملفُّ المعايير — القراءةُ تُحفَظ
# في مخزن الحالة بتاريخها وعمرِها الأقصى.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

APPLY = "--apply" in sys.argv


async def main() -> int:
    from app.services import risk_free as rf

    sanity = rf._sanity_from_config()
    print(f"نطاقُ المعقولية: {sanity} · الأجلُ المستهدَف {rf.TARGET_YEARS} "
          f"سنة ضمن {rf.TENOR_BAND}\n")

    rows, why = await rf.fetch_instruments()
    if why:
        print(f"✖ تعذّر: {why}")
        print("المحرّكُ يبقى ممتنعاً — وهذا صوابٌ لا عطب.")
        return 1
    print(f"أدواتُ سوق الصكوك: {len(rows)}")

    cands = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        one, _ = rf.choose([r])
        if one:
            cands.append(one)
    cands.sort(key=lambda c: c["tenor_years"])
    print(f"المرشَّحاتُ السياديةُ الثابتةُ بالريال داخلَ النطاق: {len(cands)}")
    for c in cands:
        print(f"   · {c['symbol']:<6} {c['maturity']} · أجل {c['tenor_years']:>5} سنة"
              f" · عائد {c['value'] * 100:.3f}٪ ({c['basis']}) · {c['name'][:40]}")

    best, why = rf.choose(rows)
    if best is None:
        print(f"\n✖ امتناع: {why}")
        return 1
    print(f"\n✔ المختار: {best['symbol']} · {best['name']}"
          f" · أجل {best['tenor_years']} سنة · استحقاق {best['maturity']}"
          f" · عائد {best['value'] * 100:.3f}٪ ({best['basis']})")

    if not APPLY:
        print("\nلم يُكتب شيء. للاعتماد: أعد التشغيل بـ‎ --apply")
        return 0

    rec = await rf.refresh()
    if rec.get("value") is None:
        print(f"✖ الكتابةُ تعذّرت: {rec.get('error')}")
        return 1
    print(f"✔ حُفظ: {rec}")
    print(f"✔ يُقرأ من المخزن: {(rf.reading() or {}).get('value')}")
    from app.services.fair_value_engine.params import load_params
    p = load_params(allow_unverified=True, allow_stale=True)
    print(f"✔ يراه المحرّك: rf={p.risk_free}")
    print(f"✔ الأثر: {p.provenance()}")
    return 0


raise SystemExit(asyncio.run(main()))
