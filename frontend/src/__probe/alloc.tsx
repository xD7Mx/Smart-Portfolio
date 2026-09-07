import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RebalanceCard } from "../pages/PortfolioPage";
import "../styles/globals.css";

/* مسبارُ جدول التوزيع — يُركّب البطاقةَ وحدَها ويُغذّيها خادمٌ مموَّه من
   سكربت القياس، فيُقاس صفُّ المجموع وإعادةُ التوزيع بلا خادمٍ ولا شبكة. */
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <div dir="rtl" style={{ padding: 16, maxWidth: 1100 }}><RebalanceCard /></div>
  </QueryClientProvider>
);
