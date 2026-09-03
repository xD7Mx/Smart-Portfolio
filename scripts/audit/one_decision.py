"""D166 — قرارٌ واحدٌ يخرج من مُنتِجٍ واحد، والشاشاتُ تعرضه.

## العطب

كان `governance_engine.evaluate_company` يُخرج قرارَ محرّك القواعد **خاماً**،
بينما `analysis.py` يمرّره على ستِّ بوّاباتِ أمان: خطٌّ أحمر ⇐ تجنّب، ولا
قيمةَ عادلة ⇐ امتناع، وتغطيةٌ دون ‎٦٠٪ ⇐ انتظار، ومسارٌ واحد أو تقديرٌ
شاذّ أو سوقٌ موازية ⇐ انتظار.

فقِيس على ‎٣٠ شركةً حقيقيةً على الخادم: **اختلفا في ١٦**. البطاقةُ تقول
«شراء قوي» لشركةٍ قرّر التطبيقُ نفسُه «انتظار»، وتُصدر حكماً على أربعٍ
امتنع عن الحكم عليها. والسببُ يُعرض تحت قرارٍ ملغى — وهو أخطرُ من
الاختلاف نفسِه.

ورأيُ الذكاء ثالثٌ منفصل: لم تكن كلمةُ «القرار» ترد في توجيهه ولا مرّة،
فيجتهد بجوار محرّكٍ حاسم — فيخرج «شراء» وأسبابُه كلُّها هبوط.

## الفحص

طبقتان، كلتاهما سلوكيّة:

  · **مبنويّة (تعمل بلا شبكة):** أنّ البطاقةَ لا تملك منتِجَ قرارٍ خاصّاً
    بها — تُستدعى بمصدرٍ مُعطَّل فيجب أن تمتنع، لا أن تُخرج حكماً خاماً.
  · **حيّة (على الخادم):** تشغّل المسارين على شركاتٍ حقيقية وتشترط
    تطابقَ الحكم حرفاً بحرف.

        docker exec sp_backend python /app/scripts/audit/one_decision.py --live
"""

from __future__ import annotations

# ══ فحصٌ لا يكتب في بيانات المالك ══ (D160)
# الوحداتُ تقرأ مسارَ المخزن عند **تحميلها**، فيُحوَّل في رأس الوحدة قبل
# أيّ استيرادٍ من `app` — بما فيها الاستيراداتُ المؤجَّلة داخل الدوالّ.
# وسكربتُ فحصٍ يغيّر حالةً ليس فحصاً.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX


