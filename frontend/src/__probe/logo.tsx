import React from "react";
import { createRoot } from "react-dom/client";
import TadawulLogo from "../components/common/TadawulLogo";
import "../styles/globals.css";
createRoot(document.getElementById("root")!).render(
  <div>
    <div id="measure" style={{ position: "absolute", opacity: 0 }}>
      <TadawulLogo height={200} latin={false} />
    </div>
    <div style={{ padding: 16, background: "#4c1d95", display: "flex", gap: 20, alignItems: "center" }}>
      <TadawulLogo height={15} latin={false} wordColor="#ffffff" />
      <TadawulLogo height={22} latin={false} wordColor="#ffffff" />
      <TadawulLogo height={40} latin={false} wordColor="#ffffff" />
    </div>
  </div>
);
