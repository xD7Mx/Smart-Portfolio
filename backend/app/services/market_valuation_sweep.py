"""درجةُ جودةٍ وسعرٌ عادلٌ **لكلّ ورقةٍ في السوق** — مخزَنٌ يقرؤه الفرز.

    from app.services.market_valuation_sweep import sweep
    await sweep()                  # السوقُ كلُّه من اللقطة
    await sweep(["1120", "2050"])  # أو رموزٌ بأعيانها

## لماذا

بأمر المالك: «جميعُ شركات السوق اجعل لها درجةً للجودة ودرجةً للسعر
العادل». وكان عمودُ «السعر العادل» في الفرز يُملأ من **هدفِ بيوت
الخبرة** (‏D386) — أي رقمٌ مستعارٌ باسمٍ ليس له، ويُفرغ الآن بعد أن
عاد الاسمُ لصاحبه. فالفراغُ لا يُقبَل والاستعارةُ لا تُقبَل: يبقى أن
**يُحسَب سعرُنا العادل لكلّ رمزٍ ويُخزَّن**.

## وكيف بلا إغراقِ مزوّد

  · **لا نداءَ خارجيّ لهذه المسحة**: `analyze_company(..., allow_supplement=False)`
    تقرأ القوائمَ من الباب الواحد (‏تداول — XBRL المخزَّن) واللقطةَ
    للسعر. فالمسحةُ تعمل على ما نملكه لا على حصّةِ مزوّد.
  · **تزامنٌ محدود** بسيمافور، والفشلُ الفرديُّ يُعَدّ ولا يُسقط المسحة.
  · **كتابةٌ جماعيةٌ واحدة** إلى مخزن الأساسيات نفسِه الذي يقرؤه الفرز
    (‏`_fund_store_put_many`) — لا ملفَّ ثانياً ولا مصدرَ حقيقةٍ ثانياً.

## وما يُكتب

`fair_value` · `fair_value_conf` · `fair_value_asof` (‏أحدثُ فترةٍ ماليةٍ
لا تاريخُ الجلب · D380) · `fair_value_age_days` · `fair_value_stale` ·
`fair_value_low/high` · `finance_score` · `score_asof`.

وما امتنع محرّكُه يُكتب له **سببُ الامتناع** لا صفرٌ ولا فراغٌ صامت:
`fair_value_unavailable` — فالشاشةُ تقول «لم يُقدَّر ولماذا».
"""
from __future__ import annotations

import asyncio
from datetime import date

from loguru import logger

CONC = 6


# ══ والتعذّرُ يُسمّى سببُه في التقرير ══ (D424)
# كانت `_one` تمسك كلَّ استثناءٍ وتُسجّله في مستوى **debug** ثمّ تُعيد
# `None`. فسقط المحرّكُ في 268 ورقةً من 273 بخطأٍ واحدٍ في سطرٍ واحد،
# وخرج التقريرُ «تعذّرت 268» بلا اسمِ خطأٍ ولا موضع — واحتاج كشفُه
# كاشفاً مستقلّاً. فصار صنفُ الخطأ ونصُّه يُجمعان ويخرجان في التقرير
# نفسِه، فيُقرأ سببُ السقوط الجماعيّ من سطرٍ واحد.
_FAIL_KINDS: dict[str, int] = {}


async def _one(sym: str, sem: asyncio.Semaphore) -> tuple[str, dict] | None:
    async with sem:
        try:
            from app.services.analysis import analyze_company
            a = await analyze_company(f"{sym}.SR", allow_supplement=False)
        except Exception as e:                                    # noqa: BLE001
            _k = f"{type(e).__name__}: {str(e)[:120]}"
            _FAIL_KINDS[_k] = _FAIL_KINDS.get(_k, 0) + 1
            logger.warning(f"مسحةُ التقييم {sym}: {_k}")
            return None
        if not a:
            return None
        fv = a.get("fair_value_detail") or {}
        out: dict = {
            "fair_value": a.get("fair_value"),
            "fair_value_low": a.get("fair_value_low"),
            "fair_value_high": a.get("fair_value_high"),
            "fair_value_conf": a.get("fair_value_conf"),
            "fair_value_asof": a.get("fair_value_asof"),
            "fair_value_age_days": a.get("fair_value_age_days"),
            "fair_value_stale": a.get("fair_value_stale"),
            "fair_value_unavailable": (fv.get("unavailable_reason")
                                       if a.get("fair_value") is None else None),
            "score_asof": date.today().isoformat(),
        }
        # ودرجةُ الجودة من مصدرها الواحد — إن حسبها التحليلُ في هذه الجولة
        _fin = a.get("financial") or {}
        _sc = _fin.get("score") if isinstance(_fin, dict) else None
        if _sc is None:
            _sc = (a.get("governance") or {}).get("score") if isinstance(
                a.get("governance"), dict) else None
        if isinstance(_sc, (int, float)):
            out["finance_score"] = round(float(_sc), 1)
        # وتاريخُ القوائم التي بُنيت عليها الدرجة (‏D381 · D384)
        _prov = a.get("governance_provenance") or {}
        if _prov.get("تاريخ الأرقام"):
            out["stmt_asof"] = _prov["تاريخ الأرقام"]
            out["stmt_age_days"] = _prov.get("عمر الأرقام أياماً")
        return sym, out


