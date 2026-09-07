import React from "react";
import { createRoot } from "react-dom/client";
import TadawulLogo from "../components/common/TadawulLogo";
import "../styles/globals.css";
createRoot(document.getElementById("root")!).render(
  <div>
    <div id="measure" style={{ position: "absolute", opacity: 0 }}>
      <TadawulLogo height={200} />
    </div>
    <div style={{ padding: 16, background: "linear-gradient(90deg,#4338ca,#6d28d9)",
                  display: "flex", gap: 20, alignItems: "center" }}>
      <TadawulLogo height={16} wordColor="#fff" title="تداول" />
      <TadawulLogo height={22} wordColor="#fff" />
      <TadawulLogo height={32} wordColor="#fff" />
    </div>
    <div style={{ padding: 16, background: "#fff", display: "flex", gap: 20, alignItems: "center" }}>
      <TadawulLogo height={16} />
      <TadawulLogo height={22} />
      <TadawulLogo height={32} />
    </div>
  </div>
);
