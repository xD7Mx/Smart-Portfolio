#!/usr/bin/env python3
"""حارسُ D818 — الفوليوم بروفايل للسوقين (بأمر المالك 2026-11-24): «الثيتا والتآكلُ الزمنيّ في العقود المحرّكُ الرئيسيّ لخسارة تسعين بالمئة
من الناس… أفكّر بإضافة أحد معايير اختيار السترايكات: الفوليوم بروفايل»، ثمّ: «نعم موافق — التكاملُ بين السوقين والخبراتُ التي نبنيها بتحسين
الفرص قوّةٌ لنا ولصقر».

  ١ البناء: حجمُ كلّ شمعةٍ يوزَّع على مداها، ونقطةُ التحكّم عند أكثف سعر، ومنطقةُ القيمة 70٪ حولها، وعُقدُ الحجم الكثيف والفراغاتُ في مواضعها؛
    والسيولةُ الضعيفةُ تُعلَم فلا يُبنى عليها حكم.
  ٢ مزادُ إغلاق «تداول» لا يصنع نقطةَ تحكّمٍ زائفة: آخرُ شمعةٍ في اليوم يُقصّ حجمُها.
  ٣ شاهدُ «الحجم» عند صقر (ثالثُ الثمانية): قاعدةُ حجمٍ قريبةٌ تحت السعر أو خروجٌ من القيمة نحو فراغ ⇐ يوافق؛ جدارٌ قريبٌ أمامه أو مطاردةٌ
    بعيدةٌ عن القيمة ⇐ يتحفّظ؛ وبلا بروفايلٍ أو بسيولةٍ ضعيفة ⇐ غير متوفّر — ولا يرفض وحده.
  ٤ عقودُ الأمريكيّ: جدارُ حجمٍ ثقيلٌ بين السعر والتنفيذ يُسقط العقد (والوقتُ يأكله وهو ينتظر)، والهدفُ عقدةُ الحجم التالية إن سبقت الهدفَ
    الفنيّ، والخروجُ من القيمة نحو فراغٍ يرفع الدرجة — والنافذةُ تتبع أجلَ العقد.
  ٥ السهمُ السعوديّ: الوقفُ تحت قاعدة الحجم إن كانت أضيقَ من الوقف الثابت، والهدفُ عقدةُ الحجم التالية إن سبقت الهدف — وبلا بروفايلٍ كما كانا.
  ٦ السلسلةُ تحمل البروفايلَ بنافذة أجلها، والصفقةُ تحفظ قراءةَ الحجم يومَ دخولها لتُقاس.

    python3 scripts/audit/volume_profile_d818.py
"""
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp_d818_")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import math  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import volume_profile as VP  # noqa: E402

# ── ١ البناء: قمّتان (100 و110) وفراغٌ بينهما عند 105 فوق أرضيّةٍ من التداول ──


def shape(c: float) -> float:
    if abs(c - 105) < 1.5:
        return 0.03
    return 0.3 + math.exp(-((c - 100) / 1.5) ** 2) + 0.7 * math.exp(-((c - 110) / 1.5) ** 2)


def bars_at(scale=1e6):
    out = []
    for i in range(81):
        c = 95 + i * 0.25
        out.append({"date": f"2026-11-{1 + i // 8:02d} {10 + i % 8}:00", "open": c, "high": c + 0.25, "low": c - 0.25, "close": c, "volume": shape(c) * scale})
    return out


vp = VP.build(bars_at())
thin = VP.build(bars_at(scale=1e3))
few = VP.build(bars_at()[:20])
hv = [h["p"] for h in vp["hvn"]] if vp else []
check(vp and abs(vp["poc"] - 100) <= 0.6 and vp["val"] <= vp["poc"] <= vp["vah"] and any(abs(p - 100) <= 0.6 for p in hv) and any(abs(p - 110) <= 0.8 for p in hv)
      and any(abs(p - 105) <= 1.5 for p in vp["lvn"]) and len(vp["bins"]) == VP.N_BINS and max(vp["bins"]) == 1.0 and not vp["thin"]
      and thin and thin["thin"] and few is None,
      "١ البناء: نقطةُ التحكّم عند أكثف سعر (100)، ومنطقةُ القيمة تحيط بها، والعقدتان الكثيفتان (100 · 110) والفراغُ (105) في مواضعها — "
      "والسيولةُ الضعيفةُ تُعلَم، وأقلُّ من ثلاثين شمعةً لا بروفايل",
      vp and f"POC {vp['poc']} · VA {vp['val']}–{vp['vah']} · HVN {hv} · LVN {vp['lvn']}")

