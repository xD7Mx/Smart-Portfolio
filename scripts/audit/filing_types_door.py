#!/usr/bin/env python3
"""أيَّ صنفٍ من القوائم نسأل تداولَ عنه — وأيَّها نترك (‏D407؟).

    python3 scripts/audit/filing_types_door.py              # عيّنةٌ ممتدّة
    python3 scripts/audit/filing_types_door.py 1120 2010 8010

يُشغَّل **على خادم المالك** حيث الطريقُ إلى تداولَ مفتوح.

## الفرضيّةُ التي يقيسها — ولا يُسلَّم بها

`filings_for_ex` تنادي خدمةَ `statementsTabData` بمُعاملَين **ثابتَين**:
`statementType=6` و`reportType=1`. فنحن نسأل عن صنفٍ واحدٍ ولا نسأل عن
غيره. وقِيس على الخادم أمران قد يكونان أثرَ ذلك:

  · **٢٤ ورقةً** تردّ «القائمةُ تُجيب ولا ملفَّ XBRL فيها» — وقد تكون
    ملفّاتُها تحت صنفٍ لا نسأل عنه، فالبابُ مغلقٌ من عندنا لا من المصدر.
  · **٢٦٨ من ٢٧٠** أرقامُها شائخة، ووسيطُ عمر القوائم ‎٨٤ يوماً — وإن
    كان `reportType=1` هو **السنويّ**، فنحن نقرأ السنويّاتِ ونترك
    الربعيّاتِ الأحدثَ حيث هي. وذاك عجزُ بناءٍ لا نقصُ إفصاح.

ولا يُصلَح شيءٌ قبل القياس: يُسأل المصدرُ عن كلّ تركيبةٍ ويُطبع ما
تردّه — عددُ الملفّات وأحدثُ تاريخ. فإن ردّت تركيبةٌ أخرى أحدثَ، فالعطبُ
مُثبَتٌ بعينه ويُفتح الباب. وإن لم تردّ، فالمصدرُ لا ينشر وتُقال الحقيقة.
"""
from __future__ import annotations

import asyncio
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

# التركيباتُ المسؤولُ عنها: ما نسأله اليوم أوّلاً، ثمّ ما نتركه.
COMBOS = [(st, rt) for st in ("6", "1", "2", "3", "4", "5")
          for rt in ("1", "2", "3")]


async def _probe(symbol: str) -> dict:
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    import importlib
    _X = importlib.import_module("app.services.tadawul_xbrl")
    ORIGIN = _X.ORIGIN
    url = (row_for(symbol) or {}).get("company_url")
    if not url:
        return {"رمز": symbol, "خطأ": "لا رابطَ في اللقطة"}
    full = ORIGIN + url if url.startswith("/") else url
    status, page = await fetch(full)
    if status != 200 or not page:
        return {"رمز": symbol, "خطأ": f"صفحةُ الشركة HTTP {status}"}
    mb = _X._BASE.search(page)
    ep = next((m.group(0) for m in _X._NJ.finditer(page)
               if m.group(1) == "statementsTabData"), None)
    if not mb or not ep:
        return {"رمز": symbol, "خطأ": "لا خدمةَ في الصفحة"}
    base = mb.group(1).rstrip("/") + "/" + ep
    found: dict[str, str] = {}
    for st, rt in COMBOS:
        st_, body = await fetch(base, params={"statementType": st,
                                              "reportType": rt,
                                              "requestLocale": "en"},
                                referer=full)
        if st_ != 200 or not body:
            continue
        dates = []
        for href in re.findall(r"href=[\"']([^\"']+)[\"']", body):
            if "XBRL_DOCS" not in href or not href.endswith(".html"):
                continue
            d = re.search(r"_(\d{4}-\d{2}-\d{2})_", href)
            if d:
                dates.append(d.group(1))
        if dates:
            found[f"{st}/{rt}"] = f"{len(dates)} ملفّاً · أحدثُ {max(dates)}"
        await asyncio.sleep(0.4)
    return {"رمز": symbol, "التركيبات": found}


async def main() -> int:
    args = [a for a in sys.argv[1:] if a.isdigit()]
    from app.services.tadawul_market import refresh as _mrefresh
    await _mrefresh()
    if args:
        syms = args
    else:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        _all = sorted(main_market(MARKET_UNIVERSE).keys())
        syms = _all[::max(1, len(_all) // 10)][:10]
    print(f"عيّنةٌ: {' '.join(syms)}\n")
    worst = 0
    for s in syms:
        r = await _probe(s)
        if r.get("خطأ"):
            print(f"  {s}: ⚠ {r['خطأ']}")
            continue
        f = r["التركيبات"]
        if not f:
            print(f"  {s}: لا ملفَّ في أيّ تركيبةٍ من {len(COMBOS)}")
            continue
        _ours = f.get("6/1")
        _best = max(f.values(), key=lambda v: v.split("أحدثُ ")[-1])
        _flag = "  ← تركيبةٌ أحدثُ مما نسأل" if (
            _ours is None or _best.split("أحدثُ ")[-1]
            > _ours.split("أحدثُ ")[-1]) else ""
        worst += 1 if _flag else 0
        print(f"  {s}:{_flag}")
        for k, v in sorted(f.items()):
            print(f"      {'▸' if k == '6/1' else ' '} {k:5s} {v}"
                  + ("   ← ما نسأله اليوم" if k == "6/1" else ""))
    print(f"\nأوراقٌ لها مصدرٌ أحدثُ مما نسأل عنه: {worst} من {len(syms)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        sys.exit(0)
