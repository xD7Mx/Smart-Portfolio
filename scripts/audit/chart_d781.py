#!/usr/bin/env python3
"""حارسُ D781 — الرسمُ كتريدنق فيو: «+» يضيف ما في الرسم إلى القائمة، وسهمُ الطيّ لأسماء المؤشّرات، والضغطُ على المؤشّر يفتح إعداداته (2026-11-21).

قال المالك: «ضع علامةَ زائدٍ في الرسم — ما يظهر عليه، عقداً أو سهماً، يُضاف إلى القائمة المفتوحة… وبجانب أسماء المؤشّرات العينُ في اليمين،
أبغى في اليسار سهماً يُخفي اسمَ المؤشّر بالكامل مثل تريدنق فيو — يختفي أو ينطوي… وعندما أضغط على المؤشّر نفسِه داخل الرسم تظهر إعداداتُه».
والسلوكُ في المتصفّح يقيسه ‏pro_chart_d736.mjs (١٢هـ)؛ وهذا يحرس الأوصال.

    python3 scripts/audit/chart_d781.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
fail = 0


def check(ok, label):
    global fail
    if not ok:
        fail = 1
    print(f"{'PASS' if ok else 'FAIL'} {label}")


pc = (ROOT / "frontend/src/components/chart/ProChart.tsx").read_text(encoding="utf-8")
tr = (ROOT / "frontend/src/components/market/TradeRoom.tsx").read_text(encoding="utf-8")
css = (ROOT / "frontend/src/styles/globals.css").read_text(encoding="utf-8")
click = (re.search(r"const onClick = \(p: MouseEventParams\) => \{[\s\S]*?\n {4}\};", pc) or [""])[0]
check('data-role="pc-fold"' in pc and 'data-role="pc-fold-n"' in pc and 'data-role="pc-fold-pane"' in pc and 'lsSet("sp_chart_legfold"' in pc
      and "{!legFold && <>" in pc and "[paneTops, legFold]" in pc,
      "١ سهمُ الطيّ في يسار وسيلة الإيضاح يطوي أسماءَ المؤشّرات (ويُبقي عددَها) في اللوحة الرئيسة ولوحات المذبذبات — ويُحفظ، وتُملأ القيمُ بعد فكّه")
check('data-role="pc-chip-cfg"' in pc and "chart.subscribeClick(onClick)" in pc and "e.series.includes(hit as any)" in click and "openCfgRef.current(k)" in click
      and not re.search(r"draw", click, re.I) and 'if (k === "d7m") setShowCfg(true)' in pc,
      "٢ الضغطُ على المؤشّر — اسمِه في وسيلة الإيضاح أو خطِّه في الرسم — يفتح إعداداته (‏D7M · Stoch RSI · CVD)، ولا شأنَ لنقرة المكتبة بالرسم")
check('data-role="troom-add"' in tr and 'data-role="troom-add-menu"' in tr and 'data-role="troom-inlist"' in tr and 'data-role="troom-added"' in tr
      and "marketApi.watchAdd(symbol, nameOf(symbol), g)" in tr and "gid != null ? addTo.mutate(gid) : setAddMenu" in tr,
      "٣ «+» في رأس الرسم يضيف ما عليه (سهماً أو عقداً) إلى القائمة المفتوحة — وإن كانت «محفظتي» أو «المؤشرات» فقوائمُك تختار منها، و«أُضيف» تأكيداً، "
      "وما في القائمة عليه علامة")
check(".pc-chip-name {" in css and "min-width: 32px; min-height: 32px; margin: -8px 0" in css and ".pc-fold {" in css and ".troom-plus {" in css,
      "٤ أهدافُ اللمس الجديدة ≥ 32px دون أن تكبر وسيلةُ الإيضاح")
print("\nالنتيجة:", "نظيف ✔" if not fail else "فشل ✘")
sys.exit(fail)
