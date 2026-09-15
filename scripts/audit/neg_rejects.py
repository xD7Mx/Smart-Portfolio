#!/usr/bin/env python3
"""الاثنتان والعشرون المتروكة — تُعرَض بحرفها لا تُوصَف (D321).

    docker exec sp_backend python /app/scripts/audit/neg_rejects.py

قِيس: `main:144/166` و«بلا رمز:22». و«بلا رمز» حكمُ قارئنا لا وصفُ
الصفّ: فإمّا صفوفُ مجاميعَ ليست صفقاتٍ (فالتركُ صواب)، وإمّا الرمزُ فيها
باسمِ حقلٍ لم نطابقه (فالتركُ عطبٌ يحذف صفقاتٍ حقيقية). ولا يُحكم بينهما
إلا بعرضِ الصفوف نفسِها — وهو ما يفعله هذا القياس: يُنادى المصدرُ بنفس
خطّة الخدمة، ثمّ يُطبع كلُّ صفٍّ يرفضه `normalize` كاملاً بمفاتيحه.
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from collections import Counter

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")


async def main() -> int:
    from app.services import special_deals as sd
    from app.services.tadawul_http import smart_flow

    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    from datetime import date, timedelta
    to_d = date.today()
    from_d = to_d - timedelta(days=max(1, days))
    params = {"sector": "All", "company": "All",
              "fromDate": from_d.strftime("%d-%m-%Y"),
              "toDate": to_d.strftime("%d-%m-%Y"), "requestLocale": "ar"}

    page_url = sd.NEG_PAGE.format(market="main")

    def plan():
        status, page = yield {"url": page_url}
        mb = sd._BASE_RE.search(page or "")
        me = sd._NEG_EP.search(page or "")
        if not (mb and me):
            return None, f"لا خدمة (HTTP {status})"
        url = mb.group(1).rstrip("/") + "/" + me.group(0)
        status, body = yield {"url": url, "params": params, "referer": page_url}
        return body, f"HTTP {status}"

    body, note = await smart_flow(plan, warm=page_url)
    print(f"═ المصدر: {note} · {len(body or '')} حرفاً ═")
    if not body:
        return 1
    rows = (json.loads(body) or {}).get("data") or []
    print(f"  صفوفٌ وصلت: {len(rows)}")

    ok = sd.normalize(rows)
    print(f"  فُهم منها: {len(ok)}")

    bad = []
    for r in rows:
        if not isinstance(r, dict):
            bad.append({"—": repr(r)[:80]})
            continue
        raw = sd._pick(r, sd.FIELDS["symbol"])
        if not (raw and re.search(r"\d{4}", str(raw))):
            bad.append(r)
    print(f"\n═ المتروكةُ بلا رمز: {len(bad)} ═")
    for r in bad[:30]:
        print("   " + json.dumps(r, ensure_ascii=False)[:230])

    if bad:
        keys = Counter(k for r in bad for k in r)
        print("\n  مفاتيحُها: " + " · ".join(f"{k}:{n}" for k, n in
                                             keys.most_common(20)))
        # أيُّ حقلٍ فيها يحمل أربعةَ أرقامٍ متتالية؟ هذا هو الرمزُ إن وُجد.
        cand = Counter(k for r in bad for k, v in r.items()
                       if re.fullmatch(r"\s*\d{4}\s*", str(v or "")))
        print("  حقولٌ تحمل رمزاً رباعياً: "
              + (" · ".join(f"{k}:{n}" for k, n in cand.most_common(10))
                 or "لا شيء — فليست صفقاتٍ برمز"))
    print()
    if not bad:
        print("الحكم: لا صفَّ متروكاً — العددان متساويان.")
    else:
        print("الحكم: اقرأ الصفوفَ أعلاه. إن حملت حقلاً برمزٍ رباعيٍّ فهو"
              " نقصٌ في مرشّحاتنا يُضاف اسمُه. وإلا فهي ليست صفقاتٍ ويبقى"
              " تركُها صواباً — ويُقال عددُها لا يُخفى.")
    return 0


raise SystemExit(asyncio.run(main()))
