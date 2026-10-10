#!/usr/bin/env python3
"""حارسُ التجميد D635 — القاعدةُ ٤ من `docs/ENGINES_V1.md`: «يرفض أيَّ تعديلٍ على ملفّات المحرّكات ما لم يُرفق
بتقرير بوابةٍ يتفوّق على خطّ الأساس المجمَّد».

بأمر المالك: «يجب القضاء على ظاهرة التعديل اللانهائي». فالتعديلُ لا يُمنع بالوعد بل بالبنية:
  · بصمةُ ملفّات المحرّكات تُقارَن ببصمة الإصدار المجمَّد (`engine_baseline.json`).
  · فإن تغيّرت ولا تقريرَ لها في `engine_reports/<البصمة>.json` ← ساقط.
  · وإن وُجد التقرير فيجب ألّا يتراجع في أيّ مقياس، وأن يتفوّق في واحدٍ على الأقلّ ← وإلّا ساقط.

التقريرُ يُنتجه `engine_report_save.py` من مخرَج البوابة على الخادم للبصمة نفسِها."""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SVC = ROOT / "backend/app/services"
FILES = sorted([
    *(SVC / f for f in ("analysis.py", "fair_value.py", "data_quality.py", "statement_merge.py", "scores.py",
                        "expert_panel.py", "sector_multiples.py", "governance_rules.py", "valuation_fields.py",
                        "four_scores.py", "fair_value_models.py", "tadawul_financials.py", "tadawul_xbrl.py",
                        "decision_engine.py", "technical.py", "market_valuation_sweep.py", "material_events.py",
                        "red_lines.py", "confidence.py", "financial_features.py")),
    ROOT / "backend/app/data/archetype_spec.py", ROOT / "backend/app/data/governance_rules.yaml",
])
BASE = ROOT / "scripts/audit/engine_baseline.json"
REPORTS = ROOT / "scripts/audit/engine_reports"

# اتجاهُ كلّ مقياس: أعلى أفضل (+1) أو أدنى أفضل (−1)، وسماحُ الضجيج
DIRECTION = {"coverage": (+1, 0.005), "unnamed_missing": (-1, 0), "stale": (-1, 0), "precapital": (-1, 0),
             "far_share": (-1, 0.005), "median_dev": (-1, 0.005), "conf_share": (+1, 0.01),
             "conf_high_share": (+1, 0.01),                          # ‏D672: حصّةُ «مرتفعة»
             # ‏D639: محرّكاتُ ٢–٥ — فإصلاحُ الجودة أو الفنّيّ يُقاس بها، لا يُردّ «بلا فائدة» لأنّ السعرَ العادل لم يتغيّر
             # ‏D643 (بقرار المالك): التغطيةُ «حكمٌ صادر» — الاستبعادُ المسمّى لتهديد البقاء حكمٌ لا فجوة
             "q_verdict_coverage": (+1, 0.005), "q_unnamed": (-1, 0), "q_stale_unlabeled": (-1, 0), "q_redline_high": (-1, 0),
             "d_bad": (-1, 0), "d_noreason": (-1, 0), "s_nosrc": (-1, 0),
             "t_unrecorded_jumps": (-1, 0), "t_no_tech": (-1, 0), "t_bad_rsi": (-1, 0),
             # ‏D649: رقمُ اليوم واحد — صفحةُ الشركة مقابل الفرز (`parity_gate.py`)
             "p_fv_mismatch": (-1, 0), "p_conf_mismatch": (-1, 0), "p_dec_mismatch": (-1, 0),
             "p_fv_drift": (-1, 0), "p_conf_drift": (-1, 0),
             # ‏D658: قرارٌ يُقيَّد بـ«مسارٍ واحد» وقيمتُه من النماذج المتعدّدة
             "d_single_contra": (-1, 0)}


def fingerprint() -> str:
    h = hashlib.sha1()
    for f in FILES:
        h.update(f.relative_to(ROOT).as_posix().encode())
        h.update(f.read_bytes() if f.exists() else b"<missing>")
    return h.hexdigest()[:12]


def compare(base: dict, new: dict) -> tuple[list[str], list[str]]:
    """← (التراجعات، التحسّنات)."""
    worse, better = [], []
    for k, (d, tol) in DIRECTION.items():
        b, n = base.get(k), new.get(k)
        if b is None or n is None:
            continue
        diff = (n - b) * d
        if diff < -tol:
            worse.append(f"{k}: {b} ← {n}")
        elif diff > tol:
            better.append(f"{k}: {b} ← {n}")
    flagged = set(base.get("flagged") or [])
    for sec, b in (base.get("sector_dev") or {}).items():
        n = (new.get("sector_dev") or {}).get(sec)
        if n is None or sec in flagged:
            continue
        if n - b > 0.01:
            worse.append(f"قطاع {sec}: {b} ← {n}")
        elif b - n > 0.01:
            better.append(f"قطاع {sec}: {b} ← {n}")
    for k, ok in (base.get("verdict") or {}).items():
        if ok and not (new.get("verdict") or {}).get(k, False):
            worse.append(f"بندٌ اجتاز ثمّ سقط: {k}")
    return worse, better


def main() -> int:
    fp = fingerprint()
    if not BASE.exists():
        print(f"PASS التجميدُ لم يُفعَّل بعد — بصمةُ المحرّكات {fp}")
        return 0
    base = json.loads(BASE.read_text(encoding="utf-8"))
    if fp == base.get("fingerprint"):
        print(f"PASS المحرّكاتُ كما جُمّدت في الإصدار {base.get('version')} — {fp}")
        return 0
    rep = REPORTS / f"{fp}.json"
    if not rep.exists():
        print(f"FAIL تعديلٌ على ملفّات المحرّكات ({base.get('fingerprint')} ← {fp}) بلا تقرير بوابة — "
              f"شغّل engine_gate على الخادم ثمّ engine_report_save.py")
        return 1
    new = json.loads(rep.read_text(encoding="utf-8")).get("metrics") or {}
    worse, better = compare(base.get("metrics") or {}, new)
    if worse:
        print("FAIL الإصدارُ الجديد يتراجع عن المجمَّد:\n     " + "\n     ".join(worse))
        return 1
    if not better:
        print("FAIL الإصدارُ الجديد لا يتفوّق على المجمَّد في أيّ مقياس — تعديلٌ بلا فائدةٍ مقيسة")
        return 1
    print("PASS الإصدارُ الجديد يتفوّق بلا تراجع:\n     " + "\n     ".join(better))
    return 0


if __name__ == "__main__":
    sys.exit(main())
