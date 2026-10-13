"""كاشف D700 (قراءةٌ فقط): ما نشرته مسحةُ الإنتاج بعد المحرّك المثبت بالنتائج — التغطيةُ وتوزيعُ الثقة وسجلُّ الإصابة المقيس،
والتأمينُ والخدماتُ الماليةُ محجوبةٌ بسببها، وعيّناتٌ بأسمائها.

    docker exec sp_backend python /app/scripts/audit/fv_live_d700_door.py
"""
import collections
import sys

sys.path.insert(0, "/app")


def main():
    from app.services.content_engine import fund_store_load
    from app.services.statement_merge import archetype_of
    from app.data.market_universe import MARKET_UNIVERSE as MU
    from app.data.universe import main_market, is_nomu
    st = fund_store_load() or {}
    syms = sorted(s for s in main_market(MU) if not is_nomu(s))
    have = [s for s in syms if isinstance((st.get(s) or {}).get("fair_value"), (int, float))]
    print(f"@@LIVE@@ بسعرٍ عادل {len(have)} من {len(syms)} · تاريخُ المسحة "
          f"{collections.Counter(str((st.get(s) or {}).get('score_asof')) for s in syms).most_common(2)}")
    print("@@CONF@@", dict(collections.Counter((st.get(s) or {}).get("fair_value_conf") for s in have)))
    tr = [s for s in have if (st.get(s) or {}).get("fair_value_track")]
    print(f"@@TRACK@@ يحمل سجلَّ الإصابة {len(tr)} من {len(have)}")
    ins = [s for s in syms if archetype_of(s) in ("insurance", "financial")]
    shown = [s for s in ins if s in have]
    print(f"@@FIN@@ تأمينٌ وخدماتٌ مالية {len(ins)} · بسعرٍ عادل {len(shown)} {shown[:6]}")
    why = collections.Counter(str((st.get(s) or {}).get("fair_value_unavailable"))[:70] for s in syms if s not in have)
    for w, n in why.most_common(6):
        print(f"   {n:>3} × {w}")
    for s in ("1120", "1180", "2010", "2222", "7010", "4190", "8010", "2280"):
        r = st.get(s) or {}
        print(f"@@S@@ {s} {(MU.get(s) or {}).get('name_ar')}: عادل {r.get('fair_value')} · ثقة {r.get('fair_value_conf')} · "
              f"{r.get('fair_value_track') or r.get('fair_value_unavailable') or '—'}")


main()
