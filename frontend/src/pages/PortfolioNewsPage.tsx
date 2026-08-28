import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Newspaper } from "lucide-react";
import { marketApi } from "../services/api";
import NewsList from "../components/common/NewsList";

/**
 * أخبار المحفظة — تستخدم **نفس** مكوّن أخبار السوق (NewsList) فيتطابق شكل
 * الخبر ونافذة تفاصيله في كل أقسام التطبيق: بطاقة بهوية بصرية حقيقية، ونافذة
 * فيها الملخّص (أو ملخّص قاعدي صادق عند غيابه) وزرّ مصدر لا يظهر إلا إن كان
 * الرابط يفتح فعلاً.
 */
export default function PortfolioNewsPage() {
  const { data: news = [], isLoading } = useQuery({
    queryKey: ["portfolio-news"],
    queryFn: () => marketApi.portfolioNews().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
  });

  return (
    <div className="space-y-5 fade-in">
      <div>
        <h1 className="text-2xl font-medium text-[var(--ink)] flex items-center gap-2">
          <Newspaper size={20} className="text-[var(--warn-ink)]" /> أخبار المحفظة
        </h1>
      </div>

      <div className="card">
        <NewsList news={news} isLoading={isLoading}
          emptyText="لا توجد أخبار حالياً لشركات المحفظة" pageSize={20} />
      </div>
    </div>
  );
}
