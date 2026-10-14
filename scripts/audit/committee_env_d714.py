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
      and "bash scripts/ops/committee_image.sh ;;" in ops,
      "٥ واللجنةُ في مهمّة ‎audit‎ تُشغَّل في صورة الخادم نفسِها، والمستودعُ للقراءة فقط، والمضيفُ احتياطٌ إن غابت الصورة "
      "(ولا تُشغَّل في دورة النشر — ‏D716)")

# ‏D714 (الجولةُ الثانية · run 38605415518): ما سقط في الصورة وحدَها كان عيوبَ حرّاسٍ لا عيوبَ شيفرة — فيُمنع عودُها:
eck = (ROOT / "scripts/audit/engine_cache_key.py").read_text(encoding="utf-8")
check(".write_bytes(" not in eck and ".write_text(" not in eck,
      "٦ حارسُ مفتاح الكاش يقيس بلا كتابةٍ في شيفرة المحرّك — كتب فيها ثمّ أعادها، فسقط حيث الشيفرةُ للقراءة فقط")
import ast, os, tempfile
st = (ROOT / "scripts/audit/static.py").read_text(encoding="utf-8")
fn = next((n for n in ast.parse(st).body if isinstance(n, ast.FunctionDef) and n.name == "tracked_files"), None)
got = None
if fn is not None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as t:
        t.write("a.py\nb/c.ts\n")
    old_env = dict(os.environ)
    os.environ.update(PATH="/nonexistent", SP_TRACKED=t.name)
    ns = {"os": os, "subprocess": subprocess, "pathlib": pathlib, "ROOT": ROOT}
    try:
        exec(compile(ast.Module([fn], []), "static.py", "exec"), ns)
        got = [x for x in ns["tracked_files"]() if x]
    except Exception as e:                                           # noqa: BLE001
        got = f"{type(e).__name__}: {e}"
    finally:
        os.environ.clear(); os.environ.update(old_env); os.unlink(t.name)
ic = (ROOT / "scripts/audit/install_command.py").read_text(encoding="utf-8")
check(got == ["a.py", "b/c.ts"] and "SP_TRACKED" in ic,
      "٧ وحارسُ الأسرار (وجردُ أمر التركيب) يقرآن جردَ المضيف حين لا ‎git‎ — لا «تعذّر سردُ الملفّات» في صورة الخادم", str(got)[:80])
check("git ls-files > \"$TRK\"" in img and "-e SP_TRACKED=/tmp/sp_tracked" in img and '"$TRK":/tmp/sp_tracked:ro' in img,
      "٨ والمضيفُ يُعدّ الجردَ ويربطه للقراءة في حاوية اللجنة")
dd = (ROOT / "scripts/audit/deals_and_depth.py").read_text(encoding="utf-8")
c6 = dd.index("# ── ٦ ·")
seg = dd[c6:dd.index("# ── ٨", c6) if "# ── ٨" in dd[c6:] else len(dd)]
check(all(f"sd.{x}" in seg.split('"٦ ولا يُمحى')[0] for x in ("tadawul_negotiated", "tadawul_trade_details", "argaam_deals", "fetch_rows"))
      and seg.count("sd.tadawul_negotiated") >= 2,
      "٩ وحارسُ الصفقات يُبدّل طبقاتِ الجلب الأربعَ كلَّها في ٦ و٧ — بشبكةٍ أجاب «تداول» الحقيقيّ فقاس الحارسُ الشبكةَ لا السلوك")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
