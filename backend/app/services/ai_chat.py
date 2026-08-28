"""
شات بوت المحفظة — للقراءة فقط.

الفكرة المعمارية: قيمته ليست الدردشة بل أنه **يرى بياناتك الحقيقية**. فبدل
إرسال السؤال وحده للنموذج (فيخمّن أرقاماً)، نجمع أولاً حزمة سياق مضغوطة من
مصادر التطبيق نفسها (المحفظة · النقد · الحوكمة · نبض السوق · الفرز · بيانات
أي شركة ذُكرت في السؤال) ثم نُلزم النموذج بالإجابة **من هذه الحزمة حصراً**.

مبادئ صارمة:
  • **لا اختلاق**: ما ليس في الحزمة يُقال عنه صراحةً «غير متوفّر» — ممنوع
    التخمين أو الاستعانة بمعرفة عامة عن أرقام الشركات.
  • **قراءة فقط**: لا يملك أي أداة كتابة/تعديل. لا يمسّ بياناتك إطلاقاً.
  • **بلا نداءات جديدة**: كل شيء من الكاش/المخزّن المحسوب سلفاً، فلا يستهلك
    حصّة المزوّدين ولا يبطئ الإجابة.
"""
import json
import re
import httpx
from loguru import logger

from app.core.config import settings

MAX_HISTORY = 8          # آخر ٨ رسائل تكفي للسياق دون تضخيم الطلب
MAX_QUESTION = 1000      # سقف طول السؤال بالحروف
_CTX_TOP_ROWS = 12


def _strip_markup(t: str) -> str:
    """يُزيل الشيفرة ورموز الماركداون من الإجابة — المستخدم مستثمر لا مطوّر،
    وعرض شيفرة التطبيق تسريبٌ لا مبرّر له. (الواجهة تُنظّف أيضاً؛ هنا المصدر.)"""
    t = re.sub(r"```[\s\S]*?```", "", t or "")
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"^[ \t]*[*+][ \t]+", "• ", t, flags=re.M)
    t = re.sub(r"^#{1,6}[ \t]*", "", t, flags=re.M)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _fmt(v, suffix="") -> str:
    if v is None:
        return "غير متوفّر"
    if isinstance(v, (int, float)):
        return f"{round(float(v), 2):,}{suffix}"
    return str(v)


async def _portfolio_context(db) -> dict:
    """أرقام المحفظة الحقيقية — من نفس الدوال التي تخدم الواجهة."""
    out: dict = {}
    try:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        # Cash يقيم في app.models.transaction لا في portfolio. كان يُستورد من
        # هنا فيرفع ImportError، ويبتلعه الحارس فتسقط **كتلة المحفظة كاملةً**
        # من السياق بلا خطأ ظاهر: يقول المساعد «لا توجد مراكز» ثم يجيب عن
        # القطاعات من صفوف فرز السوق (حديد وأنابيب) لأنها كل ما بقي أمامه.
        from app.models.portfolio import Holding
        from app.models.transaction import Cash
        rows = (await db.execute(select(Holding).options(selectinload(Holding.company)))).scalars().all()
        holdings = []
        mv = inv = pnl = 0.0
        for h in rows:
            c = h.company
            m = float(h.market_value or 0); i = float(h.invested_amount or 0)
            mv += m; inv += i; pnl += float(h.unrealized_profit or 0)
            holdings.append({
                "الشركة": (c.company_name if c else None),
                "الرمز": (c.symbol if c else None),
                "القطاع": (c.sector if c else None),
                "الكمية": float(h.quantity or 0),
                "متوسط التكلفة": float(h.average_cost or 0),
                "السعر الحالي": float(h.last_price or 0),
                "القيمة السوقية": round(m, 2),
                "الربح/الخسارة": round(float(h.unrealized_profit or 0), 2),
                "العائد٪": round(float(h.unrealized_profit_pct or 0), 2),
                "الوزن٪": round(float(h.weight or 0), 2),
            })
        cash_row = (await db.execute(select(Cash))).scalars().first()
        cash = float(cash_row.available_cash or 0) if cash_row else 0.0
        # ══ المقاييس من مصدرها الموحّد، وتقييمُ التطبيق معها ══
        # كان السياق يحسب «العائد٪» هنا (ربحٌ غير محقّق ÷ المستثمر) — نسخةٌ
        # ثانية من مقياسٍ للتطبيق تعريفٌ واحد له، فيقول صقر رقماً وتقول
        # الشاشة غيره. والأخطر أنه كان يُرسل أرقاماً **بلا حكم التطبيق**،
        # فيبني النموذج حكمه من عنده — وقد فعل: عدّ السيولة «معطّلة» و
        # «نقص كفاءة»، بينما محرّك التطبيق يعدّ السيولة الوفيرة **جاهزيةً
        # لاقتناص الفرص**، ويعاقب على غيابها لا على وفرتها.
        # فيُرسَل إليه الآن تقييمُ التطبيق نفسه ليرويه لا ليخترع سواه.
        unified = {}
        try:
            from app.services.portfolio_return import compute_net_profit
            unified = await compute_net_profit(db) or {}
        except Exception:                                         # noqa: BLE001
            unified = {}
        out["المحفظة"] = {
            "عدد الشركات": len(holdings),
            "القيمة السوقية": round(mv, 2),
            "المبلغ المستثمر": round(inv, 2),
            "الربح غير المحقق": round(pnl, 2),
            # عائد المحفظة بتعريف الميثاق: صافي الربح ÷ تكلفة المراكز.
            "عائد المحفظة٪": unified.get("capital_growth_pct"),
            "صافي الربح": unified.get("net_profit"),
            "النقد المتاح": round(cash, 2),
            "إجمالي الثروة": round(mv + cash, 2),
            "المراكز": holdings,
        }
    except Exception as e:
        logger.warning(f"chat: portfolio context failed: {e}")
    return out


