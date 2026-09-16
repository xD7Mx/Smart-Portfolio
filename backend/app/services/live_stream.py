"""بثٌّ مباشرٌ للأسعار — دفعٌ لا سؤال (D290).

## ما طلبه المالك

«أريد الأرقام تتحرّك مثل التطبيق البنكيّ بدون تأخيرٍ نهائياً — صفرُ ثانية».

## لماذا لا يكفي الإسراع

السؤالُ الدوريُّ (‏polling) فيه تأخيرٌ **بنيويّ**: الرقمُ يصل الخادمَ في
لحظةٍ، وتسأل الشاشةُ بعدها — فالمنتظَرُ متوسّطُه نصفُ دورة. وتقصيرُ
الدورة لا يُلغي التأخير، بل يُضاعف الأسئلةَ عن رقمٍ لم يتغيّر.

فالحلُّ قلبُ الاتّجاه: **الخادمُ يدفع** فور وصول رقمٍ جديد. صفرُ انتظارٍ
من جهة التطبيق، وهو ما يفعله تطبيقُ البنك بعينه.

## وسقفُ الفورية ليس عندنا — مقيسٌ لا موصوف (D326)

قِيس على خادم المالك والسوقُ مفتوح: جدولُ مراقبة السوق في «تداول» ينشر
كلَّ **أربعِ دقائقَ إلى خمس** — زمنُ المصدر انتقل ‎1:48:00 → ‎1:52:23 →
‎1:56:49، ورأسُ جوابه يقول `cache-control: public, max-age=300`، ولا
رأسَ ذاكرةٍ وسيطةٍ بيننا وبينه. فالآلةُ هنا تدفع في نصف ثانية، **والمصدرُ
لا يُنتج ما تدفعه**: «صفرُ ثانية» من هذا المصدر غيرُ ممكن، والأسعارُ
بالثانية تُباع باشتراك.

وما قيل قبلاً «تسعةُ تغيّراتٍ في ثلاث ثوان» كان قياساً على **مجرًى
مصنوعٍ في الفحص** لا على «تداول» — فالآلةُ هي التي قيست، لا المصدر.
ويبقى الدفعُ صواباً على كلّ حال: ما ينشره المصدرُ يصل الشاشةَ لحظةَ
وصوله بلا سؤالٍ ولا نصفِ دورةِ انتظار.

## البنية

  · **مضخّةٌ واحدة** (`_pump`) تُجدّد اللقطةَ كلَّ ثانيةٍ ما دام **أحدٌ
    يشاهد** والسوقُ مفتوح. ولو شاهد مئةُ مستخدمٍ فالمضخّةُ واحدة — لا
    نداءَ لكلّ مشترك.
  · **وتتوقّف وحدَها** حين ينفضّ الجميع أو يُغلق السوق: صفرُ نداءٍ في
    العطلة، وصفرٌ حين لا يُشاهد أحد.
  · **ولا يُدفَع إلا ما تغيّر**: الفرقُ فقط (رمزٌ ← سعرٌ ونسبة)، فالحزمةُ
    بايتاتٌ لا مئاتُ كيلوبايت.
  · **ونبضةُ حياةٍ** كلَّ خمسَ عشرةَ ثانيةً تمنع الوسائطَ من قطع الاتّصال
    الصامت.
  · **وكلُّ مشترِكٍ طابورٌ محدود**: مشترِكٌ بطيءٌ يُسقَط عنه الأقدمُ ولا
    يُكدَّس في الذاكرة.

## القاعدةُ التي لا تُخرَق

السعرُ المدفوعُ هو نفسُه سعرُ اللقطة — **منتِجٌ واحدٌ للمعنى الواحد**.
والبثُّ طريقُ تسليمٍ لا مصدرٌ ثانٍ: من انقطع عنه رجع إلى السؤال الدوريّ
فيرى الرقمَ نفسَه متأخّراً قليلاً، لا رقماً آخر.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

from loguru import logger

# ══ أرضيّةٌ لا تِكّةٌ ══ (D300)
# كانت الدورةُ «اقرأ ثمّ نَمْ ثانيةً»، فالفاصلُ الحقيقيُّ = ثانيةٌ **زائدَ**
# زمنِ القراءة (نصفُ ثانيةٍ أو أكثر لصفحة السوق كاملةً) — أي ثانيةٌ ونصفٌ
# بين رقمٍ ورقم. والآن: تُقاس القراءةُ ويُنام **ما تبقّى** من الأرضيّة
# فقط. فالفاصلُ نصفُ ثانيةٍ حين يُسعِف المصدر، لا ثانيةٌ ونصف.
PUMP_INTERVAL = 0.5         # أدنى فاصلٍ بين دورتين — لا نَومٌ فوق القراءة
# ══ إيقاعُ المصدر هو السقف — ولا يُطرَق بابٌ لا يُفتَح ══ (D326)
# قِيس على خادم المالك والسوقُ مفتوح: جدولُ مراقبة السوق في «تداول»
# ينشر كلَّ **أربعِ دقائقَ إلى خمس** (زمنُ المصدر: ‎1:48:00 → ‎1:52:23 →
# ‎1:56:49)، ورأسُ جوابه يقول `cache-control: public, max-age=300`. وكانت
# المضخّةُ تنادي المصدرَ كلَّ دورةٍ — نحو مئةٍ وسبعين نداءً في كلّ نافذةِ
# نشرٍ واحدة، كلُّها تعيد الجسمَ نفسَه بالحرف. وذلك لا يُسرّع رقماً،
# ويُعرّض المصدرَ والحجبَ لما لا فائدة فيه.
#
# فصار النداءُ بإيقاعٍ يليق بالمصدر (‎SOURCE_POLL)، والدفعُ يبقى **لحظةَ
# التغيّر** بدورةٍ سريعةٍ تقرأ المحفوظ. فتأخيرُ الاكتشاف لا يتجاوز
# ‎SOURCE_POLL على إيقاعٍ من مئتين وستّين ثانية — بعُشر النداءات.
SOURCE_POLL = 15.0
HEARTBEAT = 15.0             # نبضةُ حياةٍ تمنع القطعَ الصامت
QUEUE_MAX = 8                # طابورُ كلّ مشترِك — القديمُ يُسقَط لا يُكدَّس
# ══ لكلّ اتّصالٍ عمرٌ أقصى ══
# مجرًى بلا سقفِ عمرٍ يبقى مفتوحاً إلى الأبد: يُقاس في التجربة أن إغلاقَه
# من جهة العميل قد لا يبلغ المولِّد، فيظلّ مشترِكاً «حاضراً» وهو منقطع —
# فتبقى المضخّةُ تعمل لمن لا يُشاهد. والسقفُ يُغلقه بأدبٍ، و`EventSource`
# في المتصفّح يعيد الوصلَ تلقائياً بلا أن يرى المستخدمُ شيئاً.
MAX_STREAM_SECONDS = 600.0
# مهلةٌ تمنع مصدراً متعثّراً من تجميد الدفع (D299): تجديدٌ لا يعود في عشر
# ثوانٍ لا يصلح لمضخّةٍ دورتُها ثانية — يُعلَن تعذّره ويُتراجَع عنه.
REFRESH_WAIT = 10.0

_subs: set[asyncio.Queue] = set()
_pump: asyncio.Task | None = None
_last: dict[str, tuple] = {}          # آخرُ ما دُفع لكلّ رمز — لحساب الفرق
_idx_last: tuple | None = None        # وآخرُ ما دُفع من المؤشّر
_idx_task: asyncio.Task | None = None  # إيقاظُ المؤشّر — واحدٌ في الطريق


def _kick_index() -> None:
    """يوقظ تجديدَ المؤشّر ولا ينتظره — وواحدٌ في الطريق لا أكثر.

    ══ لا نداءَ في طريق الدفع ══ (D299)
    أوّلُ صياغةٍ انتظرت نداءَ المؤشّر داخل المضخّة بمهلة، فقِيس بالحارس أن
    الانتظارَ وحدَه استهلك عمرَ المجرى: دفعةٌ واحدةٌ بدل أربع. والقاعدةُ
    المكتوبةُ عندنا أصلاً: يُوقَظ التجديدُ ويُعاد فوراً بما في الذاكرة.
    """
    global _idx_task
    if _idx_task is not None and not _idx_task.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _idx_task = loop.create_task(_idx_once())


async def _idx_once() -> None:
    from app.services.tadawul_market import index_quote
    try:
        await asyncio.wait_for(index_quote(), 10.0)
    except Exception as e:                                        # noqa: BLE001
        logger.debug("بثٌّ: المؤشّرُ تعذّر {}: {}", type(e).__name__, e)


async def _index_push(net: bool = True) -> list | None:
    """المؤشّرُ يُدفَع كما تُدفَع الأسعار — أو None إن لم يتغيّر (D299).

    ══ لسانُ تاسي وبطاقةُ النبض كانا يسألان كلَّ دقيقة ══
    المجرى كان يحمل الأسعارَ وحدَها، فبقي المؤشّرُ على السؤال الدوريّ —
    وحين يعمل الدفعُ تُبطئ الشاشةُ سؤالَها إلى دقيقة. فالنتيجةُ رقمٌ
    يتجمّد في بطاقةٍ مكتوبٌ فيها «جلسةٌ مباشرة». والمعنى الواحدُ يُدفَع
    من المنتِج الواحد: `index_quote` بذاكرتها (‏`INDEX_TTL`) — فالنداءُ
    للمصدر كلَّ ثلاث ثوانٍ لا كلَّ دورةِ مضخّة.
    """
    global _idx_last
    from app.services import cache
    from app.services.tadawul_market import INDEX_KEY

    rec = cache.get(INDEX_KEY)
    if not isinstance(rec, dict):
        # الذاكرةُ فارغةٌ: يُوقَظ التجديدُ ولا يُنتظَر — ويصل في الدورة
        # التالية. ومَن يفتح المجرى لا يوقظ شيئاً (`net=False`).
        if net:
            _kick_index()
        return None
    if not isinstance(rec, dict) or rec.get("price") is None:
        return None
    key = (rec.get("price"), rec.get("change_pct"))
    if _idx_last == key:
        return None
    _idx_last = key
    return [rec.get("price"), rec.get("change_pct")]


def subscribers() -> int:
    return len(_subs)


def _market_open() -> bool:
    from app.services.market_phase import market_phase
    now = datetime.now()
    return market_phase((now.weekday() + 1) % 7,
                        now.hour * 60 + now.minute) != "closed"


def _diff(rows: dict) -> dict:
    """ما تغيّر فقط: {رمز: [سعر، نسبة]}. وأوّلُ دفعةٍ كاملةٌ بطبعها."""
    out: dict[str, list] = {}
    for sym, r in (rows or {}).items():
        if not isinstance(r, dict):
            continue
        p, c = r.get("price"), r.get("change_pct")
        if p is None:
            continue
        key = (p, c)
        if _last.get(sym) != key:
            _last[sym] = key
            out[sym] = [p, c]
    return out


def _publish(payload: dict) -> None:
    dead = []
    for q in list(_subs):
        try:
            if q.full():
                q.get_nowait()            # الأقدمُ يُسقَط — لا تكديس
            q.put_nowait(payload)
        except Exception:                                         # noqa: BLE001
            dead.append(q)
    for q in dead:
        _subs.discard(q)


async def _pump_loop() -> None:
    """يُجدّد ويدفع ما دام أحدٌ يشاهد. ويتوقّف وحدَه."""
    from app.services.tadawul_market import refresh, snapshot

    logger.info("🔴 بثُّ الأسعار: مضخّةٌ بدأت ({} مشترك)", len(_subs))
    idle = 0.0
    fails = 0
    reads = 0
    pushes = 0
    calls = 0          # نداءاتُ المصدر — تُعلَن كي يُقاس الإيقاع
    t0 = asyncio.get_event_loop().time()
    try:
        while _subs:
            cycle = asyncio.get_event_loop().time()
            if not _market_open():
                # مغلقٌ: نبضةُ حياةٍ فقط — لا نداءَ للمصدر
                await asyncio.sleep(HEARTBEAT)
                _publish({"hb": 1})
                continue
            # لا يُنادى المصدرُ إلا إن شاخ المحفوظُ بمقدار إيقاعه (D326).
            from app.services.tadawul_market import age_seconds
            age = age_seconds()
            due = age is None or age >= SOURCE_POLL
            try:
                if due:
                    await asyncio.wait_for(refresh(), REFRESH_WAIT)
                    calls += 1
                if fails:
                    logger.info("🔴 بثُّ الأسعار: التجديدُ عاد بعد {} تعذّراً", fails)
                fails = 0
            except Exception as e:                                # noqa: BLE001
                # ══ صمتٌ لا يُغتفَر ══ (D299)
                # كان يُسجَّل DEBUG. فإن رفض المصدرُ التجديدَ تجمّدت الأرقامُ
                # كلُّها والشاشةُ تقول «جلسةٌ مباشرة» — **وفي السجلّ لا شيء**.
                # فعطبٌ يُسكِت الميزةَ كلَّها يُعلَن، ويُتراجَع عن الإغراق.
                fails += 1
                if fails in (1, 5) or fails % 30 == 0:
                    logger.warning("🔴 بثُّ الأسعار: التجديدُ تعذّر {} مرّةً — {}: {}",
                                   fails, type(e).__name__, e)
            payload: dict = {}
            reads += 1
            changed = _diff(snapshot() or {})
            if changed:
                payload["q"] = changed
            idx = await _index_push()
            if idx:
                payload["i"] = idx
            if payload:
                payload["t"] = datetime.now().strftime("%H:%M:%S")
                _publish(payload)
                pushes += 1
                idle = 0.0
            else:
                idle += PUMP_INTERVAL
                if idle >= HEARTBEAT:
                    _publish({"hb": 1})
                    idle = 0.0
            # ══ الإيقاعُ يُقاس ويُعلَن ══ (D300)
            # لا يُوصَف الزمنُ بالكلام: يُطبع كم دفعةً في كم ثانيةً وكم
            # يستغرق نداءُ المصدر — فيُقرأ الإيقاعُ الحقيقيُّ من السجلّ.
            spent = asyncio.get_event_loop().time() - cycle
            if reads % 60 == 0:
                span = asyncio.get_event_loop().time() - t0
                logger.info("🔴 بثُّ الأسعار: {} دفعةً في {:.0f} ثانية · "
                            "{} نداءً للمصدر · قراءتُه {:.0f} مل.ث · "
                            "عمرُ المحفوظ {}",
                            pushes, span, calls, spent * 1000,
                            f"{age:.0f}ث" if age is not None else "—")
            if fails:
                # تراجعٌ عند التعذّر: مصدرٌ يرفض لا يُطرَق بلا فائدة.
                await asyncio.sleep(PUMP_INTERVAL + min(fails, 5) * 2)
            else:
                # وما تبقّى من الأرضيّة فقط — والقراءةُ الطويلةُ لا تُضاف.
                await asyncio.sleep(max(0.0, PUMP_INTERVAL - spent))
    finally:
        logger.info("⚪ بثُّ الأسعار: مضخّةٌ توقّفت")


def _ensure_pump() -> None:
    global _pump
    if _pump is not None and not _pump.done():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _pump = loop.create_task(_pump_loop())


async def stream():
    """مولِّدُ أحداثٍ لمشترِكٍ واحد — يُغلَق طابورُه حتماً عند الانقطاع."""
    q: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_MAX)
    _subs.add(q)
    _ensure_pump()
    started = asyncio.get_event_loop().time()
    try:
        # ══ نبضةٌ فوريةٌ قبل كلّ شيء ══
        # قِيس على الخادم: `curl` على المجرى طبع **صفرَ أسطر** في اثنتَي
        # عشرةَ ثانية. والسببُ أن أوّلَ ما يُرسَل كان معلّقاً على وجود
        # بياناتٍ؛ فإن لم تكن (سوقٌ مغلقٌ ولقطةٌ غيرُ حيّة) لم يخرج حرفٌ
        # حتى نبضةِ الحياة بعد خمسَ عشرةَ ثانية. فصار أوّلُ شيءٍ يخرج
        # **تعليقَ حياةٍ فوراً**: يُثبت أن المجرى قائمٌ للعميل وللوسيط في
        # اللحظة الأولى، سواءٌ كان في السوق رقمٌ أم لا.
        yield ": open\n\n"

        # ثمّ الحالةُ الحاضرةُ: **بالقاعدة نفسِها التي تقرأ بها كلُّ شاشة**
        # (‏`usable_rows` — حيٌّ في الجلسة وآخرُ إغلاقٍ خارجَها). وكان
        # يُقرأ `snapshot()` الصارمُ وحدَه، فيبقى المجرى صامتاً يومَي
        # العطلة ويُظنّ معطوباً وهو سليم. ويُعلَن **أحيٌّ هو**.
        from app.services.tadawul_market import usable_rows
        rows, live, at = usable_rows()
        first = {s: [r.get("price"), r.get("change_pct")]
                 for s, r in (rows or {}).items()
                 if isinstance(r, dict) and r.get("price") is not None}
        # والمؤشّرُ في الدفعة الأولى أيضاً: بطاقةُ النبض تملأ فوراً ولا
        # تنتظر دورةَ مضخّةٍ ولا سؤالاً دورياً (D299).
        # من الذاكرة فقط: لا نداءَ للمصدر في طريق فتح المجرى.
        try:
            first_idx = await _index_push(net=False)
        except Exception:                                         # noqa: BLE001
            first_idx = None
        if first or first_idx:
            body = {"t": datetime.now().strftime("%H:%M:%S"),
                    "live": bool(live), "at": at}
            if first:
                body["q"] = first
            if first_idx:
                body["i"] = first_idx
            yield "data: " + json.dumps(body, ensure_ascii=False) + "\n\n"
        while asyncio.get_event_loop().time() - started < MAX_STREAM_SECONDS:
            try:
                payload = await asyncio.wait_for(q.get(), timeout=HEARTBEAT * 2)
            except asyncio.TimeoutError:
                yield ": hb\n\n"                      # تعليقٌ يُبقي الاتّصال
                continue
            if payload.get("hb"):
                yield ": hb\n\n"
                continue
            yield "data: " + json.dumps(payload, ensure_ascii=False) + "\n\n"
    finally:
        _subs.discard(q)
