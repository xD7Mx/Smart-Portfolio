#!/usr/bin/env python3
"""بابُ إعلان النتائج: أرقامٌ موحَّدةٌ لمن يودع PDF (D366).

    docker exec sp_backend python /app/scripts/audit/announce_door.py 4141 9515
    docker exec sp_backend python /app/scripts/audit/announce_door.py

قِيس ونُهي الأمرُ فيه (‏D365): ‎82 ورقةً من ‎396 تودع قوائمَها **PDF**
ولا XBRL لها — ‎150 نداءً على مصفوفة `statementType`×`reportType` ردّت
صفرَ XBRL. فقراءةُ PDF طبقةٌ ثقيلةٌ وهشّة: جداولُ حرّةٌ بلا تصنيفٍ
رسميّ، ومطابقةُ البنود فيها **تقريبٌ** — وهو منهيٌّ عنه في الميثاق
(«بندٌ يُملأ بأقربِ اسمٍ شبيهٍ أسوأُ من لا بيانات»).

## وبابٌ أخفُّ وأصدقُ يُقاس أوّلاً

«تداول» تُلزِم كلَّ مُصدِرٍ بإعلان **«النتائج المالية الأولية»** في
**جدولٍ موحَّدٍ** (إيرادات · ربحٌ تشغيليّ · صافي ربح · ربحيةُ سهم ·
حقوقُ المساهمين) — وهو صفحةُ HTML لا PDF، ومُهيكلٌ بحكم الإلزام لا
بحكم اجتهاد المُصدِر. ووحدتُنا `tadawul_announcements.py` تصنّف
**أنواعَ** الإعلانات ولا تستخرج أرقامَها.

فهذا الكاشفُ يسأل: هل لصفحة الشركة بابٌ للإعلانات؟ وهل في جوابه
أرقامُ النتائج؟ — ويُطبَع لكلّ خدمةٍ في الصفحة: حجمُ الجواب · عددُ
الصفوف · وكم مفردةً من مفردات جدول النتائج ظهرت فيه. ولا يُخمَّن
عنوانٌ ولا اسمُ خدمة: يُقرأ من الصفحة كما هو (طريقةُ الجلب المسجَّلة).
"""
from __future__ import annotations

import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()]

# مفرداتُ جدول النتائج الموحَّد — عربيٌّ وإنجليزيّ، كما تُنشَر
WORDS = ("الإيرادات", "صافي الربح", "الربح التشغيلي", "ربحية السهم",
         "إجمالي حقوق المساهمين", "الربح الإجمالي",
         "net profit", "total revenue", "operating profit",
         "earnings per share", "gross profit", "total shareholders")
_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


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
        syms = list(seen.values())[:4]
    print(f"═ بابُ إعلان النتائج ═ أوراقٌ: {' · '.join(syms) or '—'}")
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
        svcs = {m.group(1): m.group(0) for m in X._NJ.finditer(page)}
        print(f"\n── {sym}: خدماتُ الصفحة ({len(svcs)}): "
              + (" · ".join(svcs) or "لا شيء"))
        if not mb:
            print("   بلا <base> — لا يُبنى نداء")
            continue
        base = mb.group(1).rstrip("/")
        # وأرقامُ النتائج قد تكون في الصفحة نفسِها — فتُقاس قبل النداءات
        _w0 = [w for w in WORDS if w.lower() in page.lower()]
        print(f"   وفي الصفحة نفسِها من مفردات النتائج: {len(_w0)}"
              + (f" ({' · '.join(_w0[:5])})" if _w0 else ""))
        for nm, sp in list(svcs.items())[:10]:
            for prm in ({"requestLocale": "en"},
                        {"requestLocale": "en", "statementType": "1",
                         "reportType": "1"}):
                try:
                    s2, b2 = await fetch(f"{base}/{sp}", params=prm,
                                         referer=full)
                except Exception as e:                            # noqa: BLE001
                    print(f"   ⟨{nm}⟩ {prm and len(prm)} → تعذّر"
                          f" {type(e).__name__}")
                    continue
                if s2 != 200 or not b2:
                    print(f"   ⟨{nm}⟩ → HTTP {s2}")
                    break
                hit = [w for w in WORDS if w.lower() in b2.lower()]
                n_rows = "—"
                try:
                    dj = json.loads(b2)
                    d2 = dj.get("data") if isinstance(dj, dict) else dj
                    n_rows = len(d2) if isinstance(d2, list) else "—"
                except Exception:                                 # noqa: BLE001
                    pass
                print(f"   ⟨{nm}⟩ → {len(b2)} حرفاً · صفوفٌ={n_rows} ·"
                      f" أرقامٌ={len(_NUM.findall(b2))} ·"
                      f" **مفرداتُ النتائج: {len(hit)}**"
                      + (f" ({' · '.join(hit[:4])})" if hit else ""))
                if hit:
                    break

    print("\nالحكم: خدمةٌ يظهر في جوابها **مفرداتُ جدول النتائج مع أرقام**"
          " هي البابُ المطلوب — تُقرأ بنودُها بالحرف كما فُعل بـXBRL،"
          " وتُوصَل طبقةً مكمِّلةً لمن يودع PDF. وإن لم تظهر في أيّ خدمةٍ"
          " فالخيارُ الباقي قراءةُ PDF، وكلفتُها تُقال صريحةً: جداولُ"
          " حرّةٌ بلا تصنيفٍ رسميّ، ومطابقةٌ بالتقريب يمنعها الميثاق.")
    return 0


raise SystemExit(asyncio.run(main()))
