"""عقلُ التطبيق الواحد (D548) — ملفُّ الشركة من محرّكاتنا كلّها، يقرؤه كلُّ من يكتب رأياً.

قال المالك: «أريد إعادةَ هيكلة رأي الذكاء ليتوافق مع محرّكاتنا ونماذجنا ويفكّر بعقل
التطبيق الواحد». وكان رأيُ الذكاء يقرأ أرقامَ ياهو العامّة (مكرّرٌ وعائدٌ على الحقوق)
ولا يعرف الدرجةَ المالية ولا أركانَها ولا نماذجَ السعر العادل ولا ترتيبَ النجوم ولا
نموذجَ الأبحاث؛ وتقريرُ الشركة يوصي بقاعدةٍ ثانية (±15٪) غيرِ قرار التطبيق.

فالملفُّ هنا واحد، ومنه:
  · **القرار** — قرارُ محرّك الحوكمة نفسُه بسببه (لا يُعاد تقييمُه).
  · **المحرّكات** — الدرجةُ المالية، والأركانُ الأربعة، والسعرُ العادلُ بنطاقه وثقته،
    وموقعُ الشركة في نجوم تاسي بعائلاتها الأقوى.
  · **الأبحاث** — توقّعُ الربع القادم بطريقته الأدقّ وخطئها، والنموُّ المركّب،
    والموسمية، والسهمُ منذ 2010 مقابلَ تاسي، والتوزيعات، ونطاقُ مكرّر الربحية.

ويُلحَق القسمان بالرأي كما كُتبا أياً كان كاتبُه (النموذجُ اللغويّ أو القواعد)، ويُعطى
النموذجُ اللغويُّ الملفَّ نفسَه مادّةً لنثره — فلا يختلف المعروضُ باختلاف الكاتب.
"""
from __future__ import annotations

from app.services.stars_factors import FAMILIES

_FAM = dict(FAMILIES)
_ARKAN = {"quality": "الجودة", "safety": "السلامة", "valuation": "التسعير", "timing": "التوقيت"}
_LBL = {"revenue": "الإيرادات", "ebit": "الربح التشغيلي", "net_income_parent": "صافي الدخل",
        "bank_nfi": "صافي دخل التمويل", "bank_op_income": "الدخل التشغيلي"}


def _pm(v, d=1):
    return f"{'+' if v > 0 else ''}{v:.{d}f}%" if isinstance(v, (int, float)) else None


def _mn(v):
    return f"{v / 1e6:,.0f} مليون" if isinstance(v, (int, float)) else None


def _stars(sym: str) -> dict | None:
    from app.services import lastgood
    from app.services.tasi_stars import STORE_KEY
    rec = lastgood.load(STORE_KEY) or {}
    for group, items in (("member", rec.get("members") or []), ("watch", rec.get("watch") or [])):
        for m in items:
            if str(m.get("symbol")) == sym:
                fams = sorted((m.get("families") or {}).items(), key=lambda kv: -kv[1])
                return {"group": group, "rank": m.get("rank"), "score": m.get("score"),
                        "top": [(_FAM.get(k, k), v) for k, v in fams[:2]]}
    return None


def engines(analysis: dict, sym: str) -> list[str]:
    a = analysis or {}
    out = []
    d = a.get("decision") or {}
    if d.get("label"):
        out.append(f"قرارُ التطبيق: {d['label']}" + (f" — {d['reason']}" if d.get("reason") else ""))
    fin = a.get("financial") or {}
    if fin.get("score") is not None:
        out.append(f"الدرجةُ المالية {fin['score']}/100" + (f" ({fin['verdict']})" if fin.get("verdict") else ""))
    sc = a.get("scores") or {}
    ark = [f"{_ARKAN[k]} {round(v['score'])}" for k in _ARKAN
           if isinstance(sc.get(k), dict) and isinstance(sc[k].get("score"), (int, float))
           for v in [sc[k]]]
    if ark:
        out.append("الأركانُ الأربعة: " + " · ".join(ark))
    fv, up = a.get("fair_value"), a.get("fair_value_upside_pct")
    if isinstance(fv, (int, float)):
        rng = (f" (النطاق {a['fair_value_low']:.2f}–{a['fair_value_high']:.2f})"
               if isinstance(a.get("fair_value_low"), (int, float)) and isinstance(a.get("fair_value_high"), (int, float)) else "")
        out.append(f"السعرُ العادل {fv:.2f}{rng}" + (f" · الفجوة {_pm(up)}" if up is not None else "")
                   + (f" · ثقةٌ {a['fair_value_conf']}" if a.get("fair_value_conf") else ""))
    st = _stars(sym)
    if st:
        where = "ضمن نجوم تاسي" if st["group"] == "member" else "تحت مراقبة نجوم تاسي"
        top = " و".join(f"{n} ({v})" for n, v in st["top"])
        out.append(f"{where} بالمرتبة {st['rank']} ودرجةِ {st['score']}" + (f" — أقوى عائلاته {top}" if top else ""))
    return out


