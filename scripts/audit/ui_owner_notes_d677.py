#!/usr/bin/env python3
"""حارسُ D677 · D678 · D679 — ملاحظاتُ المالك (2026-10-10)، ساكناً (والقياسُ في المتصفّح: ui_d677.mjs).

  D677 «مختبرُ الأبحاث ينتقل مكانَ المراقبة، والمراقبةُ قسمٌ مكانه — ثلاثٌ في الصفّ على الحاسوب واثنتان على الجوال».
  D678 «سيطر على التصاميم الشاذّة عن تصميم التطبيق ووحّد هويّتها في كلّ مكان: سويتش، زر، قائمة منسدلة».
       قِيس قبل الإصلاح: قائمةٌ منسدلةٌ من نظام الجهاز في «التوقعات»، وسبعةُ صناديق اختيارٍ أصلية في أربعة ملفّات،
       ورقائقُ مفعَّلةٌ بإطارٍ ملوّن في أربعة ملفّات بخلاف لغة التبويبات (أرضيةٌ مصبوغة بلا إطار).
  D679 «المستشارُ الآليّ في تحليل الذكاء مكانَ التقرير الشامل، يشرب جميعَ معلومات التطبيق» — وكان لا يقرأ آراءَ بيوت
       الخبرة ولا الأحداثَ الجوهرية ولا الخطوطَ الحمراء ولا نبضَ السوق ولا انتباهَ الحوكمة.

    python3 scripts/audit/ui_owner_notes_d677.py
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
# ── D677 ──
wl, wp, pp = rd("components/market/WatchlistTab.tsx"), rd("pages/WatchlistPage.tsx"), rd("pages/PortfolioPage.tsx")
check("grid grid-cols-2 lg:grid-cols-3 gap-3" in wl and "العادل" in wl and "DECISION_INK" in wl and 'queryKey: ["screener-lite"]' in wl,
      "١ المراقبةُ بطاقاتٌ: اثنتان في الصفّ على الجوال وثلاثٌ على الحاسوب، وتفاصيلُ كلّ شركة (العادلُ والقرار) من الفرز نفسِه")
check('dir="ltr"' in wl, "٢ والنسبُ بإشارتها في موضعها (لا «%15.0-»)")
check("<WatchlistTab onOpen={setSheet} />" in wp and "StockSheet" in wp and "WatchlistTab" not in pp and "<StarsPage embedded />" in pp,
      "٣ المراقبةُ قسمٌ يفتح ورقةَ السهم، ولم تعد تبويباً في المحفظة؛ والمختبرُ تبويبُها")
# ── D678 ──
native = []
for f in SRC.rglob("*.tsx"):
    if f.name in ("Select.tsx", "CheckBox.tsx", "Toggle.tsx"):
        continue
    t = f.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    if re.search(r"<select\b|type=\"(checkbox|radio)\"", code):
        native.append(str(f.relative_to(SRC)))
check(not native, "٤ لا قائمةَ منسدلةً ولا صندوقَ اختيارٍ من نظام الجهاز — Select وCheckBox وToggle وحدها", str(native))
bordered = [str(f.relative_to(SRC)) for f in SRC.rglob("*.tsx")
            if re.search(r'borderColor: "var\(--brand\)"|border-\[var\(--brand-ink\)\] text-\[var\(--brand-ink\)\]', f.read_text(encoding="utf-8"))]
check(not bordered, "٥ ولا رقيقةَ مفعَّلةً بإطارٍ ملوّن — `.seg-btn` بلغة التبويبات", str(bordered))
css = rd("styles/globals.css")
on = re.search(r"\.seg-btn\.on \{[^}]*\}", css)
chip = re.search(r"\.seg-btn\.chip \{[^}]*\}", css)
check(bool(on) and "color-mix(in srgb, var(--brand) 12%" in on.group(0) and "border" not in on.group(0)
      and bool(chip) and "flex: none" in chip.group(0) and len(re.findall(r"^\.seg-btn \{", css, re.M)) == 1,
      "٦ و`.seg-btn` واحدٌ: أرضيةٌ مصبوغةٌ بـ12٪ للمفعَّل بلا إطار، و`.chip` يعدّل العرضَ وحده — كتبويبات المحفظة")
tg, cb = rd("components/common/Toggle.tsx"), rd("components/common/CheckBox.tsx")
check('role="switch"' in tg and "switch inline-block" in tg and "min-h-[32px]" in tg
      and 'role="checkbox"' in cb and "var(--brand)" in cb and "min-h-[32px]" in cb,
      "٧ والمفتاحُ وصندوقُ الاختيار مكوّنان واحدان بدورَي الوصول وهدفِ لمسٍ ≥ 32px")
# ── D679 ──
ai, gv, ap = rd("pages/AIPage.tsx"), rd("pages/GovernancePage.tsx"), rd("components/governance/AutopilotCard.tsx")
check("<AutopilotCard />" in ai and ">التقرير الشامل<" not in ai and "ai-full-report" not in ai and "fullReport" not in ai and "<AutopilotCard />" not in gv,
      "٨ المستشارُ في «تحليل الذكاء» مكانَ «التقرير الشامل»، ولا يتكرّر في الحوكمة")
check("md:grid-cols-2" in ap and "rounded-2xl" in ap and "<GoalPlan />" in ap and "<AutopilotChat />" in ap,
      "٩ وتصميمُه بلغة التطبيق: لوحةُ حكمٍ، ونقاطٌ وبطاقاتٌ في عمودين على الحاسوب، والهدفُ والحوار")
apy = (ROOT / "backend/app/services/autopilot.py").read_text(encoding="utf-8")
keys = re.search(r"POS_KEYS = \((.*?)\)", apy, re.S)
need = ("analysts", "material_events", "red_lines", "warnings", "stability", "fair_value_conf", "sector")
check(bool(keys) and all(f'"{k}"' in keys.group(1) for k in need),
      "١٠ ويقرأ لكلّ شركة: آراءَ البيوت والأحداثَ الجوهرية والخطوطَ الحمراء والتحذيرات والثباتَ وثقةَ العادل والقطاع",
      ", ".join(k for k in need if not keys or f'"{k}"' not in keys.group(1)))
check('"market": market, "attention": attention' in apy and '"نبض_السوق": pk.get("market")' in apy
      and apy.count("POS_KEYS") >= 3 and "analysts" in apy.split("قواعدُ ملزمة")[1][:2500],
      "١١ ونبضَ السوق وانتباهَ الحوكمة للمحفظة كلّها — في الرأي والحوار معاً، والموجِّهُ يأمر بقراءتها")
aic = (ROOT / "backend/app/services/ai_content.py").read_text(encoding="utf-8")
snap = re.search(r"snap = \{(.*?)\}\n", aic, re.S)
written = set(re.findall(r'"(\w+)":', snap.group(1))) if snap else set()
mk = re.search(r"MARKET_KEYS = \((.*?)\)", apy, re.S)
read = re.findall(r'"(\w+)"', mk.group(1)) if mk else []
check(bool(written) and bool(read) and set(read) <= written and "for k in MARKET_KEYS" in apy,
      "١٢ ونبضُ السوق يُقرأ بمفاتيح اللقطة التي يكتبها refresh_market_brief — لا بمفاتيحَ لا وجودَ لها",
      f"يقرأ ما لا يُكتب: {sorted(set(read) - written)}" if read else "لا MARKET_KEYS")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
