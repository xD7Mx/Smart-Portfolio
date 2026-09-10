import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ScreenerTab, SectorAnalysis } from "../pages/MarketPage";
import { FairValueBar } from "../components/common/ValueBars";
import "../styles/globals.css";

/* مسبارُ جدولَي الفرز — الأسهمُ والقطاعات معاً، ليُقاس **محورُ العمود**:
   عنوانُه ورقمُه على محورٍ واحد (D238). ويُغذّيهما خادمٌ مموَّه. */
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <div dir="rtl" style={{ padding: 16, width: 1600 }}>
      {/* شريطُ التقييم بنقطته — تُقاس هنا (‏D238). */}
      <FairValueBar upside={17} />
      <ScreenerTab onOpen={() => {}} />
      <SectorAnalysis />
    </div>
  </QueryClientProvider>
);
