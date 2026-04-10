import { useQuery } from "@tanstack/react-query";
import { listTransactions } from "../../api/transactions";

export default function AnalyticsPage() {
  const { data: needsReview = [] } = useQuery({
    queryKey: ["needs-review"],
    queryFn: () => listTransactions({ needs_review: true, limit: 500 }),
    refetchInterval: 30000,
  });
  const count = needsReview.length;

  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Analytics</h1>
      {count > 0 && (
        <div className="mb-4 inline-flex items-center gap-2 bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2">
          <span className="text-yellow-700 text-sm font-medium">
            {count} transaction{count > 1 ? "s" : ""} need review
          </span>
          <a href="/transactions?needs_review=true" className="text-blue-600 text-sm hover:underline">
            Review →
          </a>
        </div>
      )}
      <p className="text-gray-500">Full analytics coming in M4.</p>
    </div>
  );
}
