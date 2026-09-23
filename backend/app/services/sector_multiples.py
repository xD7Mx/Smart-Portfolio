"""مضاعفا القطاع من السوق كلِّه لا من المحفظة (D446).

قِيس بكاشف `fv_paths_low.py`: مسارُ «مضاعف الربحية العادل» غائبٌ عن أكثر
الأوراق، لأن مضاعفَي القطاع كانا يُحسبان من **نظائرَ في محفظة المالك** —
فالشركةُ التي لا نظيرَ لها في المحفظة تُحرَم مسارَ قطاعها كلَّه.

ولقطةُ «تداول» لا تحمل مكرّرَي الربحية والدفترية (قِيس: فارغان لكلّ ورقة
— D453)، فيُحسبان من إفصاح XBRL الرسميّ لكلّ نظير (`official_multiples`).
فالمضاعفُ العادلُ للقطاع = **وسيطُ** مكرّرات النظائر من النمط
نفسِه (الوسيطُ لا المتوسّط: خاسرةٌ واحدةٌ بمكرّر 400 لا تسحب القطاع).
ويُستبعَد السالبُ والشاذّ (فوق 80 ربحيةً · فوق 20 دفتريةً)، ويُشترط أربعةُ
نظائرَ فأكثر، والورقةُ نفسُها خارجَ حساب مضاعفها.
"""
from __future__ import annotations

import statistics
from typing import Optional

_MIN_PEERS = 4


def _rows() -> dict:
    try:
        from app.services.tadawul_market import usable_rows
        return usable_rows()[0] or {}
    except Exception:                                             # noqa: BLE001
        return {}


def official_multiples(sym: str, price: float | None) -> tuple:
    """(مكرّرُ الربحية، مكرّرُ الدفترية) من إفصاح XBRL الرسميّ — أو (None, None).

    ‏D453: قِيس أنّ لقطةَ «تداول» لا تحمل `PER` ولا `PBR` لأيّ ورقة (حقلان
    فارغان دائماً)، فما بُني عليهما لم يعمل على الخادم. فيُحسبان هنا من
    آخر سنةٍ مفصَحٍ عنها: السعرُ ÷ ربحيةِ السهم، والسعرُ ÷ (الحقوق ÷ الأسهم)،
    ولا تُقرأ سنةٌ موسومةٌ بخطأ وحدةٍ في عدد الأسهم.
    """
    if not isinstance(price, (int, float)) or price <= 0:
        return None, None
    try:
        from app.services.tadawul_xbrl import for_symbol as _x
        rows = _x(sym, "annual") or []
    except Exception:                                             # noqa: BLE001
        rows = []
    if not rows:
        return None, None
    p = rows[-1]
    if p.get("shares_unit_gap") or p.get("shares_mismatch"):
        return None, None
    sh, ni, eq, eps = (p.get("shares_outstanding"), p.get("net_income"),
                       p.get("equity"), p.get("eps"))
    if not isinstance(eps, (int, float)) and isinstance(ni, (int, float)) \
            and isinstance(sh, (int, float)) and sh > 0:
        eps = ni / sh
    pe = price / eps if isinstance(eps, (int, float)) and eps > 0 else None
    pb = (price / (eq / sh) if isinstance(eq, (int, float)) and eq > 0
          and isinstance(sh, (int, float)) and sh > 0 else None)
    return pe, pb


def for_symbol(symbol, rows: dict | None = None) -> Optional[dict]:
    """{pe, pb, peers, archetype} من نظائر النمط الرسميّ — أو None."""
    from app.services.statement_merge import archetype_of
    from app.data.universe import is_main
    base = str(symbol or "").replace(".SR", "").strip()
    arch = archetype_of(base)
    if not arch:
        return None
    rows = _rows() if rows is None else rows
    pes, pbs = [], []
    for s, r in rows.items():
        s = str(s).replace(".SR", "")
        if s == base or not is_main(s) or archetype_of(s) != arch:
            continue
        pe, pb = (r or {}).get("pe_ratio"), (r or {}).get("price_to_book")
        if pe is None or pb is None:
            _pe2, _pb2 = official_multiples(s, (r or {}).get("price"))
            pe = pe if pe is not None else _pe2
            pb = pb if pb is not None else _pb2
        if isinstance(pe, (int, float)) and 0 < pe <= 80:
            pes.append(float(pe))
        if isinstance(pb, (int, float)) and 0 < pb <= 20:
            pbs.append(float(pb))
    if len(pes) < _MIN_PEERS and len(pbs) < _MIN_PEERS:
        return None
    return {"archetype": arch,
            "pe": round(statistics.median(pes), 2) if len(pes) >= _MIN_PEERS else None,
            "pb": round(statistics.median(pbs), 2) if len(pbs) >= _MIN_PEERS else None,
            "peers": max(len(pes), len(pbs)), "source": "إفصاحُ «تداول» — وسيطُ النظائر"}
