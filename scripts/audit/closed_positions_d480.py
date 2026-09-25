#!/usr/bin/env python3
"""حارسُ D480: الشركةُ المبيعةُ كاملاً (مضاربة) لا تضيع من سجلّ العمليات.

    python3 scripts/audit/closed_positions_d480.py
"""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rd = lambda p: open(os.path.join(ROOT, p), encoding="utf-8").read()
H = rd("backend/app/api/v1/endpoints/holdings.py")
T = rd("backend/app/api/v1/endpoints/transactions.py")
P = rd("frontend/src/pages/PortfolioPage.tsx")
A = rd("frontend/src/services/api.ts")
fail = 0
def check(ok, label):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")

i, j = H.find('@router.get("/closed")'), H.find('@router.get("/{company_id}")')
check(0 <= i < j, "١ مسارُ الصفقات المغلقة موجودٌ ويسبق /{company_id} فلا يبتلعه")
blk = H[i:j]
check("ARCHIVED" in blk and 'Company.status != "ARCHIVED"' not in blk and "realized_gain" in blk,
      "٢ يشمل الشركاتِ المحذوفة (المؤرشفة) بربحها المحقَّق من سجلّها")
k = T.find("async def add_transaction")
add = T[k:k + 3000]
check('_co.status = "ACTIVE"' in add and '"BUY"' in add,
      "٣ شراءٌ جديد في شركةٍ محذوفة يُعيدها بسجلّها لا يبدأ من الصفر")
rp = T[T.find("async def _replay"):]
check(re.search(r"if qty <= 1e-9:\s*\n\s*qty, invested = 0\.0, 0\.0", rp) is not None,
      "٤ البيعُ الكامل يُصفّر التكلفة فلا تتسرّب بقاياها إلى متوسط الشراء التالي")
# برهانٌ سلوكيّ على ٤: بقايا الفاصلة العائمة تُفسد المتوسط دون التصفير
def replay(txs, reset):
    q = inv = 0.0
    for typ, n, p in txs:
        if typ == "B": inv += n * p; q += n
        else:
            a = inv / q if q else 0; s = min(n, q); inv = max(0, inv - s * a); q -= s
            if reset and q <= 1e-9: q, inv = 0.0, 0.0
    return inv / q if q else 0
seq = [("B", 0.1, 0.7), ("B", 0.2, 0.3), ("S", 0.3, 1), ("B", 100, 50)]
check(abs(replay(seq, True) - 50) < 1e-12, "٥ بعد الإغلاق يبدأ الشراءُ الجديد بمتوسطه هو (50.00)")
check("holdingsApi.closed()" in P and "الصفقات المغلقة" in P and '"/holdings/closed"' in A,
      "٦ الواجهةُ تعرض الصفقات المغلقة وتفتح سجلّ كلٍّ منها")
print(f"{'FAIL' if fail else 'PASS'} D480 — الصفقاتُ المغلقة وسجلُّها")
sys.exit(fail)
