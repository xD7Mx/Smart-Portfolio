"""D528 — تقريرُ الربع: بنودُ البنوك من XBRL بالحرف، وجدولُ الربع على أرقام الراجحي.

الأرقامُ من ملفّ «تداول» (bank_labels_door.py) ومن تقرير «الرياض المالية» للربع
الثاني 2026 — التغيّراتُ يجب أن تطابق تقريرَهم بعد التقريب.

    python3 scripts/audit/quarter_report_d528.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))
from app.services import tadawul_xbrl as X  # noqa: E402
from app.services import quarter_report as Q  # noqa: E402

fail = 0


def check(ok, label, detail=""):
    global fail
    print(("PASS" if ok else "FAIL"), label, ("— " + detail) if detail else "")
    fail |= not ok


# ١ · القارئ: بنودُ البنك بالحرف، وموضعُ العمود
row = lambda *c: "<tr>" + "".join(f"<td>{x}</td>" for x in c) + "</tr>"
html = "<table>" + "".join([
    row("Level of rounding used in financial statements", "Thousands"),
    row("Period covered by financial statements", "Quarter 2"),
    row("End Date", "2026-06-30", "2025-06-30"),
    row("Loans,financing and advances, net", "762,096,104", "752,759,851"),
    row("Customer's deposits", "688,359,499", "667,287,500"),
    row("Special commission income/ gross financing and investment income", "14,483,780", "13,646,808"),
    row("Special commission income (expense)/ financing and investment income (expense), net", "8,306,780", "7,305,053"),
    row("Total operating income", "10,884,480", "9,602,821"),
    row("Profit (loss) for the period", "7,025,709", "6,161,427"),
    row("Profit (loss), attributable to equity holders of parent company", "7,012,137", "6,151,011"),
]) + "</table>"
ps = {p["as_of"]: p for p in X.parse(html).get("periods", [])}
c = ps.get("2026-06-30", {})
check(c.get("bank_loans") == 762096104000 and c.get("bank_deposits") == 688359499000
      and c.get("bank_nfi") == 8306780000 and c.get("bank_op_income") == 10884480000
      and c.get("net_income_parent") == 7012137000 and c.get("net_income") == 7025709000
      and c.get("col") == 0 and ps.get("2025-06-30", {}).get("col") == 1,
      "١ بنودُ البنك تُقرأ بالحرف، وصافي الربح يبقى كما كان، والعمودُ موسوم", str({k: c.get(k) for k in ("bank_nfi", "net_income_parent", "col")}))

# ٢ · الجدول: أرقام الراجحي (مليون ريال) — والميزانيةُ من عمود الملفّ الأوّل وحدَه
M = 1e6
qs = [
    {"as_of": "2025-06-30", "col": 0, "bank_nfi": 7305 * M, "bank_op_income": 9603 * M, "net_income_parent": 6151 * M,
     "bank_loans": 741715 * M, "bank_deposits": 664687 * M},
    {"as_of": "2026-03-31", "col": 0, "bank_nfi": 8405 * M, "bank_op_income": 10528 * M, "net_income_parent": 6752 * M,
     "bank_loans": 753730 * M, "bank_deposits": 678734 * M},
    {"as_of": "2026-06-30", "col": 0, "bank_nfi": 8307 * M, "bank_op_income": 10884 * M, "net_income_parent": 7012 * M,
     "bank_loans": 762096 * M, "bank_deposits": 688359 * M},
]
t = {r["key"]: r for r in Q.table(qs, bank=True)["rows"]}
riyad = {"bank_nfi": (14, -1), "bank_op_income": (13, 3), "net_income_parent": (14, 4), "bank_loans": (3, 1), "bank_deposits": (4, 1)}
bad = {k: (round(t[k]["yoy"]), round(t[k]["qoq"])) for k in riyad if (round(t[k]["yoy"]), round(t[k]["qoq"])) != riyad[k]}
check(not bad and len(t) == 5, "٢ التغيّرُ السنويُّ والربعيُّ يطابقان تقريرَ «الرياض المالية» للراجحي Q2 2026", str(bad))
qs[0]["col"] = 1
t2 = {r["key"]: r for r in Q.table(qs, bank=True)["rows"]}
check(t2["bank_loans"]["yoy"] is None and t2["bank_nfi"]["yoy"] is not None,
      "٣ ميزانيةُ عمودِ المقارنة (نهايةُ السنة) لا تُقارَن بالربع — والدخلُ يُقارَن")
check(Q.recommendation(20.6) == "شراء" and Q.recommendation(0) == "حياد" and Q.recommendation(-16) == "بيع"
      and Q.recommendation(None) is None, "٤ التوصيةُ بحدود ±15٪ لإجمالي العائد المتوقّع")
print(("FAIL" if fail else "PASS") + " D528 — تقريرُ الربع")
sys.exit(fail)
