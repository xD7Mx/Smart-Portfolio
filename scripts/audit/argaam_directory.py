#!/usr/bin/env python3
"""دليلُ الشركات من «أرقام» بترتيبه — تاسي وحدَه (D390).

    docker exec sp_backend python /app/scripts/audit/argaam_directory.py
    docker exec sp_backend python /app/scripts/audit/argaam_directory.py --url <عنوان>

بأمر المالك: «اجعل دليلَ الشركات هو نفسُه بترتيب أرقام… اجلب دليلَ
الشركات كاملاً من أرقام، سيظهر لك خيارانِ واحدٌ تاسي وواحدٌ نمو —
اختر تاسي فقط».

ودليلُنا اليوم يُقرأ من صفحةِ **المفكرة** في «أرقام» (`_company_index`)
لا من صفحة الدليل — فترتيبُه ترتيبُ مفكرةٍ لا ترتيبُ دليل، ولا يحمل
قسمةَ السوقَين. فيُطرَق البابُ الصحيح، ولا يُخمَّن عنوانُه:

  ١· تُقرأ صفحةُ «أرقام» ويُبحَث عن كلّ رابطٍ نصُّه أو مسارُه يذكر
     شركاتٍ أو أسعاراً أو سوقاً — فيُطبَع ما وُجد بنصّه ومساره.
  ٢· ثمّ يُفتَح المرشَّحُ ويُقاس: كم صفّاً · كم رمزاً رباعياً · هل فيه
     خيارُ «تاسي» و«نمو» (مسارانِ أو معامِلٌ) · وأوّلُ الصفوف كما هي.
  ٣· ويُفصَل السوقان: رموزُ ‎9xxx نمو وما دونها تاسي — وتُطبع القسمةُ
     لتُراجَع لا لتُسلَّم، ويُقارَن عددُ تاسي بدليلنا (‏273).

ولا يُكتب دليلٌ من هذا الكاشف: يُقاس البابُ أوّلاً، ثمّ تُنقَل القسمةُ
والترتيبُ في وحدةِ المزامنة — فالدليلُ هويّةُ السوق، وتغييرُه بلا
قياسٍ يُربك كلَّ شاشة.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

HOME = "https://www.argaam.com/ar"
ARG = [a for a in sys.argv[1:] if a.startswith("http")]
_SYM = re.compile(r"\b(\d{4})\b")
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_TD = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")
WORDS = ("شركات", "الشركات", "أسعار", "companies", "market", "تاسي",
         "نمو", "السوق الرئيسية", "السوق الموازية")


def _txt(x: str) -> str:
    return re.sub(r"\s+", " ", _TAG.sub(" ", x or "")).strip()


async def main() -> int:
    from app.services.tadawul_http import smart_fetch

    async def get(u: str, warm: str = HOME):
        try:
            st, body = await smart_fetch(u, warm=warm, timeout=25)
            return st, body or ""
        except Exception as e:                                    # noqa: BLE001
            print(f"  تعذّر {u[-48:]} — {type(e).__name__}")
            return 0, ""

    cands = list(ARG)
    if not cands:
        st, home = await get(HOME)
        print(f"═ صفحةُ «أرقام» ═ HTTP {st} · {len(home)} حرفاً")
        if st != 200 or not home:
            print("  لا تُقرأ الصفحةُ — لا يُبنى على فراغ.")
            return 1
        seen: dict[str, str] = {}
        for m in re.finditer(r"""<a\b[^>]*href=["']([^"']+)["'][^>]*>(.*?)</a>""",
                             home, re.S | re.I):
            href, label = m.group(1), _txt(m.group(2))
            blob = f"{href} {label}".lower()
            if any(w.lower() in blob for w in WORDS) and "/ar/" in href:
                if href not in seen:
                    seen[href] = label
        print(f"  روابطُ الدليل المرشَّحة: {len(seen)}")
        for h, l in list(seen.items())[:20]:
            print(f"   «{l[:40]}» → {h[:78]}")
        cands = [("https://www.argaam.com" + h if h.startswith("/") else h)
                 for h in seen if any(k in h.lower() for k in
                                      ("compan", "prices", "market"))][:4]

    for u in cands:
        st, body = await get(u)
        print(f"\n──── {u[-64:]} ──── HTTP {st} · {len(body)} حرفاً")
        if st != 200 or not body:
            continue
        rows = _TR.findall(body)
        syms: list[str] = []
        first: list[list[str]] = []
        for tr in rows:
            cells = [_txt(c) for c in _TD.findall(tr)]
            if not cells:
                continue
            m = next((_SYM.search(c) for c in cells if _SYM.search(c)), None)
            if m:
                syms.append(m.group(1))
                if len(first) < 6:
                    first.append(cells[:6])
        tasi = [s for s in syms if not s.startswith("9")]
        nomu = [s for s in syms if s.startswith("9")]
        # خيارا السوق: مسارٌ أو معامِلٌ يذكر تاسي/نمو
        opts = sorted({m.group(0) for m in re.finditer(
            r"""(?:href|value)=["'][^"']*(?:tasi|nomu|main|parallel|market[Ii]d=\d+)[^"']*["']""",
            body, re.I)})
        print(f"  صفوفٌ={len(rows)} · رموزٌ={len(syms)}"
              f" · **تاسي={len(tasi)} · نمو={len(nomu)}**"
              f" · خياراتُ سوقٍ في الصفحة={len(opts)}")
        for o in opts[:8]:
            print(f"    خيار: {o[:88]}")
        for c in first:
            print(f"    صفٌّ: {c}")
        if tasi:
            print(f"    أوّلُ عشرةٍ بترتيب الصفحة: {tasi[:10]}")
            try:
                from app.data.market_universe import MARKET_UNIVERSE
                from app.data.universe import main_market
                ours = set(main_market(MARKET_UNIVERSE).keys())
                miss = [s for s in tasi if s not in ours]
                extra = [s for s in ours if s not in set(tasi)]
                print(f"    مقابلَ دليلنا ({len(ours)}): عندهم وليس عندنا"
                      f"={len(miss)}{' · ' + ' '.join(miss[:10]) if miss else ''}"
                      f" · عندنا وليس عندهم={len(extra)}"
                      f"{' · ' + ' '.join(extra[:10]) if extra else ''}")
            except Exception:                                     # noqa: BLE001
                pass

    print("\nالحكم: الصفحةُ التي تردّ رموزَ تاسي كاملةً بترتيبها هي الدليلُ"
          " المطلوب — ويُنقَل منها **الترتيبُ والقسمةُ** إلى وحدة المزامنة،"
          " ورموزُ ‎9xxx تُستثنى بأمر المالك. وفرقُ العدد عن دليلنا يُطبَع"
          " بأسمائه لا بعدده: وافدٌ جديدٌ يُضاف، ومفقودٌ يُفحَص قبل حذفه —"
          " فالدليلُ هويّةُ السوق ولا يُغيَّر على مصدرٍ واحدٍ بلا مراجعة.")
    return 0


raise SystemExit(asyncio.run(main()))
