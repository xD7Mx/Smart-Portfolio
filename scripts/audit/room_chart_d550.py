"""D550 · D551 — الرسم: البحثُ بجانب المؤشرات، والهويّةُ على سطر السعر، وخطٌّ أفقيٌّ يُعتمد
بـ«+»؛ وغرفةُ التداول: صفحةٌ ورموزٌ تعبر الأجهزة وأسعارٌ من «تداول» أوّلاً.

    python3 scripts/audit/room_chart_d550.py
"""
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[2]
F = R / "frontend" / "src"
cp = (F / "pages/ChartPage.tsx").read_text(encoding="utf-8")
nc = (F / "components/analysis/NativeChart.tsx").read_text(encoding="utf-8")
rp = (F / "pages/RoomPage.tsx").read_text(encoding="utf-8")
st = (F / "store/appStore.ts").read_text(encoding="utf-8")
ml = (F / "components/common/MainLayout.tsx").read_text(encoding="utf-8")
mk = (R / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
se = (R / "backend/app/api/v1/endpoints/settings.py").read_text(encoding="utf-8")
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(("PASS " if ok else "FAIL ") + label)

tabs = cp[cp.index('tab("idx", "المؤشرات")'):]
check("<InlineStockSearch onPick={pick} global />" in tabs[:400] and "{title}" not in cp,
      "١ البحثُ بجانب المؤشرات ولا سطرَ لاسم الشركة")
check("identity=" in cp and "{identity}" in nc, "٢ الشعارُ والرمزُ والسعرُ في سطرٍ واحد")
check('aria-label="اعتماد الخطّ"' in nc and "createPriceLine({ price: d.h" in nc and "subscribeClick" not in nc,
      "٣ الخطُّ أفقيٌّ يتبع الإصبعَ على امتداد الرسم ويُعتمد بـ«+» خطّاً ثابتاً")
check('"/room"' in ml and "roomSymbols" in st and "setRoomSymbols" in rp and '"roomSymbols"' in se,
      "٤ غرفةُ التداول صفحةٌ رئيسية ورموزُها تُحفظ مع التخطيط على الخادم")
check('@router.get("/room")' in mk and "row_for(base)" in mk and "index_quote()" in mk,
      "٥ أسعارُ الغرفة من «تداول» أوّلاً وتاسي من خدمة مؤشّره")
css = (F / "styles/globals.css").read_text(encoding="utf-8")
check("--beige-strength: 10%;" in css and "color-mix(in srgb, var(--beige) var(--beige-strength), var(--bg))" in css
      and "gap-px" not in rp and "rounded-3xl" in rp,
      "٦ D552 البيجُ بنسبة 10٪ من مقبضٍ واحد، والغرفةُ قائمةٌ لا مربّعات")
print(("FAIL" if fail else "PASS") + " D550 · D551 — الرسمُ وغرفةُ التداول")
sys.exit(fail)
