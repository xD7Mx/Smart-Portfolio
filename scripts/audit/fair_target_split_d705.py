#!/usr/bin/env python3
"""حارسُ D705 — السعرُ العادل يحكم على الورقة الآن من قوائمها، والمستهدفُ توقّعُ سنةٍ ومعه زخمُ السوق (بأمر المالك 2026-10-14).

قال المالك: «هدفُ المحلّلين يختلف عن السعر العادل — الهدفُ رأيٌ مبنيٌّ على توقّعات المستقبل، أمّا السعرُ العادل فيحكم بناءً على
الورقة المالية للشركة: كم يستحقّ أن يكون سعرُه الآن». وكان الرقمُ المعروضُ «سعراً عادلاً» من المحرّك المركّب وفيه الزخم — حركةُ
سوقٍ لا قيمةٌ في القوائم. وقِيس (‏fv_now.py على 2,976 مشاهدة منذ 2023): العادلُ من القوائم وحدها +0.14 و+0.23 في غير الماليّة،
و+0.16 و+0.27 لقليلة النماذج، و+0.21 و+0.42 للتأمين — وطريقةُ متوسّط النماذج (‏Investing Pro) +0.03. فالحارسُ يمنع العودة:
  · مؤشّراتُ العادل بلا زخمٍ في كلّ نمط، و‎β معايَرٌ بالنصف الأوّل.
  · العادلُ لا يتحرّك بالزخم، والمستهدفُ يتحرّك به — رقمان بمعنيين لا رقمٌ مكرَّر.
  · وفئةُ الثقة بميل العادل نفسِه، والاختبارُ التاريخيّ يقيس الاثنين، وحارسُ التجميد يحرس الاثنين.

    python3 scripts/audit/fair_target_split_d705.py
"""
import os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import fair_value_models as F

SEG = F.REL_SEGMENTS
ok = all("mom" not in (v.get("fv_keys") or ("mom",)) for v in SEG.values())
check(ok and SEG["core"]["fv_keys"] == ("P", "ni_g", "ebit_ev") and SEG["thin"]["fv_keys"] == ("ri", "growth", "roe", "ni_g")
      and SEG["financial"]["fv_keys"] == ("cp",) and SEG["insurance"]["fv_keys"] == SEG["insurance"]["keys"]
      and abs(SEG["core"]["fv_beta"] - 0.269) < 1e-9 and abs(SEG["thin"]["fv_beta"] - 0.279) < 1e-9,
      "١ السعرُ العادل من القوائم وحدها في كلّ نمط — بلا زخمٍ ولا رأي، و‎β من النصف الأوّل",
      str({k: v.get("fv_keys") for k, v in SEG.items()}))

# عشرةُ أقرانٍ بقوائمَ متدرّجةٍ وزخمٍ عكسها، والشركةُ وسطٌ في قوائمها وأعلاهم زخماً
table = {f"C{k}": {"P": 0.1 * k, "ni_g": 0.05 * k, "ebit_ev": 0.01 * k, "mom": -0.1 * k} for k in range(10)}
me = {"P": 0.45, "ni_g": 0.225, "ebit_ev": 0.045, "mom": 0.9}
table["ME"] = me
res = {"value": 11.0, "model_value": 12.0, "price": 10.0, "rel": {"seg": "core", "sig": me}, "models": [], "excluded": [],
       "count": 5, "weights_kind": "proven_gmean"}
out = F.apply_relative("ME", dict(res), 10.0, table)
check(out and out.get("rel_part") == "fair" and abs(out["value"] - 10.0) < 0.3 and out.get("target_value")
      and out["target_value"] > out["value"] + 0.3,
      "٢ العادلُ لا يتحرّك بالزخم (وسطُ القوائم ⇒ عند سعره)، والمستهدفُ يتحرّك به — رقمان بمعنيين",
      f"العادل {out and out.get('value')} · المستهدف {out and out.get('target_value')}")
b = F.blend(dict(out), None, "industrial", 0.0) if out else {}
check(b.get("value") == out["value"] and b.get("target_12m") == out["target_value"] and b.get("target_err") == F.TARGET_ERR,
      "٣ والمستهدفُ بعد سنة هو المركّبُ بخطئه المقيس — لا نسخةٌ من العادل", f"{b.get('value')} · {b.get('target_12m')}")
fair_only = F.relative_value("C9", {"seg": "core", "sig": table["C9"]}, 10.0, table, "fair")
check(fair_only and F.track_bucket({**fair_only, "price": 10.0}) == "rel_core_better"
      and fair_only["models"][0]["name"].startswith("السعرُ العادل من القوائم"),
      "٤ وفئةُ الثقة بميل العادل نفسِه (‏fv_beta)، واسمُه يقول إنه من القوائم", str(fair_only and fair_only["models"][0]["name"]))
bt = open(os.path.join(ROOT, "scripts/audit/fv_backtest_d699.py"), encoding="utf-8").read()
fz = open(os.path.join(ROOT, "scripts/audit/engine_freeze_d635.py"), encoding="utf-8").read()
check('m["o_tg_ic12"]' in bt and '"rpart": res.get("rel_part")' in bt and '"o_tg_ic12": (+1' in fz,
      "٥ والاختبارُ التاريخيّ يقيس العادلَ والمستهدفَ كلّاً بنفسه، وحارسُ التجميد يحرس الاثنين")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
