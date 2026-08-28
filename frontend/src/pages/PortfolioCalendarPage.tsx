import React from "react";
import { useQuery } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { marketApi } from "../services/api";
import EventsList from "../components/market/EventsList";

/**
 * مفكرة المحفظة — المظلة الجامعة لمفكرات شركات المحفظة: إعلانات الشركات
 * فقط (توزيعات/أحقية/منحة/زيادة رأس مال/جمعيات) معزولة تماماً عن الأخبار،
 * بنفس اللغة التصميمية الموحدة: شعار الشركة + تصنيف الإعلان + ترتيب أسبوعي.
 */
export default function PortfolioCalendarPage() {
  const { data: events = [], isLoading } = useQuery({
    queryKey: ["market-events"],
    queryFn: () => marketApi.events().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });

  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <CalendarDays size={20} className="text-[var(--brand-ink)]" /> مفكرة المحفظة
        </h1>
      </div>

      <div className="card">
        {isLoading ? (
          <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <div key={i} className="h-14 skeleton rounded-xl" />)}</div>
        ) : (
          <EventsList events={events} />
        )}
      </div>
    </div>
  );
}
