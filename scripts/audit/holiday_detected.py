#!/usr/bin/env python3
"""العطلةُ تُكتشَف من المصدر لا من التقويم (‏D413).

    python3 scripts/audit/holiday_detected.py

قال المالك: «اليومَ كان عطلةً للسوق ولم يكتشف التطبيقُ ذلك». وكانت
حالةُ السوق تُحسب من **ساعة الحائط وحدَها**: الأحدُ إلى الخميس «مفتوح»
في أوقاته — فالأعيادُ والعطلُ الرسميةُ والإغلاقاتُ الطارئةُ خارجَ
الحساب. وقِيس يومَ العطلة: الساعةُ تقول `pre`، وزمنُ تغذية تداولَ
`'12:39 PM'` بينما الوقتُ ‎9:40 — تغذيةٌ متجمّدةٌ على جلسةٍ سابقة.

## ولماذا لا يُترجَم رمزُ الحالة بعد

شوهد `market_status_code = 3` مرّةً واحدةً. ومشاهدةٌ واحدةٌ لا تُنشئ
معجماً: قد يعني «مغلق»، وقد يكون حالةَ ما-قبل-الافتتاح في يومٍ عاديّ.
فالمعجمُ (`CODE_MAP`) يبقى **فارغاً حتى يثبت** بمشاهدةٍ في يومٍ حيّ،
والمشاهداتُ تُسجَّل لتُبنى بالقياس. وهذا الحارسُ يمنع أن يُملأ المعجمُ
بالتخمين، ويشترط أن يبقى الشاهدُ الذي لا يحتاج معجماً عاملاً.
"""
from __future__ import annotations

import asyncio
import pathlib
import sys
from datetime import datetime, timedelta

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    from app.services import market_state as MS
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(0)

# ── ١ · الحالةُ لا تُحسب من الساعة وحدَها ─────────────────────────────
_ep = None
for c in (ROOT / "backend/app/api/v1/endpoints/settings.py",
          pathlib.Path("/app/app/api/v1/endpoints/settings.py")):
    if c.exists():
        _ep = c
        break
if _ep is None:
    print("⚠ لا نقطةَ إعداداتٍ في مسارٍ معروف — لم يُقَس")
else:
    T = _ep.read_text("utf-8")
    check("from app.services.market_state import market_state" in T,
          "١ نقطةُ الوقت تسأل حالةَ السوق من مصدرها")
    check('"market_status_source"' in T and '"market_status_evidence"' in T,
          "١ب ولا كلمةَ بلا سندها: المصدرُ والدليلُ يخرجان معها")

# ── ٢ · ومعجمُ المصدر لا يُملأ بالتخمين ───────────────────────────────
check(isinstance(MS.CODE_MAP, dict),
      "٢ معجمُ رموز الحالة موجودٌ ومعلَن")
check(not MS.CODE_MAP,
      "٢ب وهو فارغٌ حتى يثبت معناه بمشاهدةٍ في يومٍ حيّ — لا يُخمَّن",
      f"{sorted(MS.CODE_MAP)}" if MS.CODE_MAP else "")

# ── ٣ · والشاهدُ الذي لا يحتاج معجماً يعمل ────────────────────────────
# زمنُ تغذيةٍ متخلّفٌ عن الآن داخلَ ساعات الجلسة = لا جلسةَ اليوم.
_now = MS._mecca_now()
_far = (_now - timedelta(minutes=MS.FEED_LAG_MIN + 40)).strftime("%I:%M %p")
_near = _now.strftime("%I:%M %p")
check(MS._parse_feed_time(_near) is not None,
      "٣ زمنُ التغذية يُقرأ حين يأتي بصيغته")
check(MS._parse_feed_time("لا شيء") is None,
      "٣ب وما لا يُفهم يُعاد None — لا يُخمَّن")

_p = MS._parse_feed_time(_far)
if _p is not None:
    _lag = abs((_now - _p).total_seconds()) / 60.0
    check(_lag > MS.FEED_LAG_MIN,
          "٣ج وتخلّفُ التغذية يُقاس بالدقائق", f"{_lag:.0f} دقيقة")

# ── ٤ · والحالةُ تُعاد بمصدرها ودليلها دائماً ─────────────────────────
try:
    st = asyncio.run(MS.market_state())
except Exception as e:                                            # noqa: BLE001
    print(f"⚠ تعذّر حسابُ الحالة ({type(e).__name__}) — لم يُقَس")
    st = None
