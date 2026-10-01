"""اختبارٌ شاملٌ للمستشار قبل أن يراه المالك — **بلا إرسالٍ إليه** (D567–D572).

يبني ورقةَ الأسبوع لكلّ محفظة، ويسأل صقرَ أسئلةَ المالك عبر المسار نفسِه الذي يمرّ به التطبيقُ وتلغرام،
ويُشغّل المتابعة، ويتحقّق من اتصال تلغرام بـgetMe (لا رسالة)، ويقيس زمنَ كلّ خطوة، ويفحص كلَّ جوابٍ آلياً:
بلا أرقامٍ هندية، ولا أسماءِ حقولٍ إنجليزية، ولا «محقّقة» لخسارةٍ قائمة، ولا تحيّة، ويُختم بسطر القرار.

    docker exec sp_backend python /app/scripts/audit/advisor_e2e.py
"""
import asyncio
import re
import sys
import time

sys.path.insert(0, "/app")

QS = ["مراجعة الأسبوع",
      "هل اضخ في الراجحي ريت في هذا المستوى السعري؟",
      "ماذا عن سدافكو هل اغيره بالمراعي او انتظر؟",
      "هل لجرير بديل افضل؟",
      "اريد الاكتفاء بثماني شركات، ما الذي اتخلص منه؟",
      "بع لي سدافكو",
      "كم النقد المتاح؟"]
BAD = [(r"[٠-٩]", "أرقامٌ هندية"), (r"\b(new_target|current_weight|target_weight|action|tranches|why)\b", "حقلٌ إنجليزيّ"),
       (r"خسارة[^.\n]{0,12}محقّ?قة(?! عند البيع)", "«محقّقة» لخسارةٍ قائمة"), (r"^(أهلاً|مرحباً|السلام)", "تحيّة")]


def lint(txt: str, needs_end: bool) -> list[str]:
    out = [n for p, n in BAD if re.search(p, txt or "", re.M)]
    if needs_end and "القرار" not in (txt or "")[-120:] and "القرارُ" not in (txt or "")[-120:]:
        out.append("بلا سطر القرار في الختام")
    return out


async def main():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.portfolio_scope import reset_scope, set_scope
    from app.models.portfolio import Portfolio
    from app.services.advisor_weekly import review
    from app.services.ai_chat import answer
    fails = 0
    async with AsyncSessionLocal() as db:
        ps = (await db.execute(select(Portfolio.id, Portfolio.name).where(Portfolio.is_archived.is_(False)).order_by(Portfolio.id))).all()
        for pid, name in ps:
            set_scope(pid, False)
            t0 = time.time()
            try:
                r = await review(db)
            finally:
                reset_scope()
            issues = lint(r["text"], True)
            fails += bool(issues)
            print(f"@@WEEKLY@@ {name}: {len(r['rows'])} مراكز · {round(time.time() - t0)}ث · {len(r['text'])} حرفاً · خلاصة={'نعم' if r.get('summary') else 'لا'} · عيوب={issues}")
            print(r["text"][:1800])
            print("-" * 30)
        set_scope(ps[0][0], False)
        try:
            for q in QS:
                t0 = time.time()
                res = await answer(db, q, prefer_llm=True)
                dt = round(time.time() - t0, 1)
                needs = res.get("source", "").startswith("advisor")
                issues = lint(res.get("reply"), needs)
                slow = dt > 45
                fails += bool(issues) or slow
                print(f"@@Q@@ {q} · المصدر={res.get('source')} · {dt}ث{' ⚠ بطيء' if slow else ''} · عيوب={issues}")
                print((res.get("reply") or "")[:900])
                print("-" * 30)
        finally:
            reset_scope()
    from app.services.advisor_memory import watch
    from app.services import lastgood
    print("@@ADVICES@@", len(lastgood.keys_with_prefix("advice:")), "@@WATCH@@", await watch())
    from app.services.saqr_bot import bot
    me = await bot._call("getMe") if bot.token else None
    print("@@TELEGRAM@@ مفعّل" if bot.enabled else "@@TELEGRAM@@ غيرُ مفعّل", "· البوت:", (me or {}).get("username"))
    lr = lastgood.load("know:_last_run")
    print("@@READER_LAST@@", lr)
    print("@@RESULT@@", "PASS" if not fails else f"FAIL {fails}")


asyncio.run(main())
