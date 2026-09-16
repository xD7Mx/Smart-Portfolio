#!/usr/bin/env python3
"""«بلا ملفّات» تُفصَّل إلى بواباتها الخمس (D359).

    docker exec sp_backend python /app/scripts/audit/filings_door.py
    docker exec sp_backend python /app/scripts/audit/filings_door.py --n 40

قِيس على خادم المالك بعد وصل «نمو»: اللقطةُ ‎396 رمزاً، قُرئت ‎314،
و**‎82 «بلا ملفّات»**. والعبارةُ تصف نتيجةً لا سبباً: `filings_for`
تعود فارغةً من **خمسة مواضعَ مختلفة**، وكلُّها تُطبَع كلمةً واحدة —
وهذا عينُ العطب الذي كُشف في باب الجدول: ظننتُ المكتبةَ ناقصةً وكان
النقصُ في طَرْقي.

## البواباتُ الخمس كما هي في الشفرة

  ١· لا رابطَ لصفحة الشركة في اللقطة
  ٢· صفحةُ الشركة لا تُقرأ (‏HTTP)
  ٣· الصفحةُ تُقرأ ولا `<base>` فيها، **أو لا خدمةَ اسمُها
     `statementsTabData`** ← وهذا المشتبَهُ الأوّل: لعلّ اسمَها في
     صفحات «نمو» غيرُه، كما كان جدولُ «نمو» بابَ الرئيسيّ من صفحته.
  ٤· الخدمةُ تُنادى ولا تُجيب (‏HTTP)
  ٥· تُجيب ولا رابطَ فيها إلى `XBRL_DOCS` ← **وليست «لم تودع»**:
     قِيس أن قوائمَ هؤلاء موجودةٌ بصيغة **PDF** (‏`/Resources/fsPdf/`)
     بتواريخَ حديثة. فالعبارةُ الصحيحةُ «لا ملفَّ XBRL»، والفرقُ أن
     الأولى نفيُ إيداعٍ والثانيةَ نفيُ صيغةٍ نقرؤها.

ولكلّ ورقةٍ يُطبع أيُّ بوّابةٍ أُغلقت. وإن غاب `statementsTabData`
تُجرَّب **كلُّ** خدمةٍ في الصفحة ويُعَدّ ما فيها من روابط `XBRL_DOCS`
— فيُكتشَف الاسمُ البديلُ إن وُجد، ولا يُخمَّن.
"""
from __future__ import annotations

import asyncio
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

N = 24
CONC = 4
if "--n" in sys.argv:
    i = sys.argv.index("--n")
    try:
        N = int(sys.argv[i + 1])
    except (IndexError, ValueError):
        N = 24

PARAMS = {"statementType": "6", "reportType": "1", "requestLocale": "en"}
_DOCS = re.compile(r"href=[\"']([^\"']*XBRL_DOCS[^\"']*\.html)[\"']", re.I)


