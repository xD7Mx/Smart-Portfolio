"""القوائمُ الماليةُ الرسميةُ من «تداول» بصيغة PDF — حين تقف ملفّاتُ XBRL (D476).

قِيس على خادم المالك (كاشفا `insurer_xbrl_door.py` و`tadawul_statements_door.py`):
قائمةُ ملفّات XBRL للمؤمِّنين تقف عند قوائم 2022، وتبويبُ «القوائم المالية»
في صفحة الشركة نفسِها يحمل القوائمَ السنويةَ والربعيةَ حتى 2026 بصيغة PDF
(‏8010 · 8210 · 1320). فكان المحرّكان يقوّمان شركاتٍ بقوائمَ عمرُها أربعُ
سنوات لأن قارئَنا يعرف صيغةً واحدة — والمصدرُ الرسميُّ نفسُه ينشر الأحدث.

يُقرأ من كلّ ملفٍّ سنويٍّ عمودا السنة الحالية والسابقة من صفحات القوائم
الأساسية (المركز المالي · الدخل · التدفّقات) بأسماء البنود كما نُشرت، والوحدةُ
من الصفحة نفسها. ثمّ صمّامٌ لا يُتجاوَز: صافي الربح ÷ ربحية السهم يجب أن
يطابق عددَ الأسهم المعروف — وإلا تُرفض الفترةُ ويُذكر السبب، فرقمٌ خاطئٌ
أسوأُ من فراغٍ معلَن.
"""
from __future__ import annotations

import re

from loguru import logger

_NUM = re.compile(r"^\(?-?[\d,]+(?:\.\d+)?\)?$")
_NOTE = re.compile(r"^\d{1,2}(?:\s?[.,]\s?\d{1,2})*$")      # «6.1» · «7,19» · «10, 20»
_MONTHS = {m: i for i, m in enumerate(("january", "february", "march", "april", "may", "june", "july",
                                       "august", "september", "october", "november", "december"), 1)}

