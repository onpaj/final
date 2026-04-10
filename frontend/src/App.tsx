import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AnalyticsPage from "./pages/Analytics";
import ImportsPage from "./pages/Imports";
import RulesPage from "./pages/Rules";
import SettingsPage from "./pages/Settings";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <NavBar />
          <main className="p-6">
            <Routes>
              <Route path="/" element={<AnalyticsPage />} />
              <Route path="/imports" element={<ImportsPage />} />
              <Route path="/rules" element={<RulesPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
