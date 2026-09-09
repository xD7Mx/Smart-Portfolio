#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────
# شعاراتُ الشركات — **مسبارُ قياسٍ لا إصلاح**.
#
# قال المالك: «صور الشركات لا تظهر» في فرز السوق. والرموزُ التي رآها فارغةً
# (‏8020 · 8030 · 8040) **لها روابطُ في الخريطة** — فالسببُ ليس غياباً،
# وأمامنا احتمالان لا يُرجَّح بينهما بالنظر:
#   ١· الرابطُ لا يُحمَّل (‏404 · حجبٌ · مهلة) — فالفشلُ صامتٌ ويظهر فراغ
#   ٢· يُحمَّل والصورةُ **فاتحةٌ أو شبه شفّافة** — فتُرى بيضاء على الأرضية
#
# والعلاجان مختلفان تماماً: الأوّلُ يُصلح بالمصدر، والثاني بخلفيةٍ للشعار.
# فيُقاس: يُجلب كلُّ رابط، ويُقرأ حجمُه وحالتُه، وتُحسب نسبةُ البكسل الفاتح
# والشفّاف فيه.
#
#   docker exec sp_backend python /app/scripts/audit/logo_check.py
#   docker exec sp_backend python /app/scripts/audit/logo_check.py 8020 8030 8040
#
# لا يكتب شيئاً ولا يغيّر رابطاً — يقرأ ويطبع.
# ─────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
import sys
import pathlib
import urllib.request

# ══ خريطةُ الشعارات في الواجهة، والواجهةُ غيرُ مربوطةٍ في حاوية الخادم ══
# ترى الحاويةُ `backend` و`scripts` و`data` و`storage` فقط. فيُبحث عن
# الخريطة في المواضع الممكنة كلِّها، ويُقال أين بُحث إن لم تُوجد — بدل
# سطرٍ واحدٍ يقول «لم يُعثر» ولا يقول أين. ويُشغَّل من الخادم مباشرةً:
#     cd ~/Smart-Portfolio && python3 scripts/audit/logo_check.py
_HERE = pathlib.Path(__file__).resolve()
_CANDIDATES = [
    _HERE.parents[2] / "frontend/src/data/tradingviewLogos.ts",   # جذرُ المستودع
    pathlib.Path("/app/frontend/src/data/tradingviewLogos.ts"),
    pathlib.Path.home() / "Smart-Portfolio/frontend/src/data/tradingviewLogos.ts",
    pathlib.Path("/home/ubuntu/Smart-Portfolio/frontend/src/data/tradingviewLogos.ts"),
]
MAP = next((c for c in _CANDIDATES if c.exists()), _CANDIDATES[0])
UA = {"User-Agent": "Mozilla/5.0 (logo-probe)"}
SAMPLE = ["8020", "8030", "8040", "8012", "8210", "8010", "8170", "8250"]


def links() -> dict[str, str]:
    if not MAP.exists():
        print("… لم يُعثر على خريطة الشعارات. بُحث في:")
        for c in _CANDIDATES:
            print(f"     {'✔' if c.exists() else '✖'} {c}")
        print("   شغّله من جذر المستودع على الخادم مباشرةً (لا داخل الحاوية):")
        print("     cd ~/Smart-Portfolio && python3 scripts/audit/logo_check.py")
        return {}
    txt = MAP.read_text(encoding="utf-8")
    return dict(re.findall(r'"(\d{4})"\s*:\s*"([^"]+)"', txt))


_HEX = re.compile(r"#([0-9a-fA-F]{3,8})\b")
_NAMED_LIGHT = ("white", "#fff", "#ffffff")