# البندُ كما يُنشر (بعد تصغير الحروف وحذف المسافات الزائدة) — الأوّلُ أولى.
LABELS: dict[str, tuple[str, ...]] = {
    "revenue": (r"insurance (?:service )?revenue", r"reinsurance revenue", r"revenues?", r"total revenues?", r"sales",
                r"net sales", r"revenue from contracts? with customers", r"operating revenues?",
                r"rental income(?: from investment properties)?", r"total (?:operating )?income"),
    "net_income": (r"net (?:income|profit) (?:for the (?:year|period) )?attribut\w* to (?:the )?(?:shareholders|owners|equity holders)"
                   r"(?: of the (?:parent|company))?(?: after zakat(?: and income tax)?)?",
                   r"(?:net )?(?:profit|income) for the (?:year|period) attributable to (?:the )?(?:shareholders|owners|equity holders)"
                   r"(?: of the (?:parent|company))?",
                   r"net (?:profit|income) for the (?:year|period) after zakat(?: and (?:income )?tax)?",
                   r"net (?:\(loss\) ?/ ?)?(?:profit|income)(?: ?/ ?\(loss\))? for the (?:year|period)",
                   r"(?:\(loss\) ?/ ?)?(?:profit|income)(?: ?/ ?\(loss\))? for the (?:year|period)",
                   r"net (?:\(loss\) )?(?:income|profit)(?: \(loss\))?",
                   # «(Loss) for the year» · «Net (loss) for the year» · «Profit / (loss) for the year» (صناديق عقارية)
                   r"(?:net )?\(?(?:loss|profit|income)\)?(?: ?/ ?\(?(?:loss|profit|income)\)?)? for the (?:year|period)",
                   # «Income / (loss) attributed to the shareholders after zakat and income tax» (ميدغلف 8030)
                   r"(?:net )?(?:income|profit)(?: ?/ ?\(loss\))? attribut\w* to (?:the )?shareholders after zakat(?: and income tax)?"),
    "pretax_income": (r"net (?:profit|income) for the (?:year|period)(?: attributable to shareholders)? before zakat(?: and (?:income )?tax)?",
                      r"income attributed to (?:the )?shareholders before,? zakat(?: and income tax)?",
                      r"(?:net )?(?:\(loss\) ?/ ?)?(?:profit|income)(?: ?/ ?\(loss\))? before zakat(?: and income tax)?",
                      r"net income attributed to (?:the )?shareholders before zakat(?: and income tax)?"),
    "eps": (r"basic (?:and diluted )?(?:\(loss\) ?/ ?)?earnings?(?: ?/ ?\(loss\))? per (?:share|unit).*",
            r"earnings? per (?:share|unit)(?: - basic(?: and diluted)?)?.*"),
    "total_assets": (r"total assets",),
    "total_liabilities": (r"total liabilities",),
    "equity": (r"total equity attributable to (?:the )?(?:shareholders|owners|equity holders).*",
               r"equity attributable to (?:the )?(?:shareholders|owners|equity holders).*",
               r"total shareholders[’']? equity", r"total equity",
               r"net assets attributable to (?:the )?unit ?holders"),
    "ending_cash": (r"cash and cash equivalents(?: at (?:the )?end of the (?:year|period))?",),
    "operating_cash_flow": (r"net cash (?:flows? )?(?:generated from|from|provided by|\(used in\) ?/ ?generated from|"
                            r"generated from ?/ ?\(used in\)|used in|\(used in\)|from ?/ ?\(used in\)) operating activities",),
    "capex": (r"(?:purchase|acquisition)s? of property,? (?:plant )?and equipment",
              r"additions to property,? (?:plant )?and equipment"),
    "interest_expense": (r"finance (?:costs?|charges?)", r"financial charges"),
}
_KIND = {"balance": ("total_assets", "total_liabilities", "equity", "ending_cash"),
         "income": ("revenue", "net_income", "pretax_income", "eps", "interest_expense"),
         "cash": ("operating_cash_flow", "capex", "ending_cash")}
_COMP = {k: tuple(re.compile("^" + p + r"\s*$") for p in v) for k, v in LABELS.items()}


def _val(tok: str) -> float | None:
    t = tok.strip()
    if not _NUM.match(t):
        return None
    neg = t.startswith("(") or t.startswith("-")
    try:
        v = float(t.strip("()").replace(",", "").lstrip("-"))
    except ValueError:
        return None
    return -v if neg else v


def _kind_of(text: str) -> str | None:
    head = text[:900].lower()
    if "notes to the" in head or "auditor" in head:
        return None
    if re.search(r"statement of financial position|balance sheet", head):
        return "balance"
    if re.search(r"statement of cash flows?", head):
        return "cash"
    if re.search(r"statement of (?:profit or loss|income)|income statement", head):
        return "income"
    return None


def _unit(text: str) -> float:
    t = text.lower()
    if re.search(r"(?:in|of) (?:saudi riyals? )?millions|millions of saudi|sar ?[’'`]?\s?m(?:illion)?s?\b(?! ?[’'`]?000)|\(sr millions?\)", t[:1500]) \
            and not re.search(r"thousand|[’'`]\s?000", t[:1500]):
        return 1_000_000.0
    if re.search(r"[’'`]\s?000|thousand", t):
        return 1_000.0
    return 1.0


def _as_of(text: str) -> str | None:
    m = re.search(r"(january|february|march|april|may|june|july|august|september|october|november|december)"
                  r"\s+(\d{1,2}),?\s+(20\d\d)", text[:900], re.I)
    if m:
        mo, d, y = _MONTHS[m.group(1).lower()], int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{1,2})\s+(january|february|march|april|may|june|july|august|september|october|november|december)"
                  r",?\s+(20\d\d)", text[:900], re.I)
    if m:
        d, mo, y = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


