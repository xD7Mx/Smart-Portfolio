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
from app.services import tadawul_xbrl as XB
_old = {"annual": [{"as_of": "2021-12-31", "revenue": 5.0}], "quarterly": []}
_new = {"annual": [], "quarterly": [{"as_of": "2026-06-30", "revenue": 1.0}]}
_m = XB._merge_old(_old, _new)
check([p["as_of"] for p in _m["annual"]] == ["2021-12-31"] and len(_m["quarterly"]) == 1,
      "١٥ حصادٌ أفقرُ لا يمحو سنواتٍ محفوظةً لم يقرأها", str(_m))
_m2 = XB._merge_old({"annual": [{"as_of": "2025-12-31", "revenue": 5.0}]}, {"annual": [{"as_of": "2025-12-31", "revenue": 7.0}]})
check(_m2["annual"][0]["revenue"] == 7.0, "١٦ والقراءةُ الجديدةُ للتاريخ نفسِه تغلب")
# أسطرٌ منقولةٌ حرفياً من ملفّات 2025: بوبا 8210 (بندٌ مكسور) · سابك 2010 (العائدُ للأمّ) · الإعادة 8200 (رقمان في سطر)
_bupa = ["CONSOLIDATED STATEMENT OF INCOME", "Insurance revenue", "6.1", "19,303,064", "18,101,517",
         "Income attributed to the shareholders before zakat", "and income tax", "1,252,757", "1,372,626",
         "NET INCOME ATTRIBUTED TO THE SHAREHOLDERS", "AFTER ZAKAT AND INCOME TAX", "1,079,092", "1,166,002",
         "Basic and diluted earnings per share (expressed in SR per share)", "27", "7.23", "7.79"]
b = P._pairs(_bupa, P._KIND["income"])
check(b.get("net_income") == (1079092.0, 1166002.0) and b.get("pretax_income") == (1252757.0, 1372626.0)
      and b.get("eps") == (7.23, 7.79) and b.get("revenue") == (19303064.0, 18101517.0),
      "١٧ البندُ المكسورُ على سطرين يُوصل (بوبا)", str(b))
_sabic = ["Revenue", "27", "116,525,214", "117,736,492", "Net (loss) income", "(24,724,966)", "3,723,135",
          "Attributable to:", "• Equity holders of the Parent", "(25,779,231)", "1,538,542", "• Non-controlling interests",
          "Basic and diluted earnings per share from net (loss)", "income attributable to equity holders of the Parent",
          "(Saudi Riyals)", "32", "• Net (loss) income from continuing operations", "(0.51)", "1.70", "• Net (loss) income", "(8.59)", "0.51"]
c = P._pairs(_sabic, P._KIND["income"])
check(c.get("net_income") == (-25779231.0, 1538542.0), "١٨ صافي الربح العائدُ لمساهمي الأمّ يغلب الإجماليّ (سابك)", str(c.get("net_income")))
check(c.get("eps") == (-8.59, 0.51), "١٩ وربحيةُ السهم من سطر صافي الربح لا من العمليات المستمرّة", str(c.get("eps")))
_re = ["Reinsurance revenue", "7,19", "1,672,498,610   1,129,966,260", "Net income for the year after zakat and tax",
       "140,044,427", "474,811,642", "Basic and diluted earning per share", "11", "0.43", "0.54"]
d = P._pairs(_re, P._KIND["income"])
check(d.get("revenue") == (1672498610.0, 1129966260.0) and d.get("net_income") == (140044427.0, 474811642.0)
      and d.get("eps") == (0.43, 0.54), "٢٠ رقما سطرٍ واحد يُفصلان وإيضاحُ «7,19» يُتجاوَز ولا تُحذف «0.43»", str(d))
check(P._kind_of("INDEPENDENT AUDITORS' REPORT ON FINANCIAL STATEMENTS statement of financial position") is None,
      "٢١ تقريرُ المراجع ليس قائمة")
check(P.valid(dict(p, shares_outstanding=149252006), 119458, 149679332) is None,
      "٢٢ مرجعٌ محفوظٌ بوحدةٍ مغلوطة (بوبا 119,458) لا يرفض ملفّاً اتّسق عموداه")
check(P.valid(dict(p, shares_outstanding=178476368), 2194773958, 9981125490) is not None,
      "٢٣ وعمودان غيرُ متّسقَين وبعيدان عن المرجع يُرفضان (سابك قبل الإصلاح)")
_s2 = ["Net (loss) income from continuing operations", "(345,652)", "7,274,967", "Net (loss) income", "(24,724,966)", "3,723,135",
       "Net (loss) income from continuing operations", "Attributable to:", "• Equity holders of the Parent", "(1,533,112)", "5,090,374",
       "Net (loss) income", "Attributable to:", "• Equity holders of the Parent", "(25,779,231)", "1,538,542"]
check(P._pairs(_s2, ("net_income",)).get("net_income") == (-25779231.0, 1538542.0),
      "٢٤ الكتلةُ الكلّيةُ العائدةُ للأمّ لا كتلةُ العمليات المستمرّة")
check(P._unit("All amounts in thousands of Saudi Riyals unless otherwise stated. SAR 5 million facility") == 1000.0,
      "٢٥ كلمةُ «million» في نصّ الصفحة لا تجعل الوحدةَ ملايين")
_reit = ["Other income", "1,860,258", "765,142", "(Loss) for the year", "(13,461,064)", "(187,275,085)"]
check(P._pairs(_reit, ("net_income",)).get("net_income") == (-13461064.0, -187275085.0), "٢٦ «(Loss) for the year» صافي ربح الصندوق العقاريّ")
_mg = ["Insurance revenue", "7", "1,314,513            1,026,441            2,565,761            2,026,784",
       "Income / (loss) attributed to the shareholders after zakat and income tax", "44,167                  (1,470)", "80,416", "18,168"]
g = P._pairs(_mg, P._KIND["income"])
check(g.get("net_income") == (44167.0, -1470.0) and g.get("revenue") == (1314513.0, 1026441.0),
      "٢٧ صيغةُ ميدغلف وأعمدةٌ متعدّدةٌ في سطرٍ واحد", str(g))
print(f"{'FAIL' if fail else 'PASS'} D476 — قوائمُ «تداول» PDF حين تقف XBRL")
sys.exit(fail)
