"""D536 — «نجوم تاسي» صفحةٌ مستقلّةٌ ببطاقاتها: الأداء · النجوم · المعايير.

    python3 scripts/audit/stars_page_d536.py
"""
import pathlib
import sys

SRC = pathlib.Path(__file__).resolve().parents[2] / "frontend" / "src"
rd = lambda *p: (SRC.joinpath(*p)).read_text(encoding="utf-8")
page, app, nav, store = rd("pages", "StarsPage.tsx"), rd("App.tsx"), rd("components", "common", "MainLayout.tsx"), rd("store", "appStore.ts")
checks = [
    ('path="/stars"' in app and 'stars:         { to: "/stars"' in nav, "١ مسارٌ وبندٌ في القائمة الجانبية"),
    (store.count('order.includes("stars")') >= 2, "٢ تُدرَج في الترتيب المحلّيّ والمحفوظ على الخادم معاً"),
    # D612 بأمر المالك: «مختبرُ الأبحاث» — شركاتُه وحدها، وأُلغيت سلّةُ المحرّك ومعاييرُها
    (all(t in page for t in ('>الأداء<', '>شركاتك<', 'مختبر الأبحاث')) and '>النجوم<' not in page and '>المعايير<' not in page
     and "tasiStars(" not in page, "٣ D612 مختبرُ الأبحاث: الأداءُ وشركاتُك وحدها — لا سلّةَ محرّكٍ ولا معايير"),
    ("stars" not in rd("pages", "ChartPage.tsx"), "٤ لا درجَ لها في الرسم البياني"),
]
fail = 0
for ok, label in checks:
    print(("PASS" if ok else "FAIL"), label)
    fail |= not ok
print(("FAIL" if fail else "PASS") + " D536 — نجوم تاسي صفحةٌ مستقلّة")
sys.exit(fail)
