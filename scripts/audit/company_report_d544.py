"""D544 — تقريرُ الشركة بورق تقرير المحفظة وعارضه وتصديره: الهويّةُ لا تهتزّ.

    python3 scripts/audit/company_report_d544.py
"""
import pathlib
import sys

F = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
qr = (F / "components" / "analysis" / "QuarterReport.tsx").read_text(encoding="utf-8")
cd = (F / "components" / "reports" / "CompanyReportDocument.tsx").read_text(encoding="utf-8")
rp = (F / "pages" / "ReportsPage.tsx").read_text(encoding="utf-8")
ok = ("ReportViewer" in qr and "CompanyReportDocument" in qr and "window.print" not in qr
      and 'from "./ReportDocument"' in cd and "PAPER" in cd and "#" not in cd.split("const {")[0].split("import")[-1]
      and "ReportViewer" in rp and "html-to-image" not in rp)
print(("PASS" if ok else "FAIL") + " D544 — تقريرُ الشركة بورق تقرير المحفظة وعارضه الواحد")
sys.exit(0 if ok else 1)
