#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# D264 — محرّكان واسمٌ واحد: «السعر العادل» يحمل الأقوى، ويقول أيُّهما.
#
# محرّكُ خصم التدفّقات مبنيٌّ ومحروسٌ منذ زمن، لكنّه كان معزولاً: مدخلاتُه
# من مصدرٍ خاصٍّ به، ومعاييرُه ناقصةٌ فيمتنع دائماً. وقد اكتملت: المعدَّلُ
# الخالي من المخاطر (‏D249) · البيتا المقيسة (‏D257) · القوائمُ الرسمية
# (‏D263). فوُصل بقوائمنا من **البابِ الواحد** لا بمصدرٍ رابع.
#
# وخطرُه الأكبرُ عطبٌ وقعنا فيه مرّتين (‏D147 · D174): **رقمان باسمٍ
# واحد**. فالاسمُ يبقى واحداً ويحمل الأقوى، و`rel_basis` يقول من نطق.
#
#   ٠· الجسرُ يبني مدخلاتِ المحرّك من فتراتنا (الأحدثُ عموداً أوّل)
#   ١· ولا نداءَ خارجيّاً: القوائمُ من الباب الواحد
#   ٢· وقوائمُ المزوّد تُخفض الثقةَ درجةً، والرسميةُ لا تُخفضها
#   ٣· والامتناعُ يُحفَظ امتناعاً — لا يُعاد حسابُه كلَّ فتحة
#   ٤· وحين ينطق بثقةٍ كافيةٍ يحمل الاسمَ ويُعلن أساسَه
#   ٥· وحين يمتنع أو تضعف ثقتُه يبقى الاسمُ للنظائر — لا فراغ
#   ٦· ولا يُعرض رقمان باسمٍ واحدٍ في أيّ حال
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os as _os
import tempfile as _tf

_SANDBOX = _tf.mkdtemp(prefix="sp-audit-")
_os.environ["LASTGOOD_PATH"] = _os.path.join(_SANDBOX, "lastgood.json")
_os.environ["SP_STATE_DIR"] = _SANDBOX

import asyncio  # noqa: E402
import pathlib  # noqa: E402
import sys  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, "/app")

fail = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {detail}" if detail else ""))


from app.services import cache  # noqa: E402
from app.services import lastgood  # noqa: E402
from app.services.fair_value_engine import serve as sv  # noqa: E402

# ══ الحارسُ لا يمرّ على امتناع ══
# أوّلُ تشغيلٍ مرَّ الفحصَ ٢ عبر فرع «امتنع في الحالتين»: الصندوقُ الرمليّ
# بلا معدَّلٍ خالٍ من المخاطر فامتنع المحرّكُ دائماً — وفحصٌ يمرّ على
# فراغٍ لا يفحص شيئاً. فتُبذَر المعاييرُ الحيّةُ في الصندوق كما هي على
# الخادم (‏5.694٪ من صكٍّ عشريّ · بيتا مقيسة)، فيُقاس المحرّكُ ناطقاً.
import datetime as _dt  # noqa: E402

lastgood.save("market:risk_free_sar", {
    "value": 0.05694, "as_of": _dt.date.today().isoformat(),
    "source": "تداول — سوق الصكوك", "tenor_years": 9.94})
lastgood.save("market:sector_betas", {
    "as_of": _dt.date.today().isoformat(),
    "sectors": {"المواد الأساسية": {"beta": 0.8845, "n": 45}}})


def fin(source="تداول — XBRL"):
    return {"source": source, "as_of": "2026-09-12", "periods": [
        {"as_of": f"202{y}-12-31", "year": 2020 + y,
         "revenue": 1.0e11 + y * 1e10, "net_income": 1.5e10 + y * 1e9,
         "equity": 8e10, "total_debt": 2e10, "ending_cash": 1e10,
         "operating_cash_flow": 2.2e10, "capex": -8e9,
         "ebit": 2.0e10, "interest_expense": 1.0e9,
         "shares_outstanding": 3.0e9} for y in range(4)]}


