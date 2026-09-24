#!/usr/bin/env python3
"""حارسُ D476: قارئُ قوائم «تداول» PDF يقرأ البنودَ كما نُشرت ويرفض ما لا يتّسق.

    python3 scripts/audit/pdf_statements.py

الأسطرُ منقولةٌ حرفياً من ملفّ 8010 السنويّ لعام 2025 كما أخرجه PyMuPDF على خادم المالك.
"""
import os, sys
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
try:
    from app.services import tadawul_pdf as P
except ImportError as e:
    print(f"FAIL D476 — لا يُستورد القارئ: {e}"); sys.exit(1)

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

F = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
bal = open(os.path.join(F, "pdf_8010_2025.txt"), encoding="utf-8").read()
inc = open(os.path.join(F, "pdf_8010_2025_income.txt"), encoding="utf-8").read()
check(P._kind_of(bal) == "balance" and P._kind_of(inc) == "income", "١ تُعرف صفحةُ المركز المالي وصفحةُ الدخل")
check(P._as_of(bal) == "2025-12-31", "٢ تاريخُ الفترة من رأس القائمة", P._as_of(bal))
check(P._unit(bal) == 1000.0, "٣ وحدةُ «’000» تُقرأ آلافاً")
b = P._pairs(bal.splitlines(), P._KIND["balance"])
check(b.get("total_assets") == (21763833.0, 20995701.0) and b.get("equity") == (5357500.0, 4478243.0)
      and b.get("ending_cash") == (1701158.0, 2077468.0),
      "٤ المركزُ المالي: رقمُ الإيضاح يُتجاوَز والعمودان يُقرآن", str(b))
check(b.get("total_liabilities") == (16406333.0, 16517458.0), "٥ و«إجمالي المطلوبات» لا يُخلَط بـ«المطلوبات وحقوق الملكية»")
i = P._pairs(inc.splitlines(), P._KIND["income"])
check(i.get("revenue") == (21403177.0, 18272957.0), "٦ إيرادُ التأمين باسمه المنشور", str(i.get("revenue")))
check(i.get("net_income") == (1103114.0, 1022025.0) and i.get("pretax_income") == (1226621.0, 1145014.0),
      "٧ صافي الربح بعد الزكاة وقبلها لا يتبادلان", f"{i.get('net_income')} · {i.get('pretax_income')}")
check(i.get("eps") == (7.37, 6.82), "٨ ربحيةُ السهم الأساسية لا المخفَّضة", str(i.get("eps")))
check(i.get("interest_expense") == (-20551.0, -9569.0), "٩ القوسُ سالب", str(i.get("interest_expense")))
p = {"net_income": 1103114000.0, "eps": 7.37, "total_assets": 2.1e10, "equity": 5.3e9, "shares_outstanding": 149676000}
check(P.valid(p, 150_000_000) is None, "١٠ فترةٌ متّسقةٌ تجتاز الصمّام")
check(P.valid(dict(p, shares_outstanding=149676), 150_000_000) is not None,
      "١١ وعددُ أسهمٍ بوحدةٍ مغلوطة (ألفُ ضعف) يُرفض", P.valid(dict(p, shares_outstanding=149676), 150_000_000))
check(P.valid(dict(p, equity=None), 150_000_000) is not None, "١٢ وبندٌ أساسيٌّ غائبٌ يُرفض")
from app.services import fair_value_models as FV
_q = [{"as_of": f"2022-{m:02d}-30", "revenue": 1.0, "net_income": 1.0} for m in (3, 6, 9)] + [{"as_of": "2022-12-31", "revenue": 1.0, "net_income": 1.0}]
_a = [{"as_of": "2025-12-31", "year": 2025, "revenue": 9.0, "net_income": 3.0, "equity": 5.0}]
_t, _src = FV._ttm_of(_q, _a)
check(_t.get("revenue") == 9.0 and "2025" in _src, "١٣ أرباعُ 2022 لا تُحسب «آخرَ اثني عشر شهراً» وسنةُ 2025 منشورة", _src)
check(FV._latest(_q, _a).get("equity") == 5.0, "١٤ وأحدثُ ميزانيةٍ هي الأحدثُ تاريخاً لا الربعيّة")
print(f"{'FAIL' if fail else 'PASS'} D476 — قوائمُ «تداول» PDF حين تقف XBRL")
sys.exit(fail)
