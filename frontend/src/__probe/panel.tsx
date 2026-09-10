import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AnalysisPanel from "../components/analysis/AnalysisPanel";
import "../styles/globals.css";

/* مسبارُ تبويب التحليل — يُقاس فيه موضعُ حكم «أرخص من قطاعه»: تحت العنوان
   لا في الطرف المقابل (D233)، ووجودُ القيمة النسبية في هذا التبويب. */
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}>
    <div dir="rtl" style={{ padding: 16, maxWidth: 900 }}>
      <AnalysisPanel symbol="2222" name="أرامكو" />
    </div>
  </QueryClientProvider>
);
