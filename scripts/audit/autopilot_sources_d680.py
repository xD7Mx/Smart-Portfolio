#!/usr/bin/env python3
"""حارسُ D680 — ما يشربه المستشارُ الآليّ يصله فعلاً، لا مفتاحاً لا وجودَ له.

قِيس في الإنتاج (autopilot_pack_d679_door · run 38092183639) بعد نشر D679: «القادم» 0/14 و«الثبات» 0/14 والأحداثُ الجوهرية
بعناوين إنجليزيةٍ مُحرَّفة («Alghaz Waltsnae Company …»). والتشخيص (autopilot_src_d679_door · run 38092395377):
  · صفُّ المفكرة {headline, published, kind, date_kind} — والمستشارُ يقرأ «date/title» فلا قادمَ أبداً (قديمٌ قبل D679).
  · وسمُ الثبات في ثقة محرّك الحوكمة — والمستشارُ يطلبه من «financial» في تحليل الشركة ولا يحمله.
  · والأحداثُ من الخام (‏material_events) لا من عرض الصفحة (‏events_view) الذي يحمل العنوانَ العربيَّ الرسميّ.
يُشغَّل المساعدون الثلاثة بمصادرَ مزيّفةٍ بشكلها الحقيقيّ — فيُقاس السلوكُ لا النصّ.

    python3 scripts/audit/autopilot_sources_d680.py
"""
import asyncio, os, pathlib, sys, tempfile, types
from datetime import date, timedelta
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


soon = (date.today() + timedelta(days=9)).isoformat()
past = (date.today() - timedelta(days=20)).isoformat()
# صفُّ مفكرة الشركة كما يبنيه content_engine.company_calendar
ROWS = [{"headline": "اجتماع الجمعية العامة العادية", "published": soon, "kind": "جمعية", "date_kind": "event", "source": "أرقام", "url": None},
        {"headline": "توزيع أرباح نقدية", "published": past, "kind": "توزيعات", "date_kind": "announced", "source": "أرقام", "url": None}]
sys.modules["app.api.v1.endpoints.market"] = types.SimpleNamespace(get_company_events=lambda s, n="": _ret({"data": ROWS}))


async def _ret0(v):
    return v


def _ret(v):
    return _ret0(v)


from app.services import autopilot as AP   # noqa: E402
from app.services import material_events, events_view   # noqa: E402
material_events.events_for = lambda s: _ret({"events": [{"date": past, "kind": "acquisition",
                                                         "title": "Alghaz Waltsnae Company Eligibility Alqabida"}]})
events_view.for_display = lambda s, limit=12: _ret({"events": [{"date": past, "kind": "acquisition", "kind_ar": "استحواذ",
                                                                "title": "الغاز والتصنيع تعلن تحديثاً بشأن الاستحواذ", "value": 120e6}]})
seen = {}


async def _gov(symbol, db=None, company_status=None, sector=None, with_decision=True):
    seen.update(symbol=symbol, sector=sector)
    return {"confidence": {"score": 100, "stability": 72.0, "stability_label": "مستقرّة"}}
from app.services import governance_engine   # noqa: E402
governance_engine.evaluate_company = _gov


async def main():
    up = await AP._events("2080")
    check(len(up) == 1 and up[0].get("date") == soon and up[0].get("title") == "اجتماع الجمعية العامة العادية",
          "١ «القادم» يُقرأ من صفّ المفكرة بمفتاحيه (published · headline) — والماضي لا يُعدّ قادماً", str(up))
    me = await AP._material("2080")
    t = (me[0].get("العنوان") if me else "") or ""
    check(bool(me) and any("؀" <= ch <= "ۿ" for ch in t) and me[0].get("النوع") == "استحواذ" and me[0].get("القيمة"),
          "٢ والأحداثُ الجوهرية من عرض الصفحة: عنوانٌ عربيٌّ رسميّ ونوعٌ وقيمة", str(me)[:160])
    st = await AP._stability("2080", "المرافق العامة") if hasattr(AP, "_stability") else None
    check(st == "مستقرّة" and seen.get("symbol") == "2080.SR" and seen.get("sector") == "المرافق العامة",
          "٣ والثباتُ من محرّك الحوكمة — بالرمز والقطاع اللذين تطلبه بهما نافذتُها، فتُشارك ذاكرتَها", f"{st} · {seen}")
    src = (ROOT / "backend/app/services/autopilot.py").read_text(encoding="utf-8")
    check('pos["stability"] = stb' in src and "_stability(sym, sector_of.get(sym))" in src and "autopilot:pack:v4" in src
          and "autopilot:pack:v4" in (ROOT / "backend/app/api/v1/endpoints/ai.py").read_text(encoding="utf-8"),
          "٤ والحزمةُ تضع الثلاثةَ في كلّ مركز، وذاكرتُها v4 فلا تُخدم حزمةُ اليوم الناقصة")


asyncio.run(main())
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
