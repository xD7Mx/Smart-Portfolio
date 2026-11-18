#!/usr/bin/env python3
"""كاشفُ صقر على السوق الحيّ (‏D763 · ‏D764 السعوديّ): يطبع حالَ الجلسة، والأنشطَ اليوم من مُصفّي TradingView، وحجمَ المجال (الأسيلُ + الأنشط)،
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
    from app.services import saqr_universe as SU
    t0 = time.time()
    U = await SU.universe()
    print(f"المجالُ الكامل (‏D766): {U['meta']} · {time.time() - t0:.1f}ث")
    print("  أقوى المتين:", sorted(((v[0], k) for k, v in U["fund"].items()), reverse=True)[:12])
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


async def saudi():
    """‏D764: صقر السعوديّ — تاسي والأحداثُ والنتائجُ الربعية على بيانات الخادم، ودورةٌ تجريبيةٌ في دفترٍ مؤقّت إن كانت الجلسةُ مفتوحة."""
    from datetime import datetime, timezone
    from app.services import saqr_sa as SA
    from app.services import saqr_trader as SQ
    from app.services import tadawul_market as TM
    from app.services.live_quote import sessions
    real = SQ.load("sa")
    print("\n══ السوقُ السعوديّ ══")
    pu = real.get("pulse") or {}   # ‏D767: نبضُ السوق المحفوظ (قراءةُ الإغلاق أو آخرُ دورة) وأوامرُ المالك
    print("النبضُ المحفوظ:", {k: pu.get(k) for k in ("at", "adv", "dec", "unch", "turnover", "leaders", "laggards", "results", "quarter", "brent")} if pu else "غير متوفّر")
    print("الأوامر:", SQ.cfg(real), "· تاسي المحفوظ:", real.get("regime"))
    print("الدفترُ الحقيقيّ:", f"رأس المال {SQ.equity(real):,.2f} ريال · مراكز {len(real['positions'])} · مغلقة {len(real['closed'])} · آخرُ دورة {real.get('last_cycle')}")
    ses = (await sessions())["sa"]
    print("الجلسة:", ses.get("label"), "·", ses.get("detail"))
    t0 = time.time()
    reg = await SA.regime()
    print("تاسي:", {k: reg.get(k) for k in ("verdict", "close", "sma50", "sma200", "ret3m", "chg")} if reg else "غير متوفّر", f"{time.time() - t0:.1f}ث")
    t0 = time.time()
    g = await SA.geo()
    print("الأحداث:", g if g else "غير متوفّرة", f"{time.time() - t0:.1f}ث")
    today = datetime.now(timezone.utc).date()
    from collections import Counter
    from app.services import argaam_results as AR
    q = AR.results("quarter")
    cnt = Counter(SA.results_of(sym, today)[0] for sym in list(q)[:400])
    print("النتائجُ الربعية:", len(q), "شركة ·", dict(cnt), "· عيّنة:", [(s_, q[s_].get("date"), q[s_].get("change_pct")) for s_ in list(q)[:4]])
    snap = TM.snapshot()
    print("لقطةُ تداول الحيّة:", len(snap), "شركة")
    if ses.get("state") != "open" or not snap or not reg:
        print("لا دورةَ تجريبية: الجلسةُ مغلقة أو اللقطةُ غيرُ حيّة.")
        return
    tmp = tempfile.mkdtemp()
    os.environ["SP_STATE_DIR"] = tmp

    async def quiet(_t):
        return None
    SQ._notify = quiet
    st = SQ.fresh(market="sa")
    pos = await SA._hunt(st, datetime.now(timezone.utc), snap, reg, g)
    print("دورةٌ تجريبية:", st.get("scan_meta"))
    for x in st["signals"][:20]:
        print(f"  [{x['verdict']}] {x['sym']} {x.get('name') or ''} — {x['why']}")
    print("  ⇐", f"اشترى {pos['qty']} سهم من {pos['symbol']} بـ{pos['entry_px']}" if pos else "لا صفقة")
    os.environ["SP_STATE_DIR"] = REAL


async def both():
    await main()
    await saudi()


asyncio.run(both())
