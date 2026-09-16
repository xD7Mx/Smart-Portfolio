#!/usr/bin/env python3
"""بنودُ الملفّ الرسميّ التي لم نطابقها — تُقرأ بأسمائها (D335).

    docker exec sp_backend python /app/scripts/audit/xbrl_labels.py 2222
    docker exec sp_backend python /app/scripts/audit/xbrl_labels.py --sectors 2

قِيس على خادم المالك: صفوفُ أرامكو من «تداول — XBRL» فيها الإيرادُ وصافي
الربح والتدفّقُ التشغيليُّ وربحيةُ السهم — **ولا مصروفاتٌ رأسمالية ولا
حقوقُ ملكيةٍ ولا عددُ أسهم**. فمسارُ التدفّق الحرّ (أقوى مسارات السعر
العادل) غائبٌ صامتاً، فبقي مسارانِ بديلانِ يختلفان ‎3.5× فامتنع التقدير.
وخمسُ شركاتٍ أخرى تمتنع بنقص «ربحية سهمٍ مع…».

والخريطةُ عندنا تحمل أسماءً لهذه البنود — لكنها **لم تُطابَق**، أي أن
أسماءَها في الملفّ مختلفة. ولا تُخمَّن: تُطبع هنا **كلُّ بنودِ الملفّ
التي لم نطابقها ولها أرقام**، فتُقرأ أسماؤها كما وردت وتُضاف إلى
الخريطة بالحرف. وتُطبع كذلك البنودُ المطابَقةُ لكلّ شركةٍ — فيُعرف
الناقصُ من الموجود.

══ ومسحٌ شاملٌ لكلّ القطاعات ══ (بأمر المالك: «حتى نكون شاملين»)
`--sectors N` يأخذ من **كلّ قطاعٍ** في دليل السوق ‎N شركةً (اثنتان
افتراضاً) ويُخرج لكلّ قطاع: ما نقص من البنود المطلوبة وفي كم شركة، ثمّ
أسماءَ بنودِ الملفّ غيرِ المطابَقة المتكرّرةَ في ذلك القطاع بمعانيها
(تدفّقٌ · دَينٌ · أسهمٌ/وحدات · تأمينٌ · صافي أصول). فتُقرأ صناعةُ كلّ
قطاعٍ بلغتها: التأمينُ أقساطٌ وتعويضاتٌ لا إيرادٌ وتكلفة، والصناديقُ
وحداتٌ وصافي أصولٍ لا مضاعفاتُ شركة.
"""
from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SECT_N = 2
if "--sectors" in sys.argv:
    i = sys.argv.index("--sectors")
    try:
        SECT_N = int(sys.argv[i + 1])
    except (IndexError, ValueError):
        SECT_N = 2
SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()]
SWEEP = "--sectors" in sys.argv
WANT = ("capex", "equity", "shares_outstanding", "pretax_income",
        "borrowings_current", "borrowings_noncurrent", "total_assets",
        "total_liabilities", "ending_cash", "interest_expense",
        "operating_cash_flow", "revenue", "net_income", "eps")

# معانٍ تُبحَث في أسماء البنود غير المطابَقة — لا مواضعُ ثابتة
MEANING = {
    "تدفّق/رأسماليّ": r"addition|purchase|payments? (?:for|of)|"
                      r"capital expenditure|acquisi.*(propert|asset)",
    "دَين/قروض": r"borrow|loan|sukuk|debt securit|financ(e|ing) lease|murabaha",
    "أسهم/وحدات": r"number of (?:shares|units)|units? in issue|"
                  r"weighted average number|shares outstanding",
    "تأمين": r"insurance (?:revenue|service)|premium|claims?|reinsur|"
             r"combined ratio|loss ratio",
    "صافي أصول": r"net asset value|nav per|net assets attributable",
    "حقوق ملكية": r"^total equity|equity attributable",
    "تكلفةُ تمويل": r"financ(?:e|ial) (?:cost|charge|expense)|interest expense|"
                    r"interest on (?:lease|loan|borrow)|bank charges",
    "قبل الزكاة": r"before zakat|before (?:income )?tax|profit \(loss\) before",
}