# ── ٢ مزادُ الإغلاق السعوديّ ──
sa = []
for d in range(10):
    for h in range(7):
        last = h == 6
        c = 55.0 if last else 50.0 + (h - 3) * 0.1
        sa.append({"date": f"2026-11-{d + 1:02d} {10 + h}:00", "open": c, "high": c + 0.1, "low": c - 0.1, "close": c, "volume": 5e6 if last else 1e5})
raw, cap = VP.build(sa, saudi=False), VP.build(sa, saudi=True, intraday=True)
check(raw and cap and abs(raw["poc"] - 55) < 0.5 and abs(cap["poc"] - 50) < 0.5,
      "٢ مزادُ إغلاق «تداول» (حجمٌ ضخمٌ عند سعرٍ واحدٍ آخرَ اليوم) لا يصنع نقطةَ تحكّمٍ زائفة: آخرُ شمعةٍ في اليوم يُقصّ حجمُها إلى ضعف وسيط يومها",
      f"بلا قصّ {raw and raw['poc']} · بالقصّ {cap and cap['poc']}")

# ── ٣ شاهدُ «الحجم» ──
from app.services import saqr_council as CN  # noqa: E402

base = {"zone": "داخل القيمة", "poc": 100.0, "val": 98.0, "vah": 103.0, "next": None, "next_pct": None, "wall": None, "wall_pct": None,
        "support": None, "support_pct": None, "vah_pct": 2.0, "val_pct": -3.0, "gap_ahead": False, "thin": False, "window": ""}
m_base = VP.member({**base, "support": 99.0, "support_pct": -1.0, "next": 110.0}, "long")
m_out = VP.member({**base, "zone": "فوق القيمة", "vah_pct": -2.0, "gap_ahead": True, "next": 110.0}, "long")
m_wall = VP.member({**base, "wall": 102.0, "wall_pct": 2.0, "support": 99.0, "support_pct": -1.0}, "long")
m_ext = VP.member({**base, "zone": "فوق القيمة", "vah_pct": -12.0, "support": 90.0, "support_pct": -12.0}, "long")
m_mid = VP.member(base, "long")
m_thin, m_none = VP.member({**base, "thin": True}, "long"), VP.member(None, "long")
m_short = VP.member({**base, "zone": "تحت القيمة", "val_pct": 2.0, "gap_ahead": True, "next": 90.0}, "short")
vs = [m["v"] for m in (m_base, m_out, m_wall, m_ext, m_mid, m_thin, m_none, m_short)]
rd_live = VP.read(vp, 100.6, "long")
check(vs == ["ok", "ok", "warn", "warn", "na", "na", "na", "ok"] and all(m["role"] == "الحجم" for m in (m_base, m_wall)) and "veto" not in vs
      and CN.ROLES[2] == "الحجم" and "102.00" in m_wall["say"] and rd_live and abs(rd_live["support"] - 100) <= 0.6 and rd_live["next"] and rd_live["next"] > 105,
      "٣ شاهدُ «الحجم» ثالثُ شواهد صقر الثمانية: قاعدةُ حجمٍ قريبةٌ أو خروجٌ من القيمة نحو فراغ ⇐ يوافق، وجدارٌ قريبٌ أمامه أو مطاردةٌ بعيدةٌ عن القيمة ⇐ "
      "يتحفّظ، وبلا بروفايلٍ أو بسيولةٍ ضعيفة ⇐ غير متوفّر — ولا يرفض وحده (وللبيع بالمرآة)", f"{vs} · {m_wall['say']}")

# ── ٤ عقودُ الأمريكيّ ──
from app.services import option_picks as OP  # noqa: E402

S, IV = 20.0, 0.45
TR = {"state": "صاعد", "close": S, "sma50": 19.0, "sma200": 17.0, "hi60": 22.5, "hi120": 24.0, "hi52": 26.0, "lo60": 17.5, "lo120": 16.0, "lo52": 15.0}


def row(K, dte, call=True, spread=0.04, oi=800):
    m = OP.bs_price(S, K, dte / 365, IV, call)
    return {"contract": f"X{K:g}{'C' if call else 'P'}{dte}", "strike": float(K), "bid": round(m * (1 - spread / 2), 2), "ask": round(m * (1 + spread / 2), 2),
            "last": round(m, 2), "oi": oi, "volume": 50}


