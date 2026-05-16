import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "../../packages/design-system/tokens.css";
import "./styles/globals.css";
import "./lib/i18n";

const qc = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, refetchOnWindowFocus: false, retry: 1 },
  },
});

// In prod the SPA is served under /school/, so React Router needs that prefix
// to keep internal links (NavLink, Navigate, useNavigate) on /school/*.
// In dev (Vite serves at http://localhost:5173/school/), BASE_URL is also "/school/".
const basename = (import.meta.env.BASE_URL || "/").replace(/\/$/, "") || "/";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={qc}>
      <BrowserRouter basename={basename}>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
);
