#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D297 — أمرُ التركيب يُنقَل حرفياً، ولا يُكتب من الذاكرة.
#
# سلّمتُ المالكَ حزمةً وأمراً فيه `docker compose -f docker/docker-compose.yml`
# — ومِلفُّ التشكيل في **جذر المستودع** لا في `docker/`. فخرج:
#
#     open /home/ubuntu/Smart-Portfolio/docker/docker-compose.yml:
#     no such file or directory
#
# والحزمةُ سليمةٌ تماماً: العطبُ في **سطرٍ كتبتُه من حفظي** بدل أن أنقل ما
# يطبعه `scripts/package.sh`. وهذا الصنفُ تكرّر: أمرٌ لمالكٍ على مسارٍ
# محميٍّ بالمصادقة (‏D-سابق)، ثم مسارٌ لا وجودَ له هنا. والقاعدةُ:
#
#   **ما يُسلَّم للمالك يُقاس قبل تسليمه — أو يُنقَل عن مصدرٍ مقيس.**
#
# فيُقاس هنا:
#   ٠· السكربتُ يكتب أمرَ التركيب ملفّاً (لا طبعاً عابراً يُنقَل بالحفظ)
#   ١· وكلُّ مسارٍ في الأمر موجودٌ فعلاً في المستودع
#   ٢· و`docker compose` يُنادى حيث يوجد ملفُّ التشكيل
#   ٣· واسمُ الحزمة هو الاسمُ الواحدُ المشروط
#   ٤· ولا مسارَ تشكيلٍ وهميٌّ في أيّ ملفٍّ متتبَّع
#   ٥· ولا سرَّ في الأمر
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


PKG = (ROOT / "scripts" / "package.sh").read_text(encoding="utf-8")

# ── ٠ · الأمرُ ملفٌّ يُنقَل، لا سطرٌ يُحفَظ ────────────────────────────────
check('cat > "$NAME.install.txt"' in PKG,
      "٠ أمرُ التركيب يُكتب ملفّاً بجانب الحزمة — لا يُنقَل بالحفظ")
check('cat "$NAME.install.txt"' in PKG,
      "٠ب ويُطبع أيضاً مع البناء (شرطُ البند ٢٩)")

check("/spupdate*.install.txt" in (ROOT / ".gitignore").read_text(encoding="utf-8"),
      "٠د وملفُّ الأمر مخرَجُ بناءٍ لا كودٌ — لا يدخل تاريخَ المستودع")

m = re.search(r"cat > \"\$NAME\.install\.txt\" <<'INSTALL'\n(.*?)\nINSTALL",
              PKG, re.S)
check(bool(m), "٠ج وكتلةُ الأمر تُقرأ من السكربت")
if not m:
    raise SystemExit(1)
CMD = m.group(1)

# ── ١ · كلُّ مسارٍ في الأمر موجود ───────────────────────────────────────
# تُقرأ المساراتُ النسبية (‏`-f x/y.yml` وما شابه) وتُطابَق بالمستودع.
# و«‎-f» ليست كلُّها إشارةَ ملفّ: `rm -f` قوّةٌ لا مسار. فيُقرأ ما يتبع
# `docker compose` وحدَه — أوّلُ قياسٍ سقط في هذا الفرق.
flagged = re.findall(r"docker\s+compose[^\n\\]*?-f\s+([^\s\\]+)", CMD)
gone = [p for p in flagged
        if not p.startswith("/") and not (ROOT / p).exists()]
check(not gone, f"١ وكلُّ ملفٍّ يُشار إليه بـ‎-f موجود ({len(flagged)} ملفاً)",
      "مفقود: " + "، ".join(gone) if gone else "لا إشارةَ صريحة")

# ── ٢ · `docker compose` يُنادى حيث يوجد ملفُّ التشكيل ──────────────────
compose = [p for p in ("docker-compose.yml", "compose.yml",
                       "docker-compose.yaml")
           if (ROOT / p).exists()]
check(bool(compose), "٢ ملفُّ التشكيل موجودٌ في المستودع", ", ".join(compose))
if "docker compose" in CMD and not flagged:
    # بلا ‎-f: يُنادى في مجلّدٍ يجب أن يحوي ملفَّ التشكيل في **جذر** الحزمة.
    check(bool(compose) and (ROOT / compose[0]).parent == ROOT,
          "٢ب وبلا ‎-f: التشكيلُ في الجذر حيث يُنفَّذ الأمر",
          compose[0] if compose else "")
check("docker/docker-compose" not in CMD,
      "٢ج ولا مسارٌ وهميٌّ تحت docker/ — هو عطبُ D297 بعينه")

# ── ٣ · اسمُ الحزمة واحد ────────────────────────────────────────────────
check("spupdatechanged.tar.gz" in CMD,
      "٣ واسمُ الحزمة هو الاسمُ المشروط")
check("cp -a .env" in CMD,
      "٣ب ونسخةُ .env تُحفظ قبل الفكّ — بياناتُ المالك لا تُفقد")

# ── ٤ · ولا مسارَ تشكيلٍ وهميٍّ في أيّ ملفٍّ متتبَّع ─────────────────────
try:
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.split()
except Exception as e:                                            # noqa: BLE001
    tracked = []
    print(f"…  تعذّر جردُ الملفّات ({type(e).__name__}) — لا يُعدّ نجاحاً")
bad = []
for rel in tracked:
    f = ROOT / rel
    if f.suffix not in (".md", ".sh", ".py", ".yml", ".yaml", ".txt"):
        continue
    try:
        txt = f.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        continue
    code = f.suffix in (".sh", ".py", ".yml", ".yaml")
    for line in txt.splitlines():
        # في الشيفرة: سطرُ تعليقٍ شرحٌ لا أمر — وشرحُ عطبٍ يذكر المسارَ
        # الخاطئ بنصّه (كما في هذا الحارس نفسِه) ليس عطباً.
        if code and line.lstrip().startswith("#"):
            continue
        for hit in re.findall(r"[-\w./${}]*docker-compose\.ya?ml", line):
            p = hit.lstrip("./")
            if "$" in p or "{" in p:          # قالبٌ يُملأ لا مسارٌ ثابت
                continue
            if "/" in p and not (ROOT / p).exists() and "audit" not in rel:
                bad.append(f"{rel}:{hit}")
check(not bad, f"٤ ولا مسارَ تشكيلٍ لا وجودَ له في ملفٍّ متتبَّع ({len(tracked)} ملفاً)",
      "؛ ".join(bad[:3]) if bad else "")

# ── ٥ · ولا سرَّ في الأمر ───────────────────────────────────────────────
secrets = re.findall(r"(?i)(AIza[0-9A-Za-z_\-]{20,}|sk-[0-9A-Za-z]{20,}|"
                     r"[0-9]{8,12}:AA[A-Za-z0-9_-]{30,})", CMD)
check(not secrets, "٥ ولا مفتاحَ سرّياً في أمر التركيب")

print(("FAIL" if fail else "PASS") + " D297 — أمرُ التركيب مقيسٌ لا محفوظ")
sys.exit(fail)