if isinstance(st, dict):
    check(st.get("status") in ("open", "pre", "preclose", "closed", "holiday"),
          "٤ الحالةُ من المفردات المعروفة", str(st.get("status")))
    check(bool(st.get("source")), "٤ب ومعها مصدرُها", str(st.get("source")))
    check(bool(st.get("evidence")), "٤ج ودليلُها", str(st.get("evidence")))
    check("clock_phase" in st,
          "٤د وطورُ الساعة يبقى معلَناً للمقارنة", str(st.get("clock_phase")))
    if st.get("holiday_suspected"):
        print(f"    ← يومُ عطلةٍ مُكتشَفٌ من المصدر: {st.get('evidence')}")

# ── ٥ · و«عطلة» حالٌ مستقلّةٌ عن «مغلق» ───────────────────────────────
# قال المالك: «هناك فرقٌ بين مغلق وعطلة». والمغلقُ يفتح بعد ساعات،
# والعطلةُ يومٌ كاملٌ بلا جلسة — وخلطُهما يُفقد المستثمرَ خبراً.
_ms = ROOT / "backend" / "app" / "services" / "market_state.py"
if not _ms.exists():
    _ms = pathlib.Path("/app/app/services/market_state.py")
if _ms.exists():
    S = _ms.read_text("utf-8")
    check('"status": "holiday"' in S,
          "٥ التغذيةُ المتجمّدةُ تُسمّى «عطلة» لا «مغلق»")

# ── ٦ · وأسماءُ الحالات من موضعٍ واحدٍ تقرؤه الشاشتان ─────────────────
# عادت الحالةُ إلى «نبض السوق» بأمر المالك بعد أن حُذفت في D302 لأنّها
# كانت من مصدرَين متناقضَين. فالخطرُ يعود لو نُسخت الأسماءُ في كلّ شاشة.
_lib = ROOT / "frontend" / "src" / "lib" / "marketStatus.ts"
if not _lib.exists():
    print("⚠ لا حاكمَ عرضٍ في هذه البيئة — لم يُقَس")
else:
    L = _lib.read_text("utf-8")
    check("holiday:" in L, "٦ حاكمُ العرض يعرف «عطلة» حالاً مستقلّة")
    _dup = []
    for _rel in ("frontend/src/components/common/LiveClock.tsx",
                 "frontend/src/pages/MarketPage.tsx"):
        _f = ROOT / _rel
        if not _f.exists():
            continue
        T = _f.read_text("utf-8")
        if "statusView" not in T:
            _dup.append(_rel.split("/")[-1] + ": لا يقرأ الحاكم")
        if '"السوق مفتوح"' in T or '"السوق مغلق"' in T:
            _dup.append(_rel.split("/")[-1] + ": ينسخ الأسماء")
    check(not _dup, "٦ب والشاشتان تقرآن منه ولا تنسخان الأسماء",
          " · ".join(_dup) if _dup else "")

# ── ٧ · وللعطلة علامةٌ مختلفةُ الشكل لا اللون فقط ─────────────────────
# «اعتمد أيقونة العطلة نجمةً رماديةً مثل تريدنق فيو». والعطلةُ يومٌ خارج
# الجدول، فعلامتُها تُقرأ بلمحةٍ بلا نصّ — ومن موضعٍ واحدٍ لا يُنسَخ.
_mk = ROOT / "frontend" / "src" / "components" / "common" / "StatusMark.tsx"
if not _mk.exists():
    print("⚠ لا علامةَ حالةٍ في هذه البيئة — لم يُقَس")
else:
    M = _mk.read_text("utf-8")
    check("HolidayStar" in M and "<svg" in M,
          "٧ للعطلة نجمةٌ مرسومةٌ لا نقطة")
    check("--st-idle" in M, "٧ب رماديةٌ من رموز المظهر لا لونٍ ثابت")
    _uses = []
    for _rel in ("frontend/src/components/common/LiveClock.tsx",
                 "frontend/src/pages/MarketPage.tsx"):
        _f = ROOT / _rel
        if _f.exists() and ("HolidayStar" in _f.read_text("utf-8")
                            or "StatusMark" in _f.read_text("utf-8")):
            _uses.append(_rel.split("/")[-1])
    check(len(_uses) == 2,
          "٧ج والساعةُ والنبضُ يرسمان منها معاً", "، ".join(_uses))

print(("FAIL" if fail else "PASS")
      + " D413 — العطلةُ من المصدر، ومصدرُ الأسماء واحد")
sys.exit(fail)
