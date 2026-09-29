"""
Regenerate the frontend directories from the single backend source of truth
(backend/app/data/saudi_directory.json) so the frontend can never drift from
the backend governance directory. Run after editing saudi_directory.json:

    python scripts/gen_frontend_directory.py

Writes: frontend/src/data/saudiCompanies.ts  (symbol/name_ar/name_en/sector)
        frontend/src/data/tradingviewLogos.ts (symbol -> logo url)
name_en is preserved from the existing saudiCompanies.ts where available.
"""
import json, re, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "backend/app/data/saudi_directory.json"), encoding="utf-8"))
sc_path = os.path.join(ROOT, "frontend/src/data/saudiCompanies.ts")
tv_path = os.path.join(ROOT, "frontend/src/data/tradingviewLogos.ts")

name_en = dict(re.findall(
    r'symbol:\s*"(\d+)",\s*name_ar:\s*"[^"]*",\s*name_en:\s*"([^"]*)"',
    open(sc_path, encoding="utf-8").read()))

esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
recs = [(s, d[s]["name"], name_en.get(s, ""), d[s].get("sector") or "")
        for s in sorted(d, key=lambda x: (d[x].get("sector") or "zz", x)) if d[s].get("name")]
lines = "\n".join(f'  {{ symbol: "{s}", name_ar: "{esc(na)}", name_en: "{esc(ne)}", sector: "{esc(se)}" }},'
                  for s, na, ne, se in recs)
# ══ يُستبدَل مصفوفُ الشركات وحدَه (D515) ══ كان السكربتُ يعيد كتابةَ الملفّ كاملاً
# بنسخةٍ قديمةٍ منه، فأسقط `norm` المُصدَّرةَ وما أُضيف بعده — وتوقّفت الواجهةُ كلُّها
# عن الرسم (قِيس في لجنة كشف الأعطال). فيبقى ما حول المصفوف كما هو.
_src = open(sc_path, encoding="utf-8").read()
_m = re.search(r"(export const SAUDI_COMPANIES: SaudiCompany\[\] = \[\n)(.*?)(\n\];)", _src, re.S)
assert _m, "لم يُعثر على مصفوف SAUDI_COMPANIES"
open(sc_path, "w", encoding="utf-8").write(_src[:_m.start(2)] + lines + _src[_m.end(2):])
logos = "\n".join(f'  "{s}": "{d[s]["logo"]}",' for s in sorted(d) if d[s].get("logo"))
open(tv_path, "w", encoding="utf-8").write(
'''// GENERATED from the single source of truth backend/app/data/saudi_directory.json.
// Real verified TradingView CDN logos — do not edit by hand; regenerate so the
// frontend logo map never drifts from the backend directory. Used by CompanyLogo.
export const TV_LOGOS: Record<string, string> = {
''' + logos + '''
};
''')
print(f"regenerated: {len(recs)} companies, {logos.count(chr(10))+1} logos")
