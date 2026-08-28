import React from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { marketApi } from "../../services/api";
import EventsList from "../market/EventsList";

/**
 * "المفكرة" tab — per-company corporate announcements ONLY (entitlement,
 * distribution, bonus shares, splits, rights issues, AGM), rendered through
 * the SAME unified EventsList design language as the market/portfolio
 * calendars: company logo + typed action pill + weekly ordering.
 */
export default function StockCalendar({ symbol, name }: { symbol: string; name?: string }) {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ["company-events", symbol],
    queryFn: () => marketApi.companyEvents(symbol, name).then(r => Array.isArray(r.data?.data) ? r.data.data : []),
    enabled: !!symbol,
    retry: 0,
  });

  // Adapt the per-company feed's shape to the unified EventsList contract.
  const adapted = (events as any[])
    .filter((e: any) => e.headline || e.title)
    .map((e: any) => ({
      symbol,
      kind: e.kind,
      // وسم دقّة التأريخ يُمرَّر كما هو؛ القائمة نفسها تتولّى صياغته (وسم
      // «أُعلن:») فلا يُكرَّر المنطق في عارضَين.
      date_kind: e.date_kind,
      title: e.headline || e.title,
      // بلا تاريخ = بلا تاريخ: تضعه القائمة في سلّة «بلا تاريخ محدد» ولا
      // يدخل «هذا الأسبوع» أبداً.
      date: e.date_kind === "undated" ? null : (e.published || e.date),
      url: e.url,
    }));

  return (
    <div className="card">
      <p className="card-title mb-3 flex items-center gap-1.5">
        <CalendarDays size={14} className="text-[var(--brand-ink)]" /> المفكرة
      </p>
      {isLoading ? (
        <div className="space-y-2">{[...Array(3)].map((_, i) => <div key={i} className="h-12 skeleton" />)}</div>
      ) : adapted.length === 0 ? (
        <div className="py-8 text-center text-[var(--ink-muted)] text-sm">لا توجد مواعيد أو إعلانات حالياً لهذه الشركة</div>
      ) : (
        <EventsList events={adapted} symbol={symbol} />
      )}
    </div>
  );
}
