#!/usr/bin/env python3
"""كاشفُ D806 على الخادم — «التقريرُ اليوميّ 24/11 بلا أخبارٍ محليةٍ ولا عالمية» (قراءةٌ لا تكتب شيئاً):

  ١ ما قُرئ من تقارير الجهات منذ 19/11: تاريخُه وجهتُه وصنفُه ونجحت قراءتُه أم لا ومتى.
  ٢ المذكّراتُ المحفوظة منذ 19/11: كم خبراً محلياً وعالمياً في كلٍّ.
  ٣ التقاريرُ المحفوظة لجلسات 20–24/11: عددُ المصادر، وكم خبراً محلياً وعالمياً ومركزاً ومتابعة، ووقتُ الكتابة.
  ٤ المصادرُ التي كان التقريرُ سيقرؤها لجلسة 24/11، وحالُ حصّة النموذج الآن.

    docker exec sp_backend python /app/scripts/audit/research_desk_door_d806.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import json  # noqa: E402
import sys  # noqa: E402
from datetime import date  # noqa: E402

sys.path.insert(0, "/app")


def main():
    from app.services import research_desk as RD
    k = RD.knowledge()
    floor = "2026-11-19"
    print("══ ١ ما قُرئ منذ", floor)
    rows = sorted([v for v in k["read"].values() if str(v.get("date") or "") >= floor], key=lambda v: (str(v.get("date")), str(v.get("at"))))
    for v in rows:
        print(f"   {v.get('date')} · {v.get('source')} · {v.get('kind')} · نجحت={v.get('ok')} · {v.get('at')} · {str(v.get('title') or '')[:60]}")
    print("   المجموع:", len(rows), "· فشلت:", sum(1 for v in rows if not v.get("ok")))
    print("══ ٢ المذكّرات منذ", floor)
    for n in sorted([n for n in k["notes"] if str(n.get("date") or "") >= floor], key=lambda n: str(n.get("date"))):
        print(f"   {n.get('date')} · {n.get('source')} · {n.get('kind')} · محليّ {len(n.get('local_news') or [])} · عالميّ {len(n.get('global_news') or [])}"
              f" · نقاط {len(n.get('points') or [])}")
    print("══ ٣ التقارير المحفوظة")
    d = os.path.join(RD._dir(), "reports")
    for f in sorted(os.listdir(d)):
        if f[:10] < "2026-11-20":
            continue
        try:
            r = json.load(open(os.path.join(d, f), encoding="utf-8"))
        except Exception as e:                                   # noqa: BLE001
            print("   ", f, "تعذّرت قراءتُه", type(e).__name__)
            continue
        print(f"   {f}: مصادر {r.get('n_sources')} · محليّ {len(r.get('local') or [])} · عالميّ {len(r.get('global') or [])}"
              f" · مراكز {len(r.get('portfolio') or [])} · متابعة {len(r.get('watch') or [])} · عنوان {'نعم' if r.get('headline') else 'لا'}"
              f" · كُتب {r.get('at')} · أرشيف={bool(r.get('backfill'))}")
    print("══ ٤ مصادرُ جلسة 2026-11-24")
    srcs = RD.recent_sources(k["notes"], date(2026, 11, 24))
    for n in srcs:
        print(f"   {n.get('date')} · {n.get('source')} · {n.get('kind')} · محليّ {len(n.get('local_news') or [])} · عالميّ {len(n.get('global_news') or [])}")
    print("   العدد:", len(srcs))
    from app.services.usage_tracker import can_call
    print("   حصّةُ النموذج تسمح الآن:", can_call("gemini"))
    from app.core.config import settings
    model = settings.AI_MODEL
    print("   النموذج:", model)
    print("══ ٥ تقريرُ المحفظة الافتراضية لآخر جلسة: نظرةُ صقر ومصدرُ النصّ وأوّلُ الأخبار")
    last = sorted(f for f in os.listdir(d) if f.endswith("_1.json"))[-1:]
    for f in last:
        r = json.load(open(os.path.join(d, f), encoding="utf-8"))
        m = r.get("market") or {}
        t, sq = m.get("tech") or {}, m.get("saqr") or {}
        print(f"   {f}: نظرتُنا (صقر) {t.get('view')} · الفنيُّ وحده {t.get('view_tech')} · شواهدُ صقر {len(sq.get('why') or [])} · محاور {len(sq.get('themes') or [])}"
              f" · مصدرُ النصّ {r.get('text_source') or 'قديم'} · سببُ التعذّر {r.get('ai_why') or '—'} · مصادر {r.get('n_sources')}")
        print("   العنوان:", (r.get("headline") or "—")[:120])
        for x in (r.get("local") or [])[:3]:
            print("   محليّ:", str(x.get("text"))[:110])
        for x in (r.get("global") or [])[:3]:
            print("   عالميّ:", str(x.get("text"))[:110])
    print("══ انتهى")


main()
