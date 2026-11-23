"""D536 — «نجوم تاسي» صفحةٌ مستقلّةٌ ببطاقاتها: الأداء · النجوم · المعايير.

    python3 scripts/audit/stars_page_d536.py
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
rd = lambda *p: (SRC.joinpath(*p)).read_text(encoding="utf-8")
page, app, nav, store = rd("components", "research", "DailyReport.tsx"), rd("App.tsx"), rd("components", "common", "MainLayout.tsx"), rd("store", "appStore.ts")
# ‏D763: ورقةُ التقرير انتقلت من المختبر إلى مفكرة السوق (مكوّنُ ‏DailyReport) — والمختبرُ عقودُ الخيارات والمحفظةُ وصقر
checks = [
    # ‏D677 ← D694 ← D736 (بأمر المالك 2026-11-15): المختبرُ تبويبٌ في غرفة التداول بجانب «الرسم البياني» (كان في تحليل الذكاء،
    # وقبله في المحفظة) — ورابطاه القديمان يصلانه، ولا نسخةَ ثانيةً منه في تحليل الذكاء
    ('["lab", "مختبر الأبحاث", FlaskConical]' in rd("pages", "WatchlistPage.tsx") and "<ResearchLab />" in rd("pages", "WatchlistPage.tsx")
     and "StarsPage" not in rd("pages", "AIPage.tsx") and 'navigate("/watchlist?tab=lab"' in rd("pages", "AIPage.tsx")
     and 'path="/stars"' in app and 'Navigate to="/watchlist?tab=lab"' in app,
     "١ المختبرُ تبويبٌ في غرفة التداول (‏D736)، ورابطاه القديمان /stars و/ai?tab=lab يصلان تبويبَه"),
    ('watchlist:     { to: "/watchlist"' in nav and 'path="/watchlist"' in app
     and store.count('(p === "stars" ? "watchlist" : p)') >= 3,
     "٢ والمراقبةُ قسمٌ مكانه في الترتيب المحلّيّ والمحفوظ على الخادم معاً — وصفحةُ البداية والمخفيّةُ تتبعانه"),
    # ‏D612 ← D745 (المالك 2026-11-15: «نغيّر الفكرةَ كلياً»): مختبرُ الأبحاث قسمُ أبحاث — تقريرٌ يوميٌّ وتوصياتٌ ومكتبةُ ما قُرئ،
    # كلُّ سطرٍ برقم مصدره؛ وأُلغيت سلّةُ الشركات القديمة (StarsPage)
    # ‏D746: والمصادرُ تُلزِم ولا تُعرض، والمكتبةُ في الخفاء — الصفحةُ ورقةُ التقرير نفسُها بتاريخها
    # ‏D788: والورقةُ كاملةً ("all") ومعها اختيارُ «محفظة التقرير» وسيطاً ثالثاً — فيُطابَق أوّلُ النداء لا آخرُه
    (all(t in page for t in ("التقرير اليومي", 'researchPaper(rep.date, "all"', "researchDesk(", "researchPdf(", "srcDoc=")) and "starsLab(" not in page
     and 'data-role="rl-tab"' not in page
     and "rl-lib" not in page and "researchLibrary" not in page and "<Cite" not in page and not (SRC / "pages" / "StarsPage.tsx").exists(),
     "٣ D745 · D746 · D753 مختبرُ الأبحاث قسمُ أبحاث: تقريرٌ واحدٌ بتاريخه فيه التوصياتُ، وملفُّه — بلا تبويبٍ مستقلٍّ ولا مكتبةٍ ولا مصادرَ معروضة"),
    ("stars" not in rd("pages", "ChartPage.tsx"), "٤ لا درجَ لها في الرسم البياني"),
]
fail = 0
for ok, label in checks:
    print(("PASS" if ok else "FAIL"), label)
    fail |= not ok
print(("FAIL" if fail else "PASS") + " D536 · D677 · D736 — مختبرُ الأبحاث تبويبٌ في غرفة التداول، والغرفةُ قسمٌ في القائمة")
sys.exit(fail)
