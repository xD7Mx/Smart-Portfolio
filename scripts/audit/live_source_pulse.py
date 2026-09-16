#!/usr/bin/env python3
"""هل المصدرُ نفسُه يتحرّك؟ — قياسٌ ببصمةٍ لا بظنّ (D325).

    docker exec sp_backend python /app/scripts/audit/live_source_pulse.py

قِيس في سجلّ المالك، والسوقُ مفتوح: «١ دفعةً في ١٠٠ ثانية · قراءةُ
المصدر ١١٨٩ مل.ث». فالمضخّةُ تنادي ستّين مرّةً ولا تجد رقماً تغيّر.
وثلاثةُ احتمالاتٍ لا يجوز الخلطُ بينها:

  ١· المصدرُ يردّ **الجسمَ نفسَه بالحرف** ⇒ ذاكرةٌ بيننا وبينه (بصمةٌ
     واحدةٌ لجسمين) — العطبُ في طبقةِ النقل لا في السوق.
  ٢· الجسمُ يتغيّر والأسعارُ ثابتة ⇒ المصدرُ يخدم لقطةَ إغلاقٍ أو جدولاً
     بطيءَ التحديث — فيُقال ذلك ولا يُوعَد بما لا يُنشَر.
  ٣· الأسعارُ تتغيّر ⇒ العطبُ عندنا بين القراءة والدفع.

فيُنادى المصدرُ مرّاتٍ متعاقبةً بفاصلٍ مقيس، وتُطبع لكلّ نداءٍ:
**بصمةُ الجسم**، وزمنُ المصدر إن نشره، وسعرُ ثلاثة رموزٍ نشطة. ثمّ
يُقال الحكمُ صريحاً.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import sys
import time

sys.path.insert(0, "/app")
sys.path.insert(0, "backend")

ROUNDS = int(sys.argv[1]) if len(sys.argv) > 1 else 5
GAP = float(sys.argv[2]) if len(sys.argv) > 2 else 3.0
WATCH = ("2222", "1120", "2010")


async def main() -> int:
    from app.services import tadawul_market as tm
    from app.services.market_phase import market_phase
    from datetime import datetime, timedelta, timezone

    # ══ ساعةُ الرياض لا ساعةُ الصندوق ══
    # طبعت الأداةُ أوّلَ مرّةٍ ‎10:53 وهي UTC: `docker exec` لا يحمل منطقةَ
    # الخادم، وخادمُ التطبيق على توقيت مكة. فكاد يُقرأ طورٌ خاطئ — وطورٌ
    # مقروءٌ من ساعةٍ غيرِ ساعة السوق عطبٌ سُجِّل قبلاً (D298).
    now = datetime.now(timezone(timedelta(hours=3)))
    phase = market_phase((now.weekday() + 1) % 7,
                         now.hour * 60 + now.minute)
    print(f"═ ساعةُ الرياض {now:%Y-%m-%d %H:%M:%S} · الطورُ «{phase}» ═")
    if phase == "closed":
        print("  (السوقُ مغلقٌ بحسب طورِ التطبيق — فثباتُ الرقم ليس عطباً.)")

    seen: list[dict] = []
    for i in range(ROUNDS):
        t0 = time.monotonic()
        rows, why = await tm.fetch_rows()
        ms = (time.monotonic() - t0) * 1000
        if why:
            print(f"  [{i+1}] تعذّر: {why}")
            seen.append({})
            await asyncio.sleep(GAP)
            continue
        blob = json.dumps(rows, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(blob.encode()).hexdigest()[:12]
        table = tm.normalize(rows)
        px = {s: (table.get(s) or {}).get("price") for s in WATCH}
        # زمنُ المصدر إن نشره في أيّ حقلٍ من حقوله — لا من ساعتنا.
        stamp = None
        if rows and isinstance(rows[0], dict):
            for k, v in rows[0].items():
                if re.search(r"time|date|updat", str(k), re.I) and v:
                    stamp = f"{k}={v}"
                    break
        print(f"  [{i+1}] {ms:,.0f} مل.ث · بصمة {digest} · "
              f"{len(table)} رمزاً · زمنُ المصدر {stamp or '—'}")
        print(f"       " + " · ".join(f"{s}:{px[s]}" for s in WATCH))
        seen.append({"digest": digest, "px": px, "stamp": stamp,
                     "clock": time.monotonic()})
        if i + 1 < ROUNDS:
            await asyncio.sleep(GAP)

    # ══ ورؤوسُ الجواب تُقرأ: ذاكرةُ وسيطٍ تُعلِن نفسَها ══
    # `Age` و`X-Cache` و`Cache-Control` تفرّق بين «وسيطٌ يُعيد جواباً
    # محفوظاً» وبين «مصدرٌ ينشر على إيقاعٍ». تُقرأ بالانتحال نفسِه.
    print("\n═ رؤوسُ جواب نقطة البيانات ═")
    try:
        from curl_cffi import requests as _cr

        from app.services.tadawul_http import fetch as _f
        st, page = await _f(tm.PAGE)
        mb = tm._BASE_RE.search(page or "")
        me = tm._EP_RE.search(page or "")
        if not (mb and me):
            print("  تعذّر: لم يُشتقَّ عنوانُ النقطة من الصفحة")
        else:
            url = mb.group(1).rstrip("/") + "/" + me.group(0)
            r = await asyncio.to_thread(
                lambda: _cr.get(url, params={"sectorParameter": "All",
                                             "iswatchListSelected": "NO",
                                             "requestLocale": "en"},
                                headers={"Referer": tm.PAGE},
                                impersonate="chrome", timeout=45))
            h = {k.lower(): v for k, v in dict(r.headers).items()}
            for k in ("date", "age", "cache-control", "expires", "etag",
                      "x-cache", "x-cache-hits", "via", "cf-cache-status",
                      "last-modified"):
                if k in h:
                    print(f"  {k}: {h[k]}")
            if not any(k in h for k in ("age", "x-cache", "cf-cache-status")):
                print("  (لا رأسَ ذاكرةٍ وسيطةٍ في الجواب)")
    except Exception as e:                                        # noqa: BLE001
        print(f"  تعذّر قراءةُ الرؤوس: {type(e).__name__}: {e}")

    good = [s for s in seen if s]
    print()
    if len(good) < 2:
        print("الحكم: لم تُقرأ قراءتان — انظر سببَ التعذّر أعلاه.")
        return 1
    # ══ وإيقاعُ النشر يُقاس لا يُوصَف ══
    # إن تغيّر زمنُ المصدر خلال الرصد قيل **بعد كم ثانيةٍ** تغيّر وبكم
    # خطوة — فيُعرف: مصدرٌ ينشر على إيقاعٍ أم جوابٌ محفوظٌ لا يتحرّك.
    steps = [(s["clock"] - good[0]["clock"], s["stamp"]) for s in good]
    marks = [t for i, (t, st) in enumerate(steps)
             if i and st != steps[i - 1][1]]
    if marks:
        print(f"زمنُ المصدر تغيّر بعد {marks[0]:.0f} ثانيةٍ من بدء الرصد"
              f" ({len(marks)} مرّةً في {steps[-1][0]:.0f} ثانية) — "
              "فهو ينشر على إيقاعٍ، والإيقاعُ هو السقفُ لا شاشتُنا.")
    else:
        print(f"زمنُ المصدر لم يتغيّر في {steps[-1][0]:.0f} ثانيةٍ من الرصد"
              f" (ثابتٌ على {good[-1]['stamp']}) — والرصدُ أقصرُ من إيقاعه"
              " إن كان له إيقاع، فيُعاد أطولَ قبل الحكم عليه.")

    digests = {s["digest"] for s in good}
    prices = {json.dumps(s["px"], sort_keys=True) for s in good}
    if len(digests) == 1:
        print("الحكم ١: **جسمٌ واحدٌ بالحرف** في كلّ النداءات. وهذا يحتمل"
              " أمرين لا واحداً: ذاكرةٌ وسيطةٌ تُعيد الجواب (تُعلِنها"
              " الرؤوسُ أعلاه)، أو مصدرٌ ينشر جدولَه على إيقاعٍ أطولَ من"
              " مدّة الرصد (يُعلِنه زمنُ المصدر المستديرُ ‎:00). فيُعاد"
              " الرصدُ سبعَ دقائقَ: `live_source_pulse.py 22 20`.")
        return 1
    if len(prices) == 1:
        print("الحكم ٢: الجسمُ يتغيّر والأسعارُ الثلاثةُ ثابتة — المصدرُ"
              " يخدم لقطةً بطيئةَ التحديث أو إغلاقاً. يُقال ذلك ولا"
              f" يُوعَد بما لا يُنشَر. (بصمات: {len(digests)})")
        return 1
    print(f"الحكم ٣: الأسعارُ تتغيّر في المصدر ({len(prices)} حالةً مختلفة)"
          " — فالعطبُ عندنا بين القراءة والدفع، ويُقاس هناك.")
    return 0


raise SystemExit(asyncio.run(main()))
