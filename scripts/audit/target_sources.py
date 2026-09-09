#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# مرجعٌ ثانٍ لأهداف المحلّلين — **مسبارُ اكتشافٍ لا اعتماد**.
#
# ياهو يصل ‎149 من ‎273، فيبقى ‎124 بلا هدف. والسؤال: أيُّ مصدرٍ عندنا
# يغطّي هذا النقص؟ ولا يُجاب بالوعد: يُشغَّل هذا على الخادم فيسأل المصادرَ
# المتاحةَ عن رموزٍ **يعرف يقيناً أن ياهو لا يغطّيها**، ويطبع ما وجد.
#
#   docker exec sp_backend python /app/scripts/audit/target_sources.py
#   docker exec sp_backend python /app/scripts/audit/target_sources.py --limit 40
#   docker exec sp_backend python /app/scripts/audit/target_sources.py 4340 8230
#
# لا يكتب شيئاً ولا يغيّر إعداداً — يقرأ ويطبع. وما لم يُقَس لا يُدَّعى:
# إن ردّ مصدرٌ ‎403 أو ‎404 قيل ذلك بنصّه، ولا يُفسَّر بأنه «لا يملك الرقم».
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import re
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ألفاظُ الهدف في صفحات «أرقام» — تُطابَق على النصّ العربيّ كما يُكتب.
_AR_TARGET = re.compile(
    r"(السعر\s*المستهدف|متوسط\s*السعر\s*المستهدف|القيمة\s*العادلة|توصيات\s*المحللين)")


async def yahoo_target(sym: str):
    from app.services.market_data import market_service
    from app.api.v1.endpoints.holdings import yahoo_symbol
    info = await market_service.get_company_info(yahoo_symbol(sym)) or {}
    return info.get("target_mean_price"), info.get("number_of_analysts")


async def sahmak_probe(sym: str) -> str:
    """«سهمك» — تُجرَّب مساراتٌ محتملةٌ ويُطبع ردُّها كما هو.

    لا يُفترض شكلُ بيانات: إن عاد ‎200 فُتّش في مفاتيحه عن لفظِ هدفٍ أو
    توصية، وإن عاد ‎403/404 قيل ذلك — فالخطةُ قد لا تشمل المسار.
    """
    try:
        from app.services import sahmak_library as sl
    except Exception as e:                                        # noqa: BLE001
        return f"غير متاح ({type(e).__name__})"
    base = sym.replace(".SR", "")
    found = []
    for path in (f"/analysts/{base}/", f"/targets/{base}/",
                 f"/recommendations/{base}/", f"/company/{base}/"):
        try:
            data = await sl._get(path)
        except Exception as e:                                    # noqa: BLE001
            found.append(f"{path}: خطأ {type(e).__name__}")
            continue
        if not data:
            found.append(f"{path}: لا شيء")
            continue
        keys = list(data)[:12] if isinstance(data, dict) else type(data).__name__
        hit = any(k for k in (data if isinstance(data, dict) else {})
                  if re.search(r"target|analyst|recommend|fair", str(k), re.I))
        found.append(f"{path}: ‎200 · مفاتيح {keys}" + (" · فيه هدف!" if hit else ""))
    return " | ".join(found)


async def argaam_probe(sym: str) -> str:
    """«أرقام» — تُجلب صفحةُ الشركة ويُفتَّش نصُّها عن لفظ الهدف."""
    try:
        from app.services.argaam_calendar import _company_id, _company_url, UA
        import httpx
    except Exception as e:                                        # noqa: BLE001
        return f"غير متاح ({type(e).__name__})"
    cid = await _company_id(sym.replace(".SR", ""))
    if not cid:
        return "لا معرّفَ للشركة في أرقام"
    url = _company_url(cid)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            r = await c.get(url)
    except Exception as e:                                        # noqa: BLE001
        return f"تعذّر الجلب ({type(e).__name__})"
    if r.status_code != 200:
        return f"‎{r.status_code} من {url}"
    m = _AR_TARGET.search(r.text)
    if not m:
        return "‎200 · لا لفظَ هدفٍ في الصفحة"
    # مقتطفٌ حول الموضع ليُرى السياقُ بالعين قبل أيّ اعتماد.
    i = m.start()
    snippet = re.sub(r"<[^>]+>", " ", r.text[max(0, i - 120): i + 240])
    snippet = re.sub(r"\s+", " ", snippet).strip()[:200]
    return f"‎200 · «{m.group(1)}» ⇐ {snippet}"


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    limit = 12
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    uni = main_market(MARKET_UNIVERSE)

    if args:
        syms = [a.replace(".SR", "") for a in args]
    else:
        print("… أوّلاً: أيُّ الرموز لا يغطّيها ياهو؟ (يُقرأ من الكاش، بلا نداءٍ جديد)")
        syms = []
        for s in uni:
            t, _ = await yahoo_target(s)
            if not t:
                syms.append(s)
        print(f"    بلا هدفٍ من ياهو: {len(syms)} من {len(uni)}")
        syms = syms[:limit]

    print(f"\nيُسأل عن {len(syms)} رمزاً:\n" + "─" * 74)
    for s in syms:
        name = (uni.get(s) or {}).get("name_ar") or s
        t, n = await yahoo_target(s)
        print(f"\n■ {s} · {name}")
        print(f"   ياهو  : {t if t else '—'}" + (f" ({n} محلّلاً)" if n else ""))
        print(f"   سهمك  : {await sahmak_probe(s)}")
        print(f"   أرقام : {await argaam_probe(s)}")

    print("\n" + "─" * 74)
    print("هذا مسبارُ اكتشافٍ: يقول ماذا يردّ كلُّ مصدر، ولا يعتمد رقماً.")
    print("ولا يُبنى على مصدرٍ حتى تُقاس تغطيتُه وتُقارَن بأهداف ياهو حيث يجتمعان.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
