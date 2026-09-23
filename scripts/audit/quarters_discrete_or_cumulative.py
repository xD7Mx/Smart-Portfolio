#!/usr/bin/env python3
"""فتراتُ تداولَ الربعية: منفصلةٌ أم تراكميةٌ من أوّل السنة؟

    python3 scripts/audit/quarters_discrete_or_cumulative.py

قبل أن تُجمَع أربعةُ أرباعٍ في «أرباحِ اثني عشرَ شهراً» يجب أن يُعرَف
ماذا يحمل كلُّ صفّ. فإن كانت الصفوفُ **تراكمية** (‏3M · 6M · 9M · 12M
كما يُفصح كثيرٌ من المُصدِرين) فجمعُها يضاعف الربحَ مرّتين ونصفاً،
ويُنتج مضاعفَ ربحيةٍ كاذباً ثمّ سعراً عادلاً كاذباً — وهو أسوأُ من
الامتناع لأنه رقمٌ يبدو سليماً.

## كيف يُعرَف بلا سؤالِ أحد

يُقارَن **ربعُ الختام بالسنةِ نفسِها**:

  · إن كان `صافي ربح 2025-12-31 الربعيّ` ≈ `صافي ربح 2025-12-31
    السنويّ` فالصفوفُ **تراكمية** — فالربعُ الرابعُ يحمل السنةَ كلَّها.
  · وإن كان نحوَ رُبعها فالصفوفُ **منفصلة**.

ويُطبع لكلّ رمزٍ مجموعُ أربعةِ أرباعٍ مقابلَ السنويّ، فالنسبةُ تقول
الجواب: نحوُ ‎1.0 منفصلة، ونحوُ ‎2.5 تراكمية.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


def main() -> int:
    try:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        from app.services import tadawul_xbrl as X
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    # ══ الكونُ كلُّه لا عيّنة ══
    # أوّلُ تشغيلٍ ردّ **شاهداً واحداً**، وحكمٌ على الكون من واحدٍ هو
    # عينُ ما أُصلح في D402 (نجاحٌ على عيّنةٍ فارغة) وD406 (عيّنةٌ لا
    # تمثّل). والقراءةُ من مخزنٍ محليٍّ بلا نداءٍ خارجيّ، فلا عذرَ
    # للاختصار.
    probe = sorted(main_market(MARKET_UNIVERSE).keys())

    print(f"  {'رمز':6s} {'سنةُ الأساس':12s} {'سنويّ':>14s} "
          f"{'ربعُ الختام':>14s} {'نسبة':>7s}  الحكم")
    verdicts = {"تراكمية": 0, "منفصلة": 0, "غيرُ حاسم": 0}
    no_match = 0
    # وشاهدٌ ثانٍ مستقلٌّ: في الصفوف التراكمية يتصاعد المقدارُ داخل
    # السنة (‏Q1 < Q2 < Q3 < Q4) لأنّ كلَّ صفٍّ يضمّ ما قبله. فتُقاس
    # نسبةُ السنوات المتصاعدةِ تصاعداً تامّاً — وهي في المنفصلة نادرة.
    rising = {"متصاعدة": 0, "غيرُ متصاعدة": 0}
    for s in probe:
        try:
            ann = X.for_symbol(s, "annual") or []
            qtr = X.for_symbol(s, "quarterly") or []
        except Exception:                                         # noqa: BLE001
            continue
        _a = {str(r.get("as_of") or "")[:10]: r.get("net_income")
              for r in ann if r.get("as_of")}
        _q = {str(r.get("as_of") or "")[:10]: r.get("net_income")
              for r in qtr if r.get("as_of")}
        # سنةُ أساسٍ ينتهي ربعُها الرابعُ بنهاية السنة نفسِها
        base = None
        for d in sorted(_a, reverse=True):
            if d in _q and isinstance(_a[d], (int, float)) \
                    and isinstance(_q[d], (int, float)) and _a[d]:
                base = d
                break
        # الشاهدُ الثاني: تصاعدُ الأرباع داخل السنة الواحدة
        for _yr in {d[:4] for d in _q}:
            _in = sorted((d, _q[d]) for d in _q if d.startswith(_yr)
                         and isinstance(_q[d], (int, float)))
            if len(_in) >= 3:
                _v = [abs(v) for _, v in _in]
                rising["متصاعدة" if all(a < b for a, b in zip(_v, _v[1:]))
                       else "غيرُ متصاعدة"] += 1
        if not base:
            no_match += 1
            continue
        ratio = _q[base] / _a[base]
        v = ("تراكمية" if ratio > 0.75 else
             "منفصلة" if ratio < 0.55 else "غيرُ حاسم")
        verdicts[v] += 1
        print(f"  {s:6s} {base:12s} {_a[base]:>14,.0f} "
              f"{_q[base]:>14,.0f} {ratio:>7.2f}  {v}")

    print(f"\nالحصيلة (ربعُ الختام ÷ السنويّ): {verdicts}"
          f" · بلا سنةِ أساسٍ مشتركة: {no_match} من {len(probe)}")
    print(f"الشاهدُ الثاني (تصاعدُ الأرباع داخل السنة): {rising}")
    if verdicts["تراكمية"] and not verdicts["منفصلة"]:
        print("الحكم: **تراكمية** — فلا تُجمَع الأرباعُ أبداً؛ أرباحُ اثني"
              " عشرَ شهراً = ربعُ الختام، أو سنويٌّ + فرقُ تراكميَّين.")
    elif verdicts["منفصلة"] and not verdicts["تراكمية"]:
        print("الحكم: **منفصلة** — فجمعُ أربعةِ أرباعٍ صحيحٌ لاثني عشرَ شهراً.")
    else:
        print("الحكم: **مختلطٌ أو غيرُ حاسم** — فلا يُبنى جمعٌ قبل تمييزِ"
              " كلّ صفٍّ بنوعه. والامتناعُ هنا أصدقُ من رقمٍ مضاعَف.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
