"""D532 — الشرعيةُ رمزٌ لا نصّ في قوائم الشركات، وصفوفُ «فرص السوق» تفتح صفحةَ السهم.

    python3 scripts/audit/sharia_icon_d532.py
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
gov = (SRC / "pages" / "GovernancePage.tsx").read_text(encoding="utf-8")
mkt = (SRC / "pages" / "MarketPage.tsx").read_text(encoding="utf-8")
checks = [
    ("متوافقة شرعياً" not in gov and "غير متوافقة</span>" not in gov and gov.count("<ShariaBadge") >= 2,
     "١ الحوكمة: الشرعيةُ رمزٌ في «فرص السوق» و«سلامة كل شركة»"),
    ("onClick={() => setSheet(o.symbol)}" in gov and "<StockSheet" in gov,
     "٢ صفُّ «فرص السوق» يفتح صفحةَ السهم"),
    ('text="متوافق شرعاً"' not in mkt, "٣ بطاقةُ الفرز على الجوال: الشرعيةُ رمزٌ لا وسمٌ نصّيّ"),
]
fail = 0
for ok, label in checks:
    print(("PASS" if ok else "FAIL"), label)
    fail |= not ok
print(("FAIL" if fail else "PASS") + " D532 — الشرعيةُ رمز، والصفُّ يفتح السهم")
sys.exit(fail)
