import React from "react";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { CalendarClock, Coins } from "lucide-react";
import { marketApi } from "../../services/api";

/* لصقُ لاحقةٍ ستّ عشرية على اللون (`${color}33`) يعمل مع قيمةٍ ثابتة فقط،
   ويبطل تماماً إن كان اللون رمزاً (`var(--pos-ink)33` غير صالح) فيسقط
   الخلفية أو الحدّ بلا أثر. هذه تُنتج الشفافية بطريقةٍ تقبل الاثنين. */
const mixA = (c: string, pct: number) => `color-mix(in srgb, ${c} ${pct}%, transparent)`;


const fmt = (n: number) => (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/**
 * Company dividend profile — distribution frequency, last-10-years history,
 * and an upcoming/last-distribution note. Real data from Yahoo, cached 24h.
 */
export default function DividendProfile({ symbol }: { symbol: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["dividend-profile", symbol],
    queryFn: () => marketApi.dividends(symbol).then(r => r.data.data),
    enabled: !!symbol,
    retry: 0,
  });

  if (isLoading) return <div className="card"><div className="h-32 skeleton" /></div>;
  if (!data || (!data.yearly?.length && !data.note)) return (
    <div className="card"><div className="py-8 text-center text-[var(--ink-muted)] text-sm">
      لا توجد بيانات توزيعات معلنة لهذا الرمز حالياً — تُجلب تلقائياً عند توفرها من المصدر
    </div></div>
  );

  const noteColor = data.note?.type === "upcoming" ? "var(--pos-ink)" : data.note?.type === "today" ? "var(--warn-ink)" : "var(--ink-muted)";

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Coins size={15} className="text-[var(--warn-ink)]" />
          <h3 className="card-title">ملف التوزيعات</h3>
        </div>
        {data.frequency && <span className="tag-b">التوزيع: {data.frequency}</span>}
      </div>

      {data.note && (
        <div className="flex items-center gap-2 rounded-xl p-3 mb-4 text-sm"
          style={{ background: mixA(noteColor, 9), border: `1px solid ${mixA(noteColor, 27)}`, color: noteColor }}>
          <CalendarClock size={15} className="shrink-0" />
          <span className="font-semibold">{data.note.text}</span>
        </div>
      )}

      {(data.ex_date || data.pay_date) && (
        <div className="grid grid-cols-2 gap-2 mb-4">
          <div className="kpi"><div className="kpi-lbl">تاريخ الأحقية</div><div className="kpi-val">{data.ex_date || "—"}</div></div>
          <div className="kpi"><div className="kpi-lbl">تاريخ التوزيع</div><div className="kpi-val">{data.pay_date || "—"}</div></div>
        </div>
      )}

      {data.yearly?.length > 0 && (
        <>
          <p className="text-xs font-bold text-[var(--ink-muted)] mb-2">التوزيع السنوي — آخر {data.yearly.length} سنوات (للسهم)</p>
          <div style={{ height: 180 }} dir="ltr">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.yearly} margin={{ top: 6, right: 6, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
                <XAxis dataKey="year" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} />
                <YAxis tick={{ fontSize: 10, fill: "var(--ink-muted)" }} width={40} />
                <Tooltip contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                  labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                  itemStyle={{ color: "var(--tip-text)" }}
                  formatter={(v: any) => [fmt(v) + "", "التوزيع"]} labelFormatter={(l: any) => `سنة ${l}`} />
                <Bar dataKey="amount" radius={[5, 5, 0, 0]}>
                  {data.yearly.map((_: any, i: number) => <Cell key={i} fill="var(--divs-bar)" stroke="var(--divs-bar-edge)" strokeWidth={1.25} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}

      {data.recent?.length > 0 && (
        <div className="mt-4">
          <p className="text-xs font-bold text-[var(--ink-muted)] mb-2">آخر التوزيعات المعلنة</p>
          <div className="flex flex-wrap gap-2">
            {data.recent.map((d: any, i: number) => (
              <span key={i} className="tag-n" style={{ fontSize: 11 }}>{d.date} · {fmt(d.amount)}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
