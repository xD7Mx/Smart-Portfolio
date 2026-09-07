import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import MarketTicker from "../components/common/MarketTicker";
import "../styles/globals.css";

const qc = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
qc.setQueryData(["market-overview"], { tasi: { price: 11032.91, change_pct: 0.19, prev_close: 11012 } });
qc.setQueryData(["market-movers"], {
  gainers: [
    { symbol: "1120", name: "الراجحي", price: 44.0, change_pct: 3.7 },
    { symbol: "2222", name: "أرامكو", price: 25.94, change_pct: 2.94 },
    { symbol: "7010", name: "الاتصالات", price: 9.1, change_pct: 3.06 },
  ],
  losers: [
    { symbol: "4013", name: "د. سليمان", price: 15.43, change_pct: -1.72 },
    { symbol: "4164", name: "النهدي", price: 9.78, change_pct: -1.81 },
  ],
});
qc.setQueryData(["market-news", "ar"], []);
qc.setQueryData(["server-time"], { market_status: "open" });

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <div dir="rtl"><MarketTicker /></div>
  </QueryClientProvider>
);
