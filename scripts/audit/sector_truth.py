#!/usr/bin/env python3
"""القطاعُ من مُصدِرِه: «تداول» حيٌّ رسميّ — لا يُستنبَط ولا يُترجَم (D396).

    docker exec sp_backend python /app/scripts/audit/sector_truth.py
    docker exec sp_backend python /app/scripts/audit/sector_truth.py --save

سأل المالك: «هل دليلُ الشركات من جهة تداول موجودٌ لديك؟ وهل يغنينا عن
أرقام بمعنى أنه مصنَّفٌ مثل أرقام؟». وقِيس الجوابُ على خادمه: لقطةُ
«تداول» تحمل `sector_en` **لكلّ رمز** — ‎272 رمزاً في الرئيسيّ،
‎100% لها قطاعٌ، و**‎22 قطاعاً متمايزاً** وهو عينُ عددِ قطاعاتنا.
فالتصنيفُ من مُصدِرِه حيٌّ يتجدّد، ولا يُستنبَط من صفحةٍ بقرينة موضع
(وهو المنهجُ الباطل الذي سُحب في D395).

## والخريطةُ تُقاس ولا تُترجَم

اسمُ القطاع عند «تداول» إنجليزيٌّ وعندنا عربيّ. وترجمتي من عندي رأيٌ
لا قياس — فتُبنى الخريطةُ **بالتطابق**: لكلّ اسمٍ إنجليزيٍّ يُنظَر في
أعضائه، فأيُّ اسمٍ عربيٍّ يحمله أكثرُهم في دليلنا هو مقابلُه. ومعها
تُطبَع **نسبةُ الإجماع**: خريطةٌ إجماعُها دون ‎80% مشكوكٌ فيها وتُعلَن
ولا تُستعمل.

ثمّ يُطبَع الخلافُ الحقيقيُّ — شركةٌ قطاعُها عندنا يخالف قطاعَ
«تداول» — فهذا الذي يفسد الحكم: الخريطةُ تُطبَّق بالقطاع، فشركةٌ في
قطاعٍ خطأ تُقاس بمسطرةٍ ليست لها.

ولا يُكتب في دليل التطبيق: مرجعٌ إرشاديٌّ بأمر المالك، و`--save`
يحفظه في `docs/` بتاريخِ قياسه.
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

SAVE = "--save" in sys.argv


def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market
    from app.services import tadawul_market as tm

    rows, live, at = tm.usable_rows()
    if not rows:
        print("اللقطةُ فارغة — لا قياس. (عطبٌ لا نتيجة.)")
        return 1
    ours = main_market(MARKET_UNIVERSE)
    snap = {s: r for s, r in rows.items() if not s.startswith("9")}
    print(f"═ القطاعُ من مُصدِرِه ═ لقطةٌ حيّةٌ={live} · {at}")
    print(f"  رموزُ الرئيسيّ في اللقطة: {len(snap)} · في دليلنا: {len(ours)}")

    # ── ١ · الخريطةُ بالتطابق لا بالترجمة ─────────────────────────────
    members: dict[str, list[str]] = defaultdict(list)
    for s, r in snap.items():
        en = (r or {}).get("sector_en")
        if en:
            members[en].append(s)
    print(f"\n═ خريطةُ القطاعات ═ إنجليزيٌّ={len(members)}")
    mapping: dict[str, dict] = {}
    weak = 0
    for en, syms in sorted(members.items(), key=lambda kv: -len(kv[1])):
        votes = Counter((ours.get(s) or {}).get("sector")
                        for s in syms if s in ours
                        and (ours.get(s) or {}).get("sector"))
        if not votes:
            print(f"  ✗ {en:<44} {len(syms):>3} عضواً · لا مقابلَ عندنا")
            mapping[en] = {"ar": None, "agree": 0.0, "n": len(syms)}
            weak += 1
            continue
        ar, n = votes.most_common(1)[0]
        agree = n / sum(votes.values())
        flag = "★" if agree >= 0.8 else "⚠"
        if agree < 0.8:
            weak += 1
        print(f"  {flag} {en:<44} {len(syms):>3} عضواً → {ar}"
              f" · إجماعٌ {agree * 100:.0f}%"
              + (f" · وأصواتٌ أخرى: {dict(votes.most_common()[1:4])}"
                 if len(votes) > 1 else ""))
        mapping[en] = {"ar": ar, "agree": round(agree, 3), "n": len(syms)}
    print(f"\n  خرائطُ إجماعُها دون 80% أو بلا مقابل: {weak}")

    # ── ٢ · الخلافُ الحقيقيُّ لكلّ شركة ────────────────────────────────
    mism = []
    for s, r in sorted(snap.items()):
        en = (r or {}).get("sector_en")
        our = (ours.get(s) or {}).get("sector")
        if not (en and our):
            continue
        exp = (mapping.get(en) or {}).get("ar")
        if exp and our != exp and (mapping[en]["agree"] >= 0.8):
            mism.append((s, en, exp, our))
    print(f"\n═ شركاتٌ قطاعُها عندنا يخالف «تداول» ═ {len(mism)}")
    for s, en, exp, our in mism[:30]:
        nm = (ours.get(s) or {}).get("name_ar") or ""
        print(f"  {s} {nm[:20]:<22} تداول: {exp} ≠ عندنا: {our}")

    # ── ٣ · وسلامةُ الدليل: مَن في السوق ولا يراه التطبيق ─────────────
    ghost = sorted(set(snap) - set(ours))
    stale = sorted(set(ours) - set(snap))
    print(f"\n═ سلامةُ الدليل ═")
    print(f"  في السوق ولا وجودَ له في دليلنا ({len(ghost)}): "
          + (" · ".join(f"{s}={(snap[s] or {}).get('name_en') or ''}"[:28]
                        for s in ghost) or "لا شيء"))
    print("   ← هؤلاء **لا يراهم التطبيقُ إطلاقاً**: لا درجةَ ولا سعراً"
          " عادلاً ولا اسماً.")
    print(f"  في دليلنا ولا وجودَ له في اللقطة ({len(stale)}): "
          + (" · ".join(f"{s}={(ours.get(s) or {}).get('name_ar') or ''}"[:26]
                        for s in stale) or "لا شيء"))
    print("   ← يُفحَص كلٌّ منها: أُوقف تداولُه؟ اندمج؟ أم عطبُ جلب؟"
          " ولا يُحذَف رمزٌ من الدليل على قياسٍ واحد.")

    if SAVE:
        p = pathlib.Path("/app/docs/SECTOR_TRUTH.json")
        if not p.parent.exists():
            p = pathlib.Path("docs/SECTOR_TRUTH.json")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({
            "المصدر": "لقطةُ «تداول» — sector_en",
            "تاريخُ القياس": date.today().isoformat(),
            "ملاحظة": "مرجعٌ إرشاديّ — لا يُكتب في دليل التطبيق",
            "خريطةُ القطاعات": mapping,
            "قطاعُ كلّ شركة": {s: (r or {}).get("sector_en")
                               for s, r in sorted(snap.items())},
            "خلافٌ مع دليلنا": [{"رمز": s, "تداول": exp, "عندنا": our}
                                for s, _e, exp, our in mism],
            "في السوق وليس في دليلنا": ghost,
            "في دليلنا وليس في اللقطة": stale,
        }, ensure_ascii=False, indent=1), "utf-8")
        print(f"\n  حُفظ مرجعاً: {p}")

    print("\nالحكم: القطاعُ يُقرأ من مُصدِرِه حيّاً — وهو أوثقُ من أيّ"
          " استنباط. والخريطةُ تُقاس بالتطابق فتُعلَن نسبةُ إجماعها، وما"
          " إجماعُه دون 80% لا يُستعمل. وكلُّ خلافٍ يُطبَع باسم شركته:"
          " الخريطةُ تُطبَّق بالقطاع، فشركةٌ في قطاعٍ خطأ تُقاس بمسطرةٍ"
          " ليست لها — ويفسد حكمُها في المحرّكَين معاً.")
    return 0


raise SystemExit(main())
