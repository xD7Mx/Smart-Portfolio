import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marketApi } from "../../services/api";
import { lookupCompany } from "../../data/saudiCompanies";

/* ══ القيمةُ العادلة متعدّدةُ النماذج (D468) ══
   نماذجُ ثلاث عائلاتٍ بنطاقاتها وافتراضاتها، وأقرانٌ من قطاع «تداول» الرسميّ،
   والمرجّحُ وسيطُ كلّ عائلةٍ بوزن نمط الشركة. كلُّ رقمٍ يُفتح على أصله. */

const fmt = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(2));

/* ══ شريطُ النطاق بتصميم شريط السلامة (بأمر المالك · D485) ══
   مسارٌ رفيعٌ مدوَّر، والنطاقُ ممتلئٌ بلون الحكم، ودائرةٌ بيضاءُ للقيمة،
   وخطٌّ رفيعٌ للسعر — لا مثلثاتٌ ولا أرقامٌ معلّقةٌ فوق الشريط. */
function RangeRow({ title, meta, low, high, mark, price }: {
  title: string; meta?: string; low: number; high: number; mark?: number | null; price: number;
}) {
  const lo = Math.min(low, high, price, mark ?? low), hi = Math.max(low, high, price, mark ?? high);
  const span = hi - lo || 1;
  const at = (v: number) => ((v - lo) / span) * 100;
  const fill = mark == null ? "var(--ink-muted)" : mark >= price ? "var(--gauge-pos)" : "var(--gauge-neg)";
  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline gap-2">
        <span className="flex-1 text-[13px] font-bold text-[var(--ink)]">{title}</span>
        {meta && <span className="text-[11px] text-[var(--ink-muted)]">{meta}</span>}
        {mark != null && <span className="text-[13px] font-bold tabular-nums text-[var(--ink)]">{fmt(mark)}</span>}
      </div>
      <div className="relative h-3" dir="ltr">
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-1.5 rounded-full bg-[var(--surface)]" />
        <div className="absolute top-1/2 -translate-y-1/2 h-1.5 rounded-full"
             style={{ left: `${at(Math.min(low, high))}%`, width: `${(Math.abs(high - low) / span) * 100}%`, background: fill }} />
        <div className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-[2px] h-3 bg-[var(--ink)]"
             style={{ left: `${at(price)}%` }} title={`السعر ${fmt(price)}`} />
        {mark != null && (
          <div className="absolute top-1/2 rounded-full" style={{ left: `${at(mark)}%`, width: 12, height: 12,
               transform: "translate(-50%, -50%)", background: "#ffffff", border: "1px solid var(--hairline)" }} />
        )}
      </div>
      <div className="flex justify-between text-[11px] tabular-nums text-[var(--ink-muted)]" dir="ltr">
        <span>{fmt(Math.min(low, high))}</span><span>{fmt(Math.max(low, high))}</span>
      </div>
    </div>
  );
}

