import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import FinancialsTable from "../components/analysis/FinancialsTable";
import "../styles/globals.css";

/* مسبارُ البيانات المالية — يُركّب الجدولَ وحدَه ليُقاس **موضعُ القيمة
   النسبية الدائم** (D232) في متصفّحٍ حقيقيّ: هل تظهر مع وجود هدفِ
   المحلّلين؟ وهل تبقى باسمها لا في خانته؟ */
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <div dir="rtl" style={{ padding: 16, maxWidth: 900 }}>
      <FinancialsTable symbol="2222" />
    </div>
  </QueryClientProvider>
);
