"""كاشفُ D704 (قراءةٌ فقط): دليلُ السوق الرئيسيّ كما تنشره «تداول» مقابل دليل التطبيق — بأمر المالك 2026-10-14:
«اجعل تداول مصدرَك ومصدرَ التطبيق… المهمّ أن اسمَ الشركة وقطاعَها يظهر من تداول حتى يكون التطبيقُ مواكباً للشركات الجديدة
والمنقولة والموقوفة… لتعرف شركاتِ السوق الرئيسيّ وليس نمو».

يقرأ صفحتَي «السوق الرئيسية» و«نمو» بالعربية والإنجليزية (خدمةُ الجدول نفسُها)، ويطبع: حقولَ الصفّ كما وصلت، والجديدَ في «تداول»
وليس في التطبيق، وما يعدّه التطبيقُ رئيسيّاً وليس في صفحتها، وما تنقله «تداول» إلى الرئيسية والتطبيقُ يعدّه «نمو» (حكمُ البادئة 9)،
وفرقَ القطاع والاسم العربيّ.

    docker exec sp_backend python /app/scripts/audit/tadawul_directory_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")


async def main():
    from app.services.tadawul_market import PAGE, NOMU_PAGE, fetch_rows
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market, market_of
    td: dict[str, dict] = {}
    for page, mk in ((PAGE, "main"), (NOMU_PAGE, "nomu")):
        for loc in ("ar", "en"):
            rows, why = await fetch_rows(page, locale=loc)
            print(f"@@PAGE@@ {mk} {loc} · صفوف {len(rows or [])} · {why or 'تمّ'}")
            if rows:
                r0 = rows[0]
                print(f"   الحقول: {sorted(r0)[:60]}")
                print(f"   عيّنة: { {k: r0.get(k) for k in ('companySymbol', 'companyRef', 'companyName', 'companyFullName', 'sectorName', 'sectorId', 'marketType', 'market') if k in r0} }")
            for r in rows or []:
                m = re.search(r"\b(\d{4})\b", str(r.get("companySymbol") or r.get("companyRef") or ""))
                if not m:
                    continue
                e = td.setdefault(m.group(1), {"mk": set()})
                e["mk"].add(mk)
                e[f"name_{loc}"] = " ".join(str(r.get("companyName") or "").split()) or None
                e[f"sector_{loc}"] = " ".join(str(r.get("sectorName") or "").split()) or None
            await asyncio.sleep(1.0)
    t_main = {s for s, e in td.items() if "main" in e["mk"]}
    t_nomu = {s for s, e in td.items() if "nomu" in e["mk"]}
    app_main = set(main_market(MU))
    print(f"\n@@COUNT@@ «تداول» الرئيسية {len(t_main)} · نمو {len(t_nomu)} · في الاثنتين {len(t_main & t_nomu)} · "
          f"التطبيق: الكون {len(MU)} · الرئيسيّ {len(app_main)}")
    new = sorted(t_main - set(MU))
    print(f"@@NEW@@ في رئيسية «تداول» وليست في التطبيق أصلاً {len(new)}: "
          + " · ".join(f"{s} {td[s].get('name_ar')} ({td[s].get('sector_ar')})" for s in new[:30]))
    moved = sorted(s for s in t_main if s in MU and market_of(s) != "main" and s not in app_main)
    print(f"@@MOVED@@ في رئيسية «تداول» والتطبيقُ يعدّها غيرَ رئيسية {len(moved)}: "
          + " · ".join(f"{s} {td[s].get('name_ar')}" for s in moved[:30]))
    stray = sorted(app_main - t_main)
    print(f"@@STRAY@@ يعدّها التطبيقُ رئيسيّةً وليست في صفحة «تداول» الرئيسية {len(stray)}: "
          + " · ".join(f"{s} {(MU.get(s) or {}).get('name_ar')}{' [نمو]' if s in t_nomu else ''}" for s in stray[:40]))
    both = sorted(t_main & app_main)
    from app.services.tadawul_sync import canon_sector, official_name
    sec = [s for s in both if td[s].get("sector_ar") and (MU.get(s) or {}).get("sector") != canon_sector(td[s]["sector_ar"])]   # بعد توحيد الإملاء
    print(f"@@SECTOR@@ قطاعُ التطبيق يخالف «تداول» {len(sec)} من {len(both)}: "
          + " · ".join(f"{s} {(MU.get(s) or {}).get('sector')} ← {td[s]['sector_ar']}" for s in sec[:25]))
    try:
        from app.services.tadawul_sync import official_overlay
        ov = official_overlay()
    except Exception:                                              # noqa: BLE001
        ov = {}
    nm = [s for s in both if td[s].get("name_ar") and (ov.get(s) or (MU.get(s) or {}).get("name_ar")) !=
          official_name(td[s]["name_ar"])]
    print(f"@@NAME@@ الاسمُ المعروض يخالف «تداول» {len(nm)} من {len(both)}: "
          + " · ".join(f"{s} {ov.get(s) or (MU.get(s) or {}).get('name_ar')} ← {td[s]['name_ar']}" for s in nm[:15]))
    secs = sorted({td[s].get("sector_ar") for s in t_main if td[s].get("sector_ar")})
    print(f"@@SECTORS@@ قطاعاتُ «تداول» الرئيسية {len(secs)}: {secs}")


asyncio.run(main())
