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
open(sc_path, "w", encoding="utf-8").write(
'''/**
 * Tadawul companies directory — GENERATED from the single source of truth
 * backend/app/data/saudi_directory.json (name + sector + logo). Do not edit
 * by hand: regenerate so the frontend can NEVER drift from the backend
 * governance directory. One directory, called across the whole site.
 */
export interface SaudiCompany { symbol: string; name_ar: string; name_en: string; sector: string }

export const SAUDI_COMPANIES: SaudiCompany[] = [
''' + lines + '''
];

const norm = (s: string) => (s || "").toLowerCase().replace(/[أإآ]/g, "ا").trim();

export function searchCompanies(q: string, limit = 8): SaudiCompany[] {
  const n = norm(q);
  if (!n) return [];
  return SAUDI_COMPANIES.filter(c =>
    c.symbol.startsWith(n) ||
    norm(c.name_ar).includes(n) ||
    c.name_en.toLowerCase().includes(n)
  ).slice(0, limit);
}

export function lookupCompany(symbol: string): SaudiCompany | undefined {
  return SAUDI_COMPANIES.find(c => c.symbol === (symbol || "").trim());
}
''')
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
