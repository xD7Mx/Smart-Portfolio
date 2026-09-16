#!/usr/bin/env python3
"""بابُ التأمين بعد IFRS 17، واسمُ الأقساط في شطره الصحيح (D374).

    docker exec sp_backend python /app/scripts/audit/ifrs17_door.py
    docker exec sp_backend python /app/scripts/audit/ifrs17_door.py 8010 4330

قِيس على خادم المالك جردٌ بلا شبكة: من ‎272 ورقةً في السوق الرئيسيّ،
**‎25 شركةَ تأمينٍ** أحدثُ ملفٍّ لها بعمر ‎1355–1447 يوماً (‏أحدثُها
‎2023-03-19)، و**‎19 ريتاً** بين بلا ملفٍّ (‏13) وعمرِ ‎2451–2635 يوماً
(‏6). فأربعٌ وأربعون ورقةً — ‎16% من الرئيسيّ — عطبُهما **مصدرٌ لا اسم**.

وسحبتُ إيرادَ المؤمِّن لأنه كان مطابَقاً خطأً (شطرُ المساهمين لا
عملياتُ التأمين) — وذلك صوابٌ **ولا يُغني عن سدّه**. فالفراغُ المعلَنُ
أصدقُ من الخطأ، ولا يُقبَل غايةً.

## سؤالانِ يُقاسان في نداءٍ واحدٍ ولا يُخمَّن جوابُهما

  **أ· هل الإيداعُ مستمرٌّ بتصنيفٍ آخر؟** نداؤنا مثبَّتٌ على
  `statementType=6`, `reportType=1`. و«IFRS 17» غيّر تصنيفَ قوائم
  التأمين في ‎2023 — وهو عينُ التاريخ الذي جمد عنده إيداعُهم عندنا.
  فتُجرَّب المصفوفةُ ويُطبع **لكلّ جوابٍ: عددُ ملفّاتِ XBRL وأحدثُ
  تاريخٍ فيها** — فالتاريخُ أوّلُ ما يُقاس (‏D368)، إذ بابٌ يردّ ملفّاتٍ
  قديمةً ليس فتحاً.

  **ب· وما اسمُ سطر الأقساط؟** يُقرأ أحدثُ ملفٍّ متاحٍ وتُطبع منه كلُّ
  الصفوف التي في اسمها مفردةُ إيرادِ تأمينٍ (‏أقساطٌ · اكتتابٌ ·
  مساهماتٌ · إيرادُ خدماتِ تأمين) **مع قيمها**، فيُنقَل الاسمُ بالحرف
  إلى الخريطة ولا يُلبَّس رقمٌ ثوبَ آخر.

والريتُ يُقاس معه بالسؤال نفسِه: أهو بابٌ مغلقٌ أم صيغةٌ أخرى.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SYMS = [a.replace(".SR", "") for a in sys.argv[1:] if a[:1].isdigit()]
TYPES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
REPORTS = (1, 2, 3)
_XBRL = re.compile(r"href=[\"']([^\"']*XBRL_DOCS[^\"']*\.html)[\"']", re.I)
_PDF = re.compile(r"href=[\"'][^\"']*fsPdf[^\"']*\.pdf[\"']", re.I)
_DATE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
# مفرداتُ إيرادِ المؤمِّن كما تُنشَر — عربيٌّ وإنجليزيّ
PREM = ("premium", "premiums", "contribution", "contributions",
        "insurance revenue", "underwrit", "gross written",
        "insurance service result", "أقساط", "مساهمات", "اكتتاب")
SKIP = ("reinsur", "retakaful", "unearned", "receivable", "deferred",
        "amortization", "amortisation", "accretion")


async def main() -> int:
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch

    rows, _, _ = tm.usable_rows()
    syms = SYMS
    if not syms:
        # بلا وسيطٍ: مؤمِّنانِ وريتانِ من اللقطة — لا عيّنةٌ منحازةٌ لصنف
        ins = [s for s in sorted(rows) if X._arch_of(s) == "insurance"]
        rt = [s for s in sorted(rows) if X._arch_of(s) == "reit"]
        syms = ins[:2] + rt[:2]
    print(f"═ بابُ التأمين بعد IFRS 17 ═ أوراقٌ: {' · '.join(syms) or '—'}")
    if not syms:
        print("  لا ورقةَ تُقاس — اللقطةُ فارغةٌ أو لا مرشَّح.")
        return 1

    for sym in syms:
        arch = X._arch_of(sym)
        url = (tm.row_for(sym) or {}).get("company_url")
        print(f"\n════ {sym} · نمط={arch} ════")
        if not url:
            print("  لا رابطَ لصفحة الشركة في اللقطة")
            continue
        full = X.ORIGIN + url if url.startswith("/") else url
        try:
            st, page = await fetch(full)
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّرت الصفحةُ — {type(e).__name__}")
            continue
        if st != 200 or not page:
            print(f"  صفحةُ الشركة HTTP {st}")
            continue
        mb = X._BASE.search(page)
        ep = next((m.group(0) for m in X._NJ.finditer(page)
                   if m.group(1) == "statementsTabData"), None)
        if not (mb and ep):
            print("  لا خدمةَ statementsTabData في الصفحة")
            continue
        svc = mb.group(1).rstrip("/") + "/" + ep

        # ══ أ · المصفوفةُ — ومعها **تاريخُ** ما وصل ══ (D368)
        best: tuple[str, int, int] | None = None
        for rt_ in REPORTS:
            line = []
            for stp in TYPES:
                try:
                    s2, b2 = await fetch(svc, params={
                        "statementType": str(stp), "reportType": str(rt_),
                        "requestLocale": "en"}, referer=full)
                except Exception:                                 # noqa: BLE001
                    line.append(f"{stp}:تعذّر")
                    continue
                if s2 != 200 or not b2:
                    line.append(f"{stp}:HTTP{s2}")
                    continue
                docs = _XBRL.findall(b2)
                pdfs = len(_PDF.findall(b2))
                ds = sorted(set("-".join(m) for m in _DATE.findall(b2)))
                newest = ds[-1] if ds else "—"
                line.append(f"{stp}:x{len(docs)}/p{pdfs}"
                            + (f"@{newest[:7]}" if docs else ""))
                if docs and ds:
                    y = int(newest[:4]) * 100 + int(newest[5:7])
                    if best is None or y > best[1]:
                        best = (f"reportType={rt_},statementType={stp}", y,
                                len(docs))
            print(f"  reportType={rt_} → " + " · ".join(line))
        if best:
            print(f"  ★ أحدثُ بابٍ: {best[0]} → {best[2]} ملفّاً ·"
                  f" أحدثُ تاريخ {best[1] // 100}-{best[1] % 100:02d}")
        else:
            print("  ولا ملفَّ XBRL في المصفوفة كلِّها — الإيداعُ بصيغةٍ أخرى")

        # ══ ب · اسمُ الأقساط من أحدثِ ملفٍّ متاح ══
        files, why = await X.filings_for_ex(sym, company_url=url)
        if not files:
            print(f"  ولا قائمةَ ملفّاتٍ: {why}")
            continue
        f0 = files[0]
        print(f"  أحدثُ ملفٍّ في القائمة: {str(f0.get('filed'))[:10]} ·"
              f" {str(f0.get('url'))[-52:]}")
        try:
            s3, html = await fetch(X.ORIGIN + f0["url"])
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّر تحميلُه — {type(e).__name__}")
            continue
        if s3 != 200 or not html:
            print(f"  تحميلُ الملفّ HTTP {s3}")
            continue
        hits = []
        for tr in X._TR.findall(html):
            cells = [X._clean(c) for c in X._TD.findall(tr)]
            if len(cells) < 2 or not cells[0] or len(cells[0]) > 160:
                continue
            nm = X._norm(cells[0])
            if "[text block]" in nm:
                continue
            if not any(w in nm for w in PREM):
                continue
            nums = [c for c in cells[1:]
                    if len(c) <= 40 and X._num(c) is not None]
            if not nums:
                continue
            hits.append((nm, nums[0], any(w in nm for w in SKIP)))
        print(f"  صفوفُ إيرادِ تأمينٍ ذاتُ أرقام: {len(hits)}")
        for nm, v, noisy in hits[:18]:
            print(f"     {'·' if noisy else '★'} «{nm[:70]}» = {v}")
        if hits:
            print("     (★ مرشَّحٌ للنقل · · صفٌّ فرعيٌّ: إعادةُ تأمينٍ أو"
                  " غيرُ مكتسبٍ أو مدينٌ — لا يُنقَل إيراداً)")

    print("\nالحكم: بابٌ يردّ ملفّاتٍ **أحدثَ من 2023** يُنقَل معاملُه"
          " فيُحيا قطاعانِ (44 ورقة). وإن كان أحدثُ ما يردّه 2023 فالإيداعُ"
          " انتقل إلى صيغةٍ أخرى ويُقال ذلك صريحاً بعمره. واسمُ الأقساط"
          " المعلَّمُ ★ يُنقَل بالحرف إلى الخريطة — ويبقى المسحوبُ مسحوباً"
          " حتى يُنقَل، فالفراغُ المعلَنُ أصدقُ من رقمٍ خاطئ.")
    return 0


raise SystemExit(asyncio.run(main()))