def _toks(lines: list[str]) -> list[str]:
    """أسطرٌ ← رموز: السطرُ الذي يحمل رقمين («1,672,498,610   1,129,966,260») يُفصل."""
    out = []
    for l in lines:
        t = re.sub(r"\s+", " ", l).strip().lower().rstrip(":")
        parts = t.split(" ")
        if len(parts) > 1 and all(_val(x) is not None or x in ("-", "--", "—", "–") for x in parts):
            out += parts
            continue
        # «Revenue 27 116,525,214 117,736,492» — القراءةُ الضوئيةُ تضع البندَ وأرقامَه في سطرٍ واحد
        k = len(parts)
        while k > 0 and (_val(parts[k - 1]) is not None or parts[k - 1] in ("-", "--", "—", "–")):
            k -= 1
        if 0 < k < len(parts) and len(parts) - k >= 2 and re.search(r"[a-z]{3}", " ".join(parts[:k])):
            out.append(" ".join(parts[:k]))
            out += parts[k:]
        elif t:
            out.append(t)
    return out


def ocr_enabled() -> bool:
    """القراءةُ الضوئيةُ بمفتاحٍ صريح لا افتراضاً (D477).

    قِيس على خادم المالك: Tesseract بدقّة 220 على خادمٍ بذاكرة 1GB علّق الخادمَ مرّتين
    (فحصُ «Instance status» فشل) — وإلغاءُ المهمّة لا يوقف العمليةَ داخل الحاوية.
    فلا تعمل إلا بـ`SP_PDF_OCR=1` وبعد ذاكرةِ تبديلٍ تحمي النظام.
    """
    import os
    return os.environ.get("SP_PDF_OCR", "").strip() == "1"


def mem_available_mb() -> float | None:
    try:
        for line in open("/proc/meminfo", encoding="ascii"):
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024
    except Exception:                                              # noqa: BLE001
        return None
    return None


MIN_FREE_MB = 350                            # دونها لا يُفتح ملفّ PDF — الخادمُ أولى من الحصاد


def _page_text(pg, idx: int, ocr: bool = True) -> str:
    """نصُّ الصفحة — وإن كانت صورةً ممسوحةً في مقدّمة ملفٍّ سنويّ تُقرأ ضوئياً (Tesseract في الحاوية)."""
    t = pg.get_text()
    if len(t.strip()) >= 40 or idx >= 12 or not ocr or not ocr_enabled():
        return t
    try:
        tp = pg.get_textpage_ocr(language="eng", dpi=150, full=True, tessdata=_tessdata())
        return pg.get_text(textpage=tp)
    except Exception as e:                                         # noqa: BLE001
        logger.info("OCR ص{}: {}: {}", idx + 1, type(e).__name__, str(e)[:160])
        return t


def _tessdata() -> str | None:
    """مسارُ ملفّات لغات Tesseract في الحاوية — PyMuPDF لا يجده بلا TESSDATA_PREFIX."""
    import glob, os
    env = os.environ.get("TESSDATA_PREFIX")
    if env and os.path.isdir(env):
        return env
    for d in sorted(glob.glob("/usr/share/tesseract-ocr/*/tessdata")) + ["/usr/share/tessdata"]:
        if os.path.exists(os.path.join(d, "eng.traineddata")):
            return d
    return None


_PARENT = re.compile(r"^[•\-–]?\s*(?:the )?(?:equity holders|shareholders|owners) of the (?:parent|company)(?: company)?$")


def _nums_after(norm: list[str], j: int) -> list[float | None]:
    nums: list[str] = []
    for tok in norm[j:j + 5]:
        if tok in ("-", "—", "–", "--"):
            nums.append("0"); continue
        if _val(tok) is None:
            break
        nums.append(tok)
    if (len(nums) >= 3 and _NOTE.match(nums[0]) and not nums[0].startswith("0")
            and len(nums[0].replace(",", "").replace(".", "").replace(" ", "")) <= 4):
        nums = nums[1:]
    return [_val(t) for t in nums]


