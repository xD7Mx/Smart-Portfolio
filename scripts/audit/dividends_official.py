#!/usr/bin/env python3
"""التوزيعاتُ من جدول «تداول» الرسميّ حين يعجز ياهو (D444).

    python3 scripts/audit/dividends_official.py

رآه المالك: «التوزيعات لم أجدها… واجعل مصدرها رسمي تداول». وقِيس بكاشف
`company_dividends_table.py` أن صفحةَ الشركة تحمل جدولَ `companyDividends`.
والفحصُ سلوكيّ: صفحةٌ بشكل ما قِيس، وياهو صامت، ثم يُنادى البابُ الواحد
`market_service.get_dividends` ويُشترط أن تصل الصفوفُ بتواريخها ومبالغها.
"""
from __future__ import annotations
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
import asyncio, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend")); sys.path.insert(0, "/app")
try:
    from app.services import market_data as MD, tadawul_ownership as O
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس"); sys.exit(0)

PAGE = '''<table id="companyDividends"><thead><tr><th>Announced Date</th><th>Eligibility Date</th>
<th>Distribution Date</th><th>Distribution Way</th><th>Dividend Amount</th></tr></thead><tbody>
<tr><td>07/09/2026</td><td>10/09/2026</td><td>27/09/2026</td><td>Account Transfer</td><td><span class="sar-symbol">^</span> 1.50</td></tr>
<tr><td>11/03/2026</td><td>10/06/2026</td><td>25/06/2026</td><td>Account Transfer</td><td>^ 1.00</td></tr>
<tr><td>19/03/2025</td><td>29/06/2025</td><td>17/07/2025</td><td>Account Transfer</td><td>^ 1.00</td></tr>
</tbody></table>'''
async def _page(sym): return PAGE
O.company_page = _page
async def _none(*a, **k): return None
MD.YahooFinanceAdapter.get_dividends = _none

d = asyncio.run(MD.market_service.get_dividends("4030.SR")) or {}
h = d.get("history") or []
fail = 0
def check(ok, label, det=""):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))
check(len(h) == 3, "١ ثلاثةُ توزيعاتٍ من جدول «تداول» وياهو صامت", str(h)[:120])
check(bool(h) and h[-1]["amount"] == 1.5 and h[-1]["date"] == "2026-09-10",
      "٢ آخرُها 1.50 بأحقية 2026-09-10")
check(d.get("pay_date") == "2026-09-27", "٣ وتاريخُ التوزيع 2026-09-27", str(d.get("pay_date")))
check(d.get("source") == "تداول", "٤ والمصدرُ مُعلَنٌ «تداول»")
print(("FAIL" if fail else "PASS") + " D444 — التوزيعاتُ من «تداول»")
sys.exit(fail)
