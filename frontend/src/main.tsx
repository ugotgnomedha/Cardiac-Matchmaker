import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { SWRConfig } from "swr";

import "./index.css";
import App from "./App.tsx";
import { apiRequest, isApiError } from "./utils/api";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <SWRConfig
      value={{
        fetcher: (resource: string) => apiRequest(resource),
        shouldRetryOnError: false,
        revalidateOnFocus: true,
        onError: (error) => {
          if (isApiError(error) && error.status === 401) {
            return;
          }

          console.error(error);
        },
      }}
    >
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </SWRConfig>
  </StrictMode>,
);