def _pairs(lines: list[str], keys: tuple[str, ...]) -> dict[str, tuple[float, float | None]]:
    """بنودُ الصفحة ← (الحالي، السابق).

    والبندُ قد ينكسر على سطرين أو ثلاثة («NET INCOME ATTRIBUTED TO THE SHAREHOLDERS»
    ثمّ «AFTER ZAKAT AND INCOME TAX») فيُجرَّب موصولاً. وصافي الربح العائدُ لمساهمي
    الأمّ («Attributable to: • Equity holders of the Parent») يغلب الإجماليَّ.
    """
    out: dict[str, tuple[float, float | None]] = {}
    norm = _toks(lines)
    for i, lab in enumerate(norm):
        if not lab or _val(lab) is not None:
            continue
        for span in (1, 2, 3):
            if i + span > len(norm):
                break
            parts = norm[i:i + span]
            if any(_val(x) is not None for x in parts):
                break
            joined = " ".join(parts)
            hit = None
            for key in keys:
                if key in out or not any(p.match(joined) for p in _COMP[key]):
                    continue
                hit = key
                break
            if not hit:
                continue
            vals = _nums_after(norm, i + span)
            if (not vals or vals[0] is None) and hit in ("net_income", "eps"):
                # «Attributable to: • Equity holders of the Parent» أو بنودُ ربحية السهم الفرعية
                for j in range(i + span, min(i + span + 10, len(norm))):
                    if (hit == "net_income" and _PARENT.match(norm[j])) or (
                            hit == "eps" and re.match(r"^[•\-–]?\s*net (?:\(loss\) )?(?:income|profit)(?: \(loss\))?$", norm[j])):
                        vals = _nums_after(norm, j + 1)
                        break
            if vals and vals[0] is not None:
                out[hit] = (vals[0], vals[1] if len(vals) > 1 else None)
                break
            # لا رقمَ بعده: قد يكون شطرَ بندٍ مكسورٍ على سطرين — يُجرَّب الوصل
    # الأمُّ تغلب الإجماليّ: «صافي الربح ← العائدُ إلى: • مساهمي الأمّ» — والكتلةُ
    # الكلّيةُ لا كتلةُ «العمليات المستمرّة» (قِيس: سابك 2025 تنشر الكتلتين)
    if "net_income" in keys:
        best = None
        for j, t in enumerate(norm):
            if not (_PARENT.match(t) and j >= 2 and "attributable to" in " ".join(norm[max(0, j - 3):j])):
                continue
            ctx = " ".join(norm[max(0, j - 6):j])
            if "comprehensive" in ctx:
                continue
            v = _nums_after(norm, j + 1)
            if not v or v[0] is None:
                continue
            total = "continuing" not in " ".join(norm[max(0, j - 4):j])
            if best is None or (total and not best[0]):
                best = (total, (v[0], v[1] if len(v) > 1 else None))
        if best:
            out["net_income"] = best[1]
    return out


