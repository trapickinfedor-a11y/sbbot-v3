/* ═══════════════════════════════════════════════════════
   Seller Hub Mini App v2 — App Root
   Design: Obsidian Glass (dark, glassmorphism)
   ═══════════════════════════════════════════════════════ */

import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Router, Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import SellerApp from "./pages/SellerApp";

function RouterWithBase() {
  return (
    <Router base="/seller-mini-app">
      <Switch>
        <Route path="/" component={SellerApp} />
        <Route path="/404" component={NotFound} />
        <Route component={NotFound} />
      </Switch>
    </Router>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark">
        <TooltipProvider>
          <Toaster
            theme="dark"
            position="top-center"
            toastOptions={{
              style: {
                background: "oklch(0.17 0.014 260)",
                border: "1px solid oklch(1 0 0 / 0.08)",
                color: "oklch(0.94 0.008 260)",
              },
            }}
          />
          <RouterWithBase />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