# ── ٠ · الجسر ───────────────────────────────────────────────────────────
f = sv.build_fundamentals("2010", fin(), price=70.0, shares=3.0e9)
check(f is not None and f.n_periods() == 4
      and list(f.income.columns)[0] == "2023-12-31",
      "٠ الجسرُ يبني أربعَ فتراتٍ والأحدثُ عموداً أوّل",
      f"{f.n_periods()} · {list(f.income.columns)[:2]}")
check(f.latest("income", "Total Revenue") == 1.3e11
      and f.any_of("balance", ["Stockholders Equity"]) == 8e10
      and f.any_of("cash", ["Operating Cash Flow"]) == 2.2e10,
      "٠ب والبنودُ تصل بأسماء المحرّك لا بأسمائنا")
check(sv.build_fundamentals("2010", {"periods": []}, price=70.0) is None,
      "٠ج وبلا فتراتٍ لا يُبنى مدخَلٌ فارغ")

# ── ١ · لا نداءَ خارجيّ: البابُ الواحد وحدَه ─────────────────────────────
calls: list = []


class _Svc:
    async def get_financials(self, symbol, allow_supplement=True):
        calls.append(symbol)
        return fin()


import app.services.market_data as _md  # noqa: E402
_md.market_service = _Svc()                                      # type: ignore[assignment]

out = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))
check(calls == ["2010.SR"],
      "١ القوائمُ من البابِ الواحد ونداءٌ واحدٌ لا غير", str(calls))

# ── ٢ · مصدرُ القوائم في الثقة ──────────────────────────────────────────
ORDER = ["مرتفعة", "متوسطة", "منخفضة"]
cache.set("dcf:2010:70.0", None, 0)
off = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))


class _SvcY(_Svc):
    async def get_financials(self, symbol, allow_supplement=True):
        calls.append(symbol)
        return fin("ياهو")


_md.market_service = _SvcY()                                     # type: ignore[assignment]
cache.set("dcf:2010:70.0", None, 0)
yh = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))

if off and yh:
    io, iy = ORDER.index(off["confidence"]), ORDER.index(yh["confidence"])
    check(iy >= io and (iy > io or io == 2),
          "٢ قوائمُ المزوّد لا ترفع الثقةَ فوق الرسمية",
          f"رسمي {off['confidence']} · مزوّد {yh['confidence']}")
    check(any("رسمي" in n for n in off.get("notes") or []),
          "٢ب والرسميةُ تُعلَن في الملاحظات", str(off.get("notes"))[:70])
else:
    check(off is None and yh is None,
          "٢ المحرّكُ امتنع في الحالتين — ويُقاس الامتناعُ لا يُفترَض نجاح",
          f"{off} · {yh}")

# ── ٢د · السقفُ الثابتُ لا يحبس ثقةً زال سببُها ─────────────────────────
# سقفُ الثقة كُتب في زمن ياهو، وجزءٌ منه خصمٌ لجهالة المصدر. فمع قوائمَ
# رسميةٍ لأربع فتراتٍ بلا بندٍ ناقصٍ تُرفع درجةٌ واحدة — وبشروطٍ تُقاس،
# لا لأن المصدرَ رسميٌّ وحدَه (D282).
_md.market_service = _Svc()                                      # type: ignore[assignment]
cache.set("dcf:2010:70.0", None, 0)
hi = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))
check(hi and hi["confidence"] == "مرتفعة",
      "٢د أربعُ فتراتٍ رسميةٍ بلا نقصٍ ⇒ ترتفع الثقةُ درجة",
      str((hi or {}).get("confidence")))
check(hi and any("أربع فترات" in n for n in hi.get("notes") or []),
      "٢ه ويُعلَن سببُ الرفع — لا يرتفع رقمٌ بلا بيان", str((hi or {}).get("notes"))[:80])


class _SvcShort(_Svc):
    async def get_financials(self, symbol, allow_supplement=True):
        f = fin()
        f["periods"] = f["periods"][:3]        # ثلاثُ فتراتٍ فقط
        return f


_md.market_service = _SvcShort()                                 # type: ignore[assignment]
cache.set("dcf:2010:70.0", None, 0)
sh = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))
check(sh is None or sh["confidence"] != "مرتفعة",
      "٢و وثلاثُ فتراتٍ لا ترفع — الشرطُ يُقاس لا يُفترَض",
      str((sh or {}).get("confidence")))

