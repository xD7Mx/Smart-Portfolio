#!/usr/bin/env python3
"""تقويمُ التوزيعات الرسميّ في «تداول» ومعاملاتُ getCorporateAction (D444). قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/dividend_calendar_door.py

كشف `dividend_door.py`: صفحةُ الشركة تحمل `getCorporateAction` ويعود فارغاً
بلا معاملات، وفيها رابطُ «issuer-financial-calendars/dividends». فتُطبع
المعاملاتُ التي تمرّرها صفحةُ الشركة لهذه الخدمة، وخدماتُ صفحة التقويم.
"""
import asyncio, re, sys
sys.path.insert(0, "/app")
CAL = "https://www.saudiexchange.sa/wps/portal/saudiexchange/newsandreports/issuer-financial-calendars/dividends?locale=en"


async def main():
    try:
        from app.services import tadawul_ownership as O
        from app.services.tadawul_http import fetch
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    body = await O.company_page("4030") or ""
    for m in re.finditer(r"getCorporateAction", body):
        print("↳ استعمال:", re.sub(r"\s+", " ", body[max(0, m.start()-300):m.end()+500])[:800])
    st, cal = await fetch(CAL)
    names = sorted(set(O._EP_RE.findall(cal or "")))
    print(f"═ تقويم التوزيعات — HTTP {st} · {len(cal or '')} حرفاً · خدمات: {names}")
    mb = O._BASE_RE.search(cal or "")
    base = mb.group(1).rstrip("/") if mb else ""
    for n in names:
        if not re.search(r"ivid|ction|alend|vent", n, re.I):
            continue
        ep = next(m.group(0) for m in O._EP_RE.finditer(cal) if m.group(1) == n)
        for m in re.finditer(n, cal):
            print(f"   ↳ {n} في الصفحة:", re.sub(r"\s+", " ", cal[max(0, m.start()-200):m.end()+400])[:600])
            break
        s2, raw = await fetch(f"{base}/{ep}", params={"requestLocale": "en"}, referer=base)
        print(f"   ✦ {n} — HTTP {s2} · {len(raw or '')} · {(raw or '')[:500]!r}")
    return 0

sys.exit(asyncio.run(main()))
