#!/usr/bin/env python3
"""معاملاتُ تبويب القوائم: هل XBRL تحت معاملٍ آخر؟ (D365).

    docker exec sp_backend python /app/scripts/audit/filings_params.py
    docker exec sp_backend python /app/scripts/audit/filings_params.py 4141 9515

قِيس على خادم المالك بعيّنةٍ غيرِ منحازة: ‎82 ورقةً من ‎396 قائمتُها
تُجيب بـ‎5–23 رابطاً **كلُّها PDF** (‏`/Resources/fsPdf/…_En.pdf`)
بتواريخَ حديثةٍ جدّاً (‏2026-09-14)، ولا رابطَ `XBRL_DOCS` واحد. فهؤلاء
يودعون — بصيغةٍ أخرى.

## والاحتمالُ الذي لم يُقَس بعد

نداؤنا **مثبَّتٌ**: `statementType=6` و`reportType=1`. وتبويبُ القوائم
في الصفحة فيه مُحدِّداتٌ (نوعُ القائمة · نوعُ التقرير)، فقد يكون XBRL
تحت معاملٍ آخرَ — وهو عينُ ما بيّته مرّتَين: **البابُ يتبع المعاملَ
والصفحةَ لا الاسم** (جدولُ «نمو» كان خدمةَ الرئيسيّ من صفحته).

فتُجرَّب المصفوفةُ كلُّها لكلّ ورقةٍ ويُعَدّ في كلّ جوابٍ: روابطُ
`XBRL_DOCS` وروابطُ `fsPdf`. فإن ظهر XBRL تحت معاملٍ فالمكسبُ ‎82 ورقةً
بتعديل معاملٍ واحد، وإن لم يظهر في المصفوفة كلِّها فالحكمُ مقيسٌ:
**هؤلاء يودعون PDF**، وقراءتُه طبقةٌ أخرى تُقدَّر كلفتُها ولا تُدَّعى.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()]
TYPES = range(1, 11)          # statementType
REPORTS = (1, 2, 3)           # reportType
_XBRL = re.compile(r"href=[\"'][^\"']*XBRL_DOCS[^\"']*\.html[\"']", re.I)
_PDF = re.compile(r"href=[\"'][^\"']*fsPdf[^\"']*\.pdf[\"']", re.I)


async def main() -> int:
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch

    rows, _, _ = tm.usable_rows()
    syms = SYMS
    if not syms:
        # الافتراضُ: أوراقٌ من الـ«بلا ملفّات» بعيّنةٍ موزَّعةٍ بالبادئة
        cand = [s for s in sorted(rows)
                if not X.for_symbol(s, "annual")
                and not X.for_symbol(s, "quarterly")]
        seen: dict[str, str] = {}
        for s in cand:
            seen.setdefault(s[:1], s)
        syms = list(seen.values())[:5]
    print(f"═ مصفوفةُ معاملات تبويب القوائم ═ أوراقٌ: {' · '.join(syms)}")
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
            print(f"\n── {sym}: لا خدمةَ statementsTabData في الصفحة")
            continue
        svc = mb.group(1).rstrip("/") + "/" + ep
        print(f"\n── {sym} ──")
        hits = []
        for rt in REPORTS:
            line = []
            for stp in TYPES:
                try:
                    s2, b2 = await fetch(svc, params={
                        "statementType": str(stp), "reportType": str(rt),
                        "requestLocale": "en"}, referer=full)
                except Exception:                                 # noqa: BLE001
                    line.append(f"{stp}:تعذّر")
                    continue
                if s2 != 200 or not b2:
                    line.append(f"{stp}:HTTP{s2}")
                    continue
                nx, np_ = len(_XBRL.findall(b2)), len(_PDF.findall(b2))
                line.append(f"{stp}:x{nx}/p{np_}")
                if nx:
                    hits.append((rt, stp, nx))
            print(f"   reportType={rt} → " + " · ".join(line))
        if hits:
            print(f"   **XBRL ظهر عند: "
                  + " · ".join(f"reportType={r},statementType={t}→{n} ملفّاً"
                               for r, t, n in hits) + "**")
        else:
            print("   ولا XBRL في المصفوفة كلِّها — الإيداعُ PDF لهذه الورقة")

    print("\nالحكم: إن ظهر XBRL تحت معاملٍ فالمكسبُ بتعديل معاملٍ واحد،"
          " وإن غاب في المصفوفة كلِّها فهؤلاء يودعون PDF — وقراءتُه طبقةٌ"
          " أخرى تُقدَّر كلفتُها ولا تُدَّعى. و«بلا ملفّات» تبقى عبارةً"
          " خاطئةً في حقّهم: أودعوا، بصيغةٍ لا نقرؤها.")
    return 0


raise SystemExit(asyncio.run(main()))
