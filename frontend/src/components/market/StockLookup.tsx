import React, { useState, useEffect } from "react";
import { invalidateWatchlist } from "../../services/watchlistCache";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Search, Star } from "lucide-react";
import { marketApi } from "../../services/api";
import { searchCompanies, SaudiCompany } from "../../data/saudiCompanies";
import { useAuthStore } from "../../store/authStore";
import CompanyLogo from "../common/CompanyLogo";
import StockView from "./StockView";

/**
 * بحث السوق — يفتح أي سهم في تداول بنفس بطاقة الشركة الموحّدة (StockView)،
 * فلا تختلف الشركة شكلاً بين السوق وبقية الأقسام.
 *
 * في قائمة النتائج نجمة متابعة لكل شركة: تُضيفها أو تُزيلها من قائمة المراقبة
 * الافتراضية دون فتح صفحتها أصلاً — أسرع مسار من «بحثتُ» إلى «أتابعها».
 */
export default function StockLookup({ initialSymbol, onActiveChange }: { initialSymbol?: string | null; onActiveChange?: (active: boolean) => void }) {
  const qc = useQueryClient();
  const { isOwner } = useAuthStore();
  const [q, setQ] = useState("");
  const [suggestions, setSuggestions] = useState<SaudiCompany[]>([]);
  const [symbol, setSymbol] = useState<string | null>(initialSymbol ? initialSymbol.toUpperCase() : null);

  useEffect(() => { onActiveChange?.(!!symbol); }, [symbol, onActiveChange]);

  const pick = (sym: string) => {
    setSymbol(sym.toUpperCase());
    setQ("");
    setSuggestions([]);
  };

  useEffect(() => {
    if (initialSymbol) pick(initialSymbol);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialSymbol]);

  // قائمة المراقبة الافتراضية — لرسم حالة النجمة في نتائج البحث.
  const { data: watchRows = [] } = useQuery({
    queryKey: ["watchlist"],
    queryFn: () => marketApi.watchlist().then(r => (Array.isArray(r.data.data) ? r.data.data : [])),
    enabled: isOwner,
  });
  const watchedSet = new Set(watchRows.map((w: any) => w.symbol));
  const toggleWatch = useMutation({
    mutationFn: ({ c, on }: { c: SaudiCompany; on: boolean }) => (on
      ? marketApi.watchRemove(c.symbol)
      : marketApi.watchAdd(c.symbol, c.name_ar || c.name_en)),
    onSuccess: () => invalidateWatchlist(qc),
  });

  return (
    <div className="card space-y-4">
      <div className="relative max-w-xl">
        <Search size={15} className="absolute end-3 top-1/2 -translate-y-1/2 text-[var(--ink-muted)]" />
        <input className="input px-9" placeholder="ابحث عن أي سهم بالسوق — بالرمز أو الاسم…" value={q}
          onChange={e => { setQ(e.target.value); setSuggestions(searchCompanies(e.target.value, 400)); }}
          onKeyDown={e => e.key === "Enter" && q && pick(q)} />
        {suggestions.length > 0 && (
          <div className="sp-menu absolute z-20 top-full mt-1 w-full rounded-xl overflow-hidden shadow-2xl"
            style={{ maxHeight: 300, overflowY: "auto" }}>
            {suggestions.map(c => {
              const on = watchedSet.has(c.symbol);
              return (
                <div key={c.symbol} className="w-full flex items-center gap-2 px-2 hover:panel transition-colors">
                  <button type="button" onClick={() => pick(c.symbol)}
                    className="flex-1 min-w-0 text-start py-2.5 flex items-center gap-3">
                    <CompanyLogo symbol={c.symbol} size={26} />
                    <span className="tabular-nums text-[11px] font-semibold text-[var(--ink-muted)] shrink-0" dir="ltr">{c.symbol}</span>
                    <span className="text-[var(--ink)] text-sm font-semibold truncate">{c.name_ar}</span>
                    <span className="text-[var(--ink-muted)] text-xs ms-auto hidden sm:inline truncate">{c.sector}</span>
                  </button>
                  {isOwner && (
                    <button type="button" disabled={toggleWatch.isPending}
                      onClick={() => toggleWatch.mutate({ c, on })}
                      title={on ? "إزالة من قائمة المراقبة" : "إضافة إلى قائمة المراقبة"}
                      className={"watch-star p-1.5 rounded-lg shrink-0 " + (on ? "is-on" : "")}>
                      <Star size={15} fill={on ? "currentColor" : "none"} />
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {symbol && <StockView symbol={symbol} onClose={() => setSymbol(null)} />}
    </div>
  );
}
