#!/usr/bin/env python3
"""حارسُ D716 — عملُ النشر لا يخنق الخادم.

قِيس (2026-10-14 · سجلُّ النواة بعد الإعادة): الخادمُ ‎909‎ م.ب ذاكرةً، واجتمع في دورة النشر بناءُ الواجهة (‏D715) ولجنةٌ كاملةٌ
في حاويةٍ ثانية (‏D714) فوق إقلاع الخادم وحصاد القوائم ومسحة التقييم — فنفدت الذاكرةُ والتبادلُ وقتلت النواةُ ‎uvicorn‎
(«Killed process … (uvicorn)»)، وتوقّف التطبيقُ حتى أعاد المالكُ الخادم. فالحارسُ يمنع العودة:
  · لا بناءَ للواجهة ولا لجنةَ كاملةَ في دورة النشر — كلٌّ بمهمّته منفرداً.
  · وكلُّ عملٍ ثقيل (بقيّةُ الدورة · المسحة · البناء · اللجنة) خلف بوّابة الذاكرة: لا يبدأ قبل أن يُكمل الخادمُ إقلاعَه ويتّسع
    المتاح، وإلا قيل ذلك ولم يُشغَّل.
  · وحاويةُ اللجنة بسقفٍ — إن ضاقت قُتلت هي لا الخادم.

    python3 scripts/audit/server_load_d716.py
"""
import os, pathlib, re, subprocess, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


def code(path):
    """الأوامرُ وحدها — بلا أسطر التعليق."""
    return "\n".join(l for l in (ROOT / path).read_text(encoding="utf-8").splitlines() if not l.lstrip().startswith("#"))


comp = code("scripts/ops/complete.sh")
img = code("scripts/ops/committee_image.sh")
ops = (ROOT / ".github/workflows/ops.yml").read_text(encoding="utf-8")
check("docker compose build" not in comp and "committee_image.sh" not in comp and "scripts/audit/run.sh" not in comp,
      "١ دورةُ النشر لا تبني الواجهة ولا تُشغّل اللجنةَ الكاملة — اجتماعُهما فوق الإقلاع والمسحة قتل ‎uvicorn‎")
heavy = comp.index('say "٣ · لقطةُ «تداول»"')
gate = comp.find("scripts/ops/mem_gate.sh")
check(0 <= gate < heavy and "exit 1" in comp[gate:heavy],
      "٢ وبقيّةُ الدورة خلف بوّابة الذاكرة: لا لقطةَ ولا حصادَ قبل أن يُكمل الخادمُ إقلاعَه — وإلا توقّفت الدورةُ لا الخادم")
sw = comp.index('say "٥ · مسحةُ التقييم')
check('mem_gate.sh 250 "مسحة التقييم"' in comp[:sw],
      "٣ والمسحةُ خلف البوّابة كذلك — تُؤجَّل إلى موعدها الليليّ إن ضاقت الذاكرة")
web = ops[ops.index("            web)"):]
web = web[:web.index(";;")]
bj = ops[ops.index("\n  build_web:"):ops.index("\n  run:\n")] if "\n  build_web:" in ops else ""
check("docker compose build" not in web and "runs-on: ubuntu-latest" in bj and "npm run build" in bj
      and "upload-artifact" in bj and "download-artifact" in ops and "docker cp" in web and "docker commit" in web,
      "٤ والواجهةُ تُبنى على أجهزة GitHub لا على الخادم — والخادمُ يضعها مكانَ القديمة فقط (بناءٌ امتدّ ١٧ دقيقةً على معالجٍ مستنزَف)")
m = re.search(r"docker run [^\n]*--memory (\d+)m", img)
check("mem_gate.sh" in img and m and img.index("mem_gate.sh") < img.index("docker run --rm") and int(m.group(1)) <= 512,
      "٥ واللجنةُ في صورة الخادم خلف البوّابة وحاويتُها بسقفٍ (إن ضاقت قُتلت هي لا الخادم)", f"سقف {m.group(1) if m else '؟'}م.ب")

# ٦ سلوكاً: البوّابةُ تمنع حين لا يردّ الخادم، وحين يضيق المتاح، وتأذن حين يتّسع
d = pathlib.Path(tempfile.mkdtemp(prefix="sp-d716-"))
(d / "curl").write_text("#!/bin/sh\nexit ${FAKE_CURL_RC:-0}\n"); (d / "curl").chmod(0o755)
(d / "sleep").write_text("#!/bin/sh\nexit 0\n"); (d / "sleep").chmod(0o755)
gate_sh = str(ROOT / "scripts/ops/mem_gate.sh")
env = {**os.environ, "PATH": f"{d}:{os.environ.get('PATH', '')}"}
run = lambda *a, rc="0": subprocess.run(["bash", gate_sh, *a], capture_output=True, text=True,   # noqa: E731
                                        env={**env, "FAKE_CURL_RC": rc})
down, tight, ok = run("1", "س", "20", rc="7"), run("99999999", "س", "20"), run("1", "س", "20")
check(down.returncode == 1 and "لم يُكمل إقلاعَه" in down.stdout and tight.returncode == 1 and "دون" in tight.stdout
      and ok.returncode == 0,
      "٦ وسلوكاً: الخادمُ لا يردّ ⇒ لا يُشغَّل · المتاحُ يضيق ⇒ لا يُشغَّل · يتّسع والخادمُ يردّ ⇒ يُشغَّل",
      f"{down.returncode}/{tight.returncode}/{ok.returncode}")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
