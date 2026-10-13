#!/usr/bin/env python3
"""حارسُ D687 — ملاحظاتُ المالك (2026-10-13)، ساكناً (والقياسُ في المتصفّح: ui_d683.mjs · ٢ و٤).

  «ضع حركةَ أنيميشن عند تمرير بطاقات الشاشة لأنّها قاسية، ومن الآن فصاعداً الأنيميشن جزءٌ أساسيٌّ من هويّة التصميم» ·
  «لم يعجبني اسمُ الشاشة — اجعله غرفة التداول بأيقونة الرسم البيانيّ، وتبويبُ الرسم البيانيّ داخله تبويباً داخلياً» ·
  «أضف حركةَ إيماءٍ: تمريرُ الإصبع على الجوال من اليمين إلى اليسار يُخرج القائمةَ الجانبية».
  قِيس أثناء البناء: البطاقةُ التي تتبع الإصبع تغطّي ما تحتها، واختبارُ المرسوم يقرأ بطاقةً في منتصف انزلاقها فيُسقط
  الترتيبَ خانةً قبل موضعه — فصار الاختبارُ على خانات الشبكة.

    python3 scripts/audit/ui_owner_notes_d687.py
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend/src"
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


rd = lambda *p: SRC.joinpath(*p).read_text(encoding="utf-8")   # noqa: E731
ml, app, wp, cp = rd("components/common/MainLayout.tsx"), rd("App.tsx"), rd("pages/WatchlistPage.tsx"), rd("pages/ChartPage.tsx")
check('watchlist:     { to: "/watchlist",     icon: CandlestickChart, key: "nav.watchlist" }' in ml
      and not re.search(r'^\s*chart:\s*\{ to: "/chart"', ml, re.M) and '"nav.watchlist":   { ar: "غرفة التداول"' in rd("i18n.ts"),
      "١ «غرفة التداول» بأيقونة الرسم البيانيّ في القائمة، ولا بندَ مستقلّاً للرسم")
check('<Route path="/chart"          element={<Navigate to="/watchlist?tab=chart" replace />} />' in app
      and '["chart", "الرسم البياني", CandlestickChart]' in wp and "<ChartPage embedded />" in wp and "{!embedded && (" in cp,
      "٢ والرسمُ تبويبٌ داخليّ فيها بعنوانٍ واحد، ورابطُه القديم يفتحه هناك")
check('document.addEventListener("touchstart", onStart, { passive: true })' in ml and "const open = isRtl ? dx < 0 : dx > 0;" in ml
      and "Date.now() - t0 > 450" in ml and "Math.abs(dy) > Math.abs(dx) * 0.5" in ml,
      "٣ إيماءةُ السحب على الجوال: من اليمين إلى اليسار تُخرج القائمة والعكسُ يُعيدها — سريعةٌ أفقيّةٌ لا تمريراً ولا ضغطةً مطوّلة")
hook = rd("hooks/useLongPressSort.ts")
check("const place = () =>" in hook and "const land = () =>" in hook and "el.offsetParent !== box" in hook
      and 'transform: "scale(1.04)"' not in hook,
      "٤ البطاقةُ المرفوعة تتبع الإصبع وتهبط بانزلاق، والترتيبُ يُقرأ من خانات الشبكة لا من مواضع الرسم")
css = rd("styles/globals.css")
check(".drawer-out {" in css and ".card-rise {" in css and "drawer-closing" in ml and "card-rise" in rd("components/market/WatchlistTab.tsx")
      and re.search(r"prefers-reduced-motion: reduce\)\s*\{\s*\.drawer-in, \.drawer-out", css),
      "٥ والقائمةُ تنزلق خارجةً كما دخلت، والبطاقاتُ تطلع متتابعة — مع احترام تقليل الحركة")
claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
check("**الحركةُ جزءٌ من هويّة التصميم**" in claude, "٦ والحركةُ قاعدةٌ ثابتة في مختصر التعليمات — لا يُذكَّر بها")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
