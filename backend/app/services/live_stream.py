"""بثٌّ مباشرٌ للأسعار — دفعٌ لا سؤال (D290).

## ما طلبه المالك

«أريد الأرقام تتحرّك مثل التطبيق البنكيّ بدون تأخيرٍ نهائياً — صفرُ ثانية».

## لماذا لا يكفي الإسراع

السؤالُ الدوريُّ (‏polling) فيه تأخيرٌ **بنيويّ**: الرقمُ يصل الخادمَ في
لحظةٍ، وتسأل الشاشةُ بعدها — فالمنتظَرُ متوسّطُه نصفُ دورة. وتقصيرُ
الدورة لا يُلغي التأخير، بل يُضاعف الأسئلةَ عن رقمٍ لم يتغيّر.

فالحلُّ قلبُ الاتّجاه: **الخادمُ يدفع** فور وصول رقمٍ جديد. صفرُ انتظارٍ
من جهة التطبيق، وهو ما يفعله تطبيقُ البنك بعينه.

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

PUMP_INTERVAL = 1.0          # ثانيةٌ: أسرعُ ما تُعطيه التغذيةُ المفتوحة
HEARTBEAT = 15.0             # نبضةُ حياةٍ تمنع القطعَ الصامت
QUEUE_MAX = 8                # طابورُ كلّ مشترِك — القديمُ يُسقَط لا يُكدَّس
# ══ لكلّ اتّصالٍ عمرٌ أقصى ══
# مجرًى بلا سقفِ عمرٍ يبقى مفتوحاً إلى الأبد: يُقاس في التجربة أن إغلاقَه
# من جهة العميل قد لا يبلغ المولِّد، فيظلّ مشترِكاً «حاضراً» وهو منقطع —
# فتبقى المضخّةُ تعمل لمن لا يُشاهد. والسقفُ يُغلقه بأدبٍ، و`EventSource`
# في المتصفّح يعيد الوصلَ تلقائياً بلا أن يرى المستخدمُ شيئاً.
MAX_STREAM_SECONDS = 600.0

_subs: set[asyncio.Queue] = set()
_pump: asyncio.Task | None = None
_last: dict[str, tuple] = {}          # آخرُ ما دُفع لكلّ رمز — لحساب الفرق


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
    try:
        while _subs:
            if not _market_open():
                # مغلقٌ: نبضةُ حياةٍ فقط — لا نداءَ للمصدر
                await asyncio.sleep(HEARTBEAT)
                _publish({"hb": 1})
                continue
            try:
                await refresh()
            except Exception as e:                                # noqa: BLE001
                logger.debug("بثٌّ: تجديدٌ تعذّر {}: {}", type(e).__name__, e)
            changed = _diff(snapshot() or {})
            if changed:
                _publish({"t": datetime.now().strftime("%H:%M:%S"), "q": changed})
                idle = 0.0
            else:
                idle += PUMP_INTERVAL
                if idle >= HEARTBEAT:
                    _publish({"hb": 1})
                    idle = 0.0
            await asyncio.sleep(PUMP_INTERVAL)
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
        if first:
            yield "data: " + json.dumps(
                {"t": datetime.now().strftime("%H:%M:%S"), "q": first,
                 "live": bool(live), "at": at},
                ensure_ascii=False) + "\n\n"
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
