import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getMonthlySummary } from "../../api/analytics";
import MonthSummary from "./MonthSummary";
import GroupDetail from "./GroupDetail";
import CategoryDetail from "./CategoryDetail";
import TrendsView from "./TrendsView";
import { useDataFreshness } from "../../context/DataFreshness";

type Level =
  | { view: "summary" }
  | { view: "group"; groupName: string }
  | { view: "category"; groupName: string; categoryId: string; categoryName: string };

export default function AnalyticsPage() {
  const now = new Date();
  const defaultMonth = now.getMonth() === 0 ? 12 : now.getMonth();
  const defaultYear = now.getMonth() === 0 ? now.getFullYear() - 1 : now.getFullYear();

  const [year, setYear] = useState(defaultYear);
  const [month, setMonth] = useState(defaultMonth);
  const [level, setLevel] = useState<Level>({ view: "summary" });
  const [tab, setTab] = useState<"overview" | "trends">("overview");

  const { isStale, markFresh } = useDataFreshness();

  const { data: summary, isLoading, refetch } = useQuery({
    queryKey: ["monthly-summary", year, month],
    queryFn: () => getMonthlySummary(year, month),
  });

  const monthLabel = new Date(year, month - 1).toLocaleString("cs-CZ", { month: "long", year: "numeric" });

  function prevMonth() {
    if (month === 1) { setMonth(12); setYear((y) => y - 1); }
    else setMonth((m) => m - 1);
    setLevel({ view: "summary" });
  }

  function nextMonth() {
    if (month === 12) { setMonth(1); setYear((y) => y + 1); }
    else setMonth((m) => m + 1);
    setLevel({ view: "summary" });
  }

  return (
    <div className="max-w-5xl mx-auto">
      {isStale && (
        <div className="mb-4 flex items-center justify-between bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <span className="text-blue-700 text-sm">New data available — import completed.</span>
          <button
            className="bg-blue-600 text-white text-sm px-3 py-1 rounded"
            onClick={() => { refetch(); markFresh(); }}
          >
            Refresh
          </button>
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Analytics — {monthLabel}</h1>
        <div className="flex items-center gap-2">
          <button className="text-gray-500 hover:text-gray-800 px-2" onClick={prevMonth}>‹</button>
          <button className="text-gray-500 hover:text-gray-800 px-2" onClick={nextMonth}>›</button>
        </div>
      </div>

      {/* Tab toggle — only show at summary level */}
      {level.view === "summary" && (
        <div className="flex gap-1 mb-6 border-b border-gray-200">
          {(["overview", "trends"] as const).map((t) => (
            <button
              key={t}
              className={`px-4 py-2 text-sm font-medium capitalize border-b-2 -mb-px transition-colors ${
                tab === t ? "border-blue-600 text-blue-600" : "border-transparent text-gray-500 hover:text-gray-800"
              }`}
              onClick={() => setTab(t)}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {isLoading && <p className="text-gray-400 text-sm">Loading…</p>}

      {tab === "trends" && level.view === "summary" && (
        <TrendsView year={year} month={month} />
      )}

      {tab === "overview" && summary && level.view === "summary" && (
        <MonthSummary
          summary={summary}
          onGroupClick={(groupName) => setLevel({ view: "group", groupName })}
        />
      )}

      {tab === "overview" && summary && level.view === "group" && (
        <GroupDetail
          group={summary.groups.find((g) => g.name === level.groupName)!}
          onCategoryClick={(categoryId, categoryName) =>
            setLevel({ view: "category", groupName: level.groupName, categoryId, categoryName })
          }
          onBack={() => setLevel({ view: "summary" })}
        />
      )}

      {tab === "overview" && level.view === "category" && (
        <CategoryDetail
          categoryId={level.categoryId}
          categoryName={level.categoryName}
          year={year}
          month={month}
          onBack={() => setLevel({ view: "group", groupName: level.groupName })}
        />
      )}
    </div>
  );
}