def parse_pdf(data: bytes) -> dict:
    """ملفٌّ سنويّ ← {"periods": [الحالي، السابق], "kind", "reason"}."""
    import fitz
    try:
        doc = fitz.open(stream=bytes(data), filetype="pdf")
    except Exception as e:                                         # noqa: BLE001
        return {"periods": [], "reason": f"لا يُفتح: {type(e).__name__}"}
    head = " ".join(doc[i].get_text() for i in range(min(3, doc.page_count))).lower()
    annual = bool(re.search(r"for the year ended|as at and for the year", head)) and not re.search(
        r"(?:three|six|nine)[- ]month|interim", head)
    cur: dict = {}
    prv: dict = {}
    as_of = None
    found_pages = 0
    for idx, pg in enumerate(doc):
        text = _page_text(pg, idx, ocr=annual)          # الربعيُّ لا يُقرأ ضوئياً — السنويُّ هو المطلوب
        if found_pages and "notes to the" in text[:900].lower():
            break                                  # القوائمُ الأساسيةُ قبل الإيضاحات — وما بعدها قطاعاتٌ وأجزاء
        kind = _kind_of(text)
        if not kind:
            continue
        found_pages += 1
        as_of = as_of or _as_of(text)
        mult = _unit(text)
        got = _pairs(text.splitlines(), _KIND[kind])
        for k, (a, b) in got.items():
            if k == "ending_cash" and k in cur:
                continue
            f = 1.0 if k == "eps" else mult
            cur.setdefault(k, round(a * f, 2))
            if b is not None:
                prv.setdefault(k, round(b * f, 2))
    if not found_pages:
        return {"periods": [], "annual": annual,
                "reason": "صفحاتُ القوائم الأساسية بلا طبقةٍ نصّية (صورةٌ ممسوحة)"}
    if not as_of:
        for i in range(min(3, doc.page_count)):
            as_of = _as_of(doc[i].get_text()[:3000])
            if as_of:
                break
    if not as_of:
        return {"periods": [], "annual": annual, "reason": "لا تاريخَ للفترة في رأس القائمة"}
    y = int(as_of[:4])
    periods = []
    for p, d in ((cur, as_of), (prv, f"{y - 1}{as_of[4:]}")):
        if len(p) < 3:
            continue
        p = dict(p)
        if p.get("capex") is not None:
            p["capex"] = -abs(p["capex"])
        ni, eps = p.get("net_income"), p.get("eps")
        if ni is not None and eps and abs(eps) > 1e-9 and ni / eps > 0:
            p["shares_outstanding"] = round(ni / eps, 0)
            p["shares_source"] = "مشتقٌّ: صافي الربح ÷ ربحية السهم"
        ta, tl = p.get("total_assets"), p.get("total_liabilities")
        if ta and tl is not None and ta > 0:
            p["debt_ratio"] = round(tl / ta * 100, 2)
        if p.get("operating_cash_flow") is not None and p.get("capex") is not None:
            p["free_cash_flow"] = round(p["operating_cash_flow"] - abs(p["capex"]), 2)
        pre, fc = p.get("pretax_income"), p.get("interest_expense")
        if pre is not None and fc is not None:
            p["ebit"] = round(pre + abs(fc), 2)
        p.update({"as_of": d, "year": int(d[:4]), "source": "تداول — PDF"})
        periods.append(p)
    return {"periods": sorted(periods, key=lambda x: x["as_of"]), "annual": annual,
            "reason": None if periods else "لم يُطابَق بندٌ كافٍ في صفحات القوائم"}


def valid(p: dict, ref_shares: float | None, peer_shares: float | None = None) -> str | None:
    """سببُ رفض الفترة — أو None إن اجتازت الصمّام.

    والمرجعُ نفسُه قد يكون خاطئاً (قِيس: أسهمُ 8210 المحفوظةُ من XBRL القديم 119,458
    — بالآلاف — وصافي الربح ÷ الربحية في ملفّ 2025 = 149 مليوناً في السنتين). فإن
    اتّسق عمودا الملفّ فيما بينهما (`peer_shares` = أسهمُ العمود الآخر) والمرجعُ
    بعيدٌ عنهما بفارقٍ يقارب مضاعفَ ألفٍ، فالعطبُ في المرجع لا في الملف.
    """
    for k in ("net_income", "total_assets", "equity"):
        if p.get(k) is None:
            return f"بندٌ أساسيٌّ غائب: {k}"
    sh = p.get("shares_outstanding")
    unit_off = bool(ref_shares and sh and (any(0.5 <= sh / (ref_shares * f) <= 2 for f in (1e3, 1e-3, 1e6))
                                           or not (0.1 <= sh / ref_shares <= 10)))    # مرجعٌ مختلٌّ لا تجزئةَ أسهمٍ حقيقية
    self_ok = bool(sh and peer_shares and 0.8 <= sh / peer_shares <= 1.25)
    if ref_shares and sh and not (ref_shares / 2 <= sh <= ref_shares * 2) and not (unit_off and self_ok):
        return f"صافي الربح ÷ ربحية السهم = {sh:,.0f} سهماً والمعروف {ref_shares:,.0f} — وحدةٌ أو بندٌ خاطئ"
    ta, eq = p.get("total_assets"), p.get("equity")
    if ta and eq and not (0 < eq <= ta):
        return "حقوقُ الملكية خارجَ مجموع الأصول"
    return None


