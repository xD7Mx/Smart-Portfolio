#!/usr/bin/env python3
"""سيرُ العملِ يُحلَّل ويُنفَّذ نحوُه — قبل أن يُعتمَد عليه (‏D407).

    python3 scripts/audit/workflow_parses.py

`.github/workflows/ops.yml` هو يدُ كلود على خادم المالك حين يغيب. ودُفع
مرّةً وهو **لا يُحلَّل أصلاً**: كتلةُ `python -c` أسطرُها تبدأ من العمود
صفر فتُنهي كتلةَ YAML قبل أوانها. فكان سيفشل عند أوّل تشغيلٍ — بعد جهدِ
تركيب العامل كلِّه، وفي أسوأ وقت.

وصنفُ هذا العطب أنه **يمرّ صامتاً**: لا مترجمَ يشتكي ولا اختبارَ يسقط،
ولا يظهر إلا عند أوّل استعمالٍ حقيقيّ. والميثاقُ يقول: «شغّل ما بنيتَه
وقِس مخرَجه» — وملفُّ سيرِ عملٍ لا يُشغَّل هنا، فأقلُّ ما يُقاس أن
يُحلَّل، وأن يُنفَّذ نحوُ صَدَفته، وأن تجد كلُّ مهمّةٍ معروضةٍ فرعَها.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


try:
    import yaml
except ModuleNotFoundError:
    print("⚠ لا حزمةَ yaml في هذه البيئة — لم يُقَس")
    sys.exit(0)

WF = ROOT / ".github" / "workflows"
files = sorted(WF.glob("*.yml")) + sorted(WF.glob("*.yaml"))
if not files:
    print("⚠ لا ملفَّ سيرِ عملٍ في هذه الشجرة — لم يُقَس")
    sys.exit(0)

for f in files:
    # ── ١ · يُحلَّل ─────────────────────────────────────────────────────
    try:
        doc = yaml.safe_load(f.read_text("utf-8"))
        _ok = isinstance(doc, dict)
        _why = "" if _ok else "ليس خريطةً"
    except Exception as e:                                        # noqa: BLE001
        doc, _ok, _why = None, False, f"{type(e).__name__}: {str(e)[:70]}"
    check(_ok, f"١ {f.name}: يُحلَّل", _why)
    if not _ok:
        continue

    # ── ٢ · ونحوُ صَدَفةِ كلّ خطوةٍ سليم ──────────────────────────────
    steps = [s for j in (doc.get("jobs") or {}).values()
             for s in (j.get("steps") or []) if s.get("run")]
    bad = []
    for s in steps:
        # المتغيّراتُ تُستبدَل بقيمةٍ محايدةٍ قبل الفحص: `bash -n` يقرأ
        # النحوَ لا القيم، و`${{ }}` ليست من لغة الصَّدَفة.
        src = s["run"]
        while "${{" in src and "}}" in src:
            i, j2 = src.index("${{"), src.index("}}") + 2
            src = src[:i] + "x" + src[j2:]
        p = subprocess.run(["bash", "-n"], input=src, text=True,
                           capture_output=True)
        if p.returncode != 0:
            bad.append(f"{s.get('name', '?')}: {p.stderr.strip()[:70]}")
    check(not bad, f"٢ {f.name}: نحوُ صَدَفةِ كلّ خطوةٍ سليم",
          " · ".join(bad) if bad else f"{len(steps)} خطوةً")

    # ── ٣ · وأسماءُ المُدخَلات لاتينيةٌ حتماً ──────────────────────────
    # (‏D407-ب) لغةُ تعابير GitHub (`inputs.x`) لا تقبل محرفاً غيرَ
    # لاتينيّ. واسمٌ عربيٌّ **يُحلَّل في YAML بلا شكوى** ثمّ يُبطل الملفَّ
    # كلَّه عند أوّل تشغيل — فالحارسُ الذي يقف عند التحليل وحدَه يمرّره.
    # قِيس: `inputs.المهمة` ردّ «Unexpected symbol» عند أوّل نداء.
    _on = doc.get("on") or doc.get(True) or {}
    _ins = ((_on.get("workflow_dispatch") or {}).get("inputs") or {})
    _nonascii = [k for k in _ins if not str(k).isascii()]
    check(not _nonascii, f"٣ {f.name}: أسماءُ المُدخَلات لاتينية",
          "، ".join(_nonascii) if _nonascii else f"{len(_ins)} مُدخَلاً")
    # وكذلك كلُّ تعبيرٍ `${{ … }}` في الخطوات
    _bad_expr = []
    for s in steps:
        for _seg in str(s.get("run", "")).split("${{")[1:]:
            _e = _seg.split("}}")[0]
            if not _e.isascii():
                _bad_expr.append(_e.strip()[:40])
    for _j in (doc.get("jobs") or {}).values():
        for _s in (_j.get("steps") or []):
            for _v in (_s.get("env") or {}).values():
                for _seg in str(_v).split("${{")[1:]:
                    _e = _seg.split("}}")[0]
                    if not _e.isascii():
                        _bad_expr.append(_e.strip()[:40])
    check(not _bad_expr, f"٣ب {f.name}: كلُّ تعبيرٍ لاتينيٌّ يُقبَل في التنفيذ",
          "، ".join(sorted(set(_bad_expr))) if _bad_expr else "")

    # ── ٤ · وكلُّ مهمّةٍ معروضةٍ لها فرعٌ يُنفّذها ─────────────────────
    opts = (_ins.get("task") or _ins.get("المهمة") or {}).get("options") or []
    body = "\n".join(s["run"] for s in steps)
    orphan = [o for o in opts if f"{o})" not in body]
    check(not orphan, f"٤ {f.name}: كلُّ مهمّةٍ معروضةٍ لها فرعٌ ينفّذها",
          "، ".join(orphan) if orphan else f"{len(opts)} مهمّةً")

print(("FAIL" if fail else "PASS")
      + " D407 — سيرُ العملِ يُحلَّل ونحوُه منفَّذ")
sys.exit(fail)
