#!/usr/bin/env python3
"""يحفظ مقاييسَ البوابة لبصمة المحرّكات الحالية (‏D635).

    python3 scripts/audit/engine_report_save.py <مخرَج engine_gate> [<مخرَج engines_gate_v1>] [--baseline 1.0]

بلا `--baseline`: يكتب `engine_reports/<البصمة>.json` — تقريرُ إصدارٍ مقترَح يحكم فيه حارسُ التجميد.
ومع `--baseline <الإصدار>`: يكتب خطَّ الأساس المجمَّد `engine_baseline.json` (عند التجميد وحده)."""
import datetime as dt, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from engine_freeze_d635 import BASE, REPORTS, fingerprint   # noqa: E402


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    # ‏D639: مخرَجا البوابتين (السعر العادل · المحرّكات ٢–٥) يُدمجان في تقريرٍ واحد، والأحكامُ تُجمع
    files = [a for a in args if not a.startswith("--") and (args.index(a) == 0 or args[args.index(a) - 1] != "--baseline")]
    metrics: dict = {}
    for fpath in files:
        text = pathlib.Path(fpath).read_text(encoding="utf-8", errors="replace")
        lines = [ln for ln in text.splitlines() if "@@METRICS@@" in ln]
        if not lines:
            print(f"لا سطرَ @@METRICS@@ في {fpath}")
            return 1
        m = json.loads(lines[-1].split("@@METRICS@@", 1)[1])
        verdict = {**(metrics.get("verdict") or {}), **(m.pop("verdict", None) or {})}
        metrics.update(m)
        metrics["verdict"] = verdict
    doc = {"fingerprint": fingerprint(), "measured_at": dt.date.today().isoformat(), "metrics": metrics}
    if "--baseline" in args:
        doc["version"] = args[args.index("--baseline") + 1]
        BASE.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"خطُّ الأساس المجمَّد: الإصدار {doc['version']} · {doc['fingerprint']}")
    else:
        REPORTS.mkdir(exist_ok=True)
        out = REPORTS / f"{doc['fingerprint']}.json"
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"تقريرُ البصمة {doc['fingerprint']} ← {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
