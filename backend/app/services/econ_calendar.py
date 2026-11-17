"""الأحداثُ الاقتصاديةُ الأمريكيةُ وأثرُها (‏D761 · بأمر المالك 2026-11-17).

قال المالك: «لازم يكون أيُّ حدث، أيُّ خبر — مثلاً خبرٌ جللٌ اليوم كالفيدرالي — وما الأثر؟ تفسيرٌ للأثر وتحليل: ماذا أتوقّع؛ إذا رُفعت
الفائدة هل يتضرّر السوق — إلى كول أو بوت».

المصدر: تقويمُ ‏ForexFactory الأسبوعيّ (‏`nfs.faireconomy.media/ff_calendar_thisweek.json`) — قِيس على الخادم 2026-11-17: 125 حدثاً
بالعنوان والبلد والوقت (بتوقيت نيويورك) والأهمية والتوقّع والسابق، **بلا الرقم الفعليّ** — فلا يُقال «صدر كذا»؛ بل يُقال ما يقيسه الحدث
وسيناريواه: إن جاء فوق التوقّع فكذا، ودونه فكذا، وميلُ كلٍّ منهما (عقودُ شراء · عقودُ بيع). والقراءةُ من النموذج على العنوان والتوقّع
والسابق وحدها، بعلاقاتٍ اقتصاديةٍ عامّة لا بأرقامٍ مخترعة؛ وتُخبَّأ ستّ ساعات.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from loguru import logger

FEED = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
RY = ZoneInfo("Asia/Riyadh")
IMPACT_AR = {"High": "عالٍ", "Medium": "متوسّط", "Low": "منخفض", "Holiday": "عطلة"}

READ = """أنت اقتصاديٌّ يشرح لمتداولِ خياراتٍ أمريكيّ أثرَ الأحداث الاقتصادية الأمريكية القادمة. لكلّ حدثٍ أدناه: عنوانُه ووقتُه وأهميّتُه
والتوقّعُ والسابق (إن وُجدا). لا تذكر رقماً غيرَ المعطى، ولا تدّعِ نتيجةً لم تصدر. لكلّ حدثٍ أعطِ:
- ar: اسمُه بالعربية (قصير)
- what: ماذا يقيس ولماذا يهمّ السوق — جملةٌ واحدة
- above: إن جاء أعلى من التوقّع (أو تشدّد المتحدّث): الأثرُ المرجّح على الأسهم الأمريكية والعوائد — جملة
- above_lean: ميلُ الخيارات على مؤشّر الأسهم في هذه الحالة: "call" أو "put" أو "neutral" — ويطابق جملةَ above
- below: إن جاء أدنى من التوقّع (أو تيسّر المتحدّث): الأثرُ المرجّح — جملة
- below_lean: الميلُ في هذه الحالة: "call" أو "put" أو "neutral" — ويطابق جملةَ below
JSON فقط: {"ID": {"ar": "...", "what": "...", "above": "...", "above_lean": "...", "below": "...", "below_lean": "..."}}

