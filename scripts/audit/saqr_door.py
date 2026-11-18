#!/usr/bin/env python3
"""كاشفُ صقر على السوق الحيّ (‏D763): يطبع حالَ الجلسة، والأنشطَ اليوم من مُصفّي TradingView، وحجمَ المجال (الأسيلُ + الأنشط)،
وبوّاباتِ الدخول الآن والأحداثَ العالية الأثر — ثمّ إن كان السوقُ في جلسته دورةً كاملةً **في دفترٍ مؤقّت** (لا يمسّ دفترَ صقر الحقيقيّ
ولا محفظةَ المالك ولا يرسل تلغرام) بإشاراتها: من قُبل ومن رُفض وبأيّ سبب، وأيُّ عقدٍ اختير وبكم. وآخرُه حالُ الدفتر الحقيقيّ مختصراً.

    docker exec sp_backend python /app/scripts/audit/saqr_door.py
"""
import asyncio, os, sys, tempfile, time   # noqa: E401
os.environ["TZ"] = "Asia/Riyadh"; time.tzset()
sys.path.insert(0, "/app")
sys.stdout.reconfigure(line_buffering=True)
REAL = os.environ.get("SP_STATE_DIR", "/app/storage")


async def main():
    from datetime import datetime, timezone
    from app.services import saqr_trader as SQ
    from app.services.econ_calendar import raw_week, shape
    from app.services.live_quote import sessions
    real = SQ.load()
    print("الدفترُ الحقيقيّ:", f"رأس المال {SQ.equity(real):,.2f} · نقد {real['cash']:,.2f} · مراكز {len(real['positions'])} · مغلقة {len(real['closed'])}"
          f" · يعمل {real.get('on')} · آخرُ دورة {real.get('last_cycle')}")
    ses = (await sessions())["us"]
    print("الجلسة:", ses.get("label"), "·", ses.get("detail"), "·", ses.get("source"))
    t0 = time.time()
    mv = await SQ.movers()
    print(f"الأنشطُ اليوم (TradingView): {len(mv)} في {time.time() - t0:.1f}ث — {' '.join(mv[:25])}")
    t0 = time.time()
    tr, n_mv = await SQ.trends()
    up = sum(1 for t in tr.values() if t["state"] == "صاعد")
    dn = sum(1 for t in tr.values() if t["state"] == "هابط")
    print(f"المجال: {len(tr)} رمزاً (منها {n_mv} من الأنشط خارج القائمة) · صاعد {up} · هابط {dn} · {time.time() - t0:.0f}ث")
    now = datetime.now(timezone.utc)
    ev = shape(await raw_week(), impacts=("High",))
    print("أحداثٌ عالية الأثر قادمة:", [(e["title"], e["riyadh"]) for e in ev if not e["past"]][:6])
    print("بوّاباتُ الدخول الآن:", SQ.gates({**SQ.fresh(), "on": True}, now, SQ.us_clock(now), ev) or "مفتوحة")
    if ses.get("state") != "open":
        print("\nالسوقُ ليس في جلسته الرسمية — لا دورةَ تجريبية (صقرٌ لا يتداول على عرضٍ وطلبٍ قديمين).")
        return
    # دورةٌ كاملة في دفترٍ مؤقّت: البوّاباتُ الزمنيةُ تُتجاوز هنا وحدها ليُرى قرارُ الصيد نفسُه
    tmp = tempfile.mkdtemp()
    os.environ["SP_STATE_DIR"] = tmp

    async def quiet(_t):
        return None
    SQ._notify = quiet
    st = SQ.fresh()
    t0 = time.time()
    pos = await SQ._hunt(st, now)
    print(f"\n══ دورةٌ تجريبية بـ{st['capital']:.0f} دولار · {time.time() - t0:.0f}ث · {st.get('scan_meta')} ══")
    for s in st["signals"]:
        print(f"  [{s['verdict']}] {s['sym']} {s.get('side') or ''} — {s['why']}")
    if pos:
        print(f"\n  ⇐ اشترى {pos['qty']} × {pos['contract']} بسعر {pos['entry_px']} (الكلفة {pos['cost']}) · وقف {pos['stop']} · هدف {pos['target']}")
        for w in pos["why"]:
            print("     ·", w)
    else:
        print("\n  ⇐ لا صفقة: لم يستوفِ عقدٌ القواعد ضمن الميزانية.")
    os.environ["SP_STATE_DIR"] = REAL


asyncio.run(main())
