#!/usr/bin/env python3
"""كاشفُ قائمة صقر (‏D771) على الخادم — قراءةٌ وحدها: يطبع القائمةَ المحفوظةَ التي بنتها دورةُ صقر في الجلسة (كم عقداً، وأعلاها بإيجابياته
وسلبياته، وما استُبعد ولماذا). لا يبني — قيس: بناءٌ في عمليةٍ ثانيةٍ تحمل التطبيقَ كلَّه أنفد ذاكرةَ الخادم (رمز 137).

    docker exec sp_backend python /app/scripts/audit/saqr_list_door.py
"""
import sys

sys.path.insert(0, "/app")
from app.services import saqr_list as SL   # noqa: E402
from app.services import saqr_trader as SQ   # noqa: E402

st = SQ.load("us")
c = SQ.cfg(st)
print("الأوامر:", {k: c.get(k) for k in ("per_trade", "sides", "auto")}, "· المراكز:", [p["symbol"] for p in st["positions"]], "· النقد:", st["cash"],
      "· أوامرٌ معلّقة:", len(st.get("orders") or []), "· آخرُ دورة:", st.get("last_cycle"))
r = SL.load()
if not r:
    print("لا قائمةَ محفوظةً بعد — تُبنى في أوّل دورةٍ من الجلسة.")
    sys.exit(0)
print(f"══ {r.get('label')} · أُعدّت {r.get('at')} · {len(r.get('items') or [])} عقداً من {r.get('scanned')} ورقة (المجال {r.get('universe')}) · "
      f"بميزانية {r.get('budget')} · آخرُ جلسة={r.get('snap')} · محاولة={r.get('retry')} · صيغة={r.get('v')} · دفعة={r.get('batch')} "
      f"(جديدٌ {r.get('fresh')}) · يُكمل={r.get('more')}")
done = r.get("done") or {}
if done:                                           # ‏D774: سببُ كلّ سهمٍ بعينه — أوّلُ عشرين ممتنعاً
    print("أسبابُ الممتنعين:", "؛ ".join(f"{s}: {d['why']}" + (f" ({d['low']:.0f}$)" if d.get("low") else "")
                                       for s, d in list(done.items())[:40] if d.get("why"))[:2500])
print("استُبعد:", r.get("excluded"), "· أرخصُ صالحٍ فوق الميزانية:", r.get("cheapest"))
for i in (r.get("items") or [])[:20]:
    print(f"  {i['grade']} {i['symbol']:<6} {i['type']:<4} {i['strike']:>7g} {i['expiry']} ({i['dte']}ي) كلفة {i['cost']:>6.0f} · هدف {i['gain_target']:+d}٪ "
          f"· احتمال {i['pop']:.0f}٪ · 30٪ عند {i['tp30']['price']} ({i['tp30']['pct']}٪) · +{len(i['pros'])}/-{len(i['cons'])}")
if r.get("items"):
    i = r["items"][0]
    print("  إيجابياتُ الأوّل:", i["pros"])
    print("  سلبياتُه:", i["cons"])
