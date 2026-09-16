#!/usr/bin/env python3
"""جردُ ما نملكه — السوقُ الرئيسيّ أوّلاً، و«نمو» حاشيةٌ (D369).

    docker exec sp_backend python /app/scripts/audit/reassess.py

## لماذا يُعاد التقييمُ قبل أيّ تعديلٍ آخر

بُني مصدرٌ رسميٌّ حيٌّ يتجدّد من السوق نفسِه: لقطةُ «تداول» (رئيسيّ +
نمو) وملفّاتُ XBRL و«أرقام» طبقةً مستقلّة. ثمّ صُرفت جهودٌ على أبوابٍ
تخصّ **ثُلثَ ‎82 ورقةً أكثرُها «نمو»** — أي على الهامش لا على المتن،
وهو فخُّ التعديل اللانهائيّ. فالمالكُ قضى: **الرئيسيُّ أولويةٌ، ونمو
مكمِّلٌ غيرُ مهمّ.** ولا تُكتب خارطةُ طريقٍ على تقدير: تُكتب على جرد.

## وهذا الجردُ بلا شبكةٍ عن قصد

يقرأ **المخزَنَ الدائم واللقطةَ** فقط — فيُقاس ما نملكه فعلاً لا ما
يستطيع الجلبُ إحضاره. وكلُّ سطرٍ فيه يفصل الرئيسيَّ عن «نمو» (البادئةُ
‎9 نمو، وتُطبع القسمةُ لتُراجَع لا لتُسلَّم).

يُطبع: تغطيةُ كلّ بندٍ · أعمارُ أحدثِ القوائم · من لا قوائمَ له ·
وما أُعلن «غيرَ ذي معنى» — فهذه أربعةُ أرقامٍ تكفي لترتيب الأولويات.
"""
from __future__ import annotations

import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

_D = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
TODAY = None


def _age_days(ds: str) -> int | None:
    from datetime import date
    m = _D.search(ds or "")
    if not m:
        return None
    try:
        return (TODAY - date(*(int(g) for g in m.groups()))).days
    except ValueError:
        return None


def main() -> int:
    global TODAY
    from datetime import date
    TODAY = date.today()

    from app.services import statement_merge as SM
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X

    rows, live, at = tm.usable_rows()
    if not rows:
        print("اللقطةُ فارغة — لا جردَ يُقاس. (وهذا عطبٌ لا نتيجة.)")
        return 1
    main_m = sorted(s for s in rows if not s.startswith("9"))
    nomu = sorted(s for s in rows if s.startswith("9"))
    print(f"═ جردُ ما نملك ═ اللقطةُ {len(rows)} · حيّةٌ={live} · {at}")
    print(f"  الرئيسيّ: {len(main_m)} · نمو: {len(nomu)}"
          f"  (القسمةُ بالبادئة ‎9 — تُراجَع)")

    def survey(syms: list[str], title: str) -> None:
        print(f"\n╔══ {title} — {len(syms)} ورقة ══")
        have_rows, no_rows = [], []
        cov: Counter = Counter()
        nm_cnt: Counter = Counter()
        ages: list[int] = []
        arch: Counter = Counter()
        for s in syms:
            a = X.for_symbol(s, "annual") or []
            q = X.for_symbol(s, "quarterly") or []
            per = list(a) + list(q)
            arch[SM.archetype_of(s) or "عادية"] += 1
            for k in SM.not_meaningful(s):
                nm_cnt[k] += 1
            if not per:
                no_rows.append(s)
                continue
            have_rows.append(s)
            for k in SM.NEEDED:
                if any(p.get(k) is not None for p in per):
                    cov[k] += 1
            ds = [d for d in (str(p.get("as_of") or p.get("year") or "")
                              for p in per) if _D.search(d)]
            if ds:
                g = _age_days(max(ds))
                if g is not None:
                    ages.append(g)
        n = len(syms) or 1
        print(f"  لها قوائمُ محفوظة: {len(have_rows)} ({100*len(have_rows)//n}%)"
              f" · بلا قوائم: {len(no_rows)}")
        print("  ── تغطيةُ البنود (من أصل الكلّ) ──")
        for k in SM.NEEDED:
            c = cov[k]
            bar = "█" * (20 * c // n)
            print(f"   {k:<24} {c:>4}/{n} {100*c//n:>3}% {bar}")
        if ages:
            ages.sort()
            b = Counter()
            for g in ages:
                b["≤120 يوماً" if g <= 120 else
                  "121–200" if g <= 200 else
                  "201–400" if g <= 400 else "أقدمُ من 400"] += 1
            print("  ── عمرُ أحدثِ قائمةٍ محفوظة ──")
            for k in ("≤120 يوماً", "121–200", "201–400", "أقدمُ من 400"):
                if b[k]:
                    print(f"   {k:<14} {b[k]:>4}"
                          + ("   ← يرفضها MAX_AGE_DAYS=200"
                             if k in ("201–400", "أقدمُ من 400") else ""))
            print(f"   الوسيطُ: {ages[len(ages)//2]} يوماً ·"
                  f" الأحدثُ: {ages[0]} · الأقدمُ: {ages[-1]}")
        else:
            print("  ── لا تواريخَ تُقرأ في المحفوظ (وهذا يُفحَص) ──")
        print("  ── الأصنافُ ──  "
              + " · ".join(f"{k}×{v}" for k, v in arch.most_common()))
        if nm_cnt:
            print("  ── أُعلن «غيرَ ذي معنى» (لا يُطلَب ولا يُحرَق له نداء) ──")
            print("   " + " · ".join(f"{k}×{v}"
                                     for k, v in nm_cnt.most_common(6)))
        if no_rows:
            print(f"  ── بلا قوائمَ ({len(no_rows)}) ──")
            print("   " + " · ".join(no_rows[:40])
                  + (" …" if len(no_rows) > 40 else ""))

    survey(main_m, "السوقُ الرئيسيّ — الأولوية")
    survey(nomu, "نمو — مكمِّلٌ، لا يوقف تسليماً")

    print("\nالحكم: الأولويةُ تُقاس بنسبةِ الرئيسيّ لا بعددِ الأبواب"
          " المفتوحة. وكلُّ بندٍ تغطيتُه في الرئيسيّ دون ‎90% هو عملٌ"
          " باقٍ، وكلُّ ما فوقه تمامٌ يُصان بحارسٍ لا يُعاد بناؤه.")
    return 0


raise SystemExit(main())
