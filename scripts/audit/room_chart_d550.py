"""D550 · D551 — الرسم: البحثُ بجانب المؤشرات، والهويّةُ على سطر السعر، وخطٌّ أفقيٌّ يُعتمد
بـ«+»؛ وغرفةُ التداول أُلغيت (D558) ونُقلت شركاتُها إلى المراقبة.

    python3 scripts/audit/room_chart_d550.py
"""
import pathlib
import sys

R = pathlib.Path(__file__).resolve().parents[2]
F = R / "frontend" / "src"
cp = (F / "pages/ChartPage.tsx").read_text(encoding="utf-8")
nc = (F / "components/analysis/NativeChart.tsx").read_text(encoding="utf-8")
wl = (F / "components/market/WatchlistTab.tsx").read_text(encoding="utf-8")
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
check(not (F / "pages/RoomPage.tsx").exists() and '"/room"' not in ml and '@router.get("/room")' not in mk
      and 'order.filter((p) => p !== "room")' in st and '"roomSymbols"' in se,
      "٤ D558 أُلغيت «غرفة التداول» صفحةً ومسارًا ونقطةَ بيانات، وتُحذف من ترتيبٍ محفوظ")
check("marketApi.watchAdd(x, undefined, gid)" in wl and "setRoomSymbols([])" in wl and 'className="grid grid-cols-2 mt-3 -mx-1"' in wl and "owner && editing &&" in wl and "panel p-2.5" not in wl,
      "٥ D558 شركاتُ الغرفة تُنقل مرّةً إلى مراقبة المحفظة الحالية، والمراقبةُ صفّان")
css = (F / "styles/globals.css").read_text(encoding="utf-8")
check("--beige-strength: 10%;" in css and "color-mix(in srgb, var(--beige) var(--beige-strength), var(--bg))" in css
      ,
      "٦ D552 البيجُ بنسبة 10٪ من مقبضٍ واحد")
print(("FAIL" if fail else "PASS") + " D550 · D551 — الرسمُ وغرفةُ التداول")
sys.exit(fail)
