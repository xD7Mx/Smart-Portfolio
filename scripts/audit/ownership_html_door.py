"""كاشفُ D270 (قراءةٌ فقط) — شكلُ ما تعيده نداءاتُ الملكية في «تداول». قِيس (‏ownership_url_door · run 38583314249): الصفحةُ تُقرأ
والنداءاتُ الثلاثة موجودة، لكنّها **تعيد أجزاءَ HTML لا JSON** — ‏foreginOwnerShip قِطعةٌ ‏<div> ‏(~3 آلاف حرف)، و
historicalBoardMembersWithDates جدولٌ (تاريخُ التداول · المساهم · الصفة · الأسهمُ المملوكة …)، و‏historyOfMajorShareHolder يردّ 500
بلا معاملات. والقارئُ يفترض JSON فيسقط صامتاً. فيطبع: القطعةَ الأولى كاملةً مضغوطةَ الفراغ، ورأسَ الجدول وأوّلَ صفوفه وعددَها،
وسياقَ كلّ نداءٍ في شيفرة الصفحة (ما يُمرَّر له)، ومحاولاتِ النداء الثالث بالمعاملات المرئيّة هناك.

    docker exec sp_backend python /app/scripts/audit/ownership_html_door.py
"""
import asyncio
import os
import re
import sys

os.environ.setdefault("TZ", "Asia/Riyadh")      # كخادم التطبيق (main.py) — فتعمل اللقطةُ في عمليةٍ مستقلّة
sys.path.insert(0, "/app")


def squash(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


async def main():
    import time
    if hasattr(time, "tzset"):
        time.tzset()
    from app.services import tadawul_ownership as TO
    from app.services.tadawul_http import fetch
    sym = "1120"
    page = await TO.company_page(sym)
    print(f"@@PAGE@@ {sym} · {len(page or '')} حرفاً")
    if not page:
        return
    base = TO._BASE_RE.search(page).group(1).rstrip("/")
    eps = {m.group(1): m.group(0) for m in TO._EP_RE.finditer(page)}
    for name in ("foreginOwnerShip", "historicalBoardMembersWithDates", "historyOfMajorShareHolder"):
        print(f"\n@@CTX@@ {name}")
        for m in list(re.finditer(re.escape(name), page))[:4]:
            print("   …" + squash(page[max(0, m.start() - 260):m.end() + 420])[:700] + "…")
    st, raw = await fetch(f"{base}/{eps['foreginOwnerShip']}", params={"requestLocale": "en"}, referer=base)
    print(f"\n@@FOREIGN@@ حالة {st} · {len(raw or '')}\n{squash(raw)[:4000]}")
    await asyncio.sleep(0.8)
    st, raw = await fetch(f"{base}/{eps['historicalBoardMembersWithDates']}", params={"requestLocale": "en"}, referer=base)
    trs = re.findall(r"<tr\b.*?</tr>", raw or "", re.S | re.I)
    print(f"\n@@BOARD@@ حالة {st} · {len(raw or '')} · صفوف {len(trs)}")
    for tr in trs[:6]:
        cells = [squash(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[hd]\b.*?</t[hd]>", tr, re.S | re.I)]
        print("   |", " | ".join(cells))
    print("   خامٌ لأوّل صفّ بيانات:", squash(trs[1])[:900] if len(trs) > 1 else "—")
    dates = sorted({squash(re.sub(r"<[^>]+>", " ", c)) for tr in trs[1:] for c in re.findall(r"<td\b.*?</td>", tr, re.S | re.I)[:1]})
    print(f"   تواريخُ أوّل عمود: {len(dates)} · {dates[:3]} … {dates[-3:]}")
    # ‏النداءُ الثالث: يُجرَّب بالمعاملات الشائعة لصفحات «تداول» — والصحيحُ ما يقوله سياقُ الشيفرة أعلاه
    from datetime import date
    for params in ({"requestLocale": "en", "symbol": sym}, {"requestLocale": "en", "companySymbol": sym},
                   {"requestLocale": "en", "symbol": sym, "fromDate": "2024-01-01", "toDate": date.today().isoformat()}):
        await asyncio.sleep(0.8)
        st, raw = await fetch(f"{base}/{eps['historyOfMajorShareHolder']}", params=params, referer=base)
        print(f"\n@@MAJOR@@ {params} · حالة {st} · {len(raw or '')} · {squash(raw)[:600]!r}")


asyncio.run(main())
