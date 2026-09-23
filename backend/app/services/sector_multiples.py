"""مضاعفا القطاع من السوق كلِّه لا من المحفظة (D446).

قِيس بكاشف `fv_paths_low.py`: مسارُ «مضاعف الربحية العادل» غائبٌ عن أكثر
الأوراق، لأن مضاعفَي القطاع كانا يُحسبان من **نظائرَ في محفظة المالك** —
فالشركةُ التي لا نظيرَ لها في المحفظة تُحرَم مسارَ قطاعها كلَّه.

ولقطةُ «تداول» الرسمية تحمل مكرّرَ الربحية والدفترية لكلّ ورقةٍ في الرئيسيّ
(‏272/272). فالمضاعفُ العادلُ للقطاع = **وسيطُ** مكرّرات النظائر من النمط
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
        if isinstance(pe, (int, float)) and 0 < pe <= 80:
            pes.append(float(pe))
        if isinstance(pb, (int, float)) and 0 < pb <= 20:
            pbs.append(float(pb))
    if len(pes) < _MIN_PEERS and len(pbs) < _MIN_PEERS:
        return None
    return {"archetype": arch,
            "pe": round(statistics.median(pes), 2) if len(pes) >= _MIN_PEERS else None,
            "pb": round(statistics.median(pbs), 2) if len(pbs) >= _MIN_PEERS else None,
            "peers": max(len(pes), len(pbs)), "source": "لقطةُ «تداول» — وسيطُ النظائر"}
