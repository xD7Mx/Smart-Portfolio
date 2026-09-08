import React from "react";

/* ══ صورتان للتوزيع تتحرّكان مع الجدول ══ (بأمر المالك · D191)

   الجدولُ يقول الأرقام، ولا يقول **الشكل**: أين ثِقلُ المحفظة، وهل هي
   متكوّمةٌ في قطاعٍ واحد. فصورتان بجانبه:
     · القطاعات — نصيبُ كلّ قطاعٍ من التوزيع.
     · الشركات  — وزنُ كلّ شركةٍ منسوباً إلى أكبرها.

   وسويتشٌ واحدٌ يحكمهما: **حالي** يقرأ القيمةَ السوقية، و**مستهدف** يقرأ
   الأوزانَ المكتوبة في الحقول الآن — فتتحرّك الصورةُ مع كلّ رقمٍ يُكتب
   قبل الحفظ، كبقيّة أرقام البطاقة.

   ولا مكتبةَ رسمٍ هنا: شرائطُ نسبٍ وقوسٌ مرسومٌ بـ`conic-gradient`. أخفُّ
   من حزمةٍ كاملة، ويتبع رموزَ المظهرين بلا شرط. */

/* لوحةٌ تكفي القطاعاتِ كلَّها: خمسةُ رموزِ الرسوم ثم درجاتٌ منها بشفافيةٍ
   نازلة — فلا قطاعَ يُطوى تحت «أخرى» بأمر المالك، ولا لونَ يتكرّر متجاوراً. */
const BASE = ["var(--chart-1)", "var(--chart-3)", "var(--chart-5)",
              "var(--chart-4)", "var(--chart-2)"];
const paletteAt = (i: number) => {
  const c = BASE[i % BASE.length];
  const tier = Math.floor(i / BASE.length);
  return tier === 0 ? c : `color-mix(in srgb, ${c} ${Math.max(28, 100 - tier * 26)}%, var(--surface))`;
};

export type AllocRow = {
  company_id: number; name: string; symbol: string;
  sector?: string | null; market_value?: number | null;
};

function pct(part: number, whole: number) {
  return whole > 0 ? (part / whole) * 100 : 0;
}

/** يجمع الأوزانَ بالقطاع — **كلَّ** قطاعٍ بلا طيّ. كان الذيلُ يُضمّ في
 *  «أخرى» فيختفي عن العين ما قد يكون ثُلثَ المحفظة، وقد أمر المالكُ بذكر
 *  الجميع. */
function bySector(rows: AllocRow[], weightOf: (r: AllocRow) => number) {
  const map = new Map<string, number>();
  let total = 0;
  for (const r of rows) {
    const w = Math.max(0, weightOf(r));
    if (w <= 0) continue;
    const k = r.sector || "غير مصنّف";
    map.set(k, (map.get(k) || 0) + w);
    total += w;
  }
  const parts = [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([k, v], i) => ({ key: k, value: v, color: paletteAt(i) }));
  return { parts, total };
}

export default function AllocationCharts(
  { rows, currentOf, targetOf }:
  { rows: AllocRow[];
    currentOf: (r: AllocRow) => number;
    targetOf: (r: AllocRow) => number },
) {
  const [mode, setMode] = React.useState<"current" | "target">("current");
  const weightOf = mode === "current" ? currentOf : targetOf;

  const { parts, total } = bySector(rows, weightOf);
  const companies = rows
    .map(r => ({ r, w: Math.max(0, weightOf(r)) }))
    .filter(x => x.w > 0)
    .sort((a, b) => b.w - a.w);
  const top = companies.length ? companies[0].w : 0;

  if (!total) {
    return (
      <div className="text-[11.5px] text-[var(--ink-muted)] py-3">
        {mode === "target" ? "لا أوزانَ مستهدفة بعد" : "لا قيمَ سوقية بعد"}
      </div>
    );
  }

  /* قوسُ القطاعات: زوايا متتالية من النسب نفسِها — لا حسابَ ثانٍ. */
  let acc = 0;
  const stops = parts.map(p => {
    const from = acc;
    acc += pct(p.value, total);
    return `${p.color} ${from.toFixed(2)}% ${acc.toFixed(2)}%`;
  }).join(", ");

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <p className="text-[10px] font-bold tracking-[0.06em] text-[var(--ink-muted)]">
          صورةُ التوزيع
        </p>
        {/* مبدّلٌ بلغة التطبيق نفسِها — لا تصميمٌ ثالثٌ لهذه البطاقة (D202). */}
        <div className="seg inline-flex w-fit">
          {([["current", "الحالي"], ["target", "المستهدف"]] as const).map(([k, label]) => (
            <button key={k} onClick={() => setMode(k)} aria-pressed={mode === k}
              className={"seg-btn whitespace-nowrap" + (mode === k ? " on" : "")}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 items-start">
        {/* ── القطاعات ── */}
        {/* الحلقةُ بحجم البطاقة لا رقعةً صغيرة (بأمر المالك): تتمدّد إلى
            عرض عمودها وتُسقَف كي لا تبتلع الشاشة على الحاسوب. */}
        <div className="flex flex-col sm:flex-row items-center gap-4">
          <div className="shrink-0 rounded-full w-full" style={{
            maxWidth: 220, aspectRatio: "1 / 1",
            background: `conic-gradient(${stops})`,
            /* ثقبٌ في الوسط: الحلقةُ تُقرأ نسباً، والقرصُ المصمت يُقرأ كتلة. */
            WebkitMask: "radial-gradient(circle, transparent 46%, #000 47%)",
            mask: "radial-gradient(circle, transparent 46%, #000 47%)",
          }} />
          <div className="min-w-0 space-y-1">
            {parts.map(p => (
              <div key={p.key} className="flex items-center gap-1.5 text-[11px]">
                <span className="shrink-0 rounded-sm" style={{ width: 8, height: 8, background: p.color }} />
                <span className="text-[var(--ink)] truncate">{p.key}</span>
                <span className="tabular-nums text-[var(--ink-muted)] ms-auto" dir="ltr">
                  {pct(p.value, total).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* ── الشركات: كلُّها، ومن طالت قائمتُه فالبطاقةُ تمرّر ── */}
        <div className="space-y-1.5 max-h-[260px] overflow-y-auto pe-1">
          {companies.map(({ r, w }) => (
            <div key={r.company_id} className="flex items-center gap-2 text-[11px]">
              <span className="text-[var(--ink)] truncate" style={{ width: "38%" }}>{r.name}</span>
              <span className="flex-1 h-1.5 rounded-full" style={{ background: "var(--surface)" }}>
                <span className="block h-1.5 rounded-full"
                      style={{ width: `${top > 0 ? (w / top) * 100 : 0}%`,
                               background: "var(--brand-ink)" }} />
              </span>
              <span className="tabular-nums text-[var(--ink-muted)] shrink-0" dir="ltr"
                    style={{ width: 44, textAlign: "end" }}>
                {pct(w, total).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
