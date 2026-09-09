#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# عائدُ الصكوك الحكومية من «تداول» — **مسبارُ وصولٍ لا خدمة**.
#
# دلّ المالكُ على صفحة «مراقبة سوق الصكوك». وكانت تجربتي السابقة على
# مسارٍ آخر وبترويسةٍ ناقصة، فردّت خطأً — وذلك ليس حكماً على الصفحة.
# فيُجرَّب **الرابطُ بعينه** بترويسةِ متصفّحٍ كاملة، ويُقال ما ردّ.
#
#   docker exec sp_backend python /app/scripts/audit/rf_sukuk.py
#
# لا يعتمد رقماً ولا يكتب في ملفّ المعايير: يطبع ما وصل. وإن كانت الصفحةُ
# تُملأ بجافاسكربت قيل ذلك — ولا يُلتَفّ عليه بتقديرٍ مكانه.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
import sys
import urllib.request

URLS = [
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/sukuk-market-watch?locale=ar",
    "https://www.saudiexchange.sa/wps/portal/saudiexchange/ourmarkets/sukuk-market-watch?locale=en",
]
# ترويسةُ متصفّحٍ كاملة: كثيرٌ من المواقع يردّ ‎403 لعميلٍ بلا `Accept`
# و`Accept-Language` — والفرقُ بين «محجوب» و«لم أُحسِن السؤال» جوهريّ.
HDRS = {
    "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ar,en-US;q=0.8,en;q=0.6",
    "Connection": "close",
}


def main() -> int:
    for url in URLS:
        print(f"\n■ {url}")
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=45) as r:
                body = r.read().decode("utf-8", "replace")
                code = r.status
        except Exception as e:                                    # noqa: BLE001
            print(f"   ✖ {type(e).__name__}: {e}")
            continue
        flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
        pct = re.findall(r"\d{1,2}[.,]\d{1,3}\s*%", flat)[:10]
        # أسماءُ الصكوك الحكومية تحمل سنةَ الاستحقاق — بها يُعرف الأجل.
        mats = sorted(set(re.findall(r"20(?:3[0-9]|4[0-9])", flat)))[:12]
        rows = len(re.findall(r"<tr", body, re.I))
        js = bool(re.search(r"__NEXT_DATA__|/api/|ajax|angular", body, re.I))
        print(f"   ‎{code} · حجم {len(body)} · صفوف <tr> {rows}")
        print(f"   نِسَبٌ ظاهرة: {pct or '—'}")
        print(f"   سنواتُ استحقاقٍ ظاهرة: {mats or '—'}")
        if rows == 0 and js:
            print("   ⚠ لا جدولَ في الترميز — الصفحةُ تُملأ بجافاسكربت.")
    print("\n" + "─" * 70)
    print("المطلوب: عائدُ صكٍّ حكوميٍّ بالريال استحقاقُه قريبٌ من عشر سنوات.")
    print("ولا يُؤخذ سايبور ولا أجلٌ قصيرٌ مكانه — التقييمُ يخصم تدفّقاتٍ طويلة.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
