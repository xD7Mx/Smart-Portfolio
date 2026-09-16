#!/usr/bin/env python3
"""بنودُ الملفّ الرسميّ التي لم نطابقها — تُقرأ بأسمائها (D335).

    docker exec sp_backend python /app/scripts/audit/xbrl_labels.py 2222
    docker exec sp_backend python /app/scripts/audit/xbrl_labels.py 2222 2030 2060

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
"""
from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()] or ["2222"]
WANT = ("capex", "equity", "shares_outstanding", "pretax_income",
        "borrowings_current", "borrowings_noncurrent", "total_assets",
        "total_liabilities", "ending_cash", "interest_expense")


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
            nums = [c for c in cells[1:] if X._num(c) is not None]
            if not nums:
                continue
            unmatched.append((n, nums[0]))
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
        hot = re.compile(r"propert|plant|equipment|capital expenditure|invest|"
                         r"equity|share|capital|borrow|loan|debt|zakat|tax|"
                         r"cash and cash|asset|liabilit", re.I)
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


raise SystemExit(asyncio.run(main()))
