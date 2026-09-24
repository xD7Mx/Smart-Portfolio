#!/usr/bin/env python3
"""هل تنشر مصادرُنا «قيمةً عادلة» أو سعراً مستهدفاً؟ — «تداول» و«أرقام» كما هما. قارئٌ فقط.

    docker exec sp_backend python /app/scripts/audit/fair_value_sources.py

سأل المالك: «لم نتأكّد من مصادرنا الكلّية إن كانت توفّر قيمةً عادلةً من
تداول أو أرقام». فتُفتح الصفحاتُ العامّة (لا المدفوعة — تجاوزُ اشتراك
«أرقام» مرفوضٌ بقرار المالك) ويُبحث فيها عن كلّ صيغةٍ للقيمة العادلة أو
السعر المستهدف، ويُطبع السياقُ حولها، وحالةُ كلّ صفحة، وصفوفُ التوصيات.
"""
import asyncio, re, sys
sys.path.insert(0, "/app")
KEYS = re.compile(r"القيمة العادلة|السعر العادل|السعر المستهدف|سعر مستهدف|القيمة المستهدفة|"
                  r"fair\s*value|target\s*price|price\s*target|FairValue|TargetPrice", re.I)


def ctx(body, n=4):
    out = []
    for m in KEYS.finditer(body or ""):
        s = re.sub(r"<[^>]+>|\s+", " ", body[max(0, m.start() - 160):m.end() + 200])
        out.append(s.strip()[:330])
        if len(out) >= n:
            break
    return out


async def main():
    try:
        import httpx
        from app.services import tadawul_ownership as O
        from app.services.argaam_ids import url_for
        from app.services.argaam_calendar import fetch_company_recommendations, UA
    except ModuleNotFoundError as e:
        print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); return 0
    for sym in ("2222", "2080", "4030"):
        print(f"\n═══ {sym} ═══")
        body = await O.company_page(sym) or ""
        hits = ctx(body)
        print(f"«تداول» صفحةُ الشركة: {len(body)} حرفاً · ذكرٌ للقيمة العادلة/المستهدف: {len(list(KEYS.finditer(body)))}")
        for h in hits:
            print("   ↳", h)
        u = url_for(sym)
        print(f"«أرقام» رابطُ الشركة: {u}")
        if u:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                         headers={"User-Agent": UA, "Accept-Language": "ar"}) as c:
                for path in ("", "/financial-ratios", "/analysts-estimates"):
                    try:
                        r = await c.get(u + path if path else u)
                        print(f"   صفحة{path or ' النظرة العامة'}: HTTP {r.status_code} · {len(r.text)} · ذكر={len(list(KEYS.finditer(r.text)))}")
                        for h in ctx(r.text, 3):
                            print("      ↳", h)
                    except Exception as e:                        # noqa: BLE001
                        print(f"   صفحة{path}: {type(e).__name__}")
        rec = await fetch_company_recommendations(sym)
        rows = rec.get("rows") or []
        print(f"«أرقام» توصياتُ المحلّلين: {len(rows)} صفّاً · {rec.get('url')}")
        for r in rows[:6]:
            print("   ", {k: r.get(k) for k in ("house", "verdict", "target", "date")})
    return 0

sys.exit(asyncio.run(main()))