# ── ٣ · الامتناعُ يُحفَظ امتناعاً ────────────────────────────────────────
class _SvcEmpty:
    async def get_financials(self, symbol, allow_supplement=True):
        calls.append(symbol)
        return {"source": "ياهو", "periods": [{"year": 2024}]}


_md.market_service = _SvcEmpty()                                 # type: ignore[assignment]
cache.set("dcf:9999:70.0", None, 0)
calls.clear()
a = asyncio.run(sv.value_for_symbol("9999.SR", price=70.0))
b = asyncio.run(sv.value_for_symbol("9999.SR", price=70.0))
check(a is None and b is None,
      "٣ فترةٌ واحدةٌ ⇒ امتناع — ولا رقمَ مختلَق")
check(len(calls) <= 1,
      "٣ب والامتناعُ يُحفَظ فلا يُعاد الحسابُ كلَّ فتحة", f"{len(calls)} نداء")

# ── ٤ · ٥ · ٦ · الاسمُ الواحد في صفحة التحليل ────────────────────────────
src = (ROOT / "backend" / "app" / "services" / "analysis.py").read_text(encoding="utf-8")
check('"rel_basis": "خصم التدفّقات النقدية"' in src,
      "٤ حين ينطق المحرّكُ يحمل الاسمَ ويُعلن أساسَه")
check('_dcf.get("confidence") in ("مرتفعة", "متوسطة")' in src,
      "٥ وبثقةٍ دون المتوسطة لا يحمل الاسمَ — يبقى للنظائر")
import re  # noqa: E402
blk = src.split("_dcf: dict = {}", 1)[-1][:1800]
check(blk.count("rel_value") == 1,
      "٦ ولا رقمان باسمٍ واحد — حقلٌ واحدٌ يُكتب مرّةً", str(blk.count("rel_value")))

# ── ٧ · اعتماديٌّ لا تجريبيّ ────────────────────────────────────────────
# وُضع `allow_unverified=True, allow_stale=True` يومَ كانت المعاييرُ ناقصةً
# ليعمل المحرّكُ أصلاً، ثمّ اكتملت ونسيتُ رفعَ العلَم — فبقي الرقمُ يُعرض
# باسمٍ اعتماديٍّ وهو مولودٌ في وضع التجربة (‏D279).
SV = (ROOT / "backend" / "app" / "services" / "fair_value_engine"
      / "serve.py").read_text(encoding="utf-8")
# (والتعليقُ يذكر الوضعَ القديمَ ليشرحه — والعبرةُ بالنداء لا بالشرح.)
import re as _re2  # noqa: E402
_calls = _re2.findall(r"load_params\(([^)]*)\)", SV)
check(all(not c.strip() for c in _calls) and _calls,
      "٧ المحرّكُ يُشغَّل في الوضع الصارم — لا وضعِ التجربة", str(_calls))
check("load_params()" in SV, "٧ب ومعاييرُه تُحمَّل بشروطها كاملةً")

# وسلوكاً: معاييرُ غيرُ موثَّقةٍ ⇒ امتناعٌ مُعلَن، لا هبوطٌ صامتٌ للتجربة.
import app.services.fair_value_engine.params as _pm  # noqa: E402
_orig = _pm.load_params


def _reject(*a, **k):
    raise _pm.ParamsError("verified=false في الاختبار")


sv.load_params = _reject                                         # type: ignore[attr-defined]
import app.services.fair_value_engine.serve as _sv2  # noqa: E402
_pm.load_params = _reject                                        # type: ignore[assignment]
_md.market_service = _Svc()                                      # type: ignore[assignment]
cache.set("dcf:2010:70.0", None, 0)
none_out = asyncio.run(sv.value_for_symbol("2010.SR", price=70.0))
_pm.load_params = _orig                                          # type: ignore[assignment]
check(none_out is None,
      "٧ج ومعاييرُ غيرُ اعتماديةٍ ⇒ امتناعٌ — لا رقمٌ تجريبيٌّ باسمٍ اعتماديّ",
      str(none_out)[:60])

print(("FAIL" if fail else "PASS") + " D264 — محرّكان واسمٌ واحد")
raise SystemExit(fail)
