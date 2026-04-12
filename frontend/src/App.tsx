import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import NavBar from "./components/NavBar";
import AnalyticsPage from "./pages/Analytics";
import ImportsPage from "./pages/Imports";
import ReviewPage from "./pages/Review";
import RulesPage from "./pages/Rules";
import SettingsPage from "./pages/Settings";
import CategoriesPage from "./pages/Categories";
import { DataFreshnessProvider } from "./context/DataFreshness";

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <DataFreshnessProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-gray-50">
            <NavBar />
            <main className="p-6">
              <Routes>
                <Route path="/" element={<AnalyticsPage />} />
                <Route path="/imports" element={<ImportsPage />} />
                <Route path="/review" element={<ReviewPage />} />
                <Route path="/rules" element={<RulesPage />} />
                <Route path="/categories" element={<CategoriesPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </DataFreshnessProvider>
    </QueryClientProvider>
  );
}
