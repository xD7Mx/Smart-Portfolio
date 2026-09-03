import React from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StockView from "../components/market/StockView";
import CompanyPage from "../pages/CompanyPage";
import "../styles/globals.css";
const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={qc}><div dir="rtl"><StockView symbol="2222" /></div></QueryClientProvider>
);
void CompanyPage;
