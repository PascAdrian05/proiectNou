import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { AppRouter } from "./router/AppRouter";
import { AuthProvider } from "./context/AuthContext";
import { ThemeProvider } from "./context/ThemeContext";
import { ToastProvider } from "./context/ToastContext";
import { Toaster } from "react-hot-toast";
import { ToastContainer } from "./components/ToastContainer";
import { useRegisterSW } from "./hooks/useRegisterSW";
import "./styles/global.css";

function PWAProvider({ children }) {
  useRegisterSW();
  return children;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <PWAProvider>
    <BrowserRouter>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <AppRouter />
            <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
            <ToastContainer />
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </BrowserRouter>
  </PWAProvider>
);
