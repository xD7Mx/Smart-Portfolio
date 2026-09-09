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


# ══ لا نداءَ لياهو من مسبار ══ (تصحيحٌ بعد أوّل تشغيل)
# كان يسأل `get_company_info` لكلّ رمز، فارتدّ ‎429 على الخادم: مسبارُ
# اكتشافٍ يحرق حصّةَ المزوّد ليقول ما هو مخزَّنٌ عندنا أصلاً. فصار يقرأ
# المخزنَ الدائم والكاش وحدَهما.
_FUND: dict | None = None


def _store() -> dict:
    global _FUND
    if _FUND is None:
        try:
            from app.services.content_engine import fund_store_load
            _FUND = fund_store_load() or {}
        except Exception:                                         # noqa: BLE001
            _FUND = {}
    return _FUND


async def yahoo_target(sym: str):
    base = sym.replace(".SR", "")
    row = _store().get(base) or {}
    t = row.get("target_mean_price")
    if t is None:
        try:
            from app.services import cache
            t = ((cache.get(f"fund:yahoo:{base}.SR") or {}) or {}).get("target_mean_price")
        except Exception:                                         # noqa: BLE001
            t = None
    return t, row.get("number_of_analysts")


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
        from app.services.argaam_calendar import _company_id, _company_url, UA, BASE as BASE_AR
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
    # ══ الصفحةُ تحمل الرابطَ لا الرقم ══ (قِيس في أوّل تشغيل)
    # ظهر في ستٍّ من اثنتي عشرة رابطٌ إلى صفحةٍ مخصّصة:
    #   .../analystestimates/analystrecomendationsestimate/3/<id>/4
    # فيُتبَع الرابطُ ويُقرأ ما فيه — الرابطُ وحدَه ليس رقماً.
    m = re.search(r'href="([^"]*analystrecomendationsestimate[^"]*)"', r.text, re.I)
    if not m:
        return "‎200 · لا صفحةَ تقديراتٍ في هذه الشركة"
    href = m.group(1)
    est_url = href if href.startswith("http") else BASE_AR.rstrip("/") + "/" + href.lstrip("/")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                     headers={"User-Agent": UA,
                                              "Accept-Language": "ar,en;q=0.8"}) as c:
            e = await c.get(est_url)
    except Exception as ex:                                       # noqa: BLE001
        return f"صفحةُ التقديرات تعذّرت ({type(ex).__name__}) · {est_url}"
    if e.status_code != 200:
        return f"صفحةُ التقديرات ‎{e.status_code} · {est_url}"
    text = re.sub(r"<[^>]+>", " ", e.text)
    text = re.sub(r"\s+", " ", text)
    hit = _AR_TARGET.search(text)
    if not hit:
        return f"‎200 بلا لفظِ هدفٍ · {est_url}"
    i = hit.start()
    around = text[max(0, i - 60): i + 220].strip()
    nums = re.findall(r"\d+\.\d{1,2}", around)
    return (f"«{hit.group(1)}» · أرقامٌ حولها: {nums[:6] or '—'} · {est_url}")


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    # ══ قيمةُ الخيار ليست رمزاً ══ (قِيس في تشغيل المالك)
    # كان `--limit 30` يترك «30» في القائمة الوضعية فيُسأل عنه كأنه سهم،
    # ولا يُشغَّل مسارُ «ما لا يغطّيه ياهو» أصلاً. فتُحذف قيمةُ الخيار معه.
    argv = list(sys.argv[1:])
    limit = 12
    if "--limit" in argv:
        i = argv.index("--limit")
        if i + 1 >= len(argv) or not argv[i + 1].lstrip("-").isdigit():
            print("… `--limit` بلا عددٍ صحيح.")
            return 2
        limit = int(argv[i + 1])
        del argv[i:i + 2]
    args = [a for a in argv if not a.startswith("--")]
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
