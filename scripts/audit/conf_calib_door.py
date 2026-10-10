#!/usr/bin/env python3
"""معايرةُ الثقة — ماذا تعني «مرتفعة» بالخطأ المقيس، وأيُّ نموذجٍ يُبعد الاتّفاق؟ قارئٌ فقط.

الثقةُ وعدٌ للقارئ: «مرتفعة» يجب أن تعني خطأً أصغرَ مقيساً لا كلمةً أعلى. ومعيارُها اليوم (‏D625) اتّفاقُ النماذج:
تشتّتٌ ≤ 14٪ وأربعةُ نماذج فأكثر ← خطأٌ وسيطُه 12٪ عن أهداف المحلّلين. فيُقاس هنا على كلّ ورقةٍ لها هدفُ محلّلين:
  أ) الخطأُ بحسب التشتّت وعدد النماذج — هل تحمل «المتوسطة» خطأً كخطأ «المرتفعة»؟
  ب) كلُّ نموذجٍ بخطئه وانحيازه بالنمط — أيُّها يُبعد الاتّفاقَ وهو أبعدُ عن الهدف؟
  ج) شاهدٌ مستقلّ: أهدافُ بيوت الخبرة المرخّصة (أرقام) خلال سنة — كم ورقةً يتّفق معها رقمُنا؟
"""
import asyncio, collections, datetime as dt, statistics, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services.market_screener import get_cached_screener
from app.services.content_engine import fund_store_load
from app.services.analysis import V1_UNCALIBRATED

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}
K = 0.6


def med(xs):
    return statistics.median(xs) if xs else float("nan")


def w20(xs):
    return sum(1 for x in xs if x <= 0.20) / len(xs) if xs else float("nan")


