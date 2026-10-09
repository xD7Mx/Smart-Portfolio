#!/usr/bin/env python3
"""بوابةُ رقم اليوم (‏D649) — صفحةُ الشركة مقابل الفرز لكلّ السوق الرئيسيّ. قارئٌ فقط: الكتابةُ في الكاش والمخازن معطَّلة.

    docker exec sp_backend python /app/scripts/audit/parity_gate.py

يُشغَّل وحده على الإنتاج، أو داخل `candidate_gate.py` على مخزن المرشَّح في الذاكرة. والمقاييسُ لحارس التجميد:
  p_fv_mismatch   شركاتٌ سعرُها العادل في الصفحة ≠ الفرز (> 0.5٪، أو رقمٌ مقابل «غير متوفّر»)
  p_conf_mismatch شركاتٌ رقمُها واحدٌ وثقتُه مختلفة
  p_dec_mismatch  شركاتٌ قرارُ صفحتها ≠ قرارِ الفرز"""
import asyncio, json, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services import content_engine
from app.services.analysis import analyze_company

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}


def _pos(v):
    return v if isinstance(v, (int, float)) and v > 0 else None


def _label(d):
    return (d.get("label") or d.get("raw")) if isinstance(d, dict) else d


async def main():
    store = content_engine.fund_store_load()
    deep = lastgood.load("governance:deep") or {}
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                return s, await asyncio.wait_for(analyze_company(f"{s}.SR", uni[s].get("name_ar")), timeout=45)
            except Exception as e:                                 # noqa: BLE001
                return s, {"_err": type(e).__name__}
    res = dict(await asyncio.gather(*(one(s) for s in sorted(uni))))
    fvm, cfm, dcm, err, single = [], [], [], [], []
    for s, a in res.items():
        if not a or "_err" in a:
            err.append(s)
            continue
        st = store.get(s) or {}
        if "fair_value" not in st:
            continue                                               # لم تمسحها المسحة — لا فرزَ يُقارن به
        pv, sv = _pos(a.get("fair_value")), _pos(st.get("fair_value"))
        if (pv is None) != (sv is None) or (pv and sv and abs(pv / sv - 1) > 0.005):
            fvm.append((s, pv, sv))
        elif pv and a.get("fair_value_conf") != st.get("fair_value_conf"):
            cfm.append((s, a.get("fair_value_conf"), st.get("fair_value_conf")))
        # ‏D658: قرارٌ يقول «من مسارٍ واحد بلا شاهدٍ ثانٍ» وسعرُه العادل المعروض من محرّك النماذج المتعدّدة — تناقضٌ يراه المالك
        _rule = str(((a.get("decision") or {}) if isinstance(a.get("decision"), dict) else {}).get("rule_id") or "")
        if "مسار_واحد" in _rule and (a.get("fair_value_detail") or {}).get("engine") == "fair_value_models":
            single.append(s)
        d = deep.get(s) if isinstance(deep.get(s), dict) else {}
        pl, dl = _label(a.get("decision")), _label(d.get("decision"))
        if pl and dl and pl != dl:
            dcm.append((s, pl, dl))
    # والفرزُ: أحكامُ المسحة (بلا مصدرٍ مكمِّل) في المخزن العميق — كم منها مقيَّدٌ بـ«مسارٍ واحد» وقيمتُه من النماذج المتعدّدة
    single_screen = [s for s, d in deep.items() if isinstance(d, dict) and isinstance(d.get("decision"), dict)
                     and "مسار_واحد" in str(d["decision"].get("rule_id") or "") and _pos((store.get(s) or {}).get("fair_value"))
                     and s in uni]
    n = len(res) - len(err)
    ok = not fvm and not dcm
    print(f"{'✔' if ok else '✘'} ٦ رقمُ اليوم — صفحاتٌ قِيست {n} (تعذّرت {len(err)}) · السعرُ العادل ≠ الفرز {len(fvm)} · "
          f"الثقةُ وحدها {len(cfm)} · القرار {len(dcm)}")
    for s, pv, sv in fvm[:12]:
        print(f"     {s} {uni[s].get('name_ar')} · الصفحة {pv} · الفرز {sv}")
    print(f"{'✘' if single or single_screen else '✔'} ٨ قرارٌ «من مسارٍ واحد» وقيمتُه من النماذج المتعدّدة: الصفحة {len(single)}"
          f" · الفرز {len(single_screen)}" + (f" — {' · '.join((single + single_screen)[:14])}" if single or single_screen else ""))
    for s, pl, dl in dcm[:8]:
        print(f"     قرار {s} {uni[s].get('name_ar')} · الصفحة {pl} · الفرز {dl}")
    print("@@METRICS@@" + json.dumps({"p_fv_mismatch": len(fvm), "p_conf_mismatch": len(cfm), "p_dec_mismatch": len(dcm),
                                      "d_single_contra": len(single) + len(single_screen),
                                      "verdict": {"٦ رقمُ اليوم": ok}}, ensure_ascii=False))


asyncio.run(main())
