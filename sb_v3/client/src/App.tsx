import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import ImportedData from "./pages/ImportedData";
import Operations from "./pages/Operations";
import Overview from "./pages/Overview";

export const adminRoutes = [
  "/",
  "/imported-data",
  "/jobs",
  "/proxy",
  "/workers",
  "/billing",
  "/revenue",
  "/logs",
  "/log-chat",
  "/metrics",
  "/telemetry",
  "/system",
  "/safe-bench",
  "/bot-texts",
  "/broadcasts",
] as const;

function Router() {
  return (
    <Switch>
      <Route path={"/"} component={Overview} />
      <Route path={"/imported-data"} component={ImportedData} />
      <Route path={"/jobs"} component={Operations} />
      <Route path={"/proxy"} component={Operations} />
      <Route path={"/workers"} component={Operations} />
      <Route path={"/billing"} component={Operations} />
      <Route path={"/revenue"} component={Operations} />
      <Route path={"/logs"} component={Operations} />
      <Route path={"/log-chat"} component={Operations} />
      <Route path={"/metrics"} component={Operations} />
      <Route path={"/telemetry"} component={Operations} />
      <Route path={"/system"} component={Operations} />
      <Route path={"/safe-bench"} component={Operations} />
      <Route path={"/bot-texts"} component={Operations} />
      <Route path={"/broadcasts"} component={Operations} />
      <Route path={"/404"} component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