def _lum(hex6: str) -> float:
    """إضاءةٌ نسبيةٌ تقريبيةٌ (0 أسود · 1 أبيض) — بمعامِلات الإدراك."""
    h = hex6
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    h = h[:6].ljust(6, "0")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _svg_tone(raw: bytes) -> str:
    """لونُ شعارٍ متّجهٍ (‏SVG) — بقراءة تعبئاته، بلا وسادةِ صور.

    روابطُ TradingView متّجهةٌ لا نقطية، وكان المحلّلُ يفترض PNG فيعجز عن
    كلّ رابطٍ في الخريطة. وكثيرٌ منها **أبيضُ على شفّاف** — مصمَّمٌ لأرضيةٍ
    داكنة — فيُرى كتلةً بيضاء بلا تفصيل حيث الأرضيةُ فاتحة، وهو ما يشكوه
    المالك. فتُعدّ التعبئاتُ: كم بيضاء وكم ملوّنة.
    """
    txt = raw.decode("utf-8", "replace")
    fills = [m.lower() for m in _HEX.findall(txt)]
    white = sum(1 for f in fills if f in ("fff", "ffffff", "ffffffff"))
    colored = len(fills) - white
    has_named_white = any(w in txt.lower() for w in _NAMED_LIGHT)
    if not fills and not has_named_white:
        return "لا تعبئةَ صريحة — يرث اللونَ من الصفحة (‏currentColor غالباً)"
    # ══ «ملوّن» ليست حكماً كافياً ══ (قِيس بعد تشغيل المالك)
    # عدُّ التعبئات غير البيضاء وحدَه يعدّ `#f2f2f2` لوناً وهو يكاد يكون
    # أبيض. فتُقاس **إضاءةُ** كلّ تعبئةٍ وتُطبع بقيمتها: شعارٌ كلُّ حبره
    # فوق ‎0.85 إضاءةً يُرى كتلةً باهتةً على أرضيةٍ فاتحة، وإن لم يكن
    # أبيضَ خالصاً. والرقمُ يُعرض ليُحكَم عليه لا ليُصدَّق.
    lums = sorted((round(_lum(f), 2), "#" + f) for f in set(fills))
    dark = [x for x in lums if x[0] <= 0.60]
    pale = [x for x in lums if x[0] > 0.85]
    shown = ", ".join(f"{c}({l})" for l, c in lums[:6]) or "—"
    if colored == 0 and (white or has_named_white):
        verdict = "أبيضُ خالص  ⚠ يختفي على أرضيةٍ فاتحة"
    elif not dark:
        verdict = (f"لا حبرَ داكناً — أفتحُ تعبئةٍ {lums[0][0]}"
                   "  ⚠ يُرى باهتاً على أرضيةٍ فاتحة")
    else:
        verdict = f"فيه حبرٌ داكن ({len(dark)} تعبئةً ≤0.60)"
    return f"متّجه · {verdict} · التعبئات: {shown}"


def analyse(raw: bytes) -> str:
    """نسبةُ الفاتح والشفّاف — ولل‏SVG قراءةٌ نصّيةٌ تخصّه."""
    head = raw[:400].lstrip().lower()
    if head.startswith(b"<svg") or b"<svg" in head:
        return _svg_tone(raw)
    try:
        from PIL import Image           # type: ignore
        import io
    except Exception:                                             # noqa: BLE001
        return "تعذّر التحليل (Pillow غير مثبَّت) — الحجمُ وحدَه دليل"
    try:
        im = Image.open(io.BytesIO(raw)).convert("RGBA")
        im.thumbnail((48, 48))
        px = list(im.getdata())
        n = len(px) or 1
        clear = sum(1 for r, g, b, a in px if a < 32)
        light = sum(1 for r, g, b, a in px if a >= 32 and (r + g + b) / 3 > 220)
        ink = n - clear - light
        return (f"شفّاف {clear * 100 // n}٪ · فاتحٌ جداً {light * 100 // n}٪ "
                f"· حبرٌ مرئيّ {ink * 100 // n}٪"
                + ("  ⚠ لا حبرَ يُرى على أرضيةٍ فاتحة" if ink * 100 // n < 8 else ""))
    except Exception as e:                                        # noqa: BLE001
        return f"تعذّر التحليل ({type(e).__name__})"


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    m = links()
    if not m:
        return 2
    syms = args or SAMPLE
    print(f"خريطةُ الشعارات: {len(m)} رابطاً · يُقاس {len(syms)}")
    print("─" * 74)
    ok = broken = pale = 0
    for s in syms:
        url = m.get(s)
        if not url:
            print(f"■ {s}: لا رابطَ في الخريطة")
            broken += 1
            continue
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                raw = r.read()
                code = r.status
        except Exception as e:                                    # noqa: BLE001
            print(f"■ {s}: ✖ {type(e).__name__} — {url}")
            broken += 1
            continue
        note = analyse(raw)
        if "⚠" in note:
            pale += 1
        else:
            ok += 1
        print(f"■ {s}: ‎{code} · {len(raw):,} بايت · {note}")
    print("─" * 74)
    print(f"فيها حبرٌ داكن {ok} · متعذّرة {broken} · باهتةٌ أو بيضاء {pale}")
    print("متعذّرةٌ ⇐ العلاجُ في المصدر. بيضاءُ خالصةٌ ⇐ العلاجُ أرضيةٌ داكنةٌ")
    print("ثابتةٌ تحت الشعار في المظهرين، لا تبديلُ رابط.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
