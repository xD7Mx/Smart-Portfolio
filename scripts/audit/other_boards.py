#!/usr/bin/env python3
"""بابُ الأسواق الأخرى: «نمو» والصناديق — يُكتشَف لا يُخمَّن (D356).

    docker exec sp_backend python /app/scripts/audit/other_boards.py

قِيس بالمسح الشامل على خادم المالك: ‎136 ورقةً من ‎409 **لم تُسأل أصلاً**
لأن لقطتَنا تُقرأ من جدول مراقبة **السوق الرئيسيّ** وحدَه، فلا رابطَ
لصفحات هذه الأوراق عندنا. وكلُّها رموزُ ‎9000+ — السوقُ الموازي وصناديقُ
المؤشرات. وثلاثُ عقباتٍ في جدول العقبات أصلُها هذا البابُ الواحد:
الصناديقُ الغائبةُ عن اللقطة · و«نمو» · وبابُ الصناديق المفقود.

## كيف يُكتشَف — بطريقة الجلب المسجَّلة لا بعنوانٍ مثبَّت

  ١· تُقرأ صفحةُ مراقبة السوق الرئيسيّ، وتُطبع **كلُّ** نداءاتها
     (`=NJ…=/`) — فخدمتُنا اسمُها `getMainNomucMarketDetails`، وفي
     اسمها لفظُ «نمو» نفسُه، فقد يكون البابُ هو هو بمعاملٍ آخر.
  ٢· وتُستخرَج من الصفحة **روابطُ الصفحات الشقيقة** (‏`ourmarkets/…`)
     كما وردت في الموقع — لا تُخمَّن أسماؤها.
  ٣· ثمّ تُجرَّب كلُّ خدمةٍ في كلّ صفحةٍ بمعاملات جدولِنا نفسِها،
     ويُطبع لكلّ محاولةٍ: الحالةُ · حجمُ الجواب · عددُ الصفوف · وكم
     رمزاً من الـ‎136 المفقودة ظهر فيها.

والحكمُ بالمقياس الأخير وحدَه: بابٌ لا يُخرج رموزَ ‎9000+ ليس البابَ
المطلوبَ ولو أجاب ‎200. وما لم يُوجَد يُقال إنه ليس عندنا.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

_NJ = re.compile(r"p0/[A-Za-z0-9_=]*=NJ([A-Za-z]+)=/")
_HREF = re.compile(r"href=[\"']([^\"']*ourmarkets/[^\"']*)[\"']", re.I)
_SYM = re.compile(r"\b(9[0-9]{3})\b")
PARAMS = {"sectorParameter": "All", "iswatchListSelected": "NO",
          "requestLocale": "en"}


async def _try(base: str, svc_path: str, referer: str, want: set[str]) -> str:
    """محاولةُ بابٍ واحد — تُعاد سطرَ نتيجةٍ مقروءاً."""
    from app.services.tadawul_http import fetch
    url = base.rstrip("/") + "/" + svc_path
    try:
        st, body = await fetch(url, params=PARAMS, referer=referer)
    except Exception as e:                                        # noqa: BLE001
        return f"تعذّر: {type(e).__name__}"
    if st != 200 or not body:
        return f"HTTP {st}"
    rows = None
    try:
        data = json.loads(body)
        rows = data.get("data") if isinstance(data, dict) else data
    except Exception:                                             # noqa: BLE001
        pass
    hits = sorted(set(_SYM.findall(body)) & want)
    n = len(rows) if isinstance(rows, list) else "—"
    return (f"HTTP 200 · {len(body)} حرفاً · صفوفٌ={n} · "
            f"**من المفقودة: {len(hits)}**"
            + (f" ({' · '.join(hits[:10])})" if hits else ""))


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE as U
    from app.data.universe import main_market
    from app.services import tadawul_market as tm
    from app.services.tadawul_http import fetch

    want = {str(s) for s in U} - set(main_market(U))
    print(f"═ بابُ الأسواق الأخرى ═ المفقودُ من اللقطة: {len(want)} ورقةً"
          f" · أمثلةٌ: {' · '.join(sorted(want)[:8])}")

    # والكاشفُ يُبلّغ ولا ينفجر: مصدرٌ لا يُوصَل إليه حالةٌ تُقال (D350)
    try:
        st, body = await fetch(tm.PAGE)
    except Exception as e:                                        # noqa: BLE001
        st, body = 0, ""
        print(f"\n═ صفحةُ مراقبة السوق: تعذّر الوصول — {type(e).__name__}")
    print(f"\n═ صفحةُ مراقبة السوق الرئيسيّ: HTTP {st} · {len(body or '')} حرفاً")
    if st != 200 or not body:
        print("  تعذّر — لا يُكتشَف بابٌ من صفحةٍ لم تُقرأ.")
        return 1
    base_m = tm._BASE_RE.search(body)
    base = base_m.group(1) if base_m else None
    svcs = sorted({m.group(0) for m in _NJ.finditer(body)})
    names = sorted({m.group(1) for m in _NJ.finditer(body)})
    print(f"  أساسُ الصفحة: {'موجود' if base else 'غائب'}"
          f" · نداءاتٌ: {len(svcs)}")
    for n in names:
        print(f"      ⟨{n}⟩")

    # ── ١· خدمتُنا نفسُها بمعاملاتٍ أخرى ─────────────────────────────────
    if base and svcs:
        print("\n═ ١· نداءاتُ الصفحة الرئيسية بمعاملات جدولِنا ═")
        for sp in svcs:
            nm = _NJ.search(sp).group(1)
            print(f"  ⟨{nm}⟩ → {await _try(base, sp, tm.PAGE, want)}")

    # ── ٢· الصفحاتُ الشقيقةُ كما وردت في الموقع ─────────────────────────
    links = sorted({h for h in _HREF.findall(body)})
    print(f"\n═ ٢· صفحاتٌ شقيقةٌ وُجدت في الصفحة: {len(links)} ═")
    for h in links[:24]:
        print(f"      {h[-96:]}")

    seen: set[str] = set()
    for h in links:
        url = h if h.startswith("http") else ("https://www.saudiexchange.sa"
                                              + (h if h.startswith("/") else "/" + h))
        key = url.rstrip("/").split("/")[-1].lower()
        if key in seen or "watch" not in key and "market" not in key:
            continue
        seen.add(key)
        try:
            st2, b2 = await fetch(url)
        except Exception as e:                                    # noqa: BLE001
            print(f"\n  ── {key}: تعذّر — {type(e).__name__}")
            continue
        if st2 != 200 or not b2:
            print(f"\n  ── {key}: HTTP {st2}")
            continue
        bm = tm._BASE_RE.search(b2)
        sv = sorted({m.group(0) for m in _NJ.finditer(b2)})
        hits_page = sorted(set(_SYM.findall(b2)) & want)
        print(f"\n  ── {key}: HTTP 200 · {len(b2)} حرفاً · نداءاتٌ={len(sv)}"
              f" · رموزُ 9000 في الصفحة نفسِها: {len(hits_page)}")
        if not (bm and sv):
            continue
        for sp in sv[:6]:
            nm = _NJ.search(sp).group(1)
            print(f"      ⟨{nm}⟩ → {await _try(bm.group(1), sp, url, want)}")

    print("\nالحكم: البابُ المطلوبُ هو الذي يُخرج **رموزَ 9000+** — لا الذي"
          " يُخرج أكثرَ صفوف. فإن ظهر بابٌ كهذا وُصِل باللقطة بمعاملاته"
          " كما اكتُشفت، وإن لم يظهر قيل إن هذه الأسواقَ ليست عندنا ولا"
          " يُختلَق لها صفّ.")
    return 0


raise SystemExit(asyncio.run(main()))