def research(note: dict | None) -> list[str]:
    n = note or {}
    out = []
    for k, f in (n.get("forecast") or {}).items():
        out.append(f"توقّعُنا لـ{_LBL.get(k, k)} في الربع القادم {_mn(f['value'])} — بطريقة «{f['label']}»، "
                   f"خطؤها التاريخيُّ {f['mape']}٪ وصدقُ اتّجاهها {f['hit']}٪ على {f['tested']} ربعاً"
                   if f.get("hit") is not None else
                   f"توقّعُنا لـ{_LBL.get(k, k)} في الربع القادم {_mn(f['value'])} — خطأٌ تاريخيّ {f['mape']}٪")
    g = n.get("growth") or {}
    ys = g.get("years") or []
    if g.get("rev_cagr") is not None and ys:
        out.append(f"نموُّ الإيراد المركّب {_pm(g['rev_cagr'])} سنوياً ({ys[0]}–{ys[-1]})"
                   + (f" وصافي الدخل {_pm(g['ni_cagr'])}" if g.get("ni_cagr") is not None else ""))
    if g.get("margin_last") is not None:
        out.append(f"هامشُ صافي الربح من {g['margin_first']}٪ إلى {g['margin_last']}٪")
    se = n.get("seasonality")
    if se:
        out.append(f"أقوى الأرباع تاريخياً الربعُ {se['strongest']} ({se['shares'].get(se['strongest'])}٪ من السنة، {se['years']} سنوات)")
    p = n.get("price") or {}
    if p.get("cagr") is not None:
        out.append(f"السهمُ منذ {str(p['since'])[:4]} بعائدٍ سنويٍّ {_pm(p['cagr'])}"
                   + (f" مقابلَ تاسي {_pm(p['tasi_cagr'])}" if p.get("tasi_cagr") is not None else "")
                   + (f"، وأقصى تراجع {_pm(p['max_dd'])}" if p.get("max_dd") is not None else ""))
    dv = p.get("div")
    if dv:
        out.append(f"وزّعت {dv['years_paid']} سنةً منذ {dv['since']} بانتظام {dv['regularity']}٪"
                   + (f" ونموٍّ سنويٍّ {_pm(dv['cagr'])}" if dv.get("cagr") is not None else ""))
    pb = n.get("pe_band")
    if pb and pb.get("current") is not None:
        out.append(f"مكرّرُ الربحية {pb['current']}x مقابلَ نطاقه {pb['low']}–{pb['high']}x "
                   f"(وسيطُه {pb['median']}x) — عند المئين {pb['position']} من تاريخه")
    return out


def dossier(symbol: str, analysis: dict) -> dict:
    """الملفُّ الواحد: سطورُ المحرّكات وسطورُ الأبحاث — من مخازن التطبيق وحدها."""
    sym = str(symbol).replace(".SR", "").strip()
    note = None
    try:
        from app.services.research_model import note as _note
        note = _note(sym, (analysis or {}).get("price"))
    except Exception:                                             # noqa: BLE001
        note = None
    return {"engines": engines(analysis, sym), "research": research(note), "note": note}


def attach(opinion: dict, dos: dict) -> dict:
    """يُلحق قسمي المحرّكات والأبحاث بالرأي كما هما — أياً كان كاتبُه."""
    if not opinion:
        return opinion
    if dos.get("engines"):
        opinion["engines_headline"] = "محرّكات التطبيق"
        opinion["engines_bullets"] = dos["engines"]
    if dos.get("research"):
        opinion["research_headline"] = "فريق الأبحاث"
        opinion["research_bullets"] = dos["research"]
    return opinion
