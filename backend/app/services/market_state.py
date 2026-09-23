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
  ٢· **المؤشّرُ الذي لا يتحرّك** — شاهدٌ لا يحتاج معجماً: قيمةُ «تاسي»
     تتحرّك كلَّ دقيقةٍ في جلسةٍ حيّة. فإن بقيت ثابتةً في طور «مفتوح»
     نافذةً كاملة، فالسوقُ **لا يتداول اليوم** مهما قال التقويم (‏D426).
     وكان هذا الشاهدُ يقرأ `as_of` — فقِيس يومَ العطلة أنّه `currentTime`
     أي **الوقتُ الحاليّ** لا زمنُ آخرِ صفقة، فلا يتجمّد أبداً.
  ٣· **الساعة** — احتياطٌ أخيرٌ يُعلَن مصدرُه، لا حاكمٌ أوّل.

ويُعاد مع الحالةِ **دليلُها** دائماً، فلا تُقرأ كلمةٌ بلا سندها.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime

from loguru import logger

# نافذةُ الثبات: مؤشّرٌ لم يتحرّك داخل الجلسة هذه الدقائقَ كلَّها لا
# يتداول. والمؤشّرُ في جلسةٍ حيّةٍ يتحرّك كلَّ دقيقة، فالنافذةُ واسعةٌ
# بما يكفي ألّا تحكم بعطلةٍ على هدوءٍ عابر.
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


def _observe(code, phase: str, feed_at, price=None) -> None:
    """يسجّل المشاهدةَ ليُبنى المعجمُ من القياس. والفشلُ لا يُسقط الحكم."""
    try:
        os.makedirs(os.path.dirname(_OBS), exist_ok=True)
        with open(_OBS, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "at": _mecca_now().isoformat(timespec="minutes"),
                "code": code, "clock_phase": phase, "feed_at": feed_at,
                "price": price,
            }, ensure_ascii=False) + "\n")
    except Exception as e:                                        # noqa: BLE001
        logger.debug(f"تسجيلُ حالةِ السوق تعذّر: {type(e).__name__}: {e}")


def _today_obs(now: datetime, tail: int = 800) -> list[dict]:
    """مشاهداتُ اليوم من آخر السجلّ — لا يُقرأ الملفُّ كلُّه في كلّ سؤال."""
    day = now.date().isoformat()
    try:
        with open(_OBS, encoding="utf-8") as f:
            lines = f.readlines()[-tail:]
    except OSError:
        return []
    out = []
    for ln in lines:
        try:
            r = json.loads(ln)
        except Exception:                                         # noqa: BLE001
            continue
        if str(r.get("at") or "").startswith(day):
            out.append(r)
    return out


def frozen_index_verdict(obs: list[dict], now: datetime,
                         phase: str) -> dict | None:
    """«عطلة» إن ثبت مؤشّرُ اليوم داخل الجلسة نافذةً كاملة — وإلا None.

    ══ الشاهدُ قيمةُ المؤشّر لا «الوقتُ الحاليّ» ══ (D426)
    قِيس يومَ اليوم الوطنيّ — أوّلِ عطلةٍ حقيقيةٍ يُختبر عليها الكشف:
    «زمنُ التغذية» تغيّر ‎32 مرّةً داخل ساعات الجلسة، لأنّ الحقلَ
    `currentTime` هو الوقتُ الحاليُّ للخادم لا زمنُ آخرِ صفقة. فقال
    التطبيقُ «السوق مفتوح» طوالَ جلسةِ يومِ عطلة.

    فالحكمُ هنا على **قيمة المؤشّر** في مشاهداتِ **اليوم** وفي طور
    «مفتوح» وحدَه (ما قبل الافتتاح ثابتٌ في كلّ يومٍ بطبعه): إن تحرّكت
    فهو يومُ تداول، وإن ثبتت ‎`FEED_LAG_MIN` دقيقةً فأكثرَ فلا جلسةَ اليوم.
    وبعد الجرس يبقى الحكمُ «عطلة» ليومٍ ثبتت عطلتُه — فالمغلقُ يفتح غداً
    بعد ساعات، والعطلةُ يومٌ لم يُفتح أصلاً.
    """
    day = now.date().isoformat()
    sel = []
    for o in obs or []:
        at = str(o.get("at") or "")
        px = o.get("price")
        if (at.startswith(day) and o.get("clock_phase") == "open"
                and isinstance(px, (int, float)) and px > 0):
            try:
                sel.append((datetime.fromisoformat(at), round(float(px), 2)))
            except ValueError:
                continue
    if len(sel) < 2:
        return None
    if len({p for _, p in sel}) > 1:
        return None                           # المؤشّرُ تحرّك: يومُ تداول
    sel.sort()
    span = (sel[-1][0] - sel[0][0]).total_seconds() / 60.0
    if span < FEED_LAG_MIN:
        return None                           # ثباتٌ أقصرُ من النافذة
    if phase not in ("open", "preclose", "closed"):
        return None
    return {
        "status": "holiday",
        "source": "مؤشّرُ تداولَ ثابتٌ داخل الجلسة",
        "evidence": (f"«تاسي» {sel[0][1]:,.2f} لم يتحرّك من "
                     f"{sel[0][0]:%I:%M %p} إلى {sel[-1][0]:%I:%M %p} "
                     f"({span:.0f} دقيقةً في {len(sel)} مشاهدة) — "
                     f"فلا جلسةَ اليوم"),
        "clock_phase": phase,
        "holiday_suspected": True,
    }


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
    price = idx.get("price")
    if code is not None or price is not None:
        _observe(code, phase, feed_at, price)

    # ── ١ · معجمُ المصدر، إن ثبت ──────────────────────────────────────
    mapped = CODE_MAP.get(str(code)) if code is not None else None
    if mapped:
        return {"status": mapped, "source": "تداول — حالةُ السوق",
                "evidence": f"رمزُ الحالة {code}",
                "clock_phase": phase, "code": code}

    # ── ٢ · المؤشّرُ الذي لا يتحرّك — شاهدٌ بلا معجم ─────────────────
    # ══ وفرقٌ بين «مغلق» و«عطلة» ══ (بأمر المالك)
    # «مغلق» حالٌ طبيعيةٌ في يومِ تداولٍ بعد الجرس أو قبله. و«عطلة»
    # **لا جلسةَ فيها أصلاً** — المغلقُ يفتح بعد ساعات، والعطلةُ يومٌ
    # كاملٌ لا سعرَ فيه ولا صفقة. فخلطُهما يُفقد المستثمرَ خبراً.
    v = frozen_index_verdict(_today_obs(now), now, phase)
    if v:
        v["code"] = code
        return v

    # ── ٣ · الساعةُ احتياطاً مُعلَناً ─────────────────────────────────
    return {"status": phase, "source": "ساعةُ الخادم (احتياط)",
            "evidence": ("لم يثبت معنى رمزِ الحالة بعدُ ولم يثبت مؤشّرٌ"
                         " ثابتٌ داخل الجلسة"
                         if code is not None
                         else "لم يصل رمزُ الحالة من المصدر"),
            "clock_phase": phase, "code": code}
