#!/usr/bin/env python3
"""مَن الشريكُ المكمِّل للريتات والصناديق؟ — يُقاس ولا يُسمّى بالظنّ (D341).

    docker exec sp_backend python /app/scripts/audit/fund_layers.py
    docker exec sp_backend python /app/scripts/audit/fund_layers.py --n 6

سأل المالك: «مَن الشريكُ المثاليُّ لدمجه مع تداول بخصوص القطاعات الناقصة
— الريتات والصناديق؟». والجوابُ لا يُقال برأيٍ: تُفتَح كلُّ طبقةٍ
مرشَّحةٍ على **هذه الأوراق بأعيانها** ويُطبع ما تملكه فعلاً، ثمّ يُحكَم.

وفرقٌ جوهريٌّ يُقاس هنا ولا يُخلَط:

  · **الصناديقُ العقاريةُ المتداولة (ريت)** تنشر قوائمَ مالية: إيرادُ
    إيجارٍ وصافي ربحٍ وحقوقٌ ووحداتٌ وتوزيعات. فنقصُها نقصُ **بابٍ أو
    خريطة** — يُعالَج بشريكٍ أو باسمٍ يُنقَل بالحرف.
  · **صناديقُ المؤشرات المتداولة (‏ETF)** لا قوائمَ لها **بطبيعتها**: لا
    إيرادَ ولا حقوقَ ولا ربحيةَ سهم. فطلبُ «سعرٍ عادلٍ» منها بمضاعفاتٍ
    أو تدفّقٍ حرٍّ خطأُ تصنيفٍ لا نقصُ بيانات — وقيمتُها صافي أصولها،
    وهو سعرُها تقريباً. فالصوابُ أن تُعرَّف ورقةً مؤشِّرةً لا شركةً.

ولكلّ ورقةٍ يُطبع: ما في لقطة «تداول» · عددُ ملفّات XBRL وما طابَقته
منها · أسماءُ نداءات صفحتها (‏`=NJ…=/`) فيُعرف هل لها بابٌ خاصٌّ
بالصناديق · وحالُ صفحة «أرقام» العامّة وهل أرقامُها في النصّ أصلاً.

ولا يُتجاوَز اشتراكٌ مدفوع: يُقاس **المتاحُ العامُّ** وحدَه، وما كان
خلفَ اشتراكٍ يُقال إنه ليس عندنا — وقد رفضتُ تجاوزَه مرّتين.
"""
from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

N = 4
if "--n" in sys.argv:
    i = sys.argv.index("--n")
    try:
        N = int(sys.argv[i + 1])
    except (IndexError, ValueError):
        N = 4

SECTORS = ("الصناديق العقارية المتداولة", "صناديق المؤشرات المتداولة")

# معانٍ تُبحَث في بنود الملفّ غير المطابَقة — بلغةِ الصناديق لا الشركات
MEANING = {
    "إيرادُ إيجار": r"rental income|lease income|revenue from (?:lease|rent)|"
                    r"income from real estate|operating income from",
    "وحداتٌ مُصدَرة": r"number of units|units? in issue|units? outstanding|"
                      r"weighted average number of units",
    "صافي أصول": r"net asset value|nav per|net assets attributable|"
                 r"total net assets",
    "توزيعات": r"distribution|dividends? paid|distributions? to unitholders",
    "تقييمُ عقار": r"fair value of investment propert|revaluation|"
                   r"investment properties",
}


async def _page_services(X, sym: str) -> tuple[list[str], str | None]:
    """أسماءُ نداءات صفحة الورقة — فيُعرف هل ثمّ بابٌ خاصٌّ بالصناديق."""
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    url = (row_for(f"{sym}.SR") or {}).get("company_url")
    if not url:
        return [], "لا رابطَ للورقة في اللقطة"
    st, page = await fetch(X.ORIGIN + url if url.startswith("/") else url)
    if st != 200 or not page:
        return [], f"HTTP {st}"
    return sorted({m.group(1) for m in X._NJ.finditer(page)}), None


