#!/usr/bin/env python3
"""جدولُ القوائم مرسوماً في تبويب «تداول» — بنيتُه تُقرأ (D367).

    docker exec sp_backend python /app/scripts/audit/statements_tab.py 4141 9515

قِيس ونُهي (‏D365 · D366): ‎82 ورقةً تودع ملفّاتها **PDF** ولا XBRL لها.
ثمّ ظهر في كاشف الإعلانات ما يقلب الحكم: خدمةُ `statementsTabData`
بمعامل **`statementType=1`** تردّ **‎81,310 حرفاً وفيها ‎158 رقماً**
ومفردةَ «total revenue» — أي أنها لا تردّ **قائمةَ ملفّاتٍ** بل
**الجدولَ نفسَه مرسوماً**.

ومصفوفةُ المعاملات قبلها ردّت `statementType=1 → x0/p0` لأنّي كنتُ
أعدّ **الروابطَ** (‏XBRL · PDF) لا **المحتوى** — فأخطأتُ بالمقياس
للمرّة الخامسة في هذا الباب: أقيس ما أتوقّعه لا ما وصل.

فهذا الكاشفُ يطبع **بنيةَ الجدول** كما هي: عددُ الصفوف، وأوّلُ خلايا
كلّ صفٍّ مع قيمه — فتُقرأ أسماءُ البنود بالحرف (كما فُعل بـXBRL) ولا
يُخمَّن مكانُ رقم. ولا يُبنى قارئٌ قبل أن تُقرأ البنية.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()]
TYPES = [int(a[2:]) for a in sys.argv[1:] if a.startswith("t=")] or [1, 2, 3, 4]
ROWS_SHOWN = 16


async def main() -> int:
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch

    rows, _, _ = tm.usable_rows()
    syms = SYMS
    if not syms:
        cand = [s for s in sorted(rows)
                if not X.for_symbol(s, "annual")
                and not X.for_symbol(s, "quarterly")]
        seen: dict[str, str] = {}
        for s in cand:
            seen.setdefault(s[:1], s)
        syms = list(seen.values())[:2]
    print(f"═ بنيةُ جدول القوائم ═ أوراقٌ: {' · '.join(syms) or '—'}"
          f" · أنواعٌ: {TYPES}")
    if not syms:
        print("  لا ورقةَ تُقاس — اللقطةُ فارغةٌ أو لا مرشَّح.")
        return 1

    for sym in syms:
        url = (tm.row_for(sym) or {}).get("company_url")
        if not url:
            print(f"\n── {sym}: لا رابطَ لصفحة الشركة في اللقطة")
            continue
        full = X.ORIGIN + url if url.startswith("/") else url
        try:
            st, page = await fetch(full)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n── {sym}: تعذّرت الصفحةُ — {type(e).__name__}")
            continue
        if st != 200 or not page:
            print(f"\n── {sym}: صفحةُ الشركة HTTP {st}")
            continue
        mb = X._BASE.search(page)
        ep = next((m.group(0) for m in X._NJ.finditer(page)
                   if m.group(1) == "statementsTabData"), None)
        if not (mb and ep):
            print(f"\n── {sym}: لا خدمةَ statementsTabData")
            continue
        svc = mb.group(1).rstrip("/") + "/" + ep

        for stp in TYPES:
            try:
                s2, b2 = await fetch(svc, params={
                    "statementType": str(stp), "reportType": "1",
                    "requestLocale": "en"}, referer=full)
            except Exception as e:                                # noqa: BLE001
                print(f"\n── {sym} · نوع {stp}: تعذّر {type(e).__name__}")
                continue
            if s2 != 200 or not b2:
                print(f"\n── {sym} · نوع {stp}: HTTP {s2}")
                continue
            trs = X._TR.findall(b2)
            numeric = 0
            shown = 0
            print(f"\n── {sym} · statementType={stp}: {len(b2)} حرفاً ·"
                  f" صفوفُ جدولٍ={len(trs)}")
            for tr in trs:
                cells = [X._clean(c) for c in X._TD.findall(tr)]
                if not cells or not cells[0]:
                    continue
                nums = [c for c in cells[1:] if X._num(c) is not None]
                if nums:
                    numeric += 1
                if shown < ROWS_SHOWN and (nums or len(cells) > 1):
                    shown += 1
                    print(f"     «{cells[0][:52]}» → "
                          + " · ".join(str(n)[:16] for n in nums[:3])
                          + ("" if nums else f"(بلا رقم: {cells[1:3]})"))
            print(f"     صفوفٌ ذاتُ أرقام: {numeric}")

    # ══ ثمّ مسحٌ للـ82: كم منهم فيه أرقامٌ وما أحدثُ تاريخٍ فيه ══ (D368)
    # قِيس أن التبويبَ يحمل قائمةَ دخلٍ وتدفّقٍ كاملتَين لبعضهم — لكنّ
    # تواريخَه **2023-03 و2022-09**، وهو عينُ ما كُتب في وحدتنا يوم
    # اختيار XBRL: «تبويبُ القوائم متجمّدٌ عند منتصف 2023». فالقرارُ
    # لا يُتّخذ على عيّنةِ ثلاثٍ: يُقاس **كم منهم** فيه أرقامٌ و**كم
    # عمرُ أحدثِ تاريخ** — فبينهما يُعرَف هل يُصلح تاريخاً أم لا شيء.
    if not SYMS:
        cand = [s for s in sorted(rows)
                if not X.for_symbol(s, "annual")
                and not X.for_symbol(s, "quarterly")]
        by_pfx: dict[str, list[str]] = {}
        for s_ in cand:
            by_pfx.setdefault(s_[:1], []).append(s_)
        pick: list[str] = []
        i = 0
        while len(pick) < min(24, len(cand)):
            added = False
            for k in sorted(by_pfx):
                if i < len(by_pfx[k]) and len(pick) < 24:
                    pick.append(by_pfx[k][i])
                    added = True
            if not added:
                break
            i += 1
        print(f"\n═ مسحُ الـ{len(cand)} بعيّنةٍ موزَّعةٍ ({len(pick)}) ═")
        import re as _re
        _D = _re.compile(r"20\d{2}-\d{2}-\d{2}")
        have, empty, newest_all = 0, 0, []
        sem2 = asyncio.Semaphore(3)

        async def probe(sym: str) -> None:
            nonlocal have, empty
            async with sem2:
                u = (tm.row_for(sym) or {}).get("company_url")
                if not u:
                    return
                f2 = X.ORIGIN + u if u.startswith("/") else u
                try:
                    st3, pg = await fetch(f2)
                    if st3 != 200 or not pg:
                        return
                    m2 = X._BASE.search(pg)
                    e2 = next((m.group(0) for m in X._NJ.finditer(pg)
                               if m.group(1) == "statementsTabData"), None)
                    if not (m2 and e2):
                        return
                    s4, b4 = await fetch(m2.group(1).rstrip("/") + "/" + e2,
                                         params={"statementType": "1",
                                                 "reportType": "1",
                                                 "requestLocale": "en"},
                                         referer=f2)
                except Exception:                                 # noqa: BLE001
                    return
                if s4 != 200 or not b4:
                    return
                n = sum(1 for tr in X._TR.findall(b4)
                        if any(X._num(X._clean(c)) is not None
                               for c in X._TD.findall(tr)[1:]))
                ds = sorted(set(_D.findall(b4)))
                if n:
                    have += 1
                    if ds:
                        newest_all.append(ds[-1])
                    print(f"   {sym}: {n} صفّاً ذا أرقام · أحدثُ تاريخ:"
                          f" {ds[-1] if ds else '—'}")
                else:
                    empty += 1
                    print(f"   {sym}: بلا أرقام")

        await asyncio.gather(*(probe(s) for s in pick), return_exceptions=True)
        print(f"\n   فيه أرقامٌ: {have} · بلا أرقام: {empty}"
              + (f" · أحدثُ تاريخٍ في العيّنة: {max(newest_all)}"
                 f" · أقدمُ أحدثِ تاريخ: {min(newest_all)}"
                 if newest_all else ""))

    print("\nالحكم: صفوفٌ ذاتُ أرقامٍ وأسماءٍ مقروءةٍ تعني أن القوائمَ"
          " **مرسومةٌ في التبويب** لا مرفوعةً ملفّاً — فتُنقَل أسماؤها"
          " بالحرف إلى خريطةٍ كما فُعل بـXBRL، وتُقرأ لمن لا XBRL له"
          " (‏82 ورقة). وإن كانت الصفوفُ بلا أرقامٍ فالجدولُ يُرسَم"
          " بجافاسكربت ويبقى الحكمُ على PDF.")
    return 0


raise SystemExit(asyncio.run(main()))
