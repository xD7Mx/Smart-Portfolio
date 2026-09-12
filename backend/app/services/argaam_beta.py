"""حصادُ بيتا الشركات من «أرقام» — خدمةٌ لا مسبار (D257).

كان الحصادُ في مسبارٍ يدويّ (‏scripts/audit/argaam_beta.py) يطبع ولا
يحفظ — وهو صوابُه يومَ كان السؤالُ «أتوجد تغطيةٌ أصلاً؟». وقد قِيست
التغطية (‏30/30) فصار المطلوبَ مصدراً يعمل وحدَه: هذه الدالّةُ تُشارك
المسبارَ منطقَ القراءة نفسَه، ولا تكتب شيئاً — الكتابةُ في `sector_betas`
بعد نزع الرافعة، فلا يُخلَط حصادٌ بتوثيق.
"""
from __future__ import annotations

import asyncio
import re

from loguru import logger

CONCURRENCY = 4                # رحمةً بالمصدر — الحصادُ لا يُبرّر ضغطاً
_BETA_LABEL = re.compile(r"^\s*بيتا\s*$")
_NUM = re.compile(r"^-?\d{1,2}[.,]\d{1,3}$")


def _num(s: str) -> float | None:
    s = str(s or "").strip().replace(",", ".")
    if not _NUM.match(s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


async def one(sym: str, sem: asyncio.Semaphore) -> float | None:
    """بيتا شركةٍ واحدة — أو None (بلا معرِّفٍ · تعذُّرٍ · لا صفَّ بيتا)."""
    from app.services.argaam_calendar import (UA, _company_id, _company_url,
                                              _rows_of)
    import httpx

    cid = await _company_id(sym)
    if not cid:
        return None
    async with sem:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                         headers={"User-Agent": UA,
                                                  "Accept-Language": "ar,en;q=0.8"}) as c:
                r = await c.get(_company_url(cid))
        except Exception:                                         # noqa: BLE001
            return None
    if r.status_code != 200:
        return None
    for cells in _rows_of(r.text):
        if len(cells) >= 2 and _BETA_LABEL.match(cells[0]):
            return _num(cells[1])
    return None


async def harvest(symbols: list[str]) -> dict[str, float]:
    """رمزٌ ← بيتا مرفوعة. وما لم يُقرأ يغيب — ولا يُختلق رقمٌ لأحد."""
    sem = asyncio.Semaphore(CONCURRENCY)
    vals = await asyncio.gather(*(one(s, sem) for s in symbols))
    out = {s: v for s, v in zip(symbols, vals) if isinstance(v, (int, float))}
    logger.info("بيتا «أرقام»: {} من {}", len(out), len(symbols))
    return out