import asyncio
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in ("/app", os.path.join(_ROOT, "backend"), _ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

fail = 0


def say(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}{(' — ' + detail) if detail else ''}")


SYMBOLS = ["2222", "1120", "7010", "2010", "1180", "1211", "2280", "4190",
           "4164", "4013", "1010", "1150", "2350", "5110", "4003", "1050",
           "1060", "2020", "4001", "4002", "8010", "4071", "4291", "1322",
           "2288", "4165", "8313", "6040", "4160", "1213"]


async def structural() -> None:
    """البطاقةُ تعرض ولا تصنع — فإن تعذّر المنتِجُ الواحد امتنعت.

    يُعطَّل `analyze_company` عمداً ويُشغَّل المحرّك على قوائمَ سليمة: لو
    كان يملك قراراً خاصّاً به لأخرجه، وهذا هو العطبُ بعينه. والمطلوب
    امتناعٌ صريح."""
    from app.services import governance_engine as ge
    from app.services import analysis as an
    from app.services.market_data import market_service
    from app.services.decision_engine import ABSTAIN

    async def _boom(*a, **k):
        raise RuntimeError("منتِجُ القرار مُعطَّلٌ عمداً في الفحص")

    # قوائمُ صناعيةٌ سليمةٌ تُغني عن الشبكة، فيسير المحرّكُ إلى آخره
    # ويُبتلى بتعذُّرِ المنتِج الواحد وحدَه — لا بغياب البيانات.
    periods = [{
        "year": 2023 + i, "revenue": 1000.0 * (1.08 ** i),
        "net_income": 150 * (1.08 ** i), "operating_cash_flow": 190 * (1.08 ** i),
        "free_cash_flow": 140 * (1.08 ** i), "equity": 800, "total_assets": 1600,
        "debt_ratio": 0.35, "interest_coverage": 9, "capex": -50,
    } for i in range(3)]

    async def _fin(*a, **k):
        return {"periods": periods}

    async def _info(*a, **k):
        return {"sector": "الطاقة", "name": "فحص", "price": 30.0,
                "pe_ratio": 14, "price_to_book": 1.5}

    async def _hist(*a, **k):
        return None

    real = (an.analyze_company, market_service.get_financials,
            market_service.get_company_info, market_service.get_history)
    an.analyze_company = _boom
    market_service.get_financials = _fin
    market_service.get_company_info = _info
    market_service.get_history = _hist
    try:
        out = await ge.evaluate_company("__PROBE_D166__.SR")
    except Exception as e:                                        # noqa: BLE001
        print("     (سقط المحرّك:", type(e).__name__, e, ")")
        out = None
    finally:
        (an.analyze_company, market_service.get_financials,
         market_service.get_company_info, market_service.get_history) = real

    if out is None:
        say(False, "١ تعذُّرُ المنتِج الواحد ⇐ امتناعٌ لا حكمٌ خام",
            "المحرّكُ لم يُخرج شيئاً — الفحصُ لم يبلغ موضعَه")
        return
    d = (out.get("decision") or {})
    say(d.get("raw") == ABSTAIN,
        "١ تعذُّرُ المنتِج الواحد ⇐ امتناعٌ لا حكمٌ خام", str(d.get("raw")))


async def live() -> None:
    from app.core.database import AsyncSessionLocal
    from app.services.governance_engine import evaluate_company
    from app.services.analysis import analyze_company
    from app.api.v1.endpoints.holdings import yahoo_symbol

    diff, seen = [], 0
    async with AsyncSessionLocal() as db:
        for s in SYMBOLS:
            y = yahoo_symbol(s)
            try:
                g = await evaluate_company(y, db=db)
            except Exception:
                g = None
            try:
                a = await analyze_company(y, s, db=db)
            except Exception:
                a = None
            gd = ((g or {}).get("decision") or {}).get("raw")
            ad = ((a or {}).get("decision") or {}).get("raw")
            if gd is None and ad is None:
                continue
            seen += 1
            if gd != ad:
                diff.append((s, gd, ad))

    for s, gd, ad in diff:
        print(f"     {s}: بطاقة={gd}  أداء={ad}")
    say(not diff, "٢ القرارُ واحدٌ في البطاقة وتبويب الأداء",
        f"اختلفا في {len(diff)} من {seen}")


async def prompt_carries_decision() -> None:
    """رأيُ الذكاء يُخبَر بالقرار — يُبنى التوجيهُ **فعلاً** ويُلتقط قبل
    إرساله، فيُفتَّش فيه عن الحكم نفسِه. لا قراءةَ مصدرٍ: قراءةُ المصدر
    تنجح ولو كان الحكمُ لا يبلغ التوجيهَ لعطبٍ في طريقه."""
    from app.services import ai_content

    seen = {}

    async def _capture(prompt, key, ttl):
        seen["prompt"] = prompt
        return None

    real = ai_content._generate_obj
    ai_content._generate_obj = _capture
    try:
        await ai_content.stock_opinion(
            "9999", "شركة الفحص",
            {"price": 30.0, "change_pct": 1.0,
             "fair_value": 40.0, "fair_value_upside_pct": 33.0,
             "fundamentals": {"pe_ratio": 14, "roe": 18},
             "technical": {"trend": "هابط", "rsi": 38},
             "decision": {"label": "انتظار", "raw": "انتظار",
                          "reason": "السعرُ فوق قيمتنا العادلة"}})
    finally:
        ai_content._generate_obj = real

    pr = seen.get("prompt") or ""
    say("انتظار" in pr, "٣ التوجيهُ يحمل قرارَ التطبيق نفسَه",
        "بلغ التوجيهَ" if "انتظار" in pr else "لم يبلغ التوجيهَ")
    say("السعرُ فوق قيمتنا العادلة" in pr, "٤ ويحمل سببَ القرار")
    say("لا تناقضه" in pr and "sentiment_label" in pr,
        "٥ ويُلزَم النموذجُ بعدم مناقضته")


async def main() -> int:
    await structural()
    await prompt_carries_decision()
    if "--live" in sys.argv:
        await live()
    else:
        print("… الطبقةُ الحيّة تُشغَّل على الخادم بـ--live")
    print()
    print("النتيجة:", "نظيف ✔" if not fail else "فيه ملاحظات ✘")
    return fail


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
