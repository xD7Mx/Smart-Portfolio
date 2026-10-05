#!/usr/bin/env python3
"""حارسُ D596: جدولُ «المعلومات المالية» في صفحة الشركة يُقرأ كما قِيس على التعاونية (8010)،
ويُدمج مع XBRL فلا تضيع فترةٌ أحدث ولا تُمحى خانةُ XBRL.

    python3 scripts/audit/tadawul_fin_d596.py
"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0
def check(ok, label, det=""):
    global fail
    if not ok: fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

def tr(*cells, h=False):
    t = "th" if h else "td"
    return "<tr>" + "".join(f"<{t}>{c}</{t}>" for c in cells) + "</tr>"

# الجدولُ الربعيُّ للتعاونية كما طبعه profile_fin_door3 (السالبُ في خانتين)
Q = "<table>" + "".join([
    tr("Balance Sheet", "2026-06-30", "2026-03-31", "2025-09-30", "2025-06-30", h=True),
    tr("Total Assets", "29,688,545", "25,039,412", "21,301,537", "21,315,515"),
    tr("Total Liabilities", "24,020,260", "19,393,149", "16,159,670", "16,352,376"),
    tr("Total Shareholders Equity (After Deducting the Minority Equity)", "5,666,845", "5,645,744", "5,141,867", "4,963,139"),
    tr("Total Liabilities and Shareholders Equity", "29,687,105", "25,038,893", "21,301,537", "21,315,515"),
    tr("Statement of Income", "2026-06-30", "2026-03-31", "2025-09-30", "2025-06-30"),
    tr("Total Revenue (Sales/Operating)", "6,227,981", "5,768,978", "5,405,366", "5,225,943"),
    tr("Net Profit (Loss) before Zakat and Tax", "357,300", "322,477", "211,895", "499,989"),
    tr("Zakat and Income Tax", "", "-34,612", "", "-33,877", "", "-38,637", "", "-32,572"),
    tr("Net Profit (Loss) Attributable to Shareholders of the Issuer", "321,767", "288,081", "173,258", "467,417"),
    tr("Profit (Loss) per Share", "2.15", "1.93", "1.16", "3.12"),
    tr("Cash Flows", "2026-06-30", "2026-03-31", "2025-09-30", "2025-06-30"),
    tr("Net Cash From Operating Activities", "879,169", "408,400", "", "-162,250", "", "-552,734"),
    tr("Cash and Cash Equivalents, End of the Period", "1,794,731", "1,605,326", "969,915", "825,173"),
    tr("All Figures in", "Thousands", "Thousands", "Thousands", "Thousands"),
]) + "</table>"
A = "<table>" + "".join([
    tr("Balance Sheet", "2025-12-31", "2024-12-31", "2023-12-31", "", h=True),
    tr("Total Assets", "21,763,833", "20,995,701", "18,416,726", "-"),
    tr("Total Shareholders Equity (After Deducting the Minority Equity)", "5,357,500", "4,478,243", "3,621,817", "-"),
    tr("Total Revenue (Sales/Operating)", "21,403,177", "18,275,271", "15,265,424", "-"),
    tr("Net Profit (Loss) Attributable to Shareholders of the Issuer", "1,103,114", "1,022,025", "616,426", "-"),
    tr("Profit (Loss) per Share", "7.37", "6.82", "4.11", "-"),
    tr("All Figures in", "Thousands", "Thousands", "Thousands", ""),
]) + "</table>"
OLD = "<table>" + tr("Balance Sheet", "2022-12-31", h=True) + tr("Policyholders (Ph) Assets:", "-") + tr("Total Assets", "18,914,997") + "</table>"

from app.services.tadawul_financials import parse_page, merge
g = parse_page(OLD + A + Q)
q = {p["as_of"]: p for p in g["quarterly"]}
a = {p["as_of"]: p for p in g["annual"]}
check(sorted(q) == ["2025-06-30", "2025-09-30", "2026-03-31", "2026-06-30"], "١ الجدولُ الربعيّ: أربعةُ أرباعٍ حتى 2026-06-30", str(sorted(q)))
check(sorted(a) == ["2023-12-31", "2024-12-31", "2025-12-31"], "٢ والسنويّ: ثلاثُ سنوات — والصيغةُ القديمة (2022) لا تُخلط")
check(q["2026-06-30"]["equity"] == 5_666_845_000 and q["2026-06-30"]["net_income"] == 321_767_000,
      "٣ الآلافُ تُضرب في ألف: حقوقٌ 5.67 مليار وربحُ الربع 321.8 مليون")
check(q["2026-06-30"]["eps"] == 2.15, "٤ وربحيةُ السهم لا تُضرب")
check(q["2026-03-31"]["_zakat"] == -33_877_000, "٥ والسالبُ المقسومُ على خانتين يُقرأ في موضعه", str(q["2026-03-31"].get("_zakat")))
check(q["2026-03-31"]["operating_cash_flow"] == 408_400_000 and abs(q["2026-06-30"]["operating_cash_flow"] - 470_769_000) < 1,
      "٦ والتدفّقُ التراكميّ يصير للربع: يونيو = 879.2 − 408.4", str(q["2026-06-30"].get("operating_cash_flow")))
check(abs(q["2025-09-30"]["operating_cash_flow"] - 390_484_000) < 1 and "operating_cash_flow" not in q["2025-06-30"],
      "٧ سبتمبر = تسعةُ أشهر − ستّة (+390.5)، ويونيو بلا مارسَ قبله لا يُنسب له تراكمُ ستّة أشهر")
check(a["2025-12-31"]["revenue"] == 21_403_177_000, "٨ وإيرادُ السنة 21.4 مليار")
xb = [{"as_of": "2025-06-30", "revenue": 1.0, "capex": 9.0}, {"as_of": "2022-12-31", "revenue": 2.0}]
m = {p["as_of"]: p for p in merge(xb, g["quarterly"])}
check(m["2025-06-30"]["revenue"] == 1.0 and m["2025-06-30"]["capex"] == 9.0, "٩ الدمج: خانةُ XBRL تبقى كما هي")
check(m["2025-06-30"].get("equity") == 4_963_139_000, "١٠ والجدولُ يملأ ما غاب عن XBRL في الفترة نفسِها")
check("2026-06-30" in m and "2022-12-31" in m, "١١ والفترةُ الأحدثُ تُضاف ولا تُمحى القديمة")
check(not any(k.startswith("_ytd_") for p in m.values() for k in p), "١٢ ولا تتسرّب خاناتُ التراكم الداخلية")
src = (ROOT / "backend/app/services/tadawul_xbrl.py").read_text()
check("from app.services.tadawul_financials import merge, periods" in src, "١٣ و`for_symbol` يُرجع المدموج — فكلُّ محرّكٍ يراه")
sch = (ROOT / "backend/app/scheduler/scheduler.py").read_text()
check("job_tadawul_financials" in sch and "tadawul_financials_night" in sch, "١٤ ويُقرأ السوقُ كلُّه كلَّ ليلة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