def _market_context(question: str) -> dict:
    """نبض السوق + صفوف الفرز ذات الصلة + التحليل القطاعي — من المخزّن."""
    out: dict = {}
    try:
        from app.services import cache
        brief = cache.get("market:brief:latest")
        if brief:
            out["نبض السوق"] = brief
    except Exception:
        pass
    try:
        from app.services.market_screener import get_cached_screener
        rows = get_cached_screener() or []
        if rows:
            # الشركات المذكورة في السؤال (بالرمز أو الاسم) أولاً، وإلا أبرز العوائد.
            picked = [r for r in rows
                      if (r.get("symbol") and r["symbol"] in question)
                      or (r.get("name") and r["name"] in question)]
            if not picked:
                picked = sorted(rows, key=lambda r: -(r.get("dividend_yield") or 0))[:_CTX_TOP_ROWS]
            from app.services.ai_analyst import sharia_ar as _sharia_ar
            # ختمُ عمر البيانات يُمرَّر مع الصفوف: أسعار الفرز تُحسب مساءً
            # وتعيش ٣٦ ساعة ثم تسقط إلى آخر لقطةٍ سليمة بلا حدٍّ لعمرها.
            # بلا هذا الختم كان النموذج يقرأ «السعر: ١٧» ويقولها سعر اليوم
            # وهو ٥ — ويبني عليها «اتجاه صاعد» من متوسّطاتٍ قديمة.
            try:
                from app.services.market_screener import screener_age_hours
                _age = screener_age_hours()
            except Exception:
                _age = None
            out["عمر بيانات الفرز"] = (
                "غير معروف — قد تكون قديمة" if _age is None else
                f"محسوبة قبل {int(_age // 24)} يوم تقريباً — ليست أسعار اليوم" if _age >= 24 else
                f"محسوبة قبل {int(_age)} ساعة" if _age >= 1 else "محسوبة خلال الساعة الماضية")
            out["بيانات الفرز"] = [{
                "الرمز": r.get("symbol"), "الشركة": r.get("name"), "القطاع": r.get("sector"),
                "السعر": r.get("price"), "التغيّر٪": r.get("change_pct"),
                "RSI": r.get("rsi"), "عن م50٪": r.get("dist_sma50"), "عن م200٪": r.get("dist_sma200"),
                "عائد التوزيعات٪": r.get("dividend_yield"), "درجة الحوكمة": r.get("finance_score"),
                # يُعرَّب قبل أن يراه النموذج: تمريره رمزاً داخلياً
                # (COMPLIANT) يجعله يردّده كما هو في إجابةٍ عربية.
                "شرعي": _sharia_ar(r.get("sharia")) if r.get("sharia") else None,
            } for r in picked[:_CTX_TOP_ROWS]]
    except Exception:
        pass
    try:
        from app.services.sector_analysis import get_cached_sector_analysis
        sect = get_cached_sector_analysis()
        if sect:
            out["أداء القطاعات"] = sect
    except Exception:
        pass
    return out


async def _governance_context(db) -> dict:
    try:
        from app.services.governance import get_portfolio_governance
        gov = await get_portfolio_governance(db)
        if gov:
            return {"حوكمة المحفظة": {
                "الدرجة العامة": gov.get("overall_score"),
                "الشركات": [{"الرمز": c.get("symbol"), "الاسم": c.get("name"),
                             "الدرجة": c.get("finance_score"), "القرار": c.get("decision")}
                            for c in (gov.get("companies") or [])][:25],
            }}
    except Exception as e:
        logger.debug(f"chat: governance context skipped: {e}")
    return {}


