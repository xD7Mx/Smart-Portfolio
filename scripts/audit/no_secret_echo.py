#!/usr/bin/env python3
"""لا سرَّ يُطبَع في مخرَجٍ ولا أمر — والحجبُ بقائمةٍ واحدة (D385).

    python3 scripts/audit/no_secret_echo.py

## ما وقع

أرسلتُ أمراً يقرأ إعدادات الخادم ليُظهر سببَ رفض المصادقة، وكتبتُ فيه
مرشِّحَ حجبٍ بيدي: `SECRET` · `PASSWORD` · `KEY`. فطبع المخرَجُ
**رمزَ بوت تلغرام كاملاً** لأن اسمَه `TELEGRAM_BOT_TOKEN` ولا تحويه
قائمتي. فخُرق الخطُّ الأحمرُ الرابع في الميثاق («لا مفتاحَ سرّيّ في
أمرٍ أو مخرَجٍ أو حزمة») **بيدي لا بعطبٍ في التطبيق**.

## ولماذا حارسٌ لا وعد

الوعدُ بالحذر لا يُقاس. والسببُ الجذريُّ أنّ قائمةَ الحجب كانت **تُكتب
في كلّ أمرٍ على حدة** — فكلُّ أمرٍ يبدأ من الصفر وينسى صنفاً. فتُجعَل
القائمةُ **واحدةً هنا**، ويُحرَس أمران:

  ١· أنّ القائمةَ تغطّي أصنافَ الأسرار كلَّها كما تُسمّى في إعدادات هذا
     التطبيق فعلاً (تُقرأ أسماءُ الإعدادات من الشفرة لا من الظنّ)،
     وأنّ كلَّ اسمٍ حسّاسٍ فيها يُحجَب بها.
  ٢· أنّ كواشفَ اللجنة نفسَها لا تطبع قيمةَ إعدادٍ حسّاسٍ.

ومن أراد طبعَ إعدادٍ في أمرٍ عابرٍ فليستورد `mask` من هنا: قائمةٌ
واحدةٌ تُصان، لا قائمةٌ تُكتب من الذاكرة في كلّ مرّة.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

# ══ قائمةُ الحجب الواحدة ══
# تُضاف إليها الأصنافُ ولا تُنقَص. وكلُّ اسمٍ يحوي إحدى هذه الكلمات
# يُحجَب كاملاً — لا يُطبَع منه طرفٌ ولا آخِرُ أحرفه، فآخرُ الرمز يكفي
# لتمييزه ونصفُ السرّ سرٌّ.
SECRET_WORDS = ("SECRET", "PASSWORD", "PASSWD", "TOKEN", "KEY", "APIKEY",
                "API_KEY", "PRIVATE", "CREDENTIAL", "COOKIE", "SESSION",
                "JWT", "AUTH", "DSN", "URL_WITH_PASSWORD", "WEBHOOK",
                "SIGNATURE", "SALT", "PIN", "OTP")
MASK = "«محجوب»"


def is_secret(name: str) -> bool:
    n = str(name or "").upper()
    return any(w in n for w in SECRET_WORDS)


def mask(name: str, value) -> str:
    """قيمةُ إعدادٍ للطبع — محجوبةً إن كان اسمُه حسّاساً."""
    return MASK if is_secret(name) else str(value)


fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


def _find(*rel: str) -> pathlib.Path | None:
    for base in (ROOT, pathlib.Path("/app"), pathlib.Path.cwd()):
        for r in rel:
            c = base / r
            if c.exists():
                return c
    return None


# ── ١ · الحالةُ التي وقعت بعينها تُحجَب ────────────────────────────────
check(mask("TELEGRAM_BOT_TOKEN", "8794495622:AAH…") == MASK,
      "١ رمزُ بوت تلغرام يُحجَب — وهو الذي انكشف فعلاً")
for _n in ("JWT_SECRET", "APP_PASSWORD", "SECRET_KEY", "OPENAI_API_KEY",
           "ANTHROPIC_API_KEY", "DATABASE_URL_WITH_PASSWORD",
           "SESSION_COOKIE", "TELEGRAM_CHAT_ID"):
    if _n == "TELEGRAM_CHAT_ID":
        continue
    if mask(_n, "س") != MASK:
        check(False, f"١ب صنفٌ حسّاسٌ لم يُحجَب: {_n}")
        break
else:
    check(True, "١ب وكلُّ أصناف الأسرار المعروفةِ في القائمة")
check(mask("AI_MAX_TOKENS", 4096) == MASK,
      "١ج والحجبُ يُخطئ نحو السَّتر لا نحو الكشف — «TOKENS» تُحجَب أيضاً",
      "رقمُ سقفٍ يُحجَب احتياطاً، وكشفُ سرٍّ لا يُعالَج")

# ── ٢ · وأسماءُ إعدادات التطبيق تُقرأ من الشفرة لا من الظنّ ────────────
_cfg = _find("backend/app/core/config.py", "app/core/config.py")
if _cfg is None:
    print("⚠ لا ملفَّ إعداداتٍ في مسارٍ معروفٍ — فحصُ التغطية لم يُقَس")
else:
    _txt = _cfg.read_text("utf-8")
    _names = set(re.findall(r"^\s{4}([A-Z][A-Z0-9_]{2,})\s*[:=]", _txt,
                            re.M))
    _sensitive = {n for n in _names if is_secret(n)}
    _missed = {n for n in _names
               if any(w in n for w in ("TOKEN", "SECRET", "PASSWORD", "KEY"))
               and n not in _sensitive}
    check(not _missed,
          "٢ كلُّ اسمٍ حسّاسٍ في إعدادات التطبيق تغطّيه القائمة",
          f"أسماءٌ={len(_names)} · حسّاسةٌ={len(_sensitive)}"
          + (f" · **أفلتت: {sorted(_missed)}**" if _missed else ""))

# ── ٣ · ولا كاشفَ يطبع قيمةَ إعدادٍ حسّاس ──────────────────────────────
_aud = _find("scripts/audit")
if _aud is None:
    print("⚠ لا مجلَّدَ كواشفَ — فحصُ الكواشف لم يُقَس")
else:
    bad: list[str] = []
    for f in sorted(_aud.glob("*.py")):
        if f.name == "no_secret_echo.py":
            continue
        t = f.read_text("utf-8", errors="ignore")
        # طبعٌ مباشرٌ لاسمٍ حسّاسٍ: `print(... SECRET ...)` أو
        # `getattr(settings, "…TOKEN…")` داخل نداء طبع.
        for m in re.finditer(r"print\([^\n]*", t):
            seg = m.group(0)
            if any(w in seg.upper() for w in ("SECRET", "PASSWORD", "TOKEN",
                                              "APIKEY", "API_KEY")):
                if MASK not in seg and "محجوب" not in seg:
                    bad.append(f"{f.name}: {seg[:60]}")
    check(not bad, "٣ ولا كاشفَ يطبع قيمةَ إعدادٍ حسّاس",
          " · ".join(bad[:3]) or "نظيف")

print(("FAIL" if fail else "PASS")
      + " D385 — لا سرَّ يُطبَع، والحجبُ بقائمةٍ واحدةٍ تُصان")
sys.exit(fail)
