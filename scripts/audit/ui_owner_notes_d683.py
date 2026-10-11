#!/usr/bin/env python3
"""حارسُ D683 · D684 — ملاحظاتُ المالك (2026-10-11)، ساكناً (والقياسُ في المتصفّح: ui_d683.mjs).

  D683 «المراقبة غيّر اسمها إلى الشاشة، واجعل البطاقات قابلةً للتحريك ولا تظهر أزرارُ التحريك — ضغطٌ مطوّلٌ ثمّ تحريك —
       واجعل حكمَ القرار على الجوال أسفلَ منتصف نسبة التغيّر، وثلاثُ أعمدةٍ بنفس المحتوى (وأربعٌ إن جملت)».
       جُرّبت الأربعُ على 390 فقُصّ السعرُ («…10») وانكسر الاسمُ أربعةَ أسطر — فثلاث، كما قال المالك.
       وقِيس في الثلاث: السعرُ مقصوصٌ («24.1(») بهامش الوميض السالب، ورأسُ البطاقة الأقصر ينزل 8px لأنّ الزرَّ يوسِّط محتواه.
  D684 «بطاقاتُ فرز السوق بهويّة التطبيق — لا شذوذَ نصّيّ، اللي فوق مشابهٌ للي تحت، ولا تشتّت».
       قِيس قبلها: «0.30%-» و«%6.8» والرمزُ «SR.4190» وتاريخٌ ينكسر سطرين، وصفٌّ موسَّطٌ فوق صفٍّ ممزّق المحاذاة،
       ووسمان بنمطين — وأرضيةُ الوسم لا تُرسم أصلاً: `${color}1a` على اسم رمز (`var(--info-ink)1a`) قاعدةٌ ساقطة.

    python3 scripts/audit/ui_owner_notes_d683.py
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
code = lambda t: re.sub(r"/\*.*?\*/|\{/\*.*?\*/\}|//[^\n]*", "", t, flags=re.S)   # noqa: E731
wl, i18n = rd("components/market/WatchlistTab.tsx"), rd("i18n.ts")
# ── D683 ──
named = [f for f, t in (("i18n.ts", i18n), ("WatchlistTab.tsx", wl), ("StockLookup.tsx", rd("components/market/StockLookup.tsx")),
                        ("CompanyPage.tsx", rd("pages/CompanyPage.tsx"))) if "المراقبة" in code(t)]
check('"nav.watchlist":   { ar: "الشاشة"' in i18n and ">الشاشة</h1>" in wl and not named,
      "١ «الشاشة» اسمُ القسم في القائمة والعنوان وكلِّ نصٍّ يسمّيه — لا «المراقبة»", ", ".join(named))
check('const GRID = "grid grid-cols-3 gap-2 md:gap-3"' in wl and "grid-cols-4" not in code(wl),
      "٢ ثلاثُ بطاقاتٍ في الصفّ على الجوال والحاسوب — والأربعُ جُرّبت فقُصّ فيها السعرُ والاسم")
check('grid-cols-[minmax(0,1fr)_auto]' in wl and 'data-role="chg" className="justify-self-center' in wl
      and 'data-role="dec" className="justify-self-center' in wl,
      "٣ القرارُ في عمود نسبة التغيّر وفي منتصفه تحته — شبكةٌ من عمودين لا سطران متجاوران")
hook = rd("hooks/useLongPressSort.ts")
check("useLongPressSort(" in wl and "{...sort.itemProps(" in wl and 'addEventListener("touchmove", stop, { passive: false })' in hook
      and "setPointerCapture" in hook and "onClickCapture" in hook and "delay = 420" in hook,
      "٤ الترتيبُ بضغطةٍ مطوّلة (420 مل.ث) ثمّ سحب — يُمنع تمريرُ الصفحة أثناءه، ولا تُفتح البطاقةُ بعده")
check(not re.search(r"GripVertical|ArrowUp|ArrowDown|ChevronUp|MoveVertical", code(wl)),
      "٥ ولا زرَّ تحريكٍ ولا مقبضَ ظاهراً في البطاقة")
mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
api = rd("services/api.ts")
check('@router.put("/watchlist/order", dependencies=[Depends(require_owner)])' in mk and "r.sort_order = pos[r.symbol]" in mk
      and "sort_order=(last or 0) + 1" in mk and 'watchOrder: (symbols: string[]' in api,
      "٦ والترتيبُ يُحفظ على الخادم للمالك وحده، والشركةُ الجديدة آخرَ القائمة لا وسطَ ترتيبه")
check("style={{ margin: 0 }}" in wl and "flex flex-col justify-start p-2 md:p-4" in wl and "line-clamp-2 min-h-[2.7em]" in wl,
      "٧ السعرُ لا يقصّه هامشُ الوميض، ورأسُ البطاقة لا ينزل في صفٍّ أطول، والاسمُ سطران محجوزان")
# ── D684 ──
mp = rd("pages/MarketPage.tsx")
card = mp[mp.index('data-role="scr-card"'):mp.index("{shownMobile.length < shown.length && (")]
check(card.count("<Metric ") == 6 and 'grid grid-cols-3 gap-x-2' in card and "FairValueBar" not in card and "SafetyBar" not in card,
      "٨ بطاقةُ الفرز صفّان بشبكةٍ واحدة من ثلاث خاناتٍ (ستُّ خاناتٍ بمكوّنٍ واحد) — بلا أشرطةٍ مبعثرة")
metric = mp[mp.index("function Metric("):mp.index("function Chip(")]
check('className="min-w-0"' in metric and "text-center" not in metric and '<span dir="ltr">{value' in metric,
      "٩ وكلُّ خانةٍ يمين (لا وسط)، والرقمُ في عزلٍ ‏ltr فالإشارةُ قبله والنسبةُ بعده")
chip = mp[mp.index("function Chip("):mp.index("function FilterGroup(")]
check("color-mix(in srgb, ${color} 10%" in chip and "}1a`" not in chip and "}33`" not in chip
      and "VerdictTag" not in card and '.replace(".SR", "")' in card,
      "١٠ ووسمٌ بنمطٍ واحد بأرضيةٍ تُرسم فعلاً (‏color-mix لا لاحقةٌ على اسم رمز)، والرمزُ بلا «.SR»")
check('<span className="mx-1 text-[var(--ink-muted)]">·</span>' in card and "whitespace-nowrap" in metric,
      "١١ وتاريخُ القوائم بجانب درجته في سطرٍ واحد يفصلهما «·»")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