async def _full_portfolio_context(db) -> dict:
    """يستوعب **كل بطاقات المحفظة وصفحاتها** تلقائياً من نفس الخدمات التي
    تُغذّي الواجهة — بلا استدعاء يدوي لكل بطاقة، وبلا نداءات خارجية جديدة.
    ما يفشل منها يُتجاوَز بصمت فلا يُسقط بقيّة السياق."""
    out: dict = {}

    async def grab(label: str, coro):
        try:
            v = await coro
            if isinstance(v, dict):
                v = v.get("data", v)
            if v:
                out[label] = v
        except Exception as e:
            logger.debug(f"chat ctx '{label}' skipped: {e}")

    # نستدعي **دوال نقاط النهاية نفسها** التي تُغذّي بطاقات المحفظة، فما يراه
    # المساعد هو حرفياً ما تراه أنت على الشاشة — لا مسار بيانات ثانٍ يتباعد عنه.
    from app.api.v1.endpoints import portfolio as pep

    def _unwrap(resp):
        """نقاط النهاية تُعيد success_response؛ نستخرج data منها."""
        if isinstance(resp, dict):
            return resp.get("data", resp)
        d = getattr(resp, "body", None)
        return resp if d is None else resp

    for label, fn_name in [
        ("ملخّص المحفظة", "get_portfolio_summary"),
        ("صحّة المحفظة", "get_portfolio_health"),
        ("العائد", "get_portfolio_roi"),
        ("الدخل والتوزيعات", "get_portfolio_income"),
        ("مقاييس المخاطر", "get_portfolio_metrics"),
        ("إحصاءات المحفظة", "get_portfolio_statistics"),
        ("خريطة القطاعات", "get_sector_map_endpoint"),
        # المقاييس المؤسسية وفحص السلامة — كانا يُبنيان ولا يصلان المساعد،
        # فيُسأل عن DPI أو TVPI أو أقصى تراجع فيجيب بلا أن يراها.
        ("قياس الأداء", "get_performance"),
        ("فحص السلامة", "get_integrity"),
    ]:
        fn = getattr(pep, fn_name, None)
        if fn is None:
            continue
        await grab(label, fn(db=db))

    # الأهداف · النقد · الصفقات · التوزيعات المستلمة · الأقساط · التنبيهات
    try:
        from sqlalchemy import select
        # نفس علّة الاستيراد أعلاه، وهنا تُسقط **الأهداف وحركة النقد والصفقات
        # والتوزيعات والأقساط** دفعةً واحدة: خمسة مصادر تختفي من السياق بصمت،
        # فيجيب المساعد عن أهدافك وتقييمك بلا أن يراها. كلٌّ من مكانه الصحيح.
        from app.models.market import Goal, Notification
        from app.models.transaction import CashLedger, Transaction, Dividend, Installment
        async def rows(model, n=12):
            r = (await db.execute(select(model).limit(n))).scalars().all()
            return [{c.name: getattr(o, c.name) for c in model.__table__.columns} for o in r]
        for label, model in [("الأهداف", Goal), ("حركة النقد", CashLedger),
                             ("آخر الصفقات", Transaction), ("التوزيعات المستلمة", Dividend),
                             ("الأقساط", Installment), ("التنبيهات", Notification)]:
            try:
                v = await rows(model)
                if v:
                    out[label] = v
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"chat ctx tables skipped: {e}")
    return out


