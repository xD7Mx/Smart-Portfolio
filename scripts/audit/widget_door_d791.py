#!/usr/bin/env python3
"""كاشفُ D791 على الخادم — ويدجت الآيفون (قراءةٌ لا تكتب شيئاً في القاعدة، ولا تطبع رمزاً ولا مبلغاً):

  ١ الطريقُ في الخادم الحيّ: ‏/widget/summary عامٌّ يرفض بلا رمز (‏401 برسالة الويدجت)، و‏/widget/token خلف جلسة المالك.
  ٢ رمزُ الويدجت: نافذٌ أم لا، ومتى أُنشئ، ومتى استُعمل آخرَ مرّة (يعرف المالكُ أنّ الويدجت يعمل) — لا التجزئةُ ولا التلميح.
  ٣ المحافظ: هل في القاعدة محفظةٌ «مؤرشفتُها» ‏NULL (عطبُ تمهيد القاعدة الجديدة)؟ والافتراضيةُ بمرشِّح التطبيق.
  ٤ الملخّصُ نفسُه على بيانات المالك — في جلسةٍ تُلغى في آخرها (الحفظُ يُستبدل بدفعٍ مؤقّت ثمّ ‏rollback): الثروةُ وصافي الربح
    وعائدُ المحفظة يساوي كلٌّ منها المقياسَ الموحّد (‏compute_net_profit) للمحفظة الافتراضية ولـ«كلّ المحافظ»، وما الحاضرُ
    من تغيّر اليوم وتاسي، وزمنُ الملخّص وحجمُه — ويُطبع «يساوي/لا يساوي» و«حاضر/غيرُ متوفّر» لا المبالغ.

    docker exec sp_backend python /app/scripts/audit/widget_door_d791.py
"""
import asyncio
import json
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from sqlalchemy import func, select
    from app.core.database import AsyncSessionLocal
    from app.models.portfolio import Portfolio

    print("══ ١ الطريقُ في الخادم الحيّ:")
    try:
        import httpx
        from main import app
        paths = {getattr(r, "path", "") for r in app.routes}
        summary_ok = "/api/v1/widget/summary" in paths
        manage_ok = "/api/v1/widget/token" in paths
        print(f"  الملخّصُ مسجَّل: {summary_ok} · إدارةُ الرمز مسجَّلة: {manage_ok}")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t/api/v1", timeout=60) as c:
            r1 = await c.get("/widget/summary")
            r2 = await c.get("/widget/token")
        d1 = r1.json() if r1.headers.get("content-type", "").startswith("application/json") else {}
        print(f"  بلا رمز: {r1.status_code} · رسالةُ الويدجت: {'رمزُ الويدجت' in json.dumps(d1, ensure_ascii=False)}"
              f" · إدارةُ الرمز بلا جلسة: {r2.status_code}")
    except Exception as e:                                                 # noqa: BLE001
        print(f"  تعذّر: {type(e).__name__}: {str(e)[:200]}")

    from app.api.v1.endpoints import widget as WG
    async with AsyncSessionLocal() as db:
        print("══ ٢ رمزُ الويدجت:")
        m = WG._meta(await WG._row(db))
        print(f"  نافذ: {bool(m)}" + (f" · أُنشئ {m.get('created')} · آخرُ استعمال {m.get('used') or 'لم يُستعمل بعد'}" if m else ""))

        print("══ ٣ المحافظ:")
        q = lambda s: db.execute(s.execution_options(skip_portfolio_scope=True))   # noqa: E731
        ps = (await q(select(Portfolio.id, Portfolio.is_default, Portfolio.is_archived, Portfolio.include_in_aggregate)
                      .order_by(Portfolio.id))).all()
        nul = sum(1 for p in ps if p.is_archived is None)
        dflt = (await q(select(Portfolio.id).where(Portfolio.is_archived.is_(False))
                        .order_by(Portfolio.is_default.desc(), Portfolio.id).limit(1))).scalar()
        print(f"  المحافظ {len(ps)} · مؤرشفتُها NULL: {nul} · الافتراضيةُ بمرشِّح التطبيق: {dflt}")
        for p in ps:
            print(f"  محفظة {p.id}: افتراضية {p.is_default} · مؤرشفة {p.is_archived} · في التوحيد {p.include_in_aggregate}")

    print("══ ٤ الملخّصُ على بيانات المالك (جلسةٌ تُلغى — لا يُكتب شيء):")
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.services.portfolio_return import compute_net_profit

    async def _pass(db, token):                                            # الرمزُ لا يُطلب هنا — والقاعدةُ لا تُمسّ
        return None
    WG._check = _pass
    for pf, label in ((None, "الافتراضية"), ("all", "كلّ المحافظ")):
        async with AsyncSessionLocal() as db:
            async def _flush():
                await db.flush()
            db.commit = _flush                                             # يُدفع إلى الجلسة ولا يُحفظ
            try:
                t0 = time.perf_counter()
                r = await WG.widget_summary(pf, None, db=db)
                ms = (time.perf_counter() - t0) * 1000
                d = (r or {}).get("data") or {}
                ids = [dflt] if pf is None else [p.id for p in ps if p.is_archived is False and p.include_in_aggregate is not False]
                refs = []
                for pid in ids:
                    set_scope(pid, False)
                    try:
                        refs.append(await compute_net_profit(db))
                    finally:
                        reset_scope()
                w = round(sum(x.get("wealth") or 0 for x in refs), 2)
                cost = round(sum(x.get("cost_basis") or 0 for x in refs), 2)
                nps = [x.get("net_profit") for x in refs]
                npf = round(sum(nps), 2) if nps and all(v is not None for v in nps) else None
                ret = round(npf / cost * 100, 2) if (npf is not None and cost > 0) else None
                known = sum(1 for h in d.get("holdings") or [] if isinstance(h.get("change_pct"), (int, float)))
                print(f"  {label}: محافظ {len(ids)} · حيازات {d.get('count')} · الثروة = المقياس الموحّد: {abs((d.get('wealth') or 0) - w) < 0.01}"
                      f" · صافي الربح = : {d.get('net_profit') == npf} ({'حاضر' if npf is not None else 'غيرُ متوفّر'})"
                      f" · العائد = : {d.get('return_pct') == ret} ({'حاضر' if ret is not None else 'غيرُ متوفّر'})")
                print(f"     تغيّرُ اليوم: {'حاضر' if d.get('day_change') is not None else 'غيرُ متوفّر'} (بنسبةٍ معروفة {known} من أعلى {len(d.get('holdings') or [])})"
                      f" · تاسي: {'حاضر' if d.get('tasi') else 'غيرُ متوفّر'} · الزمن {ms:.0f}ms · الحجم {len(json.dumps(d, ensure_ascii=False).encode())}B")
            except Exception as e:                                         # noqa: BLE001
                print(f"  {label}: تعذّر — {type(e).__name__}: {str(e)[:300]}")
            finally:
                await db.rollback()
                reset_scope()


asyncio.run(main())
