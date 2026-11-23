#!/usr/bin/env python3
"""كاشفُ D787 على الخادم (قراءةٌ لا تكتب إلا خبءَ القراءة):

قال المالك (2026-11-23): «سلسلةُ العقود في الفرص ما تفتح — إيش المشكلة؟»، و«وطني للحديد والصلب ما وجدتُ لها رمزاً… وصورةُ الشركة ما هي موجودة».
وفي المتصفّح ببياناتٍ مصنوعة تُفتح السلسلةُ وتُرسم — فيُقاس هنا ما لا تحمله البياناتُ المصنوعة:

  ١ سلسلةُ كلّ فرصةٍ أمريكيةٍ محفوظة: هل تعود من ياهو؟ بكم أجلاً وعقداً، وفي كم ثانية — ونقطةُ الواجهة نفسُها.
  ٢ دليلُ «تداول» المحفوظ: «حديد وطني» برمزيها (1325 · 9513)، وما في الرئيسية بلا اسمٍ أو شعارٍ في دليلنا.
  ٣ الشعار: ما يعيده خادمُنا للسعوديّ الذي لا تعرفه خريطةُ الشعارات.

    docker exec sp_backend python /app/scripts/audit/opps_chain_door.py
"""
import asyncio
import sys
import time

sys.path.insert(0, "/app")


async def main():
    from app.services import chart_scan as CS
    from app.services.options_chain import chain
    d = CS.load("us") or {}
    items = d.get("items") or []
    syms = [x["symbol"] for x in items][:12]
    print(f"══ ١ سلسلةُ عقود فرص الأمريكيّ — المحفوظُ {d.get('at')} · فرصٌ {len(items)} · يُقاس {len(syms)}")
    for s in syms:
        t0 = time.monotonic()
        why = None
        try:
            c = await asyncio.wait_for(chain(s), 30)
        except Exception as e:                                    # noqa: BLE001
            c, why = None, f"{type(e).__name__}: {e}"
        dt = time.monotonic() - t0
        if c:
            print(f"  {s}: آجال {len(c.get('expirations') or [])} · شراء {len(c.get('calls') or [])} · بيع {len(c.get('puts') or [])} · السعر {c.get('price')} · {dt:.1f} ث")
        else:
            print(f"  {s}: لا سلسلة ({why or 'None'}) · {dt:.1f} ث")
    try:
        from app.api.v1.endpoints.market import option_chain
        for s in syms[:4]:
            t0 = time.monotonic()
            r = await option_chain(s)
            data = r.get("data") if isinstance(r, dict) else None
            print(f"  نقطةُ الواجهة /market/options/{s}: {'بيانات' if data else 'فارغة'} · {(r or {}).get('message')} · {time.monotonic() - t0:.1f} ث")
    except Exception as e:                                        # noqa: BLE001
        print(f"  نقطةُ الواجهة: تعذّر {type(e).__name__}: {e}")

    print("══ ٢ دليلُ «تداول» المحفوظ:")
    from app.services.tadawul_sync import directory
    dd = directory() or {}
    print(f"  محفوظٌ {dd.get('at')} · الرئيسية {len(dd.get('main') or {})} · نمو {len(dd.get('nomu') or {})} · غائبٌ {len(dd.get('gone') or {})}")
    for s in ("1325", "9513"):
        print(f"  {s}: الرئيسية {(dd.get('main') or {}).get(s)} · نمو {(dd.get('nomu') or {}).get(s)} · غائبٌ منذ {(dd.get('gone') or {}).get(s)}")
    from app.data.saudi_directory import SAUDI_DIRECTORY
    print(f"  دليلُنا في الخادم: 1325 {SAUDI_DIRECTORY.get('1325')} · 9513 {SAUDI_DIRECTORY.get('9513')}")
    main = dd.get("main") or {}
    no_logo = [s for s in main if not (SAUDI_DIRECTORY.get(s) or {}).get("logo")]
    print(f"  في الرئيسية بلا شعارٍ في دليلنا: {len(no_logo)} — {no_logo[:30]}")
    nomu = dd.get("nomu") or {}
    moved = [s for s, v in SAUDI_DIRECTORY.items() if s not in main and s not in nomu and v.get("name")]
    print(f"  في دليلنا وغائبٌ عن الصفحتين: {len(moved)} — {moved[:30]}")

    print("══ ٣ الشعار من خادمنا:")
    from app.services import symbol_logo as SL
    for s in ["1325.SR"] + [f"{x}.SR" for x in no_logo[:4] if x != "1325"]:
        try:
            got = await asyncio.wait_for(SL.fetch_logo(s), 30)
        except Exception as e:                                    # noqa: BLE001
            got, s = None, f"{s} (تعذّر {type(e).__name__})"
        print(f"  {s}: {(got[0] + ' · ' + str(len(got[1])) + ' بايت') if got else 'لا شعار'}"
              + (f" · باسمها في الدليل: {SL._sa_logo_by_name(s.split('.')[0])}" if hasattr(SL, "_sa_logo_by_name") else " · (‏D787 لم يُنشر بعد)"))

asyncio.run(main())