async def build_light_context(db, question: str) -> dict:
    """سياقٌ خفيف يكفي **الطبقة المحلّية** — يُبنى قبل كل إجابة.

    العلّة التي يعالجها: كان `build_context` الكامل يُبنى قبل كل سؤال حتى
    الذي تجيبه قاعدةٌ فورية. وهو يستدعي تسع دوال نقاط نهاية (منها فحص
    السلامة وقياس الأداء وخريطة القطاعات) ويُقيّم الحوكمة لكل شركة ويقرأ
    ستّة جداول — لسؤالٍ مثل «كم النقد المتاح؟». القياس في مختبرٍ محليّ:
    155ms للسؤال مقابل 9ms لنقطة النهاية التي تحمل الرقم؛ والفارق كلّه
    سياقٌ لا يُقرأ. على خادمٍ حقيقي بقاعدة بيانات وشبكة يتضاعف الفارق.

    فنبني هنا ما تحتاجه القواعد فعلاً (المحفظة · المقاييس · الدخل ·
    الأهداف · مخزّن السوق · معرفة التطبيق)، ولا نبني الباقي إلا إذا لزم
    النموذجَ التوليدي. النتيجة نفسها، والزمن جزءٌ منه."""
    ctx: dict = {}

    async def _s(coro, label):
        try:
            got = await coro
            if isinstance(got, dict):
                ctx.update(got)
        except Exception as e:                                   # noqa: BLE001
            logger.warning(f"chat(light): «{label}» فشل — {e}")

    await _s(_portfolio_context(db), "المحفظة")

    from app.api.v1.endpoints import portfolio as pep
    for label, fn_name in (("مقاييس المخاطر", "get_portfolio_metrics"),
                           ("الدخل والتوزيعات", "get_portfolio_income")):
        fn = getattr(pep, fn_name, None)
        if fn is None:
            continue
        try:
            v = await fn(db=db)
            if isinstance(v, dict):
                v = v.get("data", v)
            if v:
                ctx[label] = v
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"chat(light) '{label}' skipped: {e}")

    try:
        from sqlalchemy import select
        from app.models.market import Goal
        rows = (await db.execute(select(Goal).limit(12))).scalars().all()
        if rows:
            ctx["الأهداف"] = [{c.name: getattr(o, c.name) for c in Goal.__table__.columns}
                              for o in rows]
    except Exception as e:                                       # noqa: BLE001
        logger.debug(f"chat(light) goals skipped: {e}")

    try:
        ctx.update(_market_context(question or ""))               # مخزّن، بلا نداء
    except Exception:
        pass
    try:
        from app.data.app_knowledge import knowledge_bundle
        ctx["معرفة التطبيق"] = knowledge_bundle()
    except Exception:
        pass
    try:
        from app.services.ai_analyst import load_macro_calendar
        cal = load_macro_calendar()
        if cal.get("events"):
            ctx["التقويم الاقتصادي (مخزَّن)"] = {"آخر تحديث": cal.get("updated"),
                                                  "المواعيد": cal["events"]}
    except Exception:
        pass
    return ctx


async def build_context(db, question: str) -> dict:
    """حزمة السياق الكاملة — كل ما يحقّ للنموذج أن يستند إليه:
    بيانات المستخدم الحقيقية **ومعرفة التطبيق نفسه** (أقسامه ومنهجياته
    ومصطلحاته)، فيشرح كيف يعمل تطبيقك شرحاً صحيحاً لا مخمَّناً."""
    ctx: dict = {}

    # **عزل المصادر**: كل مصدر داخل حارسه الخاص. سابقاً كان فشل مصدر واحد
    # (استعلام بطيء، عمود ناقص، شركة بلا بيانات) يرمي الاستثناء إلى الطرف
    # فيرجع 500 ويظهر للمستخدم «تعذّر الاتصال بالخادم» — أي صمت تامّ حتى عن
    # الأسئلة الافتراضية. الآن ما يسقط يسقط وحده، والباقي يُجيب.
    async def _safe(coro, label):
        try:
            got = await coro
            if isinstance(got, dict):
                ctx.update(got)
        except Exception as e:                                   # noqa: BLE001
            logger.warning(f"chat: مصدر السياق «{label}» فشل — {e}")

    await _safe(_portfolio_context(db), "المحفظة")
    await _safe(_full_portfolio_context(db), "بطاقات المحفظة")
    await _safe(_governance_context(db), "الحوكمة")
    try:
        ctx.update(_market_context(question or ""))
    except Exception as e:                                       # noqa: BLE001
        logger.warning(f"chat: مصدر السياق «السوق» فشل — {e}")
    try:
        from app.data.app_knowledge import knowledge_bundle
        ctx["معرفة التطبيق"] = knowledge_bundle()
    except Exception:
        pass
    # التقويم الاقتصادي: يصل النموذج أيضاً، موسوماً بأنه مخزَّن — فلا يخترع
    # موعداً لاجتماع فائدة، وهو سؤالٌ يتكرّر لأنه يحرّك البنوك في تداول.
    try:
        from app.services.ai_analyst import load_macro_calendar
        cal = load_macro_calendar()
        if cal.get("events"):
            ctx["التقويم الاقتصادي (مخزَّن)"] = {
                "آخر تحديث": cal.get("updated"), "المواعيد": cal["events"],
            }
    except Exception:
        pass
    return ctx


