#!/usr/bin/env python3
"""كاشفُ D782 على الخادم — قراءةٌ تقيس ما بُني ولا تكتب شيئاً في المحفظة:
  ١ أسعارُ «المؤشرات» السبعة من خدمة الأسعار نفسِها التي تقرؤها قوائمُ المراقبة (هل لكلٍّ سعر؟)
  ٢ أحداثُ السوقين الآن: عددُها واسمُها العربيّ (هل بقي حدثٌ بلا اسمٍ عربيّ؟) وقراءتُها، وأحداثُ أرامكو من مفكرتها
  ٣ السعرُ الحيُّ لسهمٍ أمريكيّ: مصدرُه وحالةُ الجلسة ومدّةُ خبئه (ثانيتان في الجلسة الرسمية)
  ٤ «تحليلُ الرسم» على لقطةٍ من شموع الخادم الحقيقية (نداءٌ واحدٌ للنموذج): هل قرأ، وكم أُسقط من قراءته لرقمٍ لا أصلَ له

    docker exec sp_backend python /app/scripts/audit/chart_d782_door.py
"""
import asyncio
import sys

sys.path.insert(0, "/app")


async def main():
    from app.api.v1.endpoints.market import INDICES_SEED
    from app.services.market_data import market_service as M
    from app.services import econ_calendar as EC, live_quote as LQ, chart_read as CR
    syms = [s for s, _ in INDICES_SEED]
    px = await M.get_prices(syms)
    print("══ ١ أسعارُ المؤشّرات:")
    for s, n in INDICES_SEED:
        p = px.get(s) or {}
        print(f"  {n} ({s}): {p.get('price', 'غير متوفّر')} · {p.get('change_pct', '—')}٪")
    print("══ ٢ الأحداث:")
    for mk, sym, nm in (("us", "", ""), ("sa", "2222.SR", "أرامكو السعودية")):
        w = await EC.week(market=mk, symbol=sym, name=nm)
        ev = w["events"]
        bare = [e["title"] for e in ev if not e.get("ar")]
        print(f"  [{mk}] {len(ev)} حدثاً · قراءةٌ {'متوفّرة' if w['read_ok'] else 'غير متوفّرة'} · بلا اسمٍ عربيّ: {bare or 'لا شيء'} · أحداثُ الشركة: {len(w['company'])}")
        for e in ev[:6]:
            print(f"     {e['riyadh']} · {e.get('ar') or e['title']} · {e['impact_ar']} · {e.get('above_lean', '—')}/{e.get('below_lean', '—')}")
        for c in w["company"][:4]:
            print(f"     الشركة: {c['date']} · {c['kind']} · {c['title'][:70]}")
    print("══ ٣ السعرُ الحيّ:")
    for s in ("NVDA", "SPY"):
        q = await LQ.live(s)
        st = (q.get("session") or {}).get("state")
        print(f"  {s}: {q.get('price')} · {q.get('source')} · الجلسة {st} · مؤجّل {q.get('delayed')} · الخبء {LQ.ttl_for(s, st, q.get('source'))} ث")
    print("══ ٤ تحليلُ الرسم:")
    bars = await M.get_bars("NVDA", "1d")
    rows = [b if isinstance(b, dict) else getattr(b, "__dict__", {}) for b in (bars or [])][-120:]
    rows = [r for r in rows if all(k in r for k in ("open", "high", "low", "close"))]
    if len(rows) < 30:
        print("  لا شموعَ كافيةٌ من الخادم لصنع لقطة — لم يُقَس")
        return
    fr = {"tf": "1d", "tf_ar": "يوم", "price": rows[-1]["close"], "shown": ["volume", "d7m"],
          "bars": [[str(r.get("date") or r.get("time")), r["open"], r["high"], r["low"], r["close"], r.get("volume") or 0] for r in rows],
          "levels": [{"kind": "swing", "label": "أعلى الفترة", "price": max(r["high"] for r in rows)},
                     {"kind": "swing", "label": "أدنى الفترة", "price": min(r["low"] for r in rows)}], "ind": {}}
    out = await CR.read({"symbol": "NVDA", "name": "NVIDIA", "market": "us", "frames": [fr]})
    if not out.get("ok"):
        print("  تعذّر النموذج — «تعذّر التحليلُ الآن»")
        return
    rd = out["reading"]
    print(f"  الاتجاه: {rd['bias']} · أُسقط {rd['dropped']} · المستويات {[(x['kind'], x['price']) for x in rd['levels']]}")
    print(f"  الخلاصة: {rd['headline']}")
    print(f"  الشراء: {rd['buy']}\n  البيع: {rd['sell']}")

asyncio.run(main())