def ref_of(dte):
    return OP.atm_iv({"calls": [row(k, dte) for k in (18, 20, 22)], "puts": [row(k, dte, False) for k in (18, 20, 22)]}, S, dte / 365)


LOOSE = {"min_rr": 0.0, "min_pop": 0.0}
P = lambda **k: {"poc": 19.5, "val": 18.5, "vah": 20.5, "hvn": [{"p": 19.5, "w": 1.0}], "lvn": [], "lo": 14.0, "hi": 28.0, "thin": False, "window": "نافذة", **k}   # noqa: E731
EV = lambda K, dte, vp=None: OP.evaluate(row(K, dte), S, dte, True, {**TR, "vp": vp} if vp else TR, ref_of(dte), rules=LOOSE)   # noqa: E731
# القصيرُ (45 يوماً): الجدارُ يُسقط، وعقدةُ الحجم هدف
k_wall, why_wall = EV(21, 45, P(hvn=[{"p": 19.5, "w": 1.0}, {"p": 20.5, "w": 0.9}]))
k_nowall, _ = EV(21, 45)
k_thin, _ = EV(21, 45, P(hvn=[{"p": 19.5, "w": 1.0}, {"p": 20.5, "w": 0.9}], thin=True))
k_tgt, _ = EV(19, 45, P(hvn=[{"p": 19.5, "w": 1.0}, {"p": 21.5, "w": 0.9}]))
k_tgt0, _ = EV(19, 45)
# البعيدُ (270 يوماً — ‏D820): لا جدارَ يُسقط ولا عقدةَ تقصّر الهدف — والدرجةُ وحدها
k_far_wall, why_far = EV(22, 270, P(hvn=[{"p": 19.5, "w": 1.0}, {"p": 21.0, "w": 0.9}]))
k_far_tgt, _ = EV(18, 270, P(hvn=[{"p": 19.5, "w": 1.0}, {"p": 23.0, "w": 0.9}]))
k_plain, _ = EV(18, 270)
k_out, _ = EV(18, 270, P(vah=19.8, hvn=[{"p": 19.5, "w": 1.0}, {"p": 27.0, "w": 0.9}], lvn=[22.0]))
st = OP.STAGES
check(k_wall is None and why_wall == "جدارُ حجمٍ قبل التنفيذ" and k_nowall and k_thin
      and st.index("جدارُ حجمٍ قبل التنفيذ") == st.index("الدلتا خارج النطاق") + 1
      and k_tgt and k_tgt["target"] == 21.5 and "الفوليوم بروفايل" in k_tgt["target_label"] and k_tgt0["target"] == 22.5 and k_tgt["vp"]["next"] == 21.5
      and k_out and abs(k_out["score"] - k_plain["score"] - 5) < 0.01 and k_plain["vp"] is None,
      "٤ العقدُ القصير (≤ 60 يوماً): جدارُ حجمٍ ثقيلٌ بين السعر والتنفيذ يُسقطه بسببه المسمّى (والسيولةُ الضعيفةُ لا تُسقطه)، والهدفُ عقدةُ الحجم التالية "
      "إن سبقت الهدفَ الفنيّ؛ والخروجُ من القيمة نحو فراغٍ يرفع الدرجة خمساً — وقراءةُ الحجم في بطاقة العقد",
      f"{why_wall} · هدف {k_tgt and k_tgt['target']} مقابل {k_tgt0['target']} · فرقُ الدرجة {k_out and round(k_out['score'] - k_plain['score'], 2)}")
src_st = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
bf = src_st[src_st.index("async def best_for("):]
bf = bf[:bf.index("\ndef ") if "\ndef " in bf else len(bf)]
check(k_far_wall and why_far == "" and k_far_tgt and k_far_tgt["target"] == 26.0 and k_far_tgt["target_label"] == "قمّة السنة" and k_far_tgt["vp"]
      and OP.VP_SHORT_DTE == 60 and 'tr_e = {**(tr or {}), "vp": vps[win]}' in bf and "OP.candidates(rows, S, e[\"dte\"], call, tr_e," in bf,
      "٤ج ‏D820 العقدُ البعيد: لا جدارَ يُسقطه ولا عقدةَ تقصّر هدفَه (قِيس على الخادم: عقدةُ بروفايل ستّة أشهرٍ هدفاً أسقطت عقودَ AMD كلَّها 69 ⇐ 0) — "
      "والبروفايلُ له درجةٌ ومعلومة؛ وعقودُ صقر نفسِه (‏7–60 يوماً) تُختار بالبروفايل بنافذة أجلها",
      f"هدفُ البعيد {k_far_tgt and k_far_tgt['target']} ({k_far_tgt and k_far_tgt['target_label']})")