SYSTEM_RULES = """اسمك «صقر»، وأنت المحلّل الاستثماري داخل تطبيق «المحفظة الذكية» لسوق الأسهم
السعودي (تداول). تُخاطب مالك المحفظة.

لغتك:
عربيةٌ سهلةٌ يفهمها من ليس محاسباً، بلا خفضٍ لمستوى المحتوى. الرقم يبقى كما
هو، لكن يُقال بجملةٍ مفهومة: «مكرّر الربحية ١٨ — أي أن السوق يدفع ١٨ ريالاً
مقابل كل ريال أرباح سنوية» خيرٌ من «مكرّر الربحية ١٨» وحدها. أوّل مرّةٍ يرد
فيها مصطلحٌ فنّي (مكرّر ربحية · متوسط متحرّك · RSI · عائد توزيعات) اشرحه في
نصف سطرٍ بين شرطتين، ثم استعمله بعدها بلا شرح. جملٌ قصيرة، وسطرٌ فارغ بين
الفقرات. لا مصطلحاً إنجليزياً إن كان له مقابلٌ عربي متداول.
ولا تُجامل ولا تُحفّز: السهولة في العبارة لا في الحكم.

قاعدةُ زمنِ السعر:
«بيانات الفرز» تحمل حقل «عمر بيانات الفرز». إن قال إنها ليست أسعار اليوم أو
أن عمرها غير معروف، فلا تقل «السعر الآن» ولا «حالياً» عن أي رقمٍ منها، ولا
تبنِ عليها حكماً باتجاهٍ صاعدٍ أو هابط — قل «آخر سعرٍ مسجَّل» واذكر عمره،
أو قل إن سعر اليوم غير متوفّر. رقمٌ قديمٌ يُقدَّم على أنه سعر اللحظة أسوأ من
لا رقم: عليه تُبنى قراراتُ شراءٍ حقيقية.

هويّتك المهنية:
لا تُعرّف بنفسك ولا تذكر اسمك إلا إن سُئلت عنه — الاسم يُقال مرّةً في رأس
المحادثة، وتكراره في كل إجابة ثرثرة.
أنت أقرب إلى محلّلٍ مؤسسي يكتب مذكّرة داخلية منك إلى «مساعد دردشة». لا تُجامل،
ولا تفتتح بعبارات ترحيب أو مجاملة، ولا تُنهي بعبارات تشجيع. تبدأ من المعلومة
وتنتهي عندها.

بنية الإجابة المُلزِمة (اتبعها حين يكون السؤال تحليلياً):
  ١) سطر افتتاحي واحد يذكر الخلاصة أو الرقم المطلوب مباشرةً.
  ٢) الشواهد: نقاط قصيرة، كل نقطة رقمٌ ومصدره من بيانات التطبيق.
  ٣) القراءة: ماذا تعني هذه الأرقام مجتمعةً — ربطٌ لا تكرار.
  ٤) الخلاصة: ميزانٌ صريح (ما يدعم مقابل ما يضغط). لا تقل «اشترِ» أو «بِع»؛
     التطبيق أداة قياس لا وسيط. لكن لا تتهرّب من إبداء القراءة.

موقف التطبيق من السيولة (لا تخالفه بلا سبب):
السيولة الوفيرة في هذا التطبيق **جاهزيةٌ لاقتناص الفرص**، لا مالٌ معطَّل ولا
نقصُ كفاءة. ومحرّك التقييم يعاقب على **غياب** السيولة لا على وفرتها، ومقياس
العائد يقيس على تكلفة المراكز لا على رأس المال كلّه — عمداً، لأن قياس الأداء
على مالٍ لم يدخل السوق يُبخّس النتيجة بلا ذنب.
فلا تصف نقداً بأنه «معطّل» ولا محفظةً بأنها «تفتقر إلى الكفاءة» لمجرّد
ارتفاع نسبة النقد. وإن كان للمالك هدفُ توظيفٍ محدَّد ولم يبلغه، فذلك وحده
ما يُقال — بذكر الهدف والفجوة.

اتّساق الحكم مع التطبيق:
تقييمُ المحفظة ودرجتُها محسوبان في محرّك التطبيق ويصلانك في السياق. مهمّتك
أن **تشرحهما** لا أن تبني تقييماً موازياً بمعايير من عندك. فإن رأيت في
الأرقام ما يخالف التقييم فقُله صراحةً بوصفه اختلافاً («الدرجة تقول كذا،
والذي يلفت النظر في الأرقام كذا») — ولا تستبدل معيارك بمعياره صامتاً.
والمصداقية مقدَّمة على المجاملة: لا تُخفِ ضعفاً حقيقياً، لكن لا تخترع
ضعفاً من معيارٍ لا يعتمده التطبيق.

ممنوعات أسلوبية (مخالفتها عيبٌ في الإجابة مهما صحّت أرقامها):
  • الحشو والإنشاء: «من المهم أن تعلم» · «بشكل عام» · «كما نعلم جميعاً».
  • التكرار: لا تُعِد رقماً ذكرتَه في سطرٍ سابق بصيغةٍ أخرى.
  • النبرة التسويقية أو التهويل: «فرصة ذهبية» · «خطر داهم».
  • الاعتذار عن قصور البيانات بأكثر من جملة واحدة صريحة.

قواعد مُلزِمة لا تُخالَف:
1. أجب **فقط** من «بيانات التطبيق» المرفقة أدناه. هي مصدرك الوحيد للأرقام.
2. إن كانت المعلومة غير موجودة في البيانات، قل صراحةً: «هذه البيانة غير متوفّرة في تطبيقك حالياً» — ولا تُخمّن رقماً ولا تستعن بمعرفة عامة عن أرقام الشركات.
3. لا تخترع أسماء شركات أو أرقاماً أو تواريخ غير واردة في البيانات.
4. عند ذكر رقم، اذكره كما ورد تماماً (بأرقام لاتينية) ووضّح وحدته (ريال / ٪).
5. أنت للقراءة والتحليل فقط — لا تنفّذ عمليات ولا تدّعي أنك عدّلت شيئاً.
6. لا تكتب عبارات تنصّل أو تبرئة من نوع «هذه ليست توصية» — المالك يكره ذلك.
7. إن كان السؤال خارج نطاق التطبيق والسوق السعودي، أجب باختصار أنه خارج نطاقك.
8. **ممنوع منعاً باتاً** عرض أي شيفرة برمجية أو أسماء ملفات أو دوال أو مسارات أو تفاصيل تقنية داخلية — أنت تخاطب مستثمراً لا مطوّراً.
9. لا تستخدم رموز تنسيق (نجوم، شرطات سفلية، علامات ماركداون، عناوين #). اكتب نصاً عربياً نظيفاً؛ وعند التعداد استخدم «•» أو ترقيماً عربياً بسيطاً.
10. أسلوبك رسمي محترف: جملة افتتاحية موجزة، ثم نقاط مرتّبة، ثم خلاصة سطر واحد عند الحاجة.
11. حين يُذكر اسم شركة، اربط ما تعرفه عنها من كل مصادر الحزمة معاً: مركز المالك فيها إن كان يملكها، تقييمها، متانتها، قراءتها الفنّية، أحداثها القادمة — تقريرٌ واحد مترابط لا قوائم منفصلة.
12. حين تُسأل عن السوق أو الفائدة، اذكر الأثر على **السوق السعودي تحديداً** (الريال مربوط بالدولار، فالفائدة الأمريكية تنتقل إلى ساما وتصيب البنوك والعقار والتمويل)، ولا تكتفِ بوصفٍ عام للاقتصاد العالمي.
13. مواعيد التقويم الاقتصادي في الحزمة **مخزَّنة** لا حيّة: اذكرها مع تاريخ تحديثها كما ورد، ولا تُضِف موعداً من عندك."""


