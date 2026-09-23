#!/usr/bin/env python3
"""ما الذي بثّته «تداول» في عطلةٍ حقيقية (D426).

    docker exec sp_backend python /app/scripts/audit/status_codes_seen.py

كشفُ العطلة يقوم على ثلاث طبقات: معجمُ رموزِ «تداول» (فارغٌ عمداً حتى
يثبت)، ثمّ شاهدُ التغذيةِ المتجمّدة، ثمّ الساعة. وحكمُ العطلة الأوّل كان
**صحيحاً بالمصادفة** على دليلٍ باطل (‏D416: فرقُ ‎180 دقيقةً كان فرقَ
التوقيت لا تأخّرَ التغذية). فلم يُثبَت الكشفُ على عطلةٍ حقيقيةٍ قطّ.

واليومُ الوطنيُّ (‏23 سبتمبر) عطلةٌ حقيقيةٌ للسوق. وكلُّ سؤالٍ عن الحالة
يُسجّل رمزَ «تداول» وطورَ الساعة وزمنَ التغذية في سجلٍّ مستقلّ. فيُقرأ
هنا **ما بُثّ فعلاً** يومَ العطلة مقابل يومِ تداولٍ عاديّ، لكلّ طورٍ من
أطوار الساعة — فيُعرف أيُّ رمزٍ يعني العطلة، وهل تجمّدت التغذيةُ داخل
ساعات الجلسة كما يفترض الشاهدُ الثاني. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import collections
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")


async def main() -> int:
    try:
        from app.services import market_state as MS
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0

    path = MS._OBS
    if not os.path.isfile(path):
        print(f"⚠ لا سجلَّ مشاهداتٍ في {path} — لم يُقَس")
    else:
        by_day: dict[str, dict[str, collections.Counter]] = {}
        feeds: dict[str, set] = collections.defaultdict(set)
        n = 0
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:                                 # noqa: BLE001
                    continue
                n += 1
                day = str(r.get("at") or "")[:10]
                ph = str(r.get("clock_phase") or "?")
                by_day.setdefault(day, {}).setdefault(
                    ph, collections.Counter())[str(r.get("code"))] += 1
                if ph in ("pre", "open", "preclose"):
                    feeds[day].add(str(r.get("feed_at")))
        print(f"مشاهداتٌ في السجلّ: {n} · أيّامٌ: {len(by_day)}\n")
        for day in sorted(by_day)[-8:]:
            print(f"═ {day} ═")
            for ph, cnt in sorted(by_day[day].items()):
                print(f"   {ph:10s} رموزٌ: {dict(cnt)}")
            fs = sorted(x for x in feeds.get(day, ()) if x and x != "None")
            if fs:
                print(f"   زمنُ التغذية داخل الجلسة: {len(fs)} قيمةً مختلفة"
                      f" · من {fs[0]} إلى {fs[-1]}")

    print("\n═ حكمُ الحالة الآن ═")
    s = await MS.market_state()
    print(json.dumps(s, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
