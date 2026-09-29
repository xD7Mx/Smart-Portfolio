import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { registerSW } from "./registerSW";

import { applyOfficialNames } from "./data/saudiCompanies";
import { marketApi } from "./services/api";

/* أسماءُ «تداول» الرسمية تُطبَّق قبل الرسم (D520) — ومهلةٌ قصيرةٌ فلا
   ينتظر التطبيقُ خادماً بطيئاً؛ تعذّرُها يُبقي الدليلَ كما هو. */
const names = Promise.race([
  marketApi.officialNames().then(r => applyOfficialNames(r.data?.data)).catch(() => 0),
  new Promise(res => setTimeout(res, 1500)),
]);

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
names.finally(() => root.render(<React.StrictMode><App /></React.StrictMode>));

// Service Worker: كاش أصول التطبيق فقط — لا يُخزَّن أي طلب بيانات مالية.
registerSW();