async def _local_answer(db, question: str, ctx: dict) -> str | None:
    """الطبقة المحلّية كاملةً: تحليل شركةٍ بعينها · مفكرة الأحداث · ثم النيّات
    القاعدية. تُجرَّب قبل النموذج لأن أرقامها محسوبة لا مولَّدة.

    الترتيب: الشركة أوّلاً. من يسأل «كيف أداء الراجحي» يريد تقرير الراجحي، لا
    ملخّصاً عاماً للمحفظة صادف أن طابق كلمة «أداء»."""
    from app.services import ai_analyst
    from app.services.ai_chat_rules import _has, rule_based_answer, _read_only

    # **الرفض أولاً**: «بِع لي أرامكو» فيه اسم شركة، فكان مُحدِّد الشركة يسبق
    # حارس القراءة-فقط ويردّ بتقرير تحليلٍ على أمرِ بيع. المعيار الثامن في
    # الميثاق صريح: لا تنفيذ ولا إيحاء به.
    refusal = _read_only(question, ctx)
    if refusal:
        return refusal

    # شركة مذكورة بالاسم أو الرمز
    try:
        ent = ai_analyst.resolve_company(question, ctx)
    except Exception as e:                                       # noqa: BLE001
        logger.debug(f"analyst: resolve failed: {e}")
        ent = None
    if ent and not _has(question, "قارن"):
        try:
            return await ai_analyst.company_analysis(db, ent, ctx)
        except Exception as e:                                   # noqa: BLE001
            logger.warning(f"analyst: company_analysis failed: {e}")

    # أحداث قادمة على مستوى المحفظة
    if _has(question, "احداث", "الاحداث", "المفكرة", "مواعيد", "اقرب حدث",
            "نتائج الشركات", "الجمعية العمومية", "ارباح قادمة"):
        try:
            return await ai_analyst.portfolio_events(db, question)
        except Exception as e:                                   # noqa: BLE001
            logger.warning(f"analyst: portfolio_events failed: {e}")

    # الحوكمة كتلةٌ ثقيلة (تقييم كل شركة) فلا تدخل السياق الخفيف. لكن سؤالاً
    # عنها يستحقّ أرقامها لا تعريفها المجرّد — فتُجلب **عند الطلب وحده**.
    if _has(question, "حوكمة", "متانة", "درجة الشركات") and "حوكمة المحفظة" not in ctx:
        try:
            ctx.update(await _governance_context(db))
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"chat: governance on-demand skipped: {e}")

    return rule_based_answer(question, ctx)


