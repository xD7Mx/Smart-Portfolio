import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import clsx from "clsx";
import { marketApi } from "../../services/api";

function Empty({ label = "لا توجد بيانات حالياً" }: { label?: string }) {
  return <div className="py-10 text-center text-[var(--ink-muted)] text-sm">{label}</div>;
}

/**
 * "حركة السعر" — general, public historical price data (not portfolio-
 * specific), so it's the same component on any stock's card whether it's a
 * portfolio holding (Company page) or a general market lookup (Market page).
 */
export default function PriceChart({ symbol }: { symbol: string }) {
  const [range, setRange] = useState("3mo");
  const { data: points = [] } = useQuery({
    queryKey: ["price-history", symbol, range],
    queryFn: () => marketApi.history(symbol, range).then(r => Array.isArray(r.data?.data) ? r.data.data : []),
    enabled: !!symbol,
  });
  const up = points.length >= 2 && points[points.length - 1].close >= points[0].close;
  const color = up ? "var(--pos-ink)" : "var(--neg-ink)";
  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <p className="card-title">حركة السعر</p>
        <div className="flex gap-1.5">
          {/* خمسُ سنواتٍ بأمر المالك. والخادمُ يدعمها أصلاً بفاصلٍ أسبوعيّ
              (‏`market_data`: 2y/5y ⇐ 1wk) — كان النقصُ في الواجهة وحدَها.
              وخمسُ سنواتٍ ليست زينةً: دورةُ السوق لا تُرى في سنة. */}
          {[["1mo", "شهر"], ["3mo", "3 أشهر"], ["6mo", "6 أشهر"], ["1y", "سنة"],
            ["5y", "5 سنوات"]].map(([id, lbl]) => (
            <button key={id} onClick={() => setRange(id)}
              className={clsx("px-3 py-1 rounded-lg text-[11px] font-bold border transition-all",
                range === id ? " text-[var(--brand-ink)] border-[var(--brand)]" : "border-[var(--hairline)] text-[var(--ink-muted)]")}>
              {lbl}
            </button>
          ))}
        </div>
      </div>
      {points.length >= 2 ? (
        <div style={{ height: 220 }} dir="ltr">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={points} margin={{ top: 5, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="pcFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,.12)" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--ink-muted)" }} tickFormatter={(d: string) => d.slice(5)} minTickGap={28} />
              <YAxis domain={["auto", "auto"]} tick={{ fontSize: 10, fill: "var(--ink-muted)" }} orientation="right" width={40} tickMargin={4} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "var(--pop)", border: "1px solid var(--line)", color: "var(--tip-text)", borderRadius: 10, fontSize: 12 }}
                labelStyle={{ color: "var(--tip-text)", fontWeight: 300, marginBottom: 4 }}
                itemStyle={{ color: "var(--tip-text)" }}
                formatter={(v: any) => [Number(v).toLocaleString("en-US", { maximumFractionDigits: 2 }) + "", "الإغلاق"]} />
              <Area type="monotone" dataKey="close" stroke={color} strokeWidth={2} fill="url(#pcFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Empty label="لا توجد بيانات سعرية تاريخية حالياً — تُجلب مرة يومياً عند توفر المصدر" />
      )}
    </div>
  );
}
