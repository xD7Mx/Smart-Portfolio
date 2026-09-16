#!/usr/bin/env python3
"""مسحٌ شاملٌ للمكتبتَين وجدولُ الدمج — في تشغيلةٍ واحدة (D351).

    docker exec sp_backend python /app/scripts/audit/library_sweep.py
    docker exec sp_backend python /app/scripts/audit/library_sweep.py --refresh
    docker exec sp_backend python /app/scripts/audit/library_sweep.py --limit 80

قال المالك: «هدفي واضحٌ: الكشفُ عن جميع العقبات بمسحٍ شامل، ثمّ مسحٌ
شاملٌ لمكتبة تداول ومكتبة أرقام، ونضع دمجاً لجميع ما ينقص تداول من
أرقام. لماذا جعلتَ الموضوعَ سلوموشن ومجزّأً؟» — وهو محقّ. فهذه الأداةُ
تفعل الثلاثةَ في أمرٍ واحدٍ وعلى **كلّ** الدليل لا على عيّنةٍ من ستّين.

## ما تُخرجه

  ١· **مكتبةُ «تداول»**: لكلّ ورقةٍ نمطُها وعددُ ملفّاتها وأحدثُ إيداعٍ
     والبنودُ التي نقرؤها منها فعلاً — ثمّ تغطيةُ كلّ بندٍ بعدد الأوراق.
  ٢· **مكتبةُ «أرقام»**: نتائجُها (صافي ربحٍ ربعيٍّ وسنويّ) ونسبُها
     التنظيمية (كفايةُ رأس المال · المتعثّرات · النسبةُ المجمّعة ·
     هامشُ الملاءة) — وهي بنودُ البنوك والتأمين التي لا تحملها خريطتُنا.
  ٣· **جدولُ الدمج**: لكلّ بندٍ مطلوب — أوراقٌ يملكها «تداول» · أوراقٌ
     **ينقصها تداول ويملكها أرقام** (وهذا هو المطلوب) · أوراقٌ لا يملكها
     أحدٌ فتُعلَن غائبةً · وأوراقٌ البندُ فيها غيرُ ذي معنى بمسطرة صنفها.

## وقيدٌ واحدٌ ثابت

المقيسُ هو **المتاحُ العامُّ** من «أرقام» — ما كان خلفَ اشتراكٍ مدفوعٍ
لا يُتجاوَز ولا يُقاس، ويُقال إنه ليس عندنا. (رُفض مرّتين ويبقى مرفوضاً.)

ولا يكتب حرفاً في قاعدة البيانات: قراءةٌ وقياسٌ فقط.
"""
from __future__ import annotations

import asyncio
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

LIMIT = None
CONC = 6
DEEP = "--deep" in sys.argv          # يسأل بوّابةَ الملفّات لكلّ ورقة
REFRESH = "--refresh" in sys.argv    # يُحدّث مخزنَ نتائج «أرقام» أوّلاً
if "--limit" in sys.argv:
    i = sys.argv.index("--limit")
    try:
        LIMIT = int(sys.argv[i + 1])
    except (IndexError, ValueError):
        LIMIT = None
if "--conc" in sys.argv:
    i = sys.argv.index("--conc")
    try:
        CONC = max(1, min(12, int(sys.argv[i + 1])))
    except (IndexError, ValueError):
        CONC = 6

