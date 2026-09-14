#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D287 — طريقةُ الجلب مسجَّلةٌ، والسجلُّ يُحرَس كما تُحرَس الشيفرة.
#
# طلب المالك تسجيلَ طريقة الجلب الذكيّ داخلَ الحزمة «حتى لا تُنسى وأستطيع
# نقلَ الطريقة ولو عملتُ من بيئةٍ أخرى». وقال أيضاً: «كثرةُ التعديلات
# تجعلك تنسى بعضها» — وهو محقّ، وهذه الوثيقةُ علاجُ ذلك.
#
# ووثيقةٌ بلا حارسٍ تشيخ بصمت: يُحذف ملفٌّ فتُصبح خريطتُها كاذبة، أو
# يُغيَّر اسمُ مَعبرٍ فتُحيل إلى ما لا وجودَ له. فتُقاس هنا:
#
#   ٠· الوثيقةُ موجودةٌ ومُحمَّلةٌ في الحزمة
#   ١· وفيها الأركانُ الخمسةُ للطريقة
#   ٢· وكلُّ ملفٍّ تُحيل إليه موجودٌ فعلاً
#   ٣· وكلُّ بلاغٍ تذكره مسجَّلٌ في السجلّ
#   ٤· والميثاقُ يُحيل إليها — فلا تُنسى في مجلّدٍ لا يُقرأ
#   ٥· ولا مفتاحَ سرّياً فيها
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


DOC_PATH = ROOT / "docs" / "FETCH_METHOD.md"
check(DOC_PATH.exists(), "٠ وثيقةُ الطريقة موجودة", str(DOC_PATH.name))
if not DOC_PATH.exists():
    raise SystemExit(1)
DOC = DOC_PATH.read_text(encoding="utf-8")
check(len(DOC) > 6000, f"٠ب ومكتملةٌ لا عنواناً ({len(DOC)} حرفاً)")

# ── ١ · الأركانُ الخمسة ─────────────────────────────────────────────────
PILLARS = {
    "انتحالُ بصمة TLS": ("curl_cffi", "impersonate"),
    "اكتشافُ النقطة": ("<base", "=NJ"),
    "طبقةُ المتصفّح": ("PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD", "executable_path"),
    "ترتيبُ الطبقات": ("تداول", "أرقام", "ياهو"),
    "انضباطُ الزمن": ("آخرُ إغلاق", "الجهلُ ليس حكماً"),
}
for name, needles in PILLARS.items():
    miss = [n for n in needles if n not in DOC]
    check(not miss, f"١ الركنُ «{name}» مشروحٌ بشيفرته",
          "غاب: " + "، ".join(miss) if miss else "")

# ── ٢ · الخريطةُ صادقة ─────────────────────────────────────────────────
paths = sorted(set(re.findall(r"`((?:backend|scripts|frontend)/[^`\s]+?\.(?:py|md|json))`",
                              DOC)))
gone = [p for p in paths if not (ROOT / p).exists()]
check(not gone, f"٢ وكلُّ ملفٍّ تُحيل إليه موجود ({len(paths)} مساراً)",
      "مفقود: " + "، ".join(gone[:3]) if gone else "")

# ── ٣ · البلاغاتُ المذكورةُ مسجَّلة ─────────────────────────────────────
reg = json.loads((ROOT / "scripts" / "audit" / "registry.json")
                 .read_text(encoding="utf-8"))
ids = {d["id"] for d in reg["defects"]}
cited = set(re.findall(r"\bD(\d{3})\b", DOC))
missing = sorted(f"D{c}" for c in cited if f"D{c}" not in ids)
check(not missing, f"٣ وكلُّ بلاغٍ تذكره مسجَّلٌ ({len(cited)} بلاغاً)",
      "غير مسجَّل: " + "، ".join(missing[:4]) if missing else "")

# ── ٤ · الميثاقُ يُحيل إليها ────────────────────────────────────────────
CLAUDE = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
check("docs/FETCH_METHOD.md" in CLAUDE,
      "٤ والميثاقُ يُحيل إليها — لا تُنسى في مجلّدٍ لا يُقرأ")

# ── ٥ · لا سرَّ فيها ───────────────────────────────────────────────────
secrets = re.findall(r"(?i)(AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z]{20,}|"
                     r"(?:api[_-]?key|token|secret|password)\s*[=:]\s*['\"][^'\"]{8,})",
                     DOC)
check(not secrets, "٥ ولا مفتاحَ سرّياً في الوثيقة", str(secrets[:1]))

print(("FAIL" if fail else "PASS") + " D287 — سجلُّ طريقة الجلب محروس")
raise SystemExit(fail)