async def main() -> int:
    from app.services import tadawul_market as tm
    from app.services import tadawul_xbrl as X
    from app.services.tadawul_http import fetch

    rows, live, at = tm.usable_rows()
    # المرشَّحون: في اللقطة وبلا صفوفٍ محفوظةٍ — وهم الذين قيل فيهم
    # «بلا ملفّات» أو «لم تُفهم» في آخر حصاد.
    cand = [s for s in sorted(rows)
            if not X.for_symbol(s, "annual") and not X.for_symbol(s, "quarterly")]
    print(f"═ تفصيلُ «بلا ملفّات» ═ اللقطةُ {len(rows)} · بلا صفوفٍ محفوظة:"
          f" {len(cand)} · يُقاس منها {min(N, len(cand))}")
    if not cand:
        # ولا تُقرأ لقطةٌ فارغةٌ صحّةً: «لا مرشَّح» مع صفرِ رموزٍ تعني
        # أن شيئاً لم يُقَس، لا أن كلَّ شيءٍ سليم.
        print("  لا مرشَّحَ — "
              + ("لكنّ اللقطةَ **فارغة**: لم يُقَس شيءٌ، ولا يُقال إن"
                 " المكتبةَ كاملة." if not rows
                 else "كلُّ ما في اللقطة له صفوفٌ محفوظة."))
        return 0 if rows else 1

    gates: Counter = Counter()
    alt: Counter = Counter()
    sem = asyncio.Semaphore(CONC)
    lines: list[str] = []

    async def one(sym: str) -> None:
        async with sem:
            url = (tm.row_for(sym) or {}).get("company_url")
            if not url:
                gates["١· لا رابطَ لصفحة الشركة في اللقطة"] += 1
                lines.append(f"  {sym}: ١ لا رابط")
                return
            full = X.ORIGIN + url if url.startswith("/") else url
            try:
                st, page = await fetch(full)
            except Exception as e:                                # noqa: BLE001
                gates[f"٢· تعذّرُ صفحةِ الشركة ({type(e).__name__})"] += 1
                lines.append(f"  {sym}: ٢ {type(e).__name__}")
                return
            if st != 200 or not page:
                gates[f"٢· صفحةُ الشركة HTTP {st}"] += 1
                lines.append(f"  {sym}: ٢ HTTP {st}")
                return
            mb = X._BASE.search(page)
            svcs = {m.group(1): m.group(0) for m in X._NJ.finditer(page)}
            if not mb:
                gates["٣· الصفحةُ بلا <base>"] += 1
                lines.append(f"  {sym}: ٣ بلا base")
                return
            base = mb.group(1).rstrip("/")
            if "statementsTabData" not in svcs:
                gates["٣· لا خدمةَ اسمُها statementsTabData"] += 1
                # ══ فتُجرَّب كلُّ خدمةٍ في الصفحة ويُعَدّ ما فيها ══
                found = []
                for nm, sp in list(svcs.items())[:8]:
                    try:
                        s2, b2 = await fetch(f"{base}/{sp}", params=PARAMS,
                                             referer=full)
                    except Exception:                             # noqa: BLE001
                        continue
                    if s2 == 200 and b2 and _DOCS.search(b2):
                        found.append(f"{nm}×{len(_DOCS.findall(b2))}")
                        alt[nm] += 1
                lines.append(f"  {sym}: ٣ بلا statementsTabData · خدماتٌ="
                             + (",".join(svcs) or "لا شيء")
                             + (f" · **بديلٌ يُخرج ملفّات: {' · '.join(found)}**"
                                if found else " · ولا بديلَ أخرج ملفّاً"))
                return
            try:
                s3, b3 = await fetch(f"{base}/{svcs['statementsTabData']}",
                                     params=PARAMS, referer=full)
            except Exception as e:                                # noqa: BLE001
                gates[f"٤· تعذّرُ نداءِ القائمة ({type(e).__name__})"] += 1
                lines.append(f"  {sym}: ٤ {type(e).__name__}")
                return
            if s3 != 200:
                gates[f"٤· نداءُ القائمة HTTP {s3}"] += 1
                lines.append(f"  {sym}: ٤ HTTP {s3}")
                return
            docs = _DOCS.findall(b3 or "")
            if not docs:
                gates["٥· لا ملفَّ XBRL — وقد تودع بصيغةٍ أخرى (PDF)"] += 1
                # ══ وما في القائمة يُطبع ══ (D364)
                # «بلا ملفّ» وصفٌ لغياب ما نبحثه، لا وصفٌ لما وصل. فقد
                # تكون القائمةُ مليئةً بروابطَ من نوعٍ آخر (‏PDF · صفحةُ
                # إفصاح) — وذاك بابٌ يُنقَل لا غيابٌ يُعلَن.
                _hrefs = re.findall(r"href=[\"']([^\"']+)[\"']", b3 or "")
                _kinds: Counter = Counter()
                for _h in _hrefs:
                    _kinds[(_h.rsplit(".", 1)[-1][:6] if "." in _h[-8:]
                            else "بلا امتداد")] += 1
                lines.append(
                    f"  {sym}: ٥ أجابت {len(b3 or '')} حرفاً · روابطُ="
                    f"{len(_hrefs)} · أنواعٌ={dict(_kinds.most_common(5))}"
                    + (f" · مثالٌ: {_hrefs[0][-60:]}" if _hrefs else ""))
            else:
                gates["٦· ملفّاتٌ موجودةٌ — والعطبُ بعد هذا الباب"] += 1
                lines.append(f"  {sym}: ٦ **{len(docs)} ملفّاً** — فالمنعُ لاحقٌ")

    # ══ والعيّنةُ تُطبَّق لا تُقتطَع من الأوّل ══ (D364)
    # أخذتُ `cand[:60]` مرتَّبةً تصاعدياً فقاستُ رموزَ 1xxx و2xxx وحدَها
    # ولم تبلغ العيّنةُ رموزَ 9xxx («نمو») إطلاقاً — ثمّ عمّمتُ منها على
    # الـ82 كلِّها فأخطأتُ. فتُقسَّم العيّنةُ على البادئة بالتساوي.
    by_pfx: dict[str, list[str]] = {}
    for s_ in cand:
        by_pfx.setdefault(s_[:1], []).append(s_)
    pick: list[str] = []
    i = 0
    while len(pick) < min(N, len(cand)):
        added = False
        for k in sorted(by_pfx):
            if i < len(by_pfx[k]) and len(pick) < N:
                pick.append(by_pfx[k][i])
                added = True
        if not added:
            break
        i += 1
    print("  العيّنةُ بالبادئة: "
          + " · ".join(f"{k}×{sum(1 for x in pick if x[:1] == k)}"
                       for k in sorted({x[:1] for x in pick})))
    await asyncio.gather(*(one(s) for s in pick), return_exceptions=True)

    print("\n═ البوّابةُ التي أُغلقت — مرتَّبةً ═")
    for k, n in gates.most_common():
        print(f"  {n:>4}  {k}")
    if alt:
        print("\n═ أسماءُ خدماتٍ بديلةٍ أخرجت ملفّاتٍ فعلاً ═")
        for k, n in alt.most_common():
            print(f"  {n:>4}  ⟨{k}⟩")
    print("\n═ تفصيلُ الأوراق ═")
    for ln in lines:
        print(ln)

    print("\nالحكم: البوّابةُ ٥ وحدَها هي «بلا ملفّاتٍ» بحقّ — شركةٌ لم"
          " تودع بصيغةِ XBRL — وقِيس أنها تودع PDF. وما فوقها عطبٌ عندنا: بوّابةٌ ٣ تعني اسمَ خدمةٍ آخرَ"
          " يُنقَل بالحرف كما نُقل بابُ جدول «نمو»، وبوّابةٌ ٦ تعني أنّ"
          " الملفّاتَ موجودةٌ والمنعَ في قراءتها لا في وجودها.")
    return 0


raise SystemExit(asyncio.run(main()))