async def pdf_links(symbol: str) -> tuple[list[dict], str | None]:
    """روابطُ القوائم PDF من تبويب «القوائم المالية» — مرتّبةً من الأحدث."""
    from app.services.tadawul_http import fetch
    from app.services.tadawul_market import row_for
    from app.services.tadawul_xbrl import ORIGIN, _BASE, _NJ
    url = (row_for(symbol) or {}).get("company_url")
    if not url:
        return [], "لا رابطَ لصفحة الشركة في اللقطة"
    full = ORIGIN + url if url.startswith("/") else url
    st, page = await fetch(full)
    mb = _BASE.search(page or "")
    ep = next((m.group(0) for m in _NJ.finditer(page or "") if m.group(1) == "statementsTabData"), None)
    if st != 200 or not mb or not ep:
        return [], f"صفحةُ الشركة HTTP {st}"
    st, body = await fetch(mb.group(1).rstrip("/") + "/" + ep,
                           params={"statementType": "5", "reportType": "1", "requestLocale": "en"}, referer=full)
    out = []
    for href in re.findall(r"href=[\"']([^\"']+_En\.pdf)[\"']", body or "", re.I):
        d = re.search(r"_(\d{4}-\d{2}-\d{2})_", href)
        out.append({"url": href if href.startswith("http") else ORIGIN + href, "filed": d.group(1) if d else "",
                    "referer": full})
    out.sort(key=lambda x: x["filed"], reverse=True)
    return out, (None if out else "لا ملفَّ PDF في تبويب القوائم")


async def read_annuals(symbol: str, after_year: int, ref_shares: float | None,
                       max_files: int = 16, report: dict | None = None) -> list[dict]:
    """فتراتٌ سنويةٌ أحدثُ من `after_year` من ملفّات PDF الرسمية — مجتازةً الصمّام."""
    from app.services.tadawul_http import fetch_bytes
    links, why = await pdf_links(symbol)
    if report is not None and why:
        report[why] = report.get(why, 0) + 1
    got: dict[str, dict] = {}
    for f in links[:max_files]:
        if f["filed"] and int(f["filed"][:4]) <= after_year:
            continue
        free = mem_available_mb()
        if free is not None and free < MIN_FREE_MB:
            logger.warning("PDF {}: الذاكرةُ المتاحة {:.0f}MB دون الحدّ — يتوقّف الاستكمال", symbol, free)
            if report is not None:
                report["ذاكرةٌ غيرُ كافية"] = report.get("ذاكرةٌ غيرُ كافية", 0) + 1
            break
        try:
            st, data = await fetch_bytes(f["url"], referer=f["referer"])
        except Exception as e:                                     # noqa: BLE001
            logger.debug("PDF {} {}: {}", symbol, f["url"], e)
            continue
        if st != 200 or not data.startswith(b"%PDF"):
            continue
        r = parse_pdf(data)
        if not r.get("annual"):
            continue
        if not r["periods"] and report is not None:
            report[r["reason"]] = report.get(r["reason"], 0) + 1
        for p in r["periods"]:
            if p["year"] <= after_year or p["as_of"] in got:
                continue
            other = next((q.get("shares_outstanding") for q in r["periods"] if q is not p), None)
            bad = valid(p, ref_shares, other)
            if bad:
                if report is not None:
                    report[bad.split(":")[0]] = report.get(bad.split(":")[0], 0) + 1
                logger.info("PDF {} {} مرفوض: {}", symbol, p["as_of"], bad)
                continue
            got[p["as_of"]] = p
    return sorted(got.values(), key=lambda p: p["as_of"])