"""


def _blocking_get(url: str) -> tuple[int, str]:
    from curl_cffi import requests as cr
    with cr.Session(impersonate="chrome") as s:
        r = s.get(url, timeout=15)
    return r.status_code, r.text or ""


async def raw_week() -> list[dict]:
    """أحداثُ الأسبوع كما هي من المصدر — مخبّأةٌ نصفَ ساعة؛ و[] عند التعذّر."""
    from app.services import cache
    hit = cache.get("econ:ff:week")
    if hit is not None:
        return hit
    try:
        st, txt = await asyncio.to_thread(_blocking_get, FEED)
        items = json.loads(txt) if st == 200 else None
    except Exception as e:                                        # noqa: BLE001
        logger.warning("الأحداثُ الاقتصادية: {}", type(e).__name__)
        items = None
    if not isinstance(items, list):
        return []
    cache.set("econ:ff:week", items, 1800)
    return items


def shape(items: list[dict], now: datetime | None = None, impacts=("High", "Medium")) -> list[dict]:
    """الأحداثُ الأمريكيةُ المهمّة: وقتُها بالرياض، وحالُها (مضى · اليوم · قادم) والوقتُ الباقي، مرتّبةً بالوقت."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(RY).date()
    out = []
    for it in items or []:
        if it.get("country") != "USD" or it.get("impact") not in impacts:
            continue
        try:
            t = datetime.fromisoformat(str(it.get("date")))
        except ValueError:
            continue
        loc = t.astimezone(RY)
        eid = hashlib.md5(f"{it.get('title')}|{it.get('date')}".encode()).hexdigest()[:10]
        out.append({"id": eid, "title": it.get("title"), "impact": it.get("impact"), "impact_ar": IMPACT_AR.get(it.get("impact"), it.get("impact")),
                    "at": t.astimezone(timezone.utc).isoformat(timespec="seconds"), "riyadh": loc.strftime("%Y-%m-%d %H:%M"),
                    "day": "اليوم" if loc.date() == today else "غداً" if loc.date() == today + timedelta(days=1) else "أمس" if loc.date() == today - timedelta(days=1)
                    else loc.strftime("%d/%m"),
                    "past": t < now, "forecast": it.get("forecast") or None, "previous": it.get("previous") or None})
    out.sort(key=lambda e: e["at"])
    return out


async def analysis(events: list[dict]) -> dict:
    """قراءةُ الأثر لكلّ حدثٍ مهمّ (مخبّأةٌ ستّ ساعاتٍ ببصمة القائمة) — و{} إن تعذّر النموذج (فيُعرض الحدثُ بلا قراءة، ويُقال ذلك)."""
    from app.services import cache
    from app.services import research_desk as RD
    todo = [e for e in events if not e["past"] or e["day"] == "اليوم"][:24]
    if not todo:
        return {}
    key = "econ:read2:" + hashlib.md5("|".join(e["id"] for e in todo).encode()).hexdigest()[:12]
    hit = cache.get(key)
    if hit is not None:
        return hit
    lines = [f"{e['id']} · {e['title']} · {e['riyadh']} بتوقيت الرياض · أهمية {e['impact']}"
             + (f" · التوقّع {e['forecast']}" if e["forecast"] else "") + (f" · السابق {e['previous']}" if e["previous"] else "") for e in todo]
    try:
        obj = await RD._gemini([{"text": READ + "\n".join(lines)}], max_tokens=5000, temperature=0.2)
    except Exception as e:                                        # noqa: BLE001
        logger.warning("الأحداثُ الاقتصادية/القراءة: {}", type(e).__name__)
        obj = None
    if not isinstance(obj, dict):
        return {}
    L = ("call", "put", "neutral")
    ok = {k: {f: str(v.get(f) or "")[:260] for f in ("ar", "what", "above", "below")}
          | {"above_lean": v.get("above_lean") if v.get("above_lean") in L else "neutral", "below_lean": v.get("below_lean") if v.get("below_lean") in L else "neutral"}
          for k, v in obj.items() if isinstance(v, dict)}
    cache.set(key, ok, 6 * 3600)
    return ok


async def week(with_reading: bool = True) -> dict:
    ev = shape(await raw_week())
    read = await analysis(ev) if with_reading and ev else {}
    for e in ev:
        r = read.get(e["id"])
        if r:
            e.update(r)
    return {"events": ev, "read_ok": bool(read), "source": "ForexFactory", "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def before(events: list[dict], until: datetime, impact: str = "High") -> list[dict]:
    """الأحداثُ المهمّةُ القادمةُ قبل وقتٍ (انتهاءُ عقدٍ مثلاً)."""
    lim = until.astimezone(timezone.utc).isoformat()
    return [e for e in events if not e["past"] and e["impact"] == impact and e["at"] <= lim]