async def main():
    from app.services.fair_value_models import for_symbol
    from app.services.analyst_opinions import for_symbol as ops
    from app.services.statement_merge import archetype_of as _arch
    rows = {str(r.get("symbol")).replace(".SR", ""): r for r in (get_cached_screener() or [])}
    store = fund_store_load()
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                return s, await asyncio.wait_for(for_symbol(s), timeout=40)
            except Exception:                                      # noqa: BLE001
                return s, None
    fv_all = dict(await asyncio.gather(*(one(s) for s in sorted(uni))))
    recs = []
    cut = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    for s, f in fv_all.items():
        r, st = rows.get(s) or {}, store.get(s) or {}
        fv, px = st.get("fair_value"), r.get("price")
        if not (isinstance(fv, (int, float)) and fv > 0 and isinstance(px, (int, float)) and px > 0 and f):
            continue
        mods = [m for m in (f.get("models") or []) if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        ms = [m["value"] for m in mods]
        md = med(ms) if ms else None
        disp = med([abs(v / md - 1) for v in ms]) if md else None
        notes = " ".join(str(n) for n in (f.get("notes") or []))
        at = r.get("analyst_target") if isinstance(r.get("analyst_target"), (int, float)) and r["analyst_target"] > 0 else None
        tg = [o["target"] for o in ops(s) if isinstance(o.get("target"), (int, float)) and o["target"] > 0
              and str(o.get("date") or "") >= cut]
        recs.append({"s": s, "fv": fv, "px": px, "at": at, "houses": tg, "n": len(ms), "disp": disp, "mods": mods,
                     "loser": ("خاسر" in notes or "خسارة" in notes), "stale": "أقدمُ من تسعة أشهر" in notes,
                     "sec": uni[s].get("sector_ar") or uni[s].get("sector") or "—", "arch": _arch(s) or "—",
                     "conf": st.get("fair_value_conf"), "reit": f.get("weights_kind") == "reit_nav"})
    ref = [x for x in recs if x["at"]]
    print(f"═ لها قيمةٌ ونماذج {len(recs)} · ولها هدفُ محلّلين {len(ref)} · ولها أهدافُ بيوتٍ خلال سنة "
          f"{sum(1 for x in recs if x['houses'])}")
    for x in ref:
        x["err"] = abs(x["fv"] / x["at"] - 1)
        x["perr"] = abs(x["px"] / x["at"] - 1)
    print(f"   الخطأ عن الهدف: رقمُنا وسيط {med([x['err'] for x in ref]):.1%} · السعرُ نفسُه {med([x['perr'] for x in ref]):.1%}")
    print("   بالكلمة المعروضة:")
    for c in ("مرتفعة", "متوسطة", "منخفضة"):
        g = [x["err"] for x in ref if x["conf"] == c]
        print(f"     {c:<8} n={len(g):>3} · وسيط {med(g):.1%} · ضمن 20٪ {w20(g):.0%}")

    print("\n═ أ) الخطأُ بالتشتّت وعدد النماذج (الرابحة · غيرُ المتأخّرة · غيرُ الريت · قطاعٌ معايَر)")
    clean = [x for x in ref if not x["loser"] and not x["stale"] and not x["reit"] and x["sec"] not in V1_UNCALIBRATED
             and x["disp"] is not None]
    for lo, hi in ((0, .10), (.10, .14), (.14, .18), (.18, .22), (.22, .30), (.30, 9)):
        for nlab, cond in (("3", lambda n: n == 3), ("4+", lambda n: n >= 4)):
            g = [x["err"] for x in clean if lo < x["disp"] <= hi and cond(x["n"])] if lo else \
                [x["err"] for x in clean if x["disp"] <= hi and cond(x["n"])]
            if g:
                print(f"     تشتّت {lo:.0%}–{hi:.0%} · نماذج {nlab:<2} · n={len(g):>3} · وسيط {med(g):.1%} · ضمن 20٪ {w20(g):.0%}")
    print("   قواعدُ مرشّحة لـ«مرتفعة» (حصّتُها من كلّ ما له قيمة · وخطؤها):")
    allv = [x for x in recs if x["disp"] is not None]
    for T in (0.14, 0.18, 0.22, 0.26, 0.30):
        for N in (3, 4):
            hi_all = [x for x in allv if not x["loser"] and not x["stale"] and not x["reit"]
                      and x["sec"] not in V1_UNCALIBRATED and x["disp"] <= T and x["n"] >= N]
            e = [x["err"] for x in hi_all if x.get("err") is not None]
            print(f"     تشتّت ≤ {T:.0%} · نماذج ≥ {N} → {len(hi_all)}/{len(recs)} = {len(hi_all) / max(1, len(recs)):.0%}"
                  f" · خطؤها وسيط {med(e):.1%} (n={len(e)}) · ضمن 20٪ {w20(e):.0%}")

    print("\n═ ب) كلُّ نموذجٍ بخطئه عن الهدف بعد المزج بالسعر، وانحيازه — بالنمط")
    per = collections.defaultdict(list)
    for x in ref:
        for m in x["mods"]:
            b = x["px"] * (m["value"] / x["px"]) ** K
            per[(x["arch"], m.get("key") or m.get("name"))].append(b / x["at"] - 1)
    arch_base = {a: med([x["err"] for x in ref if x["arch"] == a]) for a in {x["arch"] for x in ref}}
    for (a, k), v in sorted(per.items(), key=lambda kv: (kv[0][0], -med([abs(e) for e in kv[1]]))):
        if len(v) >= 6:
            mae = med([abs(e) for e in v])
            flag = " ◀ أبعدُ من الرقم المعروض" if mae > arch_base.get(a, 1) * 1.3 else ""
            print(f"     {a:<12} {str(k):<18} n={len(v):>3} · خطأ {mae:.1%} · انحياز {med(v):+.1%}{flag}")
    print(f"   خطأُ الرقم المعروض بالنمط: { {a: f'{v:.1%}' for a, v in arch_base.items()} }")

    print("\n═ ج) شاهدٌ مستقلّ: أهدافُ بيوت الخبرة المرخّصة خلال سنة (‏أرقام)")
    hs = [x for x in recs if len(x["houses"]) >= 2]
    for x in hs:
        x["hmed"] = med(x["houses"])
        x["hagree"] = abs(x["fv"] / x["hmed"] - 1)
        x["hdisp"] = med([abs(t / x["hmed"] - 1) for t in x["houses"]])
    print(f"   أوراقٌ لها هدفان فأكثر: {len(hs)} من {len(recs)} · يتّفق رقمُنا مع وسيطها ضمن 15٪: "
          f"{sum(1 for x in hs if x['hagree'] <= .15)} · ضمن 20٪: {sum(1 for x in hs if x['hagree'] <= .20)}")
    print(f"   وتشتّتُ البيوت فيما بينها وسيطُه {med([x['hdisp'] for x in hs]):.1%}")
    lowc = [x for x in hs if x["conf"] != "مرتفعة" and x["hagree"] <= .15 and not x["loser"] and not x["stale"]]
    print(f"   دون «مرتفعة» ورقمُها يتّفق مع البيوت ضمن 15٪ (رابحةٌ غيرُ متأخّرة): {len(lowc)} — "
          f"{', '.join(x['s'] for x in lowc[:15])}")


asyncio.run(main())
