"""حالةُ السوق من مصدرها لا من ساعة الحائط (‏D413).

    from app.services.market_state import market_state
    st = await market_state()      # {"status", "source", "evidence", ...}

## لماذا

قال المالك: «اليومَ كان عطلةً للسوق ولم يكتشف التطبيقُ ذلك». وكان
`/settings/clock` يحسب الحالةَ من **ساعة الحائط وحدَها**: الأحدُ إلى
الخميس «مفتوح» في أوقاته. فالأعيادُ والعطلُ الرسميةُ والإغلاقاتُ
الطارئةُ لا وجودَ لها في الحساب — ويومُ اليوم (‏اليومُ الوطنيّ) يومٌ
تداوليٌّ في نظرها.

وفي المقابل كنّا **نلتقط قولَ تداولَ نفسِه** ولا نقرؤه: حمولةُ المؤشّر
تحمل `marketStatusCode` منذ زمن، ولم يكن له قارئٌ في الخادم ولا الواجهة.

## وكيف بلا تخمينِ مفردات

قِيس على الخادم يومَ العطلة: `market_status_code = 3` الساعةَ ‎9:40،
والساعةُ تقول `pre`. ومشاهدةٌ واحدةٌ **لا تُنشئ معجماً**: قد يكون ‎3
«مغلق»، وقد يكون حالةَ ما-قبل-الافتتاح في يومٍ عاديّ. فالادّعاءُ هنا
اختلاق.

فالحكمُ يُبنى على ثلاثِ طبقاتٍ مُعلَنةِ الترتيب:

  ١· **معجمُ تداولَ المُتعلَّم**: يُسجَّل كلُّ رمزٍ يُشاهَد مع طور
     الساعة وتاريخه (`observed_codes`). وما لم يثبت معناه بمشاهدةٍ في
     يومٍ **حيٍّ** لا يُترجَم — فلا يُبنى حكمٌ على رقمٍ لا نعرفه.
  ٢· **التغذيةُ المتجمّدة** — شاهدٌ لا يحتاج معجماً: زمنُ المؤشّر
     (‏`as_of`) يتقدّم مع الجلسة الحيّة. فإن قالت الساعةُ «مفتوح» أو
     «ما قبل الافتتاح» وزمنُ المصدر متخلّفٌ عن الآن بأكثرَ من نافذةٍ
     معقولة، فالسوقُ **لا يتداول اليوم** مهما قال التقويم.
  ٣· **الساعة** — احتياطٌ أخيرٌ يُعلَن مصدرُه، لا حاكمٌ أوّل.

ويُعاد مع الحالةِ **دليلُها** دائماً، فلا تُقرأ كلمةٌ بلا سندها.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from loguru import logger

# نافذةُ تخلّفٍ مقبولةٌ لزمن المصدر داخل الجلسة. التغذيةُ تُحدَّث كلَّ
# دقائق، فتخلّفٌ يتجاوز هذا يعني توقّفاً لا بطئاً.
FEED_LAG_MIN = 25

_OBS = os.getenv("SP_STATUS_LOG", "/app/data/market_status_codes.jsonl")

# معجمُ تداولَ — **يُملأ بالقياس لا بالتخمين**. لا يُضاف رمزٌ هنا إلا
# بعد مشاهدتَين متّسقتَين على الأقلّ: واحدةٌ في يومٍ حيٍّ وأخرى خارجَه.
CODE_MAP: dict[str, str] = {}


def _mecca_now() -> datetime:
    """توقيتُ مكة **صراحةً** لا بحسب ضبط العملية (‏D416).

    كان يقرأ `datetime.now()` اتّكالاً على أنّ عمليةَ الخادم مضبوطةٌ على
    مكة. وهي كذلك في التطبيق، **لكن الكواشفَ تُشغَّل بـ`docker exec`**
    في عمليةٍ لا تمرّ بذلك الضبط فتقرأ UTC. فقارنتُ ساعةَ UTC بزمنِ
    مصدرٍ بتوقيت مكة، فخرج فرقُ ثلاثِ ساعاتٍ **ثابتاً** وقرأتُه
    «تغذيةً متجمّدةً ‎180 دقيقة» — فحكمتُ بالعطلة من فرقِ منطقةٍ زمنية.
    وصادف يومَ عطلةٍ فبدا الحكمُ صائباً، وهو أخطرُ ما يكون: دليلٌ كاذبٌ
    يؤيّده واقعٌ صادفَه.

    فالمنطقةُ تُسمّى صراحةً، وما لا يُعرف يسقط إلى الإزاحة الثابتة —
    ومكةُ لا تُغيّر توقيتَها موسمياً فالإزاحةُ ثابتةٌ حقّاً.
    """
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Riyadh")).replace(tzinfo=None)
    except Exception:                                             # noqa: BLE001
        from datetime import timedelta, timezone as _tz
        return (datetime.now(_tz.utc) + timedelta(hours=3)).replace(tzinfo=None)


def _parse_feed_time(raw) -> datetime | None:
    """`'12:39 PM'` ← وقتُ اليوم. ويُعاد None لما لا يُفهم — لا يُخمَّن."""
    s = str(raw or "").strip()
    m = re.match(r"^(\d{1,2}):(\d{2})\s*([AaPp])\.?[Mm]\.?$", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).lower()
    if h == 12:
        h = 0
    if ap == "p":
        h += 12
    n = _mecca_now()
    return n.replace(hour=h % 24, minute=mi, second=0, microsecond=0)


def _observe(code, phase: str, feed_at) -> None:
    """يسجّل المشاهدةَ ليُبنى المعجمُ من القياس. والفشلُ لا يُسقط الحكم."""
    try:
        os.makedirs(os.path.dirname(_OBS), exist_ok=True)
        with open(_OBS, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "at": _mecca_now().isoformat(timespec="minutes"),
                "code": code, "clock_phase": phase, "feed_at": feed_at,
            }, ensure_ascii=False) + "\n")
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"تسجيلُ حالةِ السوق تعذّر: {type(e).__name__}: {e}")


async def market_state() -> dict:
    """الحالةُ ومصدرُها ودليلُها. لا تُثير استثناءً أبداً."""
    from app.services.market_phase import market_phase

    now = _mecca_now()
    phase = market_phase((now.weekday() + 1) % 7,
                         now.hour * 60 + now.minute)

    idx: dict = {}
    try:
        from app.services.tadawul_market import index_quote
        idx = (await index_quote()) or {}
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"حالةُ السوق — لا حمولةَ مؤشّر: {type(e).__name__}: {e}")

    code = idx.get("market_status_code")
    feed_at = idx.get("as_of")
    if code is not None:
        _observe(code, phase, feed_at)

    # ── ١ · معجمُ المصدر، إن ثبت ──────────────────────────────────────
    mapped = CODE_MAP.get(str(code)) if code is not None else None
    if mapped:
        return {"status": mapped, "source": "تداول — حالةُ السوق",
                "evidence": f"رمزُ الحالة {code}",
                "clock_phase": phase, "code": code}

    # ── ٢ · التغذيةُ المتجمّدة — شاهدٌ بلا معجم ───────────────────────
    if phase in ("pre", "open", "preclose"):
        ft = _parse_feed_time(feed_at)
        if ft is not None:
            lag = abs((now - ft).total_seconds()) / 60.0
            if lag > FEED_LAG_MIN:
                # ══ وفرقٌ بين «مغلق» و«عطلة» ══ (بأمر المالك)
                # «مغلق» حالٌ طبيعيةٌ في يومِ تداولٍ بعد الجرس أو قبله.
                # و«عطلة» **لا جلسةَ فيها أصلاً** — والفرقُ يعني للمستثمر
                # شيئاً: المغلقُ يفتح بعد ساعات، والعطلةُ يومٌ كاملٌ لا
                # سعرَ فيه ولا صفقة. فخلطُهما في كلمةٍ واحدةٍ يُفقده خبراً
                # يحتاجه. وهذا الفرعُ لا يُبلَغ إلا **داخلَ ساعات الجلسة**
                # ومع تغذيةٍ متجمّدة — أي يومٌ كان يجب أن يتداول ولم يفعل.
                return {
                    "status": "holiday",
                    "source": "تغذيةُ تداولَ متجمّدة",
                    "evidence": (f"زمنُ المصدر {feed_at} والآن "
                                 f"{now:%I:%M %p} — تخلّفٌ {lag:.0f} دقيقة، "
                                 f"فلا جلسةَ اليوم"),
                    "clock_phase": phase, "code": code,
                    "holiday_suspected": True,
                }

    # ── ٣ · الساعةُ احتياطاً مُعلَناً ─────────────────────────────────
    return {"status": phase, "source": "ساعةُ الخادم (احتياط)",
            "evidence": ("لم يثبت معنى رمزِ الحالة بعدُ ولا تجمّدت التغذية"
                         if code is not None
                         else "لم يصل رمزُ الحالة من المصدر"),
            "clock_phase": phase, "code": code}
