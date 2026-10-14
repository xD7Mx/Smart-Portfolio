#!/usr/bin/env python3
"""حارسُ D708 — هيكلُ الملكية من «تداول» يُقرأ بالشكل الذي تعيده: HTML لا JSON.

قِيس في الإنتاج: التغطيةُ 0 من 272 والحارسُ القديمُ أخضر — لأنه أثبت القراءةَ على صفوف JSON مصطنعة، والنداءاتُ تعيد أجزاءَ HTML
تُلصق في الصفحة (‏ownership_html_door · run 38583682788): الملكيةُ الأجنبيةُ قطعةٌ فيها الحدُّ والفعليُّ ومصفوفةُ الرسم، والمجلسُ جدولُ
أيّامٍ متتالية، وكبارُ الملاك جدولان (‏5٪ فأكثر ثمّ فترةُ الحظر) يطلبان ‎history=0. وبعد الإصلاح قُرئ الحيُّ (‏run 38584166651 ·
38584582392): أرامكو 0.72٪ أجانب و«المملكة العربية السعودية» 81.484٪، والراجحي 14.06٪، والحبيب 40.03٪ و28.773٪.
فالحارسُ سلوكيٌّ على قطعٍ بشكل المقيس — وأحمرُ على القارئ القديم:

    python3 scripts/audit/ownership_html_d708.py
"""
import asyncio, os, sys, tempfile
_SB = tempfile.mkdtemp(prefix="sp-audit-")
os.environ["LASTGOOD_PATH"] = os.path.join(_SB, "lastgood.json")
os.environ["SP_STATE_DIR"] = _SB
os.environ["SP_STATUS_LOG"] = os.path.join(_SB, "status_codes.jsonl")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "backend"))

fail = 0


def check(ok, label, det=""):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}" + (f" — {det}" if det else ""))


from app.services import tadawul_ownership as TO, tadawul_http as TH

# ── قطعٌ بشكل ما أعادته «تداول» حرفاً (مختصرةُ الفراغ) ──
FOREIGN = ('<div class="foreign_ownership"> <div class="total_foreign_ownership"> <ul> <li> <h2>Total Foreign ownership*</h2> '
           '<div class="max_actual"> <div class="max_limit"> <span>Maximum Limit (%)</span> <strong>49.00</strong> </div> '
           '<div class="actual"> <span>Actual (%)</span> <strong> 14.06 </strong> </div> </div> </li> <li> '
           '<h2>Foreign strategic investors ownership</h2> <div class="max_actual"> <div class="max_limit"> <span>Actual (%)</span> '
           '<strong> 0.00 </strong> </div> </div> </li> </ul> <div class="last_update"> Last updated on : 2026-10-14 </div> </div> </div>'
           '<script type="text/javascript"> var fr= [ { name: \'Total Foreign Ownership- Maximum Limit (%) \', y: 49.0 }, '
           '{ name: \'Total Foreign Ownership- Actual (%)\', y: 14.06 }, { name: \'Foreign Strategic Investors Ownership\', y: 0.0 }, ]; '
           'companyprofile.foreignGraph(fr); </script>')


def _tr(*cells):
    return "<tr> " + " ".join(f'<td class="numeric priceUp">{c}</td>' for c in cells) + " </tr>"


BOARD = ('<table class="col-md-12 table-bordered"> <thead class="cf"> <tr> <th>Trading Date</th> <th>Shareholders</th> '
         '<th class="numeric">Designation</th> <th class="numeric">Total Shares Held Trading Day</th> '
         '<th class="numeric">Total Shares Held Prev Trading Day</th> <th>Total Shares Change</th> </tr></thead>'
         + _tr("2026-10-13 ", "عبدالله سليمان عبدالعزيز الراجحي ", "Chairman", "2.1791737%", "2.1791737%", "0<i></i>", "2.1791737%")
         + _tr("2026-10-13 ", "عبدالعزيز خالد علي الغفيلي ", "Board of Directors", "0.0012923%", "0.0012923%", "0", "0.0012923%")
         + _tr("2026-10-13 ", "عبدالرحمن عبدالله عبدالرحمن الفدي ", "Senior Executives", "0.0018090%", "0.0018090%", "0", "0.0018090%")
         + _tr("2026-10-12 ", "عبدالله سليمان عبدالعزيز الراجحي ", "Chairman", "2.1791737%", "2.1791737%", "0", "2.1791737%")
         + _tr("2026-10-12 ", "عضوٌ غادر المجلس ", "Board of Directors", "0.5000000%", "0.5000000%", "0", "0.5000000%")
         + "</table>")
MAJOR = ('<div class="time_apply"> Time Period <svg><path d="M11.6,5.5"/></svg> </div>'
         '<table><tr><th>Trading Date</th><th>Shareholders</th><th>Total Shares Held Trading Day</th>'
         '<th>Total Shares Held Prev Trading Day</th><th>Total Shares Change</th></tr>'
         + _tr("2026-10-14", "سليمان عبدالعزيز سليمان الحبيب", "40.03%", "40.03%", "0")
         + _tr("2026-10-14", "شركة محمد عبدالعزيز الحبيب واولاده القابضة", "28.773%", "28.773%", "0")
         + '</table> Major shareholder who owns 5% or more from total shares <table><tr><th>Trading Date</th></tr>'
         + _tr("2026-10-14", "مساهمٌ في فترة الحظر", "7.5%", "7.5%", "0")
         + '</table> Shareholders subject to the lock-up period as per the Listing Rules.')
PAGE = ('<base href="https://www.saudiexchange.sa/wps/portal/x/">'
        "url:'p0/IZ7_A=CZ6_B=NJforeginOwnerShip=/', url:'p0/IZ7_A=CZ6_B=NJhistoricalBoardMembersWithDates=/', "
        "url:'p0/IZ7_A=CZ6_B=NJhistoryOfMajorShareHolder=/', url:'p0/IZ7_A=CZ6_B=NJgetAllEvents=/'")
