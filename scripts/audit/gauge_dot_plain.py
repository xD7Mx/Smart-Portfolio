#!/usr/bin/env python3
"""دائرةُ الأشرطة بيضاءُ ثابتة، وزرُّ العملية علامةُ زائدٍ وحدَها (D456).

    python3 scripts/audit/gauge_dot_plain.py

قال المالك: «ألغِ وهجَ الدائرة واجعلها بيضاءَ طوالَ الوقت بلا توهّجٍ أو
وميض، وعمّمه على كلّ الأشرطة من هذا النوع» و«زرُّ عملية جديدة: احذف الكلام
وضع علامةَ زائدٍ فقط… موازيةً للقطاع ورمز الشركة».
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
vb = (ROOT / "frontend/src/components/common/ValueBars.tsx").read_text(encoding="utf-8")
cp = (ROOT / "frontend/src/pages/CompanyPage.tsx").read_text(encoding="utf-8")
m = re.search(r"function Marker\(.*?\n}\n", vb, re.S)
blk = m.group(0) if m else ""
fail = 0
def check(ok, label):
    global fail
    fail |= not ok
    print(f"{'PASS' if ok else 'FAIL'} {label}")
check(bool(blk), "٠ دائرةُ الأشرطة مكوّنٌ واحدٌ مشترك")
check("animate-pulse" not in blk and "blur(" not in blk, "١ بلا وهجٍ ولا وميض")
check("#ffffff" in blk.lower(), "٢ بيضاءُ طوالَ الوقت")
check(len(re.findall(r"absolute rounded-full", vb)) == 1, "٣ ولا دائرةَ ثانيةً بطبقة وهجٍ في أيّ شريط")
btn = re.search(r"onClick=\{\(\) => setShowTx\(true\)\}.*?</button>", cp, re.S)
check(bool(btn) and "عملية جديدة</" not in (btn.group(0) if btn else "") and "<Plus" in (btn.group(0) if btn else ""),
      "٤ زرُّ العملية علامةُ زائدٍ بلا نصّ")
print(("FAIL" if fail else "PASS") + " D456 — الدائرةُ والزرّ")
sys.exit(fail)