function ModelRow({ m, price }: { m: any; price: number }) {
  const [open, setOpen] = useState(false);
  const up = m.value >= price;
  return (
    <div className="border-b border-[var(--hairline)] last:border-0">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open}
              className="w-full min-h-[32px] flex items-center gap-2 py-2 text-right">
        <span className="flex-1 text-[13px] text-[var(--ink)]">{m.name}</span>
        <span className="text-[11px] tabular-nums text-[var(--ink-muted)]" dir="ltr">{fmt(m.low)}–{fmt(m.high)}</span>
        <span className={"min-w-[52px] text-center rounded-md px-2 py-0.5 text-[13px] font-bold tabular-nums bg-[var(--surface)] "
          + (up ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>{fmt(m.value)}</span>
      </button>
      {open && (
        <table className="w-full mb-3 text-[12px]">
          <thead>
            <tr className="text-[var(--ink-muted)] bg-[var(--surface)]">
              <th className="text-right font-bold p-2">الافتراض</th>
              <th className="text-right font-bold p-2">القيمة</th>
              <th className="text-right font-bold p-2">المدى والمصدر</th>
            </tr>
          </thead>
          <tbody>
            {(m.assumptions || []).map((a: any[], k: number) => (
              <tr key={k} className="border-t border-[var(--hairline)]">
                <td className="p-2 text-[var(--ink)]">{a[0]}</td>
                <td className="p-2 tabular-nums text-[var(--ink)]" dir="ltr" style={{ textAlign: "right" }}>{a[1]}</td>
                <td className="p-2 text-[var(--ink-muted)]">{a[2] || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function FairValuePanel({ symbol, analystTarget, week52 }: {
  symbol: string; analystTarget?: number | null; week52?: { low?: number | null; high?: number | null };
}) {
  const sym = symbol.replace(".SR", "");
  const { data: r, isLoading } = useQuery({
    queryKey: ["fvm", sym],
    queryFn: () => marketApi.fairValueModels(sym).then(x => x.data?.data || null),
    staleTime: 30 * 60 * 1000,
  });
  if (isLoading) return <div className="h-64 skeleton rounded-xl" />;
  if (!r || r.value == null) {
    return <div className="py-10 text-center text-sm text-[var(--ink-muted)]">{r?.reason || "لم تكتمل مدخلاتُ النماذج لهذه الورقة من الإفصاح الرسميّ."}</div>;
  }
  const price = r.price as number;
  const up = r.upside as number;
  const byFam: Record<string, any[]> = {};
  (r.models || []).forEach((m: any) => { (byFam[m.family] = byFam[m.family] || []).push(m); });
  const famName: Record<string, string> = { cashflow: "التدفّقات المخصومة", equity: "الأرباح والحقوق", income: "التوزيعات", multiples: "مضاعفاتُ الأقران السعوديين" };
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="card p-3 space-y-1">
          <div className="text-[11px] text-[var(--ink-muted)]">القيمة العادلة اليوم</div>
          <div className={"text-lg font-bold tabular-nums " + (up >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>{fmt(r.value)}</div>
        </div>
        <div className="card p-3 space-y-1">
          <div className="text-[11px] text-[var(--ink-muted)]">الهدف لاثني عشر شهراً</div>
          <div className={"text-lg font-bold tabular-nums " + ((r.target_12m_upside ?? 0) >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")}>{fmt(r.target_12m)}</div>
        </div>
        <div className="card p-3 space-y-1">
          <div className="text-[11px] text-[var(--ink-muted)]">البعد عن السعر</div>
          <div className={"text-lg font-bold tabular-nums " + (up >= 0 ? "text-[var(--pos-ink)]" : "text-[var(--neg-ink)]")} dir="ltr" style={{ textAlign: "right" }}>
            {up >= 0 ? "+" : ""}{up.toFixed(1)}%
          </div>
        </div>
        <div className="card p-3 space-y-1">
          <div className="text-[11px] text-[var(--ink-muted)]">عدم اليقين</div>
          <div className="text-lg font-bold text-[var(--ink)]">{r.uncertainty}</div>
        </div>
      </div>

      <div className="card p-4 space-y-5">
        {week52?.low != null && week52?.high != null && (
          <RangeRow title="نطاق السوق" meta="52 أسبوعاً" low={week52.low} high={week52.high} mark={price} price={price} />
        )}
        {analystTarget != null && (
          <RangeRow title="هدف المحللين" meta="الإجماع" low={Math.min(analystTarget, price)} high={Math.max(analystTarget, price)}
                    mark={analystTarget} price={price} />
        )}
        <RangeRow title="نماذجنا" meta={`${r.count} نموذجاً`} low={r.low} high={r.high} mark={r.value} price={price} />
      </div>

      <div className="card p-4 space-y-2">
        <div className="text-[13px] font-bold text-[var(--ink)]">العائلات ووزنها</div>
        {r.model_set && <div className="text-[12px] text-[var(--brand-ink)]">{r.model_set}</div>}
        {(r.families || []).map((f: any) => (
          <div key={f.family} className="flex items-center gap-2 min-h-[32px] text-[13px]">
            <span className="flex-1 text-[var(--ink)]">{f.name}</span>
            <span className="text-[11px] text-[var(--ink-muted)] tabular-nums">{Math.round(f.weight * 100)}%{f.models ? ` · ${f.models} نماذج` : ""}</span>
            <span className="min-w-[52px] text-center font-bold tabular-nums text-[var(--ink)]">{fmt(f.value)}</span>
          </div>
        ))}
        {(r.notes || []).map((n: string, k: number) => (
          <p key={k} className="text-[12px] leading-relaxed text-[var(--warn-ink)]">{n}</p>
        ))}
      </div>

      {Object.entries(byFam).map(([fam, ms]) => (
        <div key={fam} className="card p-4">
          <div className="text-[13px] font-bold text-[var(--ink)] mb-1">{famName[fam] || fam}</div>
          {ms.map((m: any) => <ModelRow key={m.key} m={m} price={price} />)}
        </div>
      ))}

      {(r.excluded || []).length > 0 && (
        <div className="card p-4 space-y-1.5">
          <div className="text-[13px] font-bold text-[var(--ink)]">نماذجُ استُبعدت</div>
          {r.excluded.map((e: any) => (
            <div key={e.key} className="text-[12px] text-[var(--ink-muted)]">
              <span className="text-[var(--ink)]">{e.name}</span> · {fmt(e.value)} — {e.excluded}
            </div>
          ))}
        </div>
      )}

      {(r.peers || []).length > 0 && (
        <div className="card p-4 space-y-2">
          <div className="text-[13px] font-bold text-[var(--ink)]">الأقران · {r.sector}</div>
          <div className="flex flex-wrap gap-1.5">
            {r.peers.map((p: string) => (
              <span key={p} className="rounded-md px-2 py-1 text-[12px] bg-[var(--surface)] text-[var(--ink)]">
                {lookupCompany(p)?.name_ar || p} <span className="text-[var(--ink-muted)] tabular-nums">{p}</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