async def _unmatched(X, sym: str):
    """بنودُ أحدثِ ملفٍّ رسميٍّ غيرُ المطابَقة — (الاسم، القيمة)."""
    from app.services.tadawul_http import fetch
    files = await X.filings_for(f"{sym}.SR")
    if not files:
        return None, "لا ملفّاتٍ رسمية"
    url = (files[0] or {}).get("url") or ""
    if url.startswith("/"):
        url = X.ORIGIN + url
    st, html = await fetch(url)
    if st != 200 or not html:
        return None, f"HTTP {st}"
    known = {n for names in X.LABELS.values() for n in names}
    out = []
    for tr in X._TR.findall(html):
        cells = [X._clean(c) for c in X._TD.findall(tr)]
        if len(cells) < 2 or not cells[0]:
            continue
        n = X._norm(cells[0])
        if (n in known or n in X._META.values() or len(n) < 4
                or "[text block]" in n or len(cells[0]) > 160):
            continue                                     # D373: كتلةُ نصّ
        nums = [c for c in cells[1:]
                if len(c) <= 40 and X._num(c) is not None]
        if nums:
            out.append((n, nums[0][:40]))
    return out, None


async def sweep() -> int:
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.services import tadawul_xbrl as X

    by_sec: dict[str, list[str]] = {}
    for s, m in U.items():
        sec = str((m or {}).get("sector") or "—")
        by_sec.setdefault(sec, []).append(str(s))
    print(f"═ قطاعاتٌ: {len(by_sec)} · من كلٍّ {SECT_N} شركة ═")

    for sec in sorted(by_sec):
        picks = sorted(by_sec[sec])[:SECT_N]
        print("\n═════ " + sec + " — " + " · ".join(picks) + " ═════")
        miss_cnt: Counter = Counter()
        names: dict[str, Counter] = {k: Counter() for k in MEANING}
        seen = 0
        for sym in picks:
            rows = X.for_symbol(sym, "annual")
            if rows:
                seen += 1
                for k in WANT:
                    if all(r.get(k) is None for r in rows):
                        miss_cnt[k] += 1
            else:
                miss_cnt["لا صفوفَ محفوظة"] += 1
            un, err = await _unmatched(X, sym)
            if un is None:
                print(f"  · {sym}: تعذّر — {err}")
                continue
            for n, v in un:
                for lbl, pat in MEANING.items():
                    if re.search(pat, n, re.I):
                        names[lbl][f"{n}"] += 1
        print(f"  محفوظٌ لـ{seen} من {len(picks)} · الناقصُ: "
              + (" · ".join(f"{k}×{c}" for k, c in miss_cnt.most_common())
                 or "لا شيء"))
        for lbl, cnt in names.items():
            if cnt:
                top = " · ".join(f"«{n}»" for n, _ in cnt.most_common(4))
                print(f"    [{lbl}] {top}")
    print("\nالحكم: لكلّ قطاعٍ لغتُه. ما ظهر اسمُه أعلاه يُضاف إلى"
          " `LABELS` بالحرف، وما لا يُنشَر يبقى معلَناً بغيابه — ولا"
          " يُلبَّس رقمٌ مصنوعٌ ثوبَ المنشور.")
    return 0


