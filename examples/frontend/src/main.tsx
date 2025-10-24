import { createRoot } from "react-dom/client";
import CustomerSupport  from "./pages/CustomerSupport";
import "./index.css";
import { BrowserRouter, Routes, Route } from "react-router";
const container = document.getElementById("root");
import App from "./App";
import FactPage from "./pages/Fact";
import KnowledgeAssistantPage from "./pages/KnowledgeAssistant";

if (!container) {
  throw new Error("Root element with id 'root' not found");
}

createRoot(container).render(
  <BrowserRouter>
    <Routes>
      <Route path="/" element={<App />} />
      <Route path="/customer-support" element={<CustomerSupport />} />
      <Route path="/guide" element={<FactPage />} />
      <Route path="/federal" element={<KnowledgeAssistantPage />} />
    </Routes>
  </BrowserRouter>
);