asked: list = []


async def fake_bars(sym, tf):
    asked.append((sym, tf))
    return bars_at()


from app.services.market_data import market_service as M  # noqa: E402
M.get_bars = fake_bars


async def windows():
    out = []
    for dte in (7, 30, 200):
        out.append(await VP.for_symbol("NVDA", dte, False))
    out.append(await VP.for_symbol("2222", None, None))
    return out

ws = asyncio.run(windows())
check([t for _, t in asked] == ["15m", "1h", "1d", "1h"] and asked[-1][0] == "2222.SR" and all(w and w.get("window") for w in ws)
      and VP.window(7)[1] == 520 and VP.window(None, True)[0] == "1h",
      "٤ب النافذةُ تتبع الأجل: العقدُ القريبُ (أسبوعان فأقلّ) من شموع 15 دقيقة، والشهريُّ من الساعة، والأبعدُ من اليوميّ — والسعوديُّ من الساعة، "
      "والوصفُ مع البروفايل", f"{asked}")

# ── ٥ السهمُ السعوديّ ──
from app.services import saqr_sa as SA  # noqa: E402

rd = {"thin": False, "support": 48.0, "val": 47.0, "next": 54.0}
e1 = SA.vp_exits(50.0, 8, 56.0, "أعلى 60 جلسة", rd)
e2 = SA.vp_exits(50.0, 8, 56.0, "أعلى 60 جلسة", {**rd, "thin": True})
e3 = SA.vp_exits(50.0, 8, 56.0, "أعلى 60 جلسة", {**rd, "support": 40.0, "val": 39.0, "next": 51.0})
e4 = SA.vp_exits(50.0, 8, 56.0, "أعلى 60 جلسة", None)
src_sa = (ROOT / "backend/app/services/saqr_sa.py").read_text(encoding="utf-8")
check(e1 == (47.28, "تحت قاعدة الحجم 48.00", 54.0, "عقدةُ حجمٍ كثيف") and e2 == e4 == (46.0, "−8٪", 56.0, "أعلى 60 جلسة")
      and e3 == (46.0, "−8٪", 56.0, "أعلى 60 جلسة") and "vp_exits(ask, c[\"stock_stop\"], tgt, lbl, rd)" in src_sa,
      "٥ السهمُ السعوديّ: الوقفُ تحت قاعدة الحجم بـ1.5٪ إن كانت أضيقَ من الوقف الثابت، والهدفُ عقدةُ الحجم التالية إن سبقت الهدفَ وبعدت 5٪ — "
      "والقاعدةُ البعيدة والعقدةُ القريبةُ جدّاً والسيولةُ الضعيفة وغيابُ البروفايل تُبقي الوقفَ الثابتَ والهدفَ الفنيّ",
      f"{e1} · {e3}")

# ── ٦ السلسلةُ والصفقة ──
src_mk = (ROOT / "backend/app/api/v1/endpoints/market.py").read_text(encoding="utf-8")
src_tr = (ROOT / "backend/app/services/saqr_trader.py").read_text(encoding="utf-8")
src_cn = (ROOT / "backend/app/services/saqr_council.py").read_text(encoding="utf-8")
sm = VP.summary(vp)
check('VP.for_symbol(symbol, cur["dte"], False)' in src_mk and 'got["vp"] = VP.summary(vp)' in src_mk and '"vp": k.get("vp")' in src_tr
      and "VP.member(ev.get(\"vp_rd\"), side)" in src_cn and "الحجم (الفوليوم بروفايل)" in CN.LINK_PROMPT
      and set(sm) >= {"poc", "val", "vah", "hvn", "lvn", "bins", "step", "lo", "hi", "thin"} and VP.summary(None) is None,
      "٦ سلسلةُ العقود تحمل البروفايلَ بنافذة أجلها (تُعلَّم به أسعارُ التنفيذ)، وصقرٌ يقرأ «الحجم» مع شواهده، والصفقةُ تحفظ قراءةَ الحجم يومَ دخولها")

print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
