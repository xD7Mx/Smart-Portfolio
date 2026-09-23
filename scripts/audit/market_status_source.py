#!/usr/bin/env python3
"""حالةُ السوق: أنعتمد ساعةَ الحائط أم قولَ تداول؟ (‏D413؟)

    python3 scripts/audit/market_status_source.py

قال المالك: «اليومَ كان عطلةً للسوق ولم يكتشف التطبيقُ ذلك». وقراءةُ
الشفرة تُثبت قولَه: `GET /settings/clock` يحسب الحالةَ من **ساعة الحائط
وحدَها** (`market_phase(dow, minutes)`) — الأحدُ إلى الخميس «مفتوح» في
أوقاته، والجمعةُ والسبتُ «مغلق». فالأعيادُ والعطلُ الرسميةُ لا وجودَ
لها في الحساب، فيقول التطبيقُ «مفتوح» ولا سوقَ يعمل.

وفي المقابل نحن **نلتقط قولَ تداولَ نفسِه** ولا نستعمله:
`tadawul_market.index()` تخزّن `market_status_code` من `marketStatusCode`
في حمولة المؤشّر — ولا يقرؤها أحدٌ في الخادم ولا في الواجهة.

فهذا الكاشفُ يقيس قبل أيّ إصلاح:
  ١ · هل يصل الحقلُ فعلاً ولا يكون فارغاً؟
  ٢ · ما **قيمُه** بالضبط (المفردات لا تُخمَّن)؟
  ٣ · وهل يخالف حكمَ الساعة اليوم؟ فإن خالف، فالفرقُ هو العطلةُ بعينها.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from datetime import datetime

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


async def main() -> int:
    try:
        from app.services import tadawul_market as TM
        from app.services.market_phase import market_phase
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    try:
        await TM.refresh()
    except Exception as e:                                        # noqa: BLE001
        print(f"⚠ تعذّر تحديثُ اللقطة: {type(e).__name__}: {e}")

    idx = None
    for _name in ("index", "tasi_index", "index_row"):
        _f = getattr(TM, _name, None)
        if _f is None:
            continue
        try:
            idx = await _f() if asyncio.iscoroutinefunction(_f) else _f()
        except Exception as e:                                    # noqa: BLE001
            print(f"⚠ {_name}: {type(e).__name__}: {e}")
        if isinstance(idx, dict):
            break

    if not isinstance(idx, dict):
        print("⚠ لا حمولةَ مؤشّرٍ في هذه البيئة — لم يُقَس")
        return 0

    code = idx.get("market_status_code")
    print("══ ما تقوله تداول ══")
    print(f"  market_status_code = {code!r}")
    print(f"  as_of              = {idx.get('as_of')!r}")
    print(f"  tasi               = {idx.get('value')!r} "
          f"· تغيّر {idx.get('change_pct')!r}")
    print(f"  افتتاح/أعلى/أدنى    = {idx.get('open')!r} / "
          f"{idx.get('high')!r} / {idx.get('low')!r}")

    # وكلُّ مفتاحٍ في الحمولة يُطبع مرّةً ليُعرف ما نملك فعلاً
    print(f"  مفاتيحُ الحمولة     = {sorted(idx)}")

    local = datetime.now()
    dow0 = (local.weekday() + 1) % 7
    mins = local.hour * 60 + local.minute
    clock = market_phase(dow0, mins)
    print("\n══ ما تقوله ساعتُنا ══")
    print(f"  {local:%Y-%m-%d %H:%M} (مكة) · اليومُ رقم {dow0} → {clock}")

    print("\n══ الحكم ══")
    if code in (None, ""):
        print("  ✘ الحقلُ لا يصل — فلا يصلح مصدراً وحدَه، ويجب أن يُقاس"
              " سببُ غيابه قبل الاعتماد عليه.")
    else:
        print(f"  ✔ الحقلُ يصل بقيمةٍ {code!r} — يصلح مصدراً، وتُبنى"
              " عليه خريطةُ حالاتٍ مُعلَنة.")
        print("  وإن خالف حكمَ الساعة اليومَ فالفرقُ هو **العطلةُ** التي"
              " لا تعرفها الساعة.")
    # وشاهدٌ مستقلٌّ لا يعتمد على مفردات: في العطلة لا يُفتَح المؤشّر.
    _o = idx.get("open")
    if _o in (None, 0):
        print("  وشاهدٌ مستقلٌّ: لا سعرَ افتتاحٍ للمؤشّر اليوم — "
              "علامةُ يومٍ بلا تداول.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
