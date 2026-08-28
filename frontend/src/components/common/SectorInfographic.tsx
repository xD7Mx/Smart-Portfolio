import React, { useState } from "react";

/**
 * Sector-distribution infographic — shared identically by the Dashboard
 * widget and the Portfolio page. A flat treemap: the largest sector gets
 * its own full-height block, the rest stack into up to two columns in
 * their original (descending) order — a fixed, simple grid that always
 * stays inside its own box (plain flex percentages, no measurement, no
 * overflow). Sector names + percentages sit in a wrapped legend row below
 * it, and are also always shown directly inside each cell.
 */
// Same palette Governance's dividend columns and sector-tube charts already
// use — one shared identity across every chart in the site, instead of a
// separately-tuned set. A couple of pairs (indigo/purple) sit in the
// borderline 8-12 ΔE band under `--pairs all`, which the dataviz skill
// treats as acceptable ONLY when a secondary encoding (a direct, always-on
// label) also identifies each slice — which every cell here always has.
/* لوحةُ تمييزٍ بين القطاعات — لا دلالةَ ربحٍ وخسارة (انظر COMPO_COLORS). */
/* ══ ألوان القطاعات: من عائلة الرسوم وحدها ══
   كانت تخلط رموز الرسوم برموز **دلالية**: `--pos-ink` و`--neg-ink`
   و`--warn-ink`. وهذا خطأٌ في المعنى قبل الذوق — يجعل قطاعاً يبدو «ربحاً»
   وآخرَ «خسارة»، والقطاع ليس ربحاً ولا خسارة بل هويّة. ومن أثره أن ظهرت
   في المربّعات درجاتٌ صارخة (أصفرُ تحذيرٍ وأحمرُ خسارة) لا صلة لها بهويّة
   التطبيق — وهو ما وصفه المالك بالقبح.
   والعائلة السبعة تكفي وتزيد، وكلّها من مرساةٍ واحدة. */
export const SECTOR_COLORS = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)",
  "var(--chart-5)", "var(--chart-6)", "var(--chart-7)",
];

export interface SectorSlice { name: string; value: number; pct: number }

export function buildSectorData(rows: { sector?: string | null; value: number }[]): SectorSlice[] {
  const map: Record<string, number> = {};
  rows.forEach(({ sector, value }) => {
    const s = sector || "غير مصنف";
    map[s] = (map[s] || 0) + (value || 0);
  });
  const total = Object.values(map).reduce((a, b) => a + b, 0);
  return Object.entries(map)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value, pct: total ? (value / total) * 100 : 0 }))
    .sort((a, b) => b.value - a.value);
}

const fmt0 = (n: number) => (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });

interface Item extends SectorSlice { colorIdx: number }

/** [first item alone] + the rest split (by order, not value) into up to two
 * more columns — the exact grid confirmed against the approved mockup. */
function makeColumns(items: Item[]): Item[][] {
  if (items.length <= 1) return [items];
  const [first, ...rest] = items;
  if (rest.length <= 3) return [[first], rest];
  const mid = Math.ceil(rest.length / 2);
  return [[first], rest.slice(0, mid), rest.slice(mid)];
}

function Cell({ d, hover, setHover }: { d: Item; hover: number | null; setHover: (i: number | null) => void }) {
  const isHover = hover === d.colorIdx;
  const color = SECTOR_COLORS[d.colorIdx % SECTOR_COLORS.length];
  return (
    <div
      className="relative min-w-0 min-h-0 transition-transform duration-200 ease-out"
      style={{
        flexGrow: d.pct, flexBasis: 0,
        background: color,
        borderRadius: 10,
        transform: isHover ? "translateY(-2px)" : undefined,
      }}
      onMouseEnter={() => setHover(d.colorIdx)}
      onMouseLeave={() => setHover(null)}
    >
      {/* ══ سِتارٌ تحت التسمية ══
          كان النصّ يقرأ `--ink` — أي **أسودَ** في المظهر الفاتح، بينما
          التعليق فوقه يقول إنه «يجب أن يبقى أبيضَ دائماً». فالشيفرة تنقض
          تعليقها، وهو العطب نفسه الذي أوقع «نمو العائد» في رقمين.
          ولم يكن الحلّ تبييضَه وحده: قِيس الأبيض على ألوان المربّعات فهبط
          إلى 2.15:1 على الكهرمانيّ و2.43 على السماويّ — أي نصٌّ لا يُقرأ.
          فالسِتار هو الحلّ: تدرّجٌ أسودُ ٤٠٪ يعمّق أسفل المربّع حيث تجلس
          التسمية وحدها، فيصعد الأبيض إلى 5.41:1 في أسوأ لونٍ في اللوحة
          و12.22 في أفضلها — بلا أن يُمسّ لون المربّع نفسه ولا معناه. */}
      <div className="absolute inset-x-0 bottom-0 h-[46%] pointer-events-none"
           style={{ background: "linear-gradient(to top, rgba(0,0,0,.40), rgba(0,0,0,0))" }} />
      <div className="absolute bottom-1.5 inset-x-2 leading-tight">
          <div className="sector-cell-label font-bold truncate" style={{ fontSize: 10.5 }}>{d.name}</div>
          <div className="sector-cell-label font-extrabold" style={{ fontSize: 12, opacity: 0.95 }}>{d.pct.toFixed(1)}%</div>
        </div>
    </div>
  );
}

export default function SectorInfographic({ data, size = 140 }: { data: SectorSlice[]; size?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  if (!data.length) return null;
  const items: Item[] = data.map((d, i) => ({ ...d, colorIdx: i }));
  const columns = makeColumns(items);

  return (
    <div className="flex flex-col w-full h-full">
      <div className="flex-1 min-h-0 flex flex-col gap-2">
        <span className="text-[11px] text-[var(--ink-muted)] leading-none text-center shrink-0">
          <b className="text-[var(--ink)] text-base font-extrabold">{data.length}</b> {data.length === 1 ? "قطاع" : "قطاعات"}
        </span>
        <div className="relative flex-1 min-h-0 flex gap-[3px] overflow-hidden">
          {columns.map((col, ci) => (
            col.length === 1 ? (
              <div key={ci} className="flex min-w-0 min-h-0" style={{ flexGrow: col[0].pct, flexBasis: 0 }}>
                <Cell d={col[0]} hover={hover} setHover={setHover} />
              </div>
            ) : (
              <div key={ci} className="flex flex-col gap-[3px] min-w-0 min-h-0" style={{ flexGrow: col.reduce((a, d) => a + d.pct, 0), flexBasis: 0 }}>
                {col.map(d => <Cell key={d.name} d={d} hover={hover} setHover={setHover} />)}
              </div>
            )
          ))}

          {hover !== null && (
            <div
              className="absolute z-10 rounded-xl px-3 py-2 text-xs pointer-events-none whitespace-nowrap top-1 start-1"
              style={{ background: "var(--bg)", border: "1px solid var(--field-line)" }}
            >
              <p className="text-[var(--ink)] font-bold mb-0.5">{data[hover].name}</p>
              <p className="text-[var(--ink-muted)]">{fmt0(data[hover].value)} ﷼ · {data[hover].pct.toFixed(1)}%</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
