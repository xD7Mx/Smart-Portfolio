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
    (all(t in page for t in ('>الأداء<', '>النجوم<', '>المعايير<')), "٣ بطاقاتُ الأداء والنجوم والمعايير"),
    ("stars" not in rd("pages", "ChartPage.tsx"), "٤ لا درجَ لها في الرسم البياني"),
]
fail = 0
for ok, label in checks:
    print(("PASS" if ok else "FAIL"), label)
    fail |= not ok
print(("FAIL" if fail else "PASS") + " D536 — نجوم تاسي صفحةٌ مستقلّة")
sys.exit(fail)
