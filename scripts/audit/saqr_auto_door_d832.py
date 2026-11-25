#!/usr/bin/env python3
"""كاشفُ D832 على الخادم — صقرٌ في التداول الآليّ: هل وصله آخرُ ما بنيناه؟ وكيف أداؤه الحقيقيّ؟ (قراءةٌ لا تكتب شيئاً)

قال المالك (2026-11-25): «هل صقرٌ في التداول الآليّ أصبح عقليةً موحّدة… وصلَه هذا التطوير أم لا؟ تأكّد — لا أريد إلا اللونَ الأخضر… وهل
التداولُ الآليّ في صقر السعوديّ موجود؟ هل عنده الفوليوم بروفايل؟ أريد صقرَ الأمريكيّ والسعوديّ في مستوى نجاحٍ واختيارٍ موحَّد».

  ١ لكلّ سوق: التشغيلُ الآليّ ونمطُه وإعداداتُ المالك، والأبوابُ المغلقةُ الآن، وآخرُ دورةٍ وآخرُ بحث.
  ٢ الأداءُ الحقيقيّ: المراكزُ المفتوحةُ بربحها، والمقفلةُ بنتيجتها — رابحةٌ وخاسرة، ونسبةُ النجاح، وأسبابُ الخروج.
  ٣ مصدرُ الصفقات: الأمريكيّ من دفتر «عقود الخيارات» — بحكم صقر وقراءة الحجم في كلّ توصية؟ والسعوديّ — بشواهده الثمانية وقراءة الحجم؟

    docker exec sp_backend python /app/scripts/audit/saqr_auto_door_d832.py
"""
import os
import time

os.environ.setdefault("TZ", "Asia/Riyadh")
time.tzset()

import sys  # noqa: E402
from collections import Counter  # noqa: E402

sys.path.insert(0, "/app")


def main():
    from app.services import saqr_trader as SQ
    from app.services import option_picks as OP
    for mk in ("us", "sa"):
        st = SQ.load(mk)
        c = SQ.cfg(st)
        print(f"══ {('الأمريكيّ' if mk == 'us' else 'السعوديّ')}")
        print(f"   يعمل {st.get('on')} · آليّ {c.get('auto')} · نمط {c.get('mode')} · رأسُ المال {st.get('capital')} · النقد {round(st.get('cash') or 0, 2)} · "
              f"الثروة {round(SQ.equity(st), 2)} · بدأ {st.get('started')}")
        print(f"   الإعدادات: {st.get('settings')}")
        print(f"   الأبواب الآن: {st.get('gates')} · آخرُ دورة {st.get('last_cycle')} · آخرُ بحث {st.get('last_scan')} · دورات {st.get('cycles')}")
        pos = st.get("positions") or []
        print(f"   مفتوحة {len(pos)}:")
        for p in pos[:10]:
            bid = p.get("bid") or p.get("entry_px")
            pl = ((bid or 0) / p["entry_px"] - 1) * 100 if p.get("entry_px") else 0
            print(f"      {p.get('contract')} · دخل {p.get('entry_px')} · الآن {bid} ({pl:+.1f}٪) · آليّ {p.get('auto')} · مالك {p.get('owner')} · vp {bool(p.get('vp'))} · {p.get('opened')}")
        cl = st.get("closed") or []
        wins = [x for x in cl if (x.get("pl") or 0) > 0]
        loss = [x for x in cl if (x.get("pl") or 0) <= 0]
        print(f"   مقفلة {len(cl)} · رابحة {len(wins)} · خاسرة {len(loss)} · نسبةُ النجاح {(len(wins) / len(cl) * 100 if cl else 0):.0f}٪ · "
              f"صافي {sum((x.get('pl') or 0) for x in cl):,.2f} · أسباب {dict(Counter(x.get('reason') for x in cl))}")
        for x in cl[:12]:
            print(f"      {x.get('closed', '')[:16]} {x.get('contract')} · {x.get('pl_pct', 0) if x.get('pl_pct') is not None else ''}٪ · {x.get('pl')} · {x.get('reason_ar') or x.get('reason')} · آليّ {x.get('auto')}")
        logs = (st.get("log") or [])[:10]
        for l in logs:
            print(f"      سجلّ {l.get('at', '')[:16]} {l.get('kind')}: {str(l.get('text'))[:150]}")
    print("══ ٣ دفترُ «عقود الخيارات» (مصدرُ الأمريكيّ الآليّ)")
    for b in OP.book_budgets():
        bk = OP.book_load(b)
        op = bk.get("open") or []
        cv = Counter(((e.get("council") or {}).get("verdict") or (e.get("card") or {}).get("council", {}).get("verdict") or "—") for e in op)
        vp = sum(1 for e in op if (e.get("card") or {}).get("vp"))
        dte = sorted(((e.get("card") or {}).get("dte") or 0) for e in op)
        print(f"   {b}$: مفتوحة {len(op)} · أحكامُ صقر {dict(cv)} · بقراءة حجم {vp} · آجال {dte[:3]}…{dte[-3:]} · مقفلة {len(bk.get('closed') or [])}")
        for e in op[:3]:
            card = e.get("card") or {}
            print(f"      {e.get('contract')} · درجة {card.get('score')} · هدف {e.get('target')} ({e.get('target_label')}) · حجم {(card.get('vp') or {}).get('zone')} · منذ {e.get('opened')}")
    print("══ انتهى")


main()
