import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { registerSW } from "./registerSW";

const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);
root.render(<React.StrictMode><App /></React.StrictMode>);

// Service Worker: كاش أصول التطبيق فقط — لا يُخزَّن أي طلب بيانات مالية.
registerSW();