async def main() -> int:
    from app.services import tadawul_xbrl as X

    miss_names: Counter = Counter()
    for sym in SYMS:
        print(f"\n═════ {sym} ═════")
        rows = X.for_symbol(sym, "annual")
        if rows:
            have = sorted({k for r in rows for k, v in r.items()
                           if v is not None})
            print(f"  المحفوظُ عندنا: {len(rows)} فترة · حقولٌ: {' · '.join(have)}")
            print("  الناقصُ من المطلوب: "
                  + (" · ".join(k for k in WANT
                                if all(r.get(k) is None for r in rows)) or "لا شيء"))
        else:
            print("  لا صفوفَ محفوظةً لهذه الورقة.")

        # ── والملفُّ الرسميُّ يُقرأ من جديد، وتُطبع بنودُه غيرُ المطابَقة ──
        try:
            files = await X.filings_for(f"{sym}.SR")
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّر جلبُ قائمة الملفّات: {type(e).__name__}: {e}")
            continue
        print(f"  ملفّاتٌ رسميةٌ متاحة: {len(files)}")
        if not files:
            continue
        from app.services.tadawul_http import fetch
        url = (files[0] or {}).get("url") or ""
        # الروابطُ في القائمة نسبيةٌ أحياناً — تُكمَّل بأصل الموقع كما
        # تفعل الوحدةُ نفسُها، لا بتخمينٍ في الأداة.
        if url.startswith("/"):
            url = X.ORIGIN + url
        try:
            st, html = await fetch(url)
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّر تحميلُ الملفّ: {type(e).__name__}: {e}")
            continue
        print(f"  الملفُّ الأوّل: HTTP {st} · {len(html or '')} حرفاً · {url[-60:]}")
        if not html:
            continue

        # كلُّ صفٍّ عنوانُه نصٌّ وقيمتُه رقمٌ ولم تُطابقه خريطتُنا
        known = {n for names in X.LABELS.values() for n in names}
        unmatched: list[tuple[str, str]] = []
        for tr in X._TR.findall(html):
            cells = [X._clean(c) for c in X._TD.findall(tr)]
            if len(cells) < 2 or not cells[0]:
                continue
            n = X._norm(cells[0])
            if n in known or n in X._META.values():
                continue
            # ══ وكتلةُ النصّ ليست قيمةَ بندٍ ══ (D373)
            # قِيس في مخرَج المالك: طُبعت **شفرةُ جافاسكربت** (‏boomerang
            # الخاصّةُ بالقياس) كأنها قيمةُ «مسؤوليات الإدارة» — لأن
            # صفوفَ `[text block]` تحمل صفحةً كاملةً، و`_num` يجد فيها
            # رقماً فيمرّ. فأداتي لوّثت مخرَجَها بنفسها، وأُغرقت الأسماءُ
            # المفيدةُ تحت آلافِ حرفٍ لا تُقرأ. فتُقصَّ الخلايا الطويلةُ
            # ويُستثنى صفُّ الكتلة النصّية صراحةً.
            if "[text block]" in n or len(cells[0]) > 160:
                continue
            nums = [c for c in cells[1:]
                    if len(c) <= 40 and X._num(c) is not None]
            if not nums:
                continue
            unmatched.append((n, nums[0][:40]))
            miss_names[n] += 1
        print(f"  بنودٌ ذاتُ أرقامٍ لم تُطابَق: {len(unmatched)}")
        # ما يُشبه المطلوبَ يُبرَز أوّلاً — بمعناه لا بموضعه
        # ══ ويُفصَل التدفّقُ عن الميزانية في العرض ══ (D335)
        # أوّلُ تشغيلٍ أغرق المخرَجَ ببنود الميزانية (أصولٌ والتزامات) فلم
        # يبلغ **مصروفَ أرامكو الرأسماليّ** وهو المطلوبُ الأوّل. فبنودُ
        # التدفّق تُطبع في قائمةٍ خاصّةٍ بها.
        flow = re.compile(r"addition|purchase|payments? (?:for|of)|acquisi|"
                          r"capital expenditure|proceeds|dividends? paid|"
                          r"cash flows?|net cash", re.I)
        fl = [u for u in unmatched if flow.search(u[0])]
        print(f"  ومن بنود التدفّق غيرِ المطابَقة: {len(fl)}")
        for n, v in fl[:22]:
            print(f"      ⤵ «{n}» = {v}")
        # ══ وتكلفةُ التمويل تُبرَز صريحاً ══ (D343)
        # قِيس على خادم المالك: `interest_expense` يغيب في **34 ورقةً من
        # 90**، ويسقط معه `ebit` لأنه يُشتقّ منه — فحقلانِ يحجبهما اسمٌ
        # واحد. وخريطتُنا تحمل له اسماً واحداً (`finance costs`) فقط.
        # وكان مُرشَّحُ العرض لا يذكر التمويلَ فلا تظهر صياغاتُه أصلاً.
        hot = re.compile(r"propert|plant|equipment|capital expenditure|invest|"
                         r"equity|share|capital|borrow|loan|debt|zakat|tax|"
                         r"cash and cash|asset|liabilit|financ|interest|"
                         r"charges|before zakat|profit \(loss\) before", re.I)
        pick = [u for u in unmatched if hot.search(u[0])]
        for n, v in (pick or unmatched)[:28]:
            print(f"      «{n}» = {v}")

    if len(SYMS) > 1 and miss_names:
        print("\n═ البنودُ غيرُ المطابَقة الأكثرُ تكراراً بين الشركات ═")
        for n, c in miss_names.most_common(25):
            print(f"  {c:>3}  «{n}»")

    print("\nالحكم: تُنسَخ الأسماءُ أعلاه **بالحرف** إلى `LABELS` في"
          " `tadawul_xbrl.py` لكلّ بندٍ مطلوب — فيعمل مسارُ التدفّق الحرّ"
          " وتسقط جملةُ «لا تكفي البيانات» حيث البياناتُ موجودةٌ فعلاً."
          " وما لا يوجد في الملفّ يبقى معلَناً بغيابه.")
    return 0


raise SystemExit(asyncio.run(sweep() if SWEEP else main()))
