#!/usr/bin/env python3
"""كاشفُ الدفاتر (‏D777) — قراءةٌ وحدها: أين سُجّل عقدٌ ما؟ محفظةُ صقر الأمريكية (المراكز · المغلقة · الأوامر) ودفترُ توصيات «عقود الخيارات»
لكلّ ميزانية. سأل المالك (2026-11-20): «عقدُ NIO دخلنا فيه بـ1.22 ووصل 1.60 — لا أعرف هل سُجّل في المحفظة أم لا». لا يكتب شيئاً.

    docker exec sp_backend python /app/scripts/audit/saqr_books_door.py
"""
import sys

sys.path.insert(0, "/app")
from app.services import saqr_trader as SQ   # noqa: E402
from app.services import option_picks as OP   # noqa: E402

st = SQ.load("us")
print("══ محفظةُ صقر الأمريكية · النقد", st.get("cash"), "· رأسُ المال", st.get("capital"))
for p in st.get("positions") or []:
    print(f"  مركز: {p.get('contract')} · {p.get('qty')} × {p.get('entry_px')} · فُتح {p.get('opened')} · المصدر {p.get('src')} · المالك {p.get('owner')} "
          f"· آخرُ طلب {p.get('bid')}")
for o in st.get("orders") or []:
    print(f"  أمرٌ معلّق: {o.get('contract')} · {o.get('qty')} · حدّ {o.get('limit')} · {o.get('created')}")
for c in (st.get("closed") or [])[:15]:
    print(f"  مغلقة: {c.get('contract')} · دخول {c.get('entry_px')} · خروج {c.get('exit_px')} · {c.get('opened')} ⇐ {c.get('closed')} · {c.get('reason')}")
print("══ دفترُ «عقود الخيارات» — الميزانيات:", OP.book_budgets())
for b in OP.book_budgets():
    bk = OP.book_load(b)
    for e in bk["open"]:
        print(f"  [{b}] قائمة: {e.get('contract')} · فُتحت {e.get('opened')} · دخول الوسط {e.get('entry_mid')} العرض {e.get('entry_ask')} "
              f"· آخرُ وسط {(e.get('last') or {}).get('mid')} ({(e.get('last') or {}).get('pl_pct')}٪)")
    for e in bk["closed"][:6]:
        print(f"  [{b}] أُغلقت: {e.get('contract')} · {e.get('opened')} ⇐ {e.get('closed')} · {(e.get('last') or {}).get('status')} ({(e.get('last') or {}).get('pl_pct')}٪)")
hits = [p for p in (st.get("positions") or []) + (st.get("closed") or []) if "NIO" in str(p.get("contract"))]
print("══ NIO في محفظة صقر:", len(hits), "سطراً")
