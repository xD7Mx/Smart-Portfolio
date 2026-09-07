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

const PALETTE = ["var(--chart-1)", "var(--chart-3)", "var(--chart-5)",
                 "var(--chart-4)", "var(--chart-2)"];
const REST = "var(--ink-muted)";

export type AllocRow = {
  company_id: number; name: string; symbol: string;
  sector?: string | null; market_value?: number | null;
};

function pct(part: number, whole: number) {
  return whole > 0 ? (part / whole) * 100 : 0;
}

/** يجمع الأوزانَ بالقطاع، ويضمّ الذيلَ في «أخرى» كي لا تصير الصورةُ قائمة. */
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
  const sorted = [...map.entries()].sort((a, b) => b[1] - a[1]);
  const head = sorted.slice(0, 5);
  const tailSum = sorted.slice(5).reduce((s, [, v]) => s + v, 0);
  const parts = head.map(([k, v], i) => ({ key: k, value: v, color: PALETTE[i] }));
  if (tailSum > 0) parts.push({ key: `أخرى (${sorted.length - 5})`, value: tailSum, color: REST });
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
        {/* سويتشٌ باسمين كما طلب المالك: حالي · مستهدف. */}
        <div className="inline-flex rounded-lg overflow-hidden"
             style={{ border: "1px solid var(--hairline)" }}>
          {([["current", "حالي"], ["target", "مستهدف"]] as const).map(([k, label]) => (
            <button key={k} onClick={() => setMode(k)}
              className="px-2.5 py-1 text-[11px] font-semibold transition-colors"
              style={mode === k
                ? { background: "var(--brand-ink)", color: "var(--bg)" }
                : { background: "transparent", color: "var(--ink-muted)" }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-start">
        {/* ── القطاعات ── */}
        <div className="flex items-center gap-3">
          <div className="shrink-0 rounded-full" style={{
            width: 84, height: 84,
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

        {/* ── الشركات ── */}
        <div className="space-y-1.5">
          {companies.slice(0, 8).map(({ r, w }) => (
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
          {companies.length > 8 && (
            <p className="text-[10px] text-[var(--ink-muted)]">
              و{companies.length - 8} شركةً أخرى
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
