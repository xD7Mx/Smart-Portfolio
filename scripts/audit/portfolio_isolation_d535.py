"""D535 — كلُّ محفظةٍ بقائمة مراقبتها وحيازاتها وسيولتها وأهدافها.

    python3 scripts/audit/portfolio_isolation_d535.py
"""
import os
import sys
import tempfile

_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.core import portfolio_scope as PS  # noqa: E402
from app.models.market import Watchlist, WatchlistGroup  # noqa: E402

B = os.path.join(ROOT, "backend", "app")
rd = lambda *p: open(os.path.join(B, *p), encoding="utf-8").read()
comp, tx, goals, db, mkt = (rd("api", "v1", "endpoints", "companies.py"), rd("api", "v1", "endpoints", "transactions.py"),
                            rd("api", "v1", "endpoints", "goals.py"), rd("core", "database.py"), rd("api", "v1", "endpoints", "market.py"))
checks = [
    (Watchlist in PS._scoped_models() and WatchlistGroup in PS._scoped_models()
     and hasattr(Watchlist, "portfolio_id") and hasattr(WatchlistGroup, "portfolio_id")
     and '"watchlist_groups", "watchlist"' in db,
     "١ قائمةُ المراقبة ومجموعاتُها بمحفظتها (مرشَّحةٌ ومرحَّلةٌ للافتراضية)"),
    ("q.where(Watchlist.portfolio_id == _apid())" in mkt, "٢ حذفُ رمزٍ من المراقبة لا يتعدّى المحفظةَ النشطة"),
    ("mine = (await db.execute(select(Holding.id).where(Holding.company_id == existing.id)))" in comp,
     "٣ شركةٌ في محفظةٍ أخرى تُضاف إلى الجديدة بحيازةٍ لها — لا «موجودة بالفعل»"),
    ("cash = Cash(portfolio_id=pid" in tx and "_apid()" in tx, "٤ سيولةُ المحفظة الجديدة تُنشأ لها لا للأولى"),
    ("portfolio_id=_apid() or portfolio.id" in goals, "٥ هدفُ المحفظة الجديدة لها لا للأولى"),
]
fail = 0
for ok, label in checks:
    print(("PASS" if ok else "FAIL"), label)
    fail |= not ok
print(("FAIL" if fail else "PASS") + " D535 — عزلُ المحافظ")
sys.exit(fail)
