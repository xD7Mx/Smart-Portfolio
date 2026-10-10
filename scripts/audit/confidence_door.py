#!/usr/bin/env python3
"""ثقةُ الرقم المعروض — أين تُحبس دون «مرتفعة»؟ قارئٌ فقط: الكتابةُ في الكاش والمخازن معطَّلة.

بأمر المالك (2026-10-10): «لا تعتبر المحرّكات جاهزةً حتى تكون الثقةُ مرتفعةً لأعلى من 90٪ أو 95٪». فيُقاس لكلّ شركةٍ
في السوق الرئيسيّ ما تعرضه صفحتُها: كلمةُ الثقة (‏`confidence_of`: اتّفاقُ النماذج وعددُها وحداثتُها وربحيّتها، ثمّ وسمُ
القطاع غير المعايَر)، وكلُّ مانعٍ يحبسها دون «مرتفعة» باسمه — وأيُّ نموذجٍ هو الشاذُّ حين يتباعد الاتّفاق. وثقةُ
خلاصة المجلس (‏`confidence.py`: سنواتٌ واكتمالٌ وثبات) بتوزيعها ونواقصها.
"""
import asyncio, collections, statistics, sys
sys.path.insert(0, "/app")
from app.services import cache, lastgood
cache.set = lambda *a, **k: None
lastgood.save = lambda *a, **k: None
from app.data.market_universe import MARKET_UNIVERSE
from app.data.universe import main_market, is_nomu
from app.services.analysis import analyze_company, V1_UNCALIBRATED

uni = {s: m for s, m in main_market(MARKET_UNIVERSE).items() if not is_nomu(s)}


def _name(m: dict) -> str:
    return str(m.get("name") or m.get("model") or m.get("label") or m.get("method") or "?")


async def main():
    from app.services.fair_value_models import for_symbol
    sem = asyncio.Semaphore(4)

    async def one(s):
        async with sem:
            try:
                a = await asyncio.wait_for(analyze_company(f"{s}.SR", uni[s].get("name_ar")), timeout=60)
                f = await asyncio.wait_for(for_symbol(s), timeout=30)
                return s, a, f
            except Exception as e:                                 # noqa: BLE001
                return s, {"_err": type(e).__name__}, None
    res = await asyncio.gather(*(one(s) for s in sorted(uni)))
    lab = collections.Counter()
    blk = collections.Counter()
    sole = collections.Counter()
    outl = collections.Counter()
    by_sec = collections.defaultdict(lambda: [0, 0])
    nmods = collections.Counter()
    gov = []
    gov_warn = collections.Counter()
    samples = collections.defaultdict(list)
    err = 0
    for s, a, f in res:
        if not a or "_err" in a:
            err += 1
            continue
        sec = (uni[s].get("sector_ar") or uni[s].get("sector") or "—")
        fin = a.get("financial") or {}
        gc = (fin.get("confidence") or {}) if isinstance(fin, dict) else {}
        if isinstance(gc.get("score"), (int, float)):
            gov.append(gc["score"])
            if gc["score"] < 90 and gc.get("warning"):
                for part in str(gc["warning"]).split("(")[-1].split(")")[0].split("،"):
                    gov_warn[" ".join(w for w in part.split() if not any(ch.isdigit() for ch in w))[:50]] += 1
        fv = a.get("fair_value")
        conf = a.get("fair_value_conf")
        if not isinstance(fv, (int, float)) or fv <= 0:
            lab["بلا قيمة"] += 1
            continue
        lab[conf or "—"] += 1
        by_sec[sec][1] += 1
        if conf == "مرتفعة":
            by_sec[sec][0] += 1
            continue
        f = f or {}
        mods = [m for m in (f.get("models") or []) if isinstance(m.get("value"), (int, float)) and m["value"] > 0]
        ms = [m["value"] for m in mods]
        nmods[len(ms)] += 1
        notes = " ".join(str(n) for n in (f.get("notes") or []))
        b = []
        if f.get("weights_kind") == "reit_nav":
            b.append("صندوق ريت: «متوسطة» ثابتة")
        if sec in V1_UNCALIBRATED or a.get("fair_value_calibrated") is False:
            b.append("قطاعٌ غيرُ معايَر")
        if "خاسر" in notes or "خسارة" in notes:
            b.append("خاسرة")
        if len(ms) < 3:
            b.append("أقلّ من ثلاثة نماذج")
        elif len(ms) == 3:
            b.append("ثلاثةُ نماذج فقط (المرتفعةُ تطلب أربعة)")
        if len(ms) >= 2:
            med = statistics.median(ms)
            disp = statistics.median([abs(v / med - 1) for v in ms]) if med else 1
            if disp > 0.30:
                b.append("تشتّتُ النماذج > 30٪")
            elif disp > 0.14:
                b.append("تشتّتُ النماذج 14–30٪")
            if disp > 0.14 and mods:
                far = max(mods, key=lambda m: abs(m["value"] / med - 1))
                outl[_name(far)] += 1
        if "أقدمُ من تسعة أشهر" in notes:
            b.append("قوائمُ أقدم من تسعة أشهر")
        if (a.get("fair_value_detail") or {}).get("engine") not in (None, "fair_value_models") and not f.get("value"):
            b.append("المحرّكُ الاحتياطيّ")
        if not b:
            b.append(f"غيرُ مفسَّر (ثقةُ المسحة «{conf}»)")
        for x in b:
            blk[x] += 1
            if len(samples[x]) < 6:
                samples[x].append(f"{s} {uni[s].get('name_ar') or ''}".strip())
        if len(b) == 1:
            sole[b[0]] += 1
    have = sum(v for k, v in lab.items() if k != "بلا قيمة")
    hi = lab.get("مرتفعة", 0)
    print(f"═ الشركات {len(uni)} · تعذّر {err} · لها قيمةٌ عادلة {have}")
    print(f"   الثقة: {dict(lab)}")
    print(f"   «مرتفعة» {hi}/{have} = {hi / max(1, have):.0%} · متوسطةٌ فأعلى "
          f"{hi + lab.get('متوسطة', 0)}/{have} = {(hi + lab.get('متوسطة', 0)) / max(1, have):.0%}")
    print("\n═ ما يحبس الثقةَ دون «مرتفعة» (الشركةُ قد تحمل أكثرَ من مانع) · [المانعُ الوحيد]")
    for k, n in blk.most_common():
        print(f"   {n:>3} [{sole.get(k, 0):>3}] × {k} — {', '.join(samples[k][:4])}")
    print(f"   عددُ النماذج فيما دون «مرتفعة»: {dict(sorted(nmods.items()))}")
    print(f"   النموذجُ الأبعدُ عن الوسيط حين يتباعد الاتّفاق: {outl.most_common(8)}")
    print("\n═ «مرتفعة» بالقطاع")
    for k, (h, n) in sorted(by_sec.items(), key=lambda kv: kv[1][0] / max(1, kv[1][1])):
        print(f"   {k:<30} {h:>3}/{n:<3} = {h / max(1, n):.0%}")
    if gov:
        q = sorted(gov)
        print(f"\n═ ثقةُ خلاصة المجلس (‏confidence.py) · {len(q)} شركة · وسيط {statistics.median(q):.0f} · "
              f"≥90: {sum(1 for x in q if x >= 90)} · ≥80: {sum(1 for x in q if x >= 80)} · <60: {sum(1 for x in q if x < 60)}")
        print(f"   أسبابُ ما دون 60: {gov_warn.most_common(5)}")


asyncio.run(main())
