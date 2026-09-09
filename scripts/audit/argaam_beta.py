#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# حصادُ «بيتا» من «أرقام» — **مسبارُ تغطيةٍ لا خدمة**.
#
# ## لماذا
# محرّكُ القيمة العادلة يحمل بيتا قطاعيةً معلَّمةً `unverified_default`،
# مأخوذةً من جدولٍ أجنبيٍّ لأسواقٍ ناشئة، وتُنزِل درجةَ الثقة في كلّ مخرَج.
# وقد ظهر في مسبار الجدولين أنّ «أرقام» تنشر **بيتا لكلّ شركة** في جدولٍ
# نقرأه أصلاً بنجاح: الراجحي ‎1.33 · سابك ‎1.02 · جرير ‎0.63 · الرياض ريت
# ‎0.35. فهذه بيتا **مقيسةٌ من سوقنا** لا مستوردة.
#
# ## ما لا يفعله
# لا يكتب في ملفّ المعايير ولا يُوثّق شيئاً. التوثيقُ قرارٌ بعد النظر في
# التغطية، لا أثرٌ جانبيٌّ للحصاد. وبيتا «أرقام» **مرفوعةٌ لشركة**، وما
# يطلبه المحرّك **قطاعيةٌ غيرُ مرفوعة** — فنزعُ الرافعة وأخذُ الوسيط
# خطوةٌ تالية، ولا تُبنى قبل أن تُعرف التغطيةُ الحقيقية.
#
#   docker exec sp_backend python /app/scripts/audit/argaam_beta.py
#   docker exec sp_backend python /app/scripts/audit/argaam_beta.py --limit 60
#
# رحيمٌ بالمصدر: تزامنٌ محدودٌ ومهلةٌ بين الدفعات — الحصادُ لا يُبرّر ضغطاً.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os, shutil as _sh, tempfile as _tf
_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_REAL_LG = _os.environ.get("LASTGOOD_PATH") or (
    "/app/data/lastgood.json" if _os.path.isdir("/app/data") else "")
_COPY = _os.path.join(_SANDBOX, "lastgood.json")
if _REAL_LG and _os.path.exists(_REAL_LG):
    try:
        _sh.copyfile(_REAL_LG, _COPY)
    except Exception:                                             # noqa: BLE001
        pass
_os.environ["LASTGOOD_PATH"] = _COPY
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio
import json
import pathlib
import re
import sys

for _p in ("/app", "backend", "."):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = pathlib.Path("/app/reports/argaam_beta.json")
CONC = 4                       # تزامنٌ محدودٌ — رحمةً بالمصدر
_BETA_LABEL = re.compile(r"^\s*بيتا\s*$")
_NUM = re.compile(r"^-?\d{1,2}[.,]\d{1,3}$")


def _num(s: str) -> float | None:
    s = s.strip().replace(",", ".")
    if not _NUM.match(s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


async def one(sym: str, sem) -> dict:
    from app.services.argaam_calendar import (_company_id, _company_url, UA,
                                              _rows_of)
    import httpx

    cid = await _company_id(sym)
    if not cid:
        return {"symbol": sym, "حال": "لا معرّف"}
    async with sem:
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                         headers={"User-Agent": UA,
                                                  "Accept-Language": "ar,en;q=0.8"}) as c:
                r = await c.get(_company_url(cid))
        except Exception as e:                                    # noqa: BLE001
            return {"symbol": sym, "حال": f"تعذّر ({type(e).__name__})"}
    if r.status_code != 200:
        return {"symbol": sym, "حال": f"‎{r.status_code}"}
    for cells in _rows_of(r.text):
        if len(cells) >= 2 and _BETA_LABEL.match(cells[0]):
            b = _num(cells[1])
            # قيمةٌ خارج المعقول تُعرض ولا تُقبل — بيتا سالبةٌ أو فوق ثلاثةٍ
            # في سوقٍ ضحلٍ انحيازُ قياسٍ لا خاصيّةُ سهم.
            return {"symbol": sym, "beta": b, "معقولة": bool(b and 0 < b < 3),
                    "خام": cells[1]}
    return {"symbol": sym, "حال": "لا صفَّ بيتا في الصفحة"}


async def main() -> int:
    from app.data.market_universe import MARKET_UNIVERSE
    from app.data.universe import main_market

    argv = list(sys.argv[1:])
    limit = 30
    if "--limit" in argv:
        i = argv.index("--limit")
        if i + 1 >= len(argv) or not argv[i + 1].isdigit():
            print("… `--limit` بلا عددٍ صحيح.")
            return 2
        limit = int(argv[i + 1])
        del argv[i:i + 2]
    args = [a.replace(".SR", "") for a in argv if not a.startswith("-")]

    uni = main_market(MARKET_UNIVERSE)
    syms = args or list(uni)[:limit]
    print(f"حصادُ بيتا من «أرقام» — {len(syms)} رمزاً، تزامنُ {CONC}.")
    print("─" * 74)

    sem = asyncio.Semaphore(CONC)
    rows = await asyncio.gather(*(one(s, sem) for s in syms))

    got = [r for r in rows if r.get("beta") is not None]
    sane = [r for r in got if r.get("معقولة")]
    for r in rows:
        if r.get("beta") is not None:
            flag = "" if r["معقولة"] else "  ⚠ خارج المعقول"
            print(f"  {r['symbol']:<6} بيتا {r['beta']:.2f}{flag}")
        else:
            print(f"  {r['symbol']:<6} — {r.get('حال')}")

    print("─" * 74)
    print(f"التغطية: {len(got)} من {len(syms)}"
          f" · ضمن المعقول {len(sane)}")
    if sane:
        vals = sorted(r["beta"] for r in sane)
        mid = vals[len(vals) // 2]
        print(f"الوسيط {mid:.2f} · الأدنى {vals[0]:.2f} · الأعلى {vals[-1]:.2f}")
    try:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"الخام: {OUT}")
    except Exception as e:                                        # noqa: BLE001
        print(f"تعذّر حفظُ الخام ({type(e).__name__}) — المخرَجُ أعلاه هو الأصل.")

    print("\nهذه بيتا **مرفوعةٌ لشركة**، والمحرّكُ يطلب قطاعيةً غيرَ مرفوعة.")
    print("نزعُ الرافعة وأخذُ الوسيط خطوةٌ تالية، ولا تُبنى قبل هذه التغطية.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
