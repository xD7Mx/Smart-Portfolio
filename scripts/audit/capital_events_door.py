"""كاشف D674 (قراءةٌ فقط): هل في إفصاحات «تداول» شاهدٌ على نوع زيادة رأس المال لكلّ شركةٍ يخالف عددُ أسهم قوائمها السوق؟

قِيس (‏run 38419547711): 15 شركةً بين 15٪ ومرّةٍ ونصف، ولا حدثَ رأس مالٍ في قاعدة التطبيق ولا ربحيةَ سهمٍ في إعلاناتها.
فالمصدرُ المرشَّح قائمةُ إفصاحاتها نفسُها: عناوينُ «Bonus Shares» و«Rights Issue» و«Capital Increase» بتواريخها — يُقاس هنا كم
منها يحمل شاهداً وبأيّ لفظ، قبل أن يُبنى حصّادٌ يقرأ النسبةَ وسعرَ الطرح من نصّ الإفصاح. لا يُجلب نصٌّ هنا (قائمةٌ واحدةٌ لكلّ شركة).

    docker exec sp_backend python /app/scripts/audit/capital_events_door.py
"""
import asyncio
import re
import sys

sys.path.insert(0, "/app")

D674 = ["1214", "1324", "2010", "2250", "2330", "2380", "4004", "4061", "4150", "4327", "8012", "8030", "8050", "8070", "8180"]
PAT = re.compile(r"bonus|rights?\s+issue|right\s+shares|capital\s+(increase|decrease|reduction)|increas\w*\s+(its\s+|the\s+)?capital|"
                 r"reduc\w*\s+(its\s+|the\s+)?capital|منحة|حقوق\s+أولوية|زيادة\s+رأس|تخفيض\s+رأس", re.I)


async def main():
    from app.services.tadawul_disclosure import list_for
    found = 0
    for s in D674:
        try:
            rows = await list_for(s, 80)
        except Exception as e:                                     # noqa: BLE001
            print(f"{s} · تعذّر: {type(e).__name__}")
            continue
        hits = [r for r in rows if PAT.search(r.get("title") or "")]
        found += bool(hits)
        span = f"{rows[-1].get('date')} … {rows[0].get('date')}" if rows else "—"
        print(f"══ {s} · إفصاحات {len(rows)} ({span}) · رأسُ مال {len(hits)}")
        for r in hits[:6]:
            print(f"   {r.get('date')} · {str(r.get('title'))[:150]}")
        await asyncio.sleep(1.5)                                   # تمهّلٌ مع المصدر
    print(f"\n@@CAPEV@@ لها شاهدٌ في إفصاحاتها {found} من {len(D674)}")


asyncio.run(main())