calls = []


async def fake_fetch(url, *, params=None, referer=None, timeout=45):
    calls.append((url.rsplit("NJ", 1)[-1].rstrip("=/"), dict(params or {})))
    if "NJforeginOwnerShip" in url:
        return 200, FOREIGN
    if "NJhistoricalBoardMembersWithDates" in url:
        return 200, BOARD
    if "NJhistoryOfMajorShareHolder" in url:
        return (200, MAJOR) if (params or {}).get("history") == "0" else (500, "Error 500: CWSRV0295E: Error reported: 500\n")
    return 404, ""


async def fake_page(sym):
    return PAGE

TH.fetch = fake_fetch
TO.company_page = fake_page
rec = asyncio.run(TO.read_symbol("1120"))
fo = {r["name"]: r["percent"] for r in rec.get("foreign") or []}
check(fo.get("ملكيةُ الأجانب الفعلية") == 14.06 and fo.get("الحدُّ الأعلى لملكية الأجانب") == 49.0
      and fo.get("المستثمرون الاستراتيجيون الأجانب") == 0.0,
      "١ الملكيةُ الأجنبيةُ تُقرأ من قطعة HTML — الفعليُّ والحدُّ والاستراتيجيّ بتسمياتٍ عربية", str(rec.get("foreign") or rec)[:200])
bd = rec.get("board") or []
check([b["name"] for b in bd] == ["عبدالله سليمان عبدالعزيز الراجحي", "عبدالرحمن عبدالله عبدالرحمن الفدي", "عبدالعزيز خالد علي الغفيلي"]
      and bd[0].get("position") == "رئيس مجلس الإدارة" and bd[1].get("position") == "كبار التنفيذيين"
      and abs(bd[0]["percent"] - 2.1791737) < 1e-5 and all(b.get("at") == "2026-10-13" for b in bd),
      "٢ والمجلسُ من جدولٍ: أحدثُ يومِ تداولٍ وحده (من غادر قبلَه لا يتسلّل)، والصفةُ بالعربية، والأكبرُ نسبةً أوّلاً",
      str([(b["name"], b.get("position")) for b in bd]))
mj = rec.get("major_holders") or []
check([m["name"] for m in mj] == ["سليمان عبدالعزيز سليمان الحبيب", "شركة محمد عبدالعزيز الحبيب واولاده القابضة"]
      and mj[0]["percent"] == 40.03,
      "٣ وكبارُ الملاك من الجدول الأوّل وحده — ولا يُخلط بهم الخاضعون لفترة الحظر", str(mj))
sent = {k: p for k, p in calls}
check(all(p.get("symbol") == "1120" for p in sent.values()) and sent.get("historyOfMajorShareHolder", {}).get("history") == "0"
      and "fromDate" not in sent.get("historyOfMajorShareHolder", {}),
      "٤ والنداءاتُ بمعاملات شيفرة الصفحة: الرمزُ لكلٍّ، و‎history=0 بلا مدى لكبار الملاك (بلا ‎history يردّ 500)", str(sent))

calls.clear()


async def fake_fetch_500(url, *, params=None, referer=None, timeout=45):
    if "NJhistoryOfMajorShareHolder" in url:
        return 500, "Error 500: CWSRV0295E: Error reported: 500\n"
    return await fake_fetch(url, params=params, referer=referer)

TH.fetch = fake_fetch_500
rec2 = asyncio.run(TO.read_symbol("1120"))
check("major_holders" not in rec2 and (rec2.get("failed") or {}).get("major_holders") == "HTTP 500" and rec2.get("foreign"),
      "٥ ونداءٌ يتعذّر يغيب بندُه ويُسمّى سببُه — لا يُصفَّر ولا يُسقط البنودَ الأخرى", str(rec2.get("failed")))
check(TO.parse_response("board", '<table><tr><td colspan="5">No data available in table</td></tr></table>') == []
      and TO.normalize([{"shareholderName": "صندوق", "percentage": "37.5"}])[0]["percent"] == 37.5
      and TO.parse_response("major_holders", '{"data": [{"shareholderName": "صندوق", "percentage": 37.5}]}')[0]["name"] == "صندوق",
      "٦ وجدولٌ بلا بيانات يغيب، وردُّ JSON إن عاد يومًا يُقرأ كما كان")

sch = open(os.path.join(ROOT, "backend/app/scheduler/scheduler.py"), encoding="utf-8").read()
import re
m_b = re.search(r"OWNERSHIP_BATCH = (\d+)", sch)
m_c = re.search(r"OWNERSHIP_BROWSER_CAP = (\d+)", sch)
job = sch[sch.index("async def job_ownership"):sch.index("async def job_special_deals")]
reg = sch[sch.index("job_ownership,\n"):][:200]
check(m_b and m_c and int(m_b.group(1)) * TO.MAX_AGE_DAYS >= 2 * 286 and int(m_c.group(1)) <= 10
      and "syms[:OWNERSHIP_BATCH]" in job and "browsed < OWNERSHIP_BROWSER_CAP" in job
      and "CronTrigger(hour=" in reg and "day_of_week" not in reg,
      "٧ والحصادُ ليليٌّ يغطّي الكونَ قبل أن تشيخ القراءة (دفعةٌ × ثلاثين يوماً ≥ ضعفَ الكون)، والمتصفّحُ مقيَّدٌ في الليلة",
      f"دفعة {m_b and m_b.group(1)} · متصفّح {m_c and m_c.group(1)}")
print("\nالنتيجة:", "نظيف ✔" if not fail else "عطب ✖")
sys.exit(fail)
