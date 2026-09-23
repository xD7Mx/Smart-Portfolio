#!/usr/bin/env python3
"""من أين يُقرأ تاريخُ «تاسي» — اكتشافُ خدمات الصفحة لا تخمينُ مسار (D438).

    docker exec sp_backend python /app/scripts/audit/tasi_history_door.py

رسمُ «منحنى مؤشّر تاسي» فارغٌ دائماً: «لا يتوفّر تاريخٌ لهذا المؤشّر». ومكتوبٌ
في `market_data.get_history` أنّ ياهو لا يملك لـ`^TASI.SR` إلا يوماً واحداً
في كلّ نطاق — قيدٌ دائمٌ لا حصّة. فالتاريخُ يُطلب من المصدر الرسميّ.

وقاعدةُ `docs/FETCH_METHOD.md` (§٢): لا يُحفظ مسارٌ في الشيفرة، بل تُقرأ
أسماءُ الخدمات من الصفحة نفسِها. فتُفتح صفحاتُ المؤشّر في «تداول» بانتحال
البصمة، وتُطبع كلُّ أسماء الخدمات (`=NJ…=`) ومساراتُ JSON المذكورة فيها
ممّا يوحي بتاريخٍ أو رسم. قارئٌ فقط.
"""
from __future__ import annotations

import asyncio
import re
import sys

sys.path.insert(0, "/app")

PAGES = (
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/home",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch/indices-performance",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/main-market-watch/main-market-indices",
)
_EP = re.compile(r"=NJ([A-Za-z]{4,60})=/")
_JS = re.compile(r"[\"']([^\"'\s]{6,200}(?:chart|Chart|history|History|graph|Graph|intraday|Intraday)[^\"'\s]{0,120})[\"']")


async def main() -> int:
    try:
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
        return 0
    for url in PAGES:
        try:
            st, body = await fetch(url)
        except Exception as e:                                    # noqa: BLE001
            print(f"✘ {url[-60:]} — {type(e).__name__}")
            continue
        names = sorted(set(_EP.findall(body or "")))
        hints = sorted(set(_JS.findall(body or "")))[:25]
        print(f"═ {url[-60:]} — HTTP {st} · {len(body or '')} حرفاً")
        print(f"   خدمات: {names}")
        for h in hints:
            print(f"   ↳ {h}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
