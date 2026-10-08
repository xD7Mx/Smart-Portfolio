#!/usr/bin/env python3
"""حارسُ D636: المؤشّراتُ الفنّية لا تُحسب عبر قفزةٍ يستحيل أن تكون حركةَ سوق (حدُّ «تداول» اليوميّ 10٪).
الحالاتُ من بوابة الإصدار الأوّل على الخادم (2026-10-08)."""
import os, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
_SB = tempfile.mkdtemp()
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
from app.services.technical import analyze, clean_series   # noqa: E402

fail = 0
def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))

def ser(vals):
    return [{"date": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "close": v} for i, v in enumerate(vals)]

# الميثانول: تخفيضُ رأس مال ← +350٪ ثمّ استقرار
meth = ser([8.9, 8.8, 8.87, 39.88, 40.1, 39.7])
out, ev = clean_series(meth)
check(len(out) == 6 and abs(out[0]["close"] - 8.9 * 39.88 / 8.87) < 1e-6 and ev and ev[0]["kind"] == "حدثُ رأس مال",
      "١ قفزةٌ دائمة (الميثانول +350٪) ← يُعدَّل ما قبلها بنسبتها ويُسجَّل الحدث", str(ev))
# الأسماك: شريحةٌ معطوبة 64 ← 18 (أيام) ← 65
fish = ser([64.0, 64.2, 18.28, 18.5, 19.1, 19.43, 65.7, 65.2, 65.05])
out, ev = clean_series(fish)
check([p["close"] for p in out] == [64.0, 64.2, 65.7, 65.2, 65.05] and ev[0]["kind"] == "شريحةٌ معطوبة"
      and ev[0]["date"] == fish[2]["date"] and ev[0]["until"] == fish[6]["date"],
      "٢ قفزتان متعاكستان خلال 15 جلسة ← الشريحةُ بينهما تُحذف ولا يُعدَّل شيء", str([p["close"] for p in out]))
# حركةُ سوقٍ عادية لا تُمسّ
calm = ser([10, 10.9, 9.9, 10.8, 11.5, 10.4])
out, ev = clean_series(calm)
check([p["close"] for p in out] == [10, 10.9, 9.9, 10.8, 11.5, 10.4] and not ev, "٣ حركةٌ ضمن حدّ التذبذب لا تُمسّ")
# المؤشّراتُ بعد التصحيح لا ترى القفزة
long_ = ser([8.8 + 0.01 * (i % 5) for i in range(220)] + [39.9 + 0.05 * (i % 5) for i in range(30)])
t = analyze(long_) or {}
sma = t.get("sma200") or t.get("indicators", {}).get("sma200")
check(sma is None or sma > 30, "٤ المتوسّطُ 200 بعد حدث رأس المال على أساسٍ واحد لا خليطِ أساسين", str(sma))
src = (ROOT / "backend/app/services/market_screener.py").read_text()
check("points, _tev = clean_series(points)" in src and '"tech_events": _tev' in src,
      "٥ أطرُ الفرز وعائدُ السنة (يقرؤهما المختبر) تمرّ بالتصحيح نفسِه، والأحداثُ مسجَّلة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
