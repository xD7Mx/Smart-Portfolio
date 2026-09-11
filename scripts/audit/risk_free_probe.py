#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D249 — مسبارُ المعدَّل الخالي من المخاطر بالريال، على الخادم حيث الشبكة.
#
# محرّكُ القيمة العادلة يرفض العملَ بمعدَّلٍ مفترَض، و`market_params.json`
# يحمل القيمةَ فارغةً عمداً. فهذا المسبار يجلب سوقَ الصكوك من «تداول»
# ويطبع **ما فُهم بنصّه**: الترويسة، وعددَ الصفوف، والمرشَّحاتِ السيادية
# بأجلِها وعائدِها، والمختارَ ولماذا.
#
#   docker exec sp_backend python /app/scripts/audit/risk_free_probe.py
#   docker exec sp_backend python /app/scripts/audit/risk_free_probe.py --apply
#
# بلا `--apply` لا يُكتب شيء: البنيةُ تُرى أوّلاً ثمّ يُعتمد الرقم.
# ولا يُعدّل ملفَّ المعايير — القراءةُ تُحفَظ في مخزن الحالة بتاريخها.
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
    from app.services.tadawul_announcements import _raw_fetch

    sanity = rf._sanity_from_config()
    print(f"نطاقُ المعقولية من ملفّ المعايير: {sanity}")
    print(f"الأجلُ المستهدَف: {rf.TARGET_YEARS} سنة · النطاق {rf.TENOR_BAND}\n")

    ok = False
    for url in rf.SOURCES:
        print(f"── {url}")
        try:
            status, body = await _raw_fetch(url)
        except Exception as e:                                    # noqa: BLE001
            print(f"   ✖ {type(e).__name__}: {e}\n")
            continue
        print(f"   ‏HTTP {status} · {len(body)} حرفاً")
        if status != 200:
            print()
            continue
        rows, why = rf.parse_instruments(body)
        if why:
            print(f"   ✖ {why}\n")
            continue
        print(f"   فُهم {len(rows)} صفّاً · الحقولُ المرصودة: "
              f"{sorted({k for r in rows for k in r})}")
        for r in rows[:5]:
            print(f"     · {r}")
        best, why = rf.choose(rows, sanity=sanity)
        if best is None:
            print(f"   ✖ امتناع: {why}\n")
            continue
        print(f"   ✔ المختار: {best['name']} · أجل {best['tenor_years']} سنة"
              f" · استحقاق {best['maturity']}"
              f" · عائد {best['value'] * 100:.3f}٪ ({best['basis']})"
              f" · مرشَّحات {best['peers']}\n")
        ok = True
        break

    if not ok:
        print("لم يُقرأ المعدَّل — والمحرّكُ يبقى ممتنعاً، وهذا صوابٌ لا عطب.")
        return 1

    if not APPLY:
        print("لم يُكتب شيء. للاعتماد: أعد التشغيل بـ‎ --apply")
        return 0

    rec = await rf.refresh()
    if rec.get("value") is None:
        print(f"✖ الكتابةُ تعذّرت: {rec.get('error')}")
        return 1
    print(f"✔ حُفظ: {rec}")
    back = rf.reading()
    print(f"✔ يُقرأ من المخزن: {back and back.get('value')}")
    from app.services.fair_value_engine.params import load_params
    p = load_params(allow_unverified=True, allow_stale=True)
    print(f"✔ يراه المحرّك: rf={p.risk_free} · الأثر {p.provenance()}")
    return 0


raise SystemExit(asyncio.run(main()))
