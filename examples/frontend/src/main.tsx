import { createRoot } from "react-dom/client";
import CustomerSupport  from "./pages/CustomerSupport";
import "./index.css";
import { BrowserRouter, Routes, Route } from "react-router";
import MarketingAssets from "./pages/Marketing";
const container = document.getElementById("root");
import App from "./App";

if (!container) {
  throw new Error("Root element with id 'root' not found");
}

createRoot(container).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/customer-support" element={<CustomerSupport />} />
      <Route path="/marketing-assets" element={<MarketingAssets />} />
    </Routes>
  </BrowserRouter>
);