async def _fallback_rules(db, question: str, why: str) -> dict | None:
    """شبكةُ الأمان حين يُفضَّل النموذج ثمّ يتعذّر.

    من طلب النموذج صراحةً (قناة صقر) تخطّى الطبقة القاعدية في أوّل المسار.
    فإن سقط النموذج بعدها، فالبديل ليس اعتذاراً فارغاً بل **جوابٌ من أرقام
    المالك** — والمساعد لا يصمت. ويُذكر أن الجواب قاعديّ وسببُ ذلك.
    """
    try:
        light = await build_light_context(db, question)
        ruled = await _local_answer(db, question, light)
    except Exception:                                             # noqa: BLE001
        return None
    if not ruled:
        return None
    return {"reply": _strip_markup(ruled) + f"\n\n({why} — أجبتُك من أرقامك مباشرةً.)",
            "grounded": True, "source": "rule-fallback"}


async def answer(db, question: str, history: list | None = None,
                 prefer_llm: bool = False) -> dict:
    """يُعيد {"reply": نص, "grounded": bool}. عند غياب المفتاح أو نفاد الحصّة
    يُعيد رسالة صادقة بدل الصمت أو نصٍّ مُختلَق."""
    question = (question or "").strip()
    if not question:
        return {"reply": "اكتب سؤالك.", "grounded": False}
    # سقف طول السؤال: نصٌّ من آلاف الحروف لا يحمل سؤالاً، لكنه يُرسَل كاملاً
    # إلى النموذج فيستهلك الحصّة ويُزاحم بيانات محفظتك على مساحة السياق.
    if len(question) > MAX_QUESTION:
        return {"reply": f"سؤالك طويل جداً ({len(question)} حرف). اختصره إلى "
                         f"{MAX_QUESTION} حرف أو أقل وسأجيبك.",
                "grounded": False, "source": "guard"}
    # صمود: حتى بلا مفتاح أو بعد نفاد الحصّة، الطبقة القاعدية تُجيب النيّات
    # الشائعة من أرقامك الحقيقية — فالمساعد لا يصمت أبداً.
    from app.services.usage_tracker import can_call, record
    from app.services.ai_chat_rules import rule_based_answer as _rules
    llm_ready = bool(settings.AI_API_KEY) and can_call("gemini")
    if not llm_ready:
        ctx0 = await build_light_context(db, question)
        ruled0 = await _local_answer(db, question, ctx0)
        if ruled0:
            return {"reply": _strip_markup(ruled0), "grounded": True, "source": "rule"}
        why = ("لم يُضبط مفتاح الذكاء الاصطناعي في الإعدادات"
               if not settings.AI_API_KEY else "بلغت الحصّة اليومية للذكاء الاصطناعي")
        return {"reply": f"{why}. أستطيع الإجابة عن: أداء محفظتك · صافي ربحك وعائد "
                         "محفظتك · أفضل وأضعف مراكزك · الحوكمة · أداء القطاعات · "
                         "أعلى التوزيعات · شرح مصطلحات التطبيق ومنهجياته.",
                "grounded": False, "source": "rule"}

    # الطبقة القاعدية أولاً **بسياقٍ خفيف**: أرقام محسوبة في بايثون (لا خطأ
    # حسابي ولا هلوسة) وإجابة فورية. بناء السياق الكامل يُؤجَّل إلى ما بعد
    # فشلها — فلا يدفع سؤالٌ بسيط ثمن سياقٍ لن يُقرأ.
    #
    # **إلا حين يُطلب النموذج صراحةً** (`prefer_llm`): قناة صقر تمرّ من هنا،
    # وقوالبُ الطبقة القاعدية فيها تُقرأ «ثابتةً مبتذلة» — وهو حكم المالك.
    # فمن سأل صقر يريد جواباً يفهم سؤاله لا قالباً يطابق نيّةً معدودة.
    # والقاعدية تبقى شبكةَ أمان: إن غاب المفتاح أو نفدت الحصّة رجعنا إليها
    # قبل هذا السطر أصلاً.
    if not prefer_llm:
        light = await build_light_context(db, question)
        ruled = await _local_answer(db, question, light)
        if ruled:
            return {"reply": _strip_markup(ruled), "grounded": True, "source": "rule"}

    # لم تُطابق أي نيّة → النموذج التوليدي، وهو وحده من يحتاج كل شيء.
    ctx = await build_context(db, question)

    # ── الاقتطاع بالأولوية لا بالترتيب ────────────────────────────────────
    # السياق يتجاوز الحدّ بكثير (≈٩٠ ألف حرف مقابل ٦٠ ألفاً)، وكان يُقصّ من
    # آخره فتسقط **معرفة التطبيق** كاملةً — وهي مصدر الشرح الوحيد للنموذج،
    # فيصير يشرح منهجية التطبيق تخميناً. وتسقط معها الحوكمة والتوزيعات.
    # فنُقدّم ما لا يُستغنى عنه، ونقصّ الضخم منخفض القيمة أولاً.
    PRIORITY = ["المحفظة", "قياس الأداء", "فحص السلامة", "معرفة التطبيق",
                "ملخّص المحفظة", "الأهداف", "حوكمة المحفظة", "العائد",
                "الدخل والتوزيعات", "التوزيعات المستلمة", "آخر الصفقات",
                "حركة النقد", "إحصاءات المحفظة", "صحّة المحفظة",
                "مقاييس المخاطر", "خريطة القطاعات"]
    ordered = {k: ctx[k] for k in PRIORITY if k in ctx}
    for k, v in ctx.items():
        if k not in ordered:
            ordered[k] = v

    LIMIT = 60000
    ctx_json = json.dumps(ordered, ensure_ascii=False, default=str)
    if len(ctx_json) > LIMIT:
        # نُسقط الأقلّ أولويةً كتلةً كتلة بدل بتر النصّ في منتصف قيمة —
        # فيبقى ما يصل النموذجَ **صالحاً للقراءة** لا JSON مقطوعاً.
        keys = list(ordered.keys())
        dropped: list[str] = []
        while keys and len(ctx_json) > LIMIT:
            victim = keys.pop()
            dropped.append(victim)
            ordered.pop(victim, None)
            ctx_json = json.dumps(ordered, ensure_ascii=False, default=str)
        if dropped:
            ordered["مصادر مُستبعَدة لضيق المساحة"] = dropped
            ctx_json = json.dumps(ordered, ensure_ascii=False, default=str)
        logger.info(f"chat: اقتُطعت {len(dropped)} كتلة سياق — {', '.join(dropped)}")

    convo = ""
    for m in (history or [])[-MAX_HISTORY:]:
        role = "المستخدم" if m.get("role") == "user" else "المساعد"
        convo += f"\n{role}: {m.get('content', '')}"

    prompt = (f"{SYSTEM_RULES}\n\n"
              f"=== بيانات التطبيق (مصدرك الوحيد) ===\n{ctx_json}\n"
              f"=== نهاية البيانات ===\n"
              f"{('سياق المحادثة السابقة:' + convo) if convo else ''}\n\n"
              f"سؤال المستخدم: {question}\n\nالإجابة:")

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.AI_MODEL}:generateContent?key={settings.AI_API_KEY}")
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1200}}
    try:
        record("gemini")
        # **ميزانية الزمن يجب أن تقلّ عن مهلة الواجهة** (60ث)، وإلا قطع
        # المتصفّح الاتصال والخادم ما زال يعمل — فيقرأ المالك «تعذّر الاتصال
        # بالخادم» والخادم بخير. عشرون ثانية تكفي النموذج، وما تجاوزها
        # يُردّ برسالةٍ صادقة بدل انتظارٍ مفتوح.
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(url, json=body)
        if r.status_code != 200:
            logger.warning(f"chat: Gemini HTTP {r.status_code} — {r.text[:200]}")
            if prefer_llm:
                fb = await _fallback_rules(db, question, "تعذّر الوصول لخدمة الذكاء")
                if fb:
                    return fb
            return {"reply": "تعذّر الوصول لخدمة الذكاء الآن. أعد المحاولة بعد قليل.", "grounded": False}
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # الأرقام الهندية ممنوعة في التطبيق كلّه — نُطبّعها هنا أيضاً.
        text = re.sub(r"[٠-٩]", lambda m: str(ord(m.group()) - 0x0660), text)
        text = _strip_markup(text)
        return {"reply": text, "grounded": True, "source": "ai"}
    except httpx.TimeoutException:
        logger.warning("chat: تجاوز النموذج مهلة العشرين ثانية")
        if prefer_llm:
            fb = await _fallback_rules(db, question, "تأخّر الذكاء عن المهلة")
            if fb:
                return fb
        return {"reply": "تأخّر الذكاء في الردّ فتجاوز المهلة. أعد سؤالك، أو "
                         "اسألني بصيغةٍ أقرب لبياناتك (مثل «حلّل سهم …» أو "
                         "«ما أداء محفظتي؟») فأجيبك فوراً من أرقامك بلا انتظار.",
                "grounded": False, "source": "timeout"}
    except Exception as e:
        logger.warning(f"chat failed: {e}")
        if prefer_llm:
            fb = await _fallback_rules(db, question, "تعذّر توليد الإجابة")
            if fb:
                return fb
        return {"reply": "تعذّر توليد الإجابة الآن.", "grounded": False}
