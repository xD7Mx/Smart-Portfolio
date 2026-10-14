#!/usr/bin/env python3
"""حارسُ D714 — لجنةُ النشر تقيس ولا تضجّ: بيئةٌ ناقصةٌ تُقال «لم يُقَس» لا «سقط».

قِيس على الخادم (‏audit · run 38604121248): المضيفُ بلا ‎node‎ («✖ بيئةٌ ناقصة: node») وبلا تبعيّات بايثون (‏loguru ١٢٠ مرّة ·
fastapi · sqlalchemy · pydantic_settings · apscheduler)، فكانت لجنةُ النشر تسرد عشراتِ «الساقطين» في كلّ نشر — ضجيجُ بيئةٍ لا
عطبُ شيفرة، يُخفي العطبَ الحقيقيّ إن وقع. فالحارسُ يمنع العودة:
  · فحصُ المتصفّح يمرّ بـ‎_node‎: بلا ‎node‎ «لم يُقَس» ويُعدّ، ومع ‎node‎ سقوطُه سقوط.
  · واللجنةُ في النشر وفي مهمّة ‎audit‎ تُشغَّل في صورة الخادم نفسِها، والمستودعُ مربوطٌ للقراءة فقط.

    python3 scripts/audit/committee_env_d714.py
"""
import pathlib, re, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


run = (ROOT / "scripts/audit/run.sh").read_text(encoding="utf-8")
m = re.search(r"(?ms)^_node\(\) \{.*?^\}", run)
bare = re.findall(r"(?m)^\s*node scripts/audit/\S+", run)
check(bool(m) and not bare and len(re.findall(r"(?m)^\s*_node scripts/audit/", run)) >= 30,
      "١ كلُّ فحص متصفّحٍ في اللجنة يمرّ بـ‎_node‎ — لا نداءَ ‎node‎ مجرّداً يُحسب ساقطاً بنقص البيئة", f"مجرّدٌ {len(bare)}")
if m:
    fn = m.group(0)
    r = subprocess.run(["/bin/bash", "-c", f"_SKIPPED=0\n{fn}\n_node scripts/audit/x.mjs; echo \"rc=$? n=$_SKIPPED\""],
                       capture_output=True, text=True, env={"PATH": "/nonexistent"})
    check("لم يُقَس" in r.stdout and "rc=0 n=1" in r.stdout,
          "٢ وبلا ‎node‎ يُقال «لم يُقَس» ويُعدّ — لا يُحسب سقوطاً", r.stdout.strip().replace("\n", " · ")[:120])
    import shutil
    nd = shutil.which("node")
    if nd:
        r2 = subprocess.run(["/bin/bash", "-c", f"_SKIPPED=0\n{fn}\n_node -e 'process.exit(3)'; echo \"rc=$?\""],
                            capture_output=True, text=True)
        check("rc=3" in r2.stdout, "٣ ومع ‎node‎ سقوطُ الفحص سقوطٌ — لا يُرخى شيء", r2.stdout.strip()[-20:])
check("لم يُقَس هنا (لا node)" in run and "${_SKIPPED}" in run,
      "٤ والحكمُ يذكر عددَ ما لم يُقَس — «اجتاز فيما قِيس» لا «اجتاز» مطلقاً")
img = (ROOT / "scripts/ops/committee_image.sh").read_text(encoding="utf-8") if (ROOT / "scripts/ops/committee_image.sh").exists() else ""
comp = (ROOT / "scripts/ops/complete.sh").read_text(encoding="utf-8")
ops = (ROOT / ".github/workflows/ops.yml").read_text(encoding="utf-8")
check('/dev/null:/repo/$f:ro' in img and 'for f in .env backend/.env' in img and '-v "$PWD/backend":/app:ro' in img,
      "٤ب ولا يرى الحرّاسُ أسرارَ الخادم: ‎.env‎ مُقنَّعٌ بملفٍّ فارغ (قِيس أنّ الإعدادات تطبع قيمَ مفاتيحه الزائدة)، و‎/app‎ هي ‎backend‎ المستودع لا نسخةُ الصورة")
check('-v "$PWD":/repo:ro' in img and "docker inspect -f '{{.Config.Image}}' sp_backend" in img
      and "exec bash scripts/audit/run.sh" in img
      and "bash scripts/ops/committee_image.sh" in comp and "bash scripts/ops/committee_image.sh ;;" in ops,
      "٥ واللجنةُ في النشر ومهمّة ‎audit‎ تُشغَّل في صورة الخادم نفسِها، والمستودعُ للقراءة فقط، والمضيفُ احتياطٌ إن غابت الصورة")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