async def _argaam(sym: str) -> str:
    """حالُ صفحة «أرقام» العامّة — أرقامٌ في النصّ أم جافاسكربت؟"""
    from app.services.tadawul_http import fetch
    for url in (f"https://www.argaam.com/ar/tadawul/tasi/{sym}",
                f"https://www.argaam.com/ar/company/companyoverview/marketid/3/companyid/{sym}"):
        try:
            st, html = await fetch(url)
        except Exception as e:                                    # noqa: BLE001
            return f"تعذّر: {type(e).__name__}"
        if st != 200 or not html:
            continue
        txt = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
        txt = re.sub(r"<[^>]+>", " ", txt)
        nums = re.findall(r"\d[\d,]{4,}(?:\.\d+)?", txt)
        return (f"HTTP 200 · {len(html)} حرفاً · أرقامٌ في النصّ: {len(nums)}"
                + (f" (مثالٌ {nums[0]})" if nums else " — أي أنها تُرسَم بجافاسكربت"))
    return "لا صفحةً عامّةً تُقرأ"


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X

    rows, live, at = tm.usable_rows()
    print(f"═ لقطةُ «تداول»: {len(rows)} رمزاً · حيّةٌ={live} · {at} ═")

    for sec in SECTORS:
        syms = sorted(s for s, m in U.items()
                      if str((m or {}).get("sector") or "") == sec)
        picks = [str(s).replace(".SR", "") for s in syms[:N]]
        print(f"\n═════ {sec} — {len(syms)} ورقةً · قِيس منها "
              f"{len(picks)}: {' · '.join(picks)} ═════")
        names: dict[str, Counter] = {k: Counter() for k in MEANING}

        for sym in picks:
            print(f"\n── {sym} ──")
            snap = rows.get(sym) or {}
            has = [k for k in ("price", "change_pct", "market_cap", "pe_ratio",
                               "price_to_book", "volume", "week52_high")
                   if snap.get(k) is not None]
            print(f"  لقطةُ تداول: {', '.join(has) or 'لا شيء'}")

            saved = X.for_symbol(sym, "annual")
            print(f"  صفوفٌ محفوظةٌ عندنا: {len(saved)}")
            try:
                files = await X.filings_for(f"{sym}.SR")
            except Exception as e:                                # noqa: BLE001
                files = []
                print(f"  تعذّر جلبُ الملفّات: {type(e).__name__}: {e}")
            print(f"  ملفّاتُ XBRL الرسمية: {len(files)}")

            if files:
                from app.services.tadawul_http import fetch
                url = (files[0] or {}).get("url") or ""
                if url.startswith("/"):
                    url = X.ORIGIN + url
                st, html = await fetch(url)
                got = X.parse(html or "")
                ps = got.get("periods") or []
                if ps:
                    fields = sorted({k for p in ps for k, v in p.items()
                                     if v is not None})
                    print(f"    مُطابَقٌ: {len(ps)} فترة · {' · '.join(fields)}")
                else:
                    print(f"    HTTP {st} · لا فتراتٍ تُقرأ من الملفّ")
                # وبنودُ الملفّ غيرُ المطابَقة بلغةِ الصناديق
                known = {n for v in X.LABELS.values() for n in v}
                for tr in X._TR.findall(html or ""):
                    cells = [X._clean(c) for c in X._TD.findall(tr)]
                    if len(cells) < 2 or not cells[0]:
                        continue
                    n = X._norm(cells[0])
                    if n in known or n in X._META.values() or len(n) < 4:
                        continue
                    if not any(X._num(c) is not None for c in cells[1:]):
                        continue
                    for lbl, pat in MEANING.items():
                        if re.search(pat, n, re.I):
                            names[lbl][n] += 1

            svc, err = await _page_services(X, sym)
            print(f"  نداءاتُ صفحتها: {err or (', '.join(svc[:12]) or 'لا شيء')}")
            print(f"  «أرقام» العامّة: {await _argaam(sym)}")

        print(f"\n  ══ بنودُ الملفّ بلغةِ {sec} ══")
        any_named = False
        for lbl, cnt in names.items():
            if cnt:
                any_named = True
                print(f"    [{lbl}] "
                      + " · ".join(f"«{n}»" for n, _ in cnt.most_common(4)))
        if not any_named:
            print("    لا بندَ من هذه المعاني في الملفّات المقروءة.")

    print("\nالحكم: يُقرأ أعلاه ثلاثةُ أسئلةٍ بأجوبةٍ مقيسة — أتنشر هذه"
          " الأوراقُ ملفّاً رسمياً؟ وإن نشرت فبأيّ أسماء؟ وإن لم تنشر فهل"
          " لصفحتها بابٌ خاصٌّ بالصناديق (‏`=NJ…=/`)؟ فالشريكُ يُختار على"
          " هذا لا على شهرةِ اسمه — وما كان خلفَ اشتراكٍ يُقال إنه ليس"
          " عندنا ولا يُتجاوَز.")
    return 0


raise SystemExit(asyncio.run(main()))