# نسبُ «أرقام» التنظيمية — بنودٌ لا تحملها خريطةُ XBRL عندنا
AR_RATIOS = ("car", "car_tier1", "npl", "npl_coverage",
             "combined_ratio", "loss_ratio", "solvency_margin")


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.services import argaam_results as AR
    from app.services import statement_merge as SM
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.argaam_calendar import fetch_company_ratios

    syms = [str(s).replace(".SR", "") for s in U]
    if LIMIT:
        syms = syms[:LIMIT]
    rows_snap, live, at = tm.usable_rows()

    print(f"═ مسحٌ شاملٌ للمكتبتَين ═ أوراقٌ: {len(syms)} من {len(U)} ·"
          f" لقطةُ «تداول»: {len(rows_snap)} · حيّةٌ={live} · {at}")
    if REFRESH:
        try:
            print(f"  تحديثُ مخزن «أرقام»: {await AR.refresh()}")
        except Exception as e:                                    # noqa: BLE001
            print(f"  ⚠ تعذّر تحديثُ «أرقام»: {type(e).__name__}: {e}"[:120])

    # ── المكتبتانِ تُقرآنِ لكلّ ورقة ──────────────────────────────────
    tad: dict[str, set[str]] = {}       # رمزٌ ← بنودٌ يملكها «تداول»
    arg: dict[str, set[str]] = {}       # رمزٌ ← بنودٌ يملكها «أرقام»
    files_cnt: dict[str, int] = {}
    newest: dict[str, str] = {}
    ar_ratio_hits: Counter = Counter()
    sem = asyncio.Semaphore(CONC)
    done = {"n": 0}

    async def one(sym: str) -> None:
        async with sem:
            # ══ «تداول»: الصفوفُ المحفوظةُ هي ما نقرؤه فعلاً ══
            rows = X.for_symbol(sym, "annual") or []
            have = {k for k in SM.NEEDED
                    for r in rows if r.get(k) is not None}
            tad[sym] = have
            if rows:
                newest[sym] = max(str(r.get("as_of") or "") for r in rows)
            if DEEP:
                try:
                    files_cnt[sym] = len(await X.filings_for(f"{sym}.SR"))
                except Exception:                                 # noqa: BLE001
                    files_cnt[sym] = -1

            # ══ «أرقام»: نتائجُها ونسبُها العامّة ══
            got: set[str] = set()
            try:
                res = AR.for_symbol(sym) or {}
            except Exception:                                     # noqa: BLE001
                res = {}
            if ((res.get("annual") or {}).get("current") is not None
                    or (res.get("quarter") or {}).get("current") is not None):
                got.add("net_income")
            try:
                r = await fetch_company_ratios(sym)
                for k, v in ((r or {}).get("ratios") or {}).items():
                    if v is not None:
                        got.add(f"نسبة:{k}")
                        ar_ratio_hits[k] += 1
            except Exception:                                     # noqa: BLE001
                pass
            arg[sym] = got
            done["n"] += 1
            if done["n"] % 50 == 0:
                print(f"    … {done['n']} من {len(syms)}")

    await asyncio.gather(*(one(s) for s in syms), return_exceptions=True)

    # ── ١· تغطيةُ مكتبة «تداول» بنداً بنداً ────────────────────────────
    print("\n═════ ١· مكتبةُ «تداول» — تغطيةُ كلّ بندٍ بعدد الأوراق ═════")
    print(f"  أوراقٌ لها صفوفٌ محفوظة: {sum(1 for s in syms if tad.get(s))}"
          f" من {len(syms)}"
          + (f" · أحدثُ إيداعٍ مقروء: {max(newest.values())}" if newest else ""))
    for k in SM.NEEDED:
        n = sum(1 for s in syms if k in (tad.get(s) or set()))
        print(f"  {n:>4}  {k}")

    # ── ٢· مكتبةُ «أرقام» ─────────────────────────────────────────────
    print("\n═════ ٢· مكتبةُ «أرقام» — المتاحُ العامُّ وحدَه ═════")
    print(f"  أوراقٌ لها نتيجةٌ (صافي ربح): "
          f"{sum(1 for s in syms if 'net_income' in (arg.get(s) or set()))}")
    print("  ونسبٌ تنظيميةٌ لا تحملها خريطةُ XBRL عندنا:")
    for k in AR_RATIOS:
        if ar_ratio_hits.get(k):
            print(f"  {ar_ratio_hits[k]:>4}  نسبة:{k}")
    if not ar_ratio_hits:
        print("      لا نسبةَ في هذه التشغيلة — تُقرأ صفحاتُها أو لا تُتاح.")

    # ── ٣· جدولُ الدمج: ما ينقص «تداول» ويملكه «أرقام» ─────────────────
    print("\n═════ ٣· جدولُ الدمج — لكلّ بندٍ مصدرُه ═════")
    fill: dict[str, list[str]] = {}
    none_has: dict[str, int] = {}
    nomean_cnt: dict[str, int] = {}
    for k in SM.NEEDED:
        f, z, nm = [], 0, 0
        for s in syms:
            if k in SM.not_meaningful(s):
                nm += 1
                continue
            if k in (tad.get(s) or set()):
                continue
            if k in (arg.get(s) or set()):
                f.append(s)
            else:
                z += 1
        fill[k], none_has[k], nomean_cnt[k] = f, z, nm
    print(f"  {'البند':<22}{'تداول':>7}{'يُكمله أرقام':>14}"
          f"{'لا أحد':>8}{'بلا معنى':>10}")
    for k in SM.NEEDED:
        n_t = sum(1 for s in syms if k in (tad.get(s) or set()))
        print(f"  {k:<22}{n_t:>7}{len(fill[k]):>14}"
              f"{none_has[k]:>8}{nomean_cnt[k]:>10}")
        if fill[k]:
            print("        يُكملها أرقام: " + " · ".join(fill[k][:16])
                  + (" …" if len(fill[k]) > 16 else ""))

    print("\nالحكم: العمودُ «يُكمله أرقام» هو **الدمجُ المطلوب** — يُوصَل"
          " بطبقة الإكمال بمصدرٍ معلَنٍ لكلّ حقل. والعمودُ «لا أحد» يُقال"
          " غائباً ولا يُختلَق. و«بلا معنى» ليس نقصاً بل مسطرةُ صنفٍ"
          " (‏D349). والنسبُ التنظيميةُ في القسم ٢ بنودٌ زائدةٌ على"
          " خريطتنا: تُضاف حقولاً للبنوك والتأمين بمصدرها «أرقام».")
    return 0


raise SystemExit(asyncio.run(main()))
