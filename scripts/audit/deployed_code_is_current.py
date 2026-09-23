#!/usr/bin/env python3
"""ما يعمل في الحاوية هو ما دُفع — لا نسخةٌ سابقة (‏D410).

    python3 scripts/audit/deployed_code_is_current.py

قِيس: صُحّح حدُّ الشيخوخة من ‎45 إلى ‎137 يوماً ودُفع وأُعيد تشغيلُ
الخادم، ثمّ خرجت المسحةُ بـ**266 شائخةً من 270** — بدل أن تنهار إلى
بضع عشرات. فالإصلاحُ في المستودع والحاويةُ تعمل بالقديم.

وهذا أخبثُ أصناف العطب: **كلُّ شيءٍ يقول إنه نجح**. الدفعُ نجح،
والحارسُ أخضرُ على شجرة العمل، والتشغيلُ «أُعيد» — والمالكُ يقرأ على
شاشته أرقامَ نسخةٍ ماتت. ولا يُكشَف إلا بأن يُسأل **الكودُ العامل
نفسُه** عمّا عنده، لا الشجرةُ التي كتبناها.

## ما يُقاس

  ١ · ثوابتُ المحرّك في الشجرة == ثوابتُه كما تُقرأ من مسار التشغيل.
  ٢ · ودوالُّ أُضيفت حديثاً موجودةٌ فعلاً حيث يُشغَّل.
  ٣ · وبصمةُ ملفّ المحرّك واحدةٌ في الموضعَين.

ويُشغَّل **داخل الحاوية** (‏`docker exec … python /app/scripts/…`)
فيقارن `/app` بما في المستودع. فإن اختلفا فالنشرُ لم يكتمل — ولا
يُقرأ أيُّ قياسٍ بعده على أنه حكمٌ على المنتَج.
"""
from __future__ import annotations

# ══ لا فحصَ يكتب في بيانات المالك ══ (D160 · D429)
# يُحوَّل مخزنُ الحالة إلى مجلّدٍ مؤقّت **قبل** أيّ استيرادٍ من `app`،
# فالوحداتُ تقرأ مسارَها عند تحميلها. وسجلُّ مشاهداتِ حالة السوق معه:
# حكمُ العطلة يقرأ مشاهداتِ اليوم، فمشاهدةُ فحصٍ تدخله تُفسد دليلَه.
import os as _os, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX
_os.environ["SP_STATUS_LOG"] = _os.path.join(_SANDBOX, "status_codes.jsonl")

import hashlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


REL = "app/services/fair_value.py"
CANDS = [ROOT / "backend" / REL, pathlib.Path("/app") / REL]
seen = {}
for c in CANDS:
    if c.exists():
        seen[str(c)] = c

if len(seen) < 2:
    # بيئةٌ واحدةٌ فقط (شجرةٌ بلا حاوية أو العكس): يُقاس ما يمكن.
    print(f"⚠ نسخةٌ واحدةٌ من المحرّك مرئيّةٌ هنا ({list(seen) or 'لا شيء'})"
          " — المقارنةُ بين الشجرة والحاوية لم تُقَس")
    if not seen:
        sys.exit(0)
else:
    _h = {k: hashlib.sha256(v.read_bytes()).hexdigest()[:12]
          for k, v in seen.items()}
    check(len(set(_h.values())) == 1,
          "٣ بصمةُ المحرّك واحدةٌ في الشجرة ومسار التشغيل",
          " · ".join(f"{k}={h}" for k, h in _h.items()))

# ── ١ · الثوابتُ كما يقرؤها المُستورِد فعلاً ──────────────────────────
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
try:
    from app.services import fair_value as _fv
except ModuleNotFoundError as e:
    print(f"⚠ بيئةٌ ناقصة ({e.name}) — لم يُقَس")
    sys.exit(fail)

_where = getattr(_fv, "__file__", "?")
_stale = getattr(_fv, "STALE_AFTER_DAYS", None)
check(_stale is not None,
      "١ حدُّ الشيخوخة موجودٌ في المحرّك العامل",
      f"{_stale} · من {_where}")
if _stale is not None:
    check(120 <= _stale <= 150,
          "١ب وهو المشتقُّ من دورة الإفصاح لا القديمُ (‏45)", str(_stale))

# ── ٢ · والدوالُّ الحديثةُ موجودةٌ حيث يُشغَّل ─────────────────────────
for _name in ("risk_flags", "compute"):
    check(callable(getattr(_fv, _name, None)),
          f"٢ الدالّةُ `{_name}` موجودةٌ في النسخة العاملة")

print(("FAIL" if fail else "PASS")
      + " D410 — ما يعمل هو ما دُفع")
sys.exit(fail)