async def sweep(symbols: list[str] | None = None, *, conc: int = CONC) -> dict:
    """يحسب الدرجةَ والسعرَ العادل لكلّ رمزٍ ويخزّنهما. يُعاد تقريرٌ مقيس."""
    from app.services.content_engine import _fund_store_put_many

    # ══ الكونُ هو الدليلُ الرسميُّ للسوق الرئيسيّ — لا اللقطة ══ (D387)
    # قضى المالك: «عند مسح السوق يكون بالمعطيات الرسمية: القطاعات 23
    # والشركات 273… نمو لا أريده، فدمجُ الاثنين يجعل المحرّكَ ضعيفاً».
    # وكانت المسحةُ تأخذ رموزَها من **اللقطة** (396 = 272 رئيسيّ + 124
    # نمو) فتخلط شركاتٍ مُلزَمةً بإفصاحٍ كاملٍ بأوراقِ سوقٍ موازٍ —
    # فتُقاس مسطرةٌ واحدةٌ على صنفَين، وذاك إضعافٌ لا توسيع.
    # فالكونُ من `main_market` (‏273 شركةً · 22 قطاعاً · صفرُ رموزِ نمو)،
    # واللقطةُ تبقى للسعرِ وحدَه. والصناديقُ المتداولة خارجَه بحقّ: أوراقٌ
    # لا شركاتٌ، إفصاحُها صافي أصولٍ لا قوائمَ ربعية.
    syms = [str(s).replace(".SR", "") for s in (symbols or [])]
    if not syms:
        from app.data.market_universe import MARKET_UNIVERSE
        from app.data.universe import main_market
        syms = sorted(main_market(MARKET_UNIVERSE).keys())
    # ولا يتسلّل رمزُ «نمو» بحالٍ — ولو مُرّر بالوسيط
    syms = [s for s in syms if not s.startswith("9")]
    if not syms:
        return {"خطأ": "لا رموزَ في السوق الرئيسيّ — دليلٌ فارغ"}

    sem = asyncio.Semaphore(max(1, min(12, conc)))
    _FAIL_KINDS.clear()
    done: dict[str, dict] = {}
    failed = 0
    t0 = asyncio.get_event_loop().time()
    for i in range(0, len(syms), 50):
        chunk = syms[i:i + 50]
        res = await asyncio.gather(*(_one(s, sem) for s in chunk),
                                   return_exceptions=True)
        for r in res:
            if isinstance(r, tuple):
                done[r[0]] = r[1]
            else:
                failed += 1
        # كتابةٌ كلَّ خمسين: مسحةٌ تُقطع لا تُضيّع ما أنجزته
        _fund_store_put_many({k: v for k, v in done.items()})
        logger.info(f"مسحةُ التقييم: {len(done)} من {len(syms)}")

    have_fv = sum(1 for v in done.values() if v.get("fair_value") is not None)
    have_sc = sum(1 for v in done.values() if v.get("finance_score") is not None)
    stale = sum(1 for v in done.values() if v.get("fair_value_stale"))
    rep = {
        "السوقُ": "الرئيسيّ فقط (‏نمو مستثنىً بأمر المالك)",
        "رموزٌ": len(syms),
        "كُتبت": len(done),
        "لها سعرٌ عادل": have_fv,
        "لها درجةُ جودة": have_sc,
        "شائخةُ الأرقام": stale,
        "تعذّرت": failed,
        "ثوانٍ": round(asyncio.get_event_loop().time() - t0, 1),
    }
    if _FAIL_KINDS:
        rep["أسبابُ التعذّر"] = dict(sorted(_FAIL_KINDS.items(),
                                            key=lambda x: -x[1])[:5])
    logger.info(f"مسحةُ التقييم انتهت: {rep}")
    return rep
