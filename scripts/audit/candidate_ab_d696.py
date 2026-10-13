#!/usr/bin/env python3
"""حارسُ D696 — الأساسُ والمرشَّحُ يُقاسان في الجولة نفسِها، وكلُّ قياسٍ يُنسب إلى الشيفرة التي قاسها.

قِيس (‏D693): إصلاحٌ لا يجري سطرُه في البوابة أُسقط بانحراف التأمين 8.8٪ ← 10.0٪ لأنّ شاهدَ الأساس قِيس 10:38 والمرشَّحَ
12:30 وبينهما حصادُ 142 قائمةً عند النشر — فالفرقُ بياناتٌ لا شيفرة. فمهمّةُ `candidate_ab` تقيس الأساسَ المجمَّد
(من `git archive`) ثمّ المرشَّحَ متتاليَين، والبوابةُ تطبع بصمةَ ما قاسته، والحافظُ يرفض قياساً لغير شيفرته.

    python3 scripts/audit/candidate_ab_d696.py
"""
import contextlib, io, json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/audit"))
import engine_report_save as S   # noqa: E402
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


tmp = pathlib.Path(tempfile.mkdtemp())
S.BASE, S.REPORTS = tmp / "base.json", tmp / "reports"
S.BASE.write_text(json.dumps({"version": "2.3", "fingerprint": "c8c1b64d08b3", "metrics": {}}))
S.fingerprint = lambda: "a07498b692e0"          # الشجرةُ هنا: المرشَّح


def gate(fp, m):
    f = tmp / f"g_{fp}.txt"
    f.write_text(f"@@ENGINE_FP@@ {fp} · /tmp/control\n@@METRICS@@" + json.dumps(m))
    return str(f)


def run(*argv):
    sys.argv = ["engine_report_save.py", *argv]
    with contextlib.redirect_stdout(io.StringIO()):
        return S.main()


g_base, g_cand = gate("c8c1b64d08b3", {"median_dev": 0.139}), gate("a07498b692e0", {"median_dev": 0.139})
ctl = S.REPORTS / "c8c1b64d08b3.control.json"
check(run(g_base, "--control", "--measured", "2026-10-14") == 0 and ctl.exists()
      and json.loads(ctl.read_text())["fingerprint"] == "c8c1b64d08b3",
      "١ شاهدُ الأساس يُحفظ ببصمة ما قاسته البوابةُ (من الجولة نفسِها) — والشجرةُ هنا على المرشَّح")
check(run(g_cand, "--control") == 1, "٢ وقياسُ المرشَّح لا يُحفظ شاهداً للأساس")
check(run(g_base) == 1, "٣ وقياسُ الأساس لا يُحفظ تقريراً للمرشَّح الذي في الشجرة")
check(run(g_cand, "--measured", "2026-10-14") == 0 and (S.REPORTS / "a07498b692e0.json").exists(),
      "٤ وقياسُ المرشَّح يُحفظ تقريراً له")
check(run(g_base, g_cand) == 1, "٥ ولا يُدمج مخرَجا شيفرتين في تقريرٍ واحد")
gate_src = (ROOT / "scripts/audit/candidate_gate.py").read_text(encoding="utf-8")
ops = (ROOT / ".github/workflows/ops.yml").read_text(encoding="utf-8")
check(gate_src.count('print(f"@@ENGINE_FP@@ {_FP} · {_ROOT}")') == 4 and 'os.environ.get("SP_CODE_ROOT")' in gate_src
      and "assert os.path.dirname(os.path.dirname(_app.__file__)) == os.path.normpath(_ROOT)" in gate_src,
      "٦ البوابةُ تُحمّل `app` من جذر الشيفرة المختار وتتحقّق منه، وتطبع بصمتَها في كلّ بوابةٍ من الأربع")
check("candidate_ab)" in ops and '""|*[!0-9a-f]*)' in ops and 'git archive "$P" backend/app' in ops
      and "SP_CODE_ROOT=/tmp/control" in ops and ops.index("الشاهد: الأساسُ") < ops.index("المرشَّح: الشجرةُ الحاليّة"),
      "٧ ومهمّةُ candidate_ab: مرجعٌ سداسيٌّ وحدَه، والأساسُ من git archive ثمّ المرشَّحُ في الجولة نفسِها")
check("_cache._flush = lambda *a, **k: None" in gate_src and 'if k.startswith("fvm:")' in gate_src
      and gate_src.index("_cache._flush = lambda") < gate_src.index('if k.startswith("fvm:")'),
      "٨ والجانبان يحسبان النماذجَ الآن من البيانات نفسِها — كاشُها يُنزع من ذاكرة القياس وحده ولا يُكتب القرصُ منه")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
