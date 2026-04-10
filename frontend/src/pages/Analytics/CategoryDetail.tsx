import { useQuery } from "@tanstack/react-query";
import { listTransactions } from "../../api/transactions";

interface Props {
  categoryId: string;
  categoryName: string;
  year: number;
  month: number;
  onBack: () => void;
}

export default function CategoryDetail({ categoryId, categoryName, year, month, onBack }: Props) {
  const dateFrom = `${year}-${String(month).padStart(2, "0")}-01`;
  const dateTo = `${year}-${String(month).padStart(2, "0")}-31`;

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId, limit: 500 }),
  });

  return (
    <div>
      <button className="text-blue-600 text-sm mb-4 hover:underline" onClick={onBack}>
        ← Back to group
      </button>
      <h2 className="text-xl font-bold mb-4">{categoryName}</h2>
      {isLoading ? (
        <p className="text-gray-400 text-sm">Loading…</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                {["Date", "Counterparty", "Description", "Amount"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2.5 text-gray-500">{tx.booking_date}</td>
                  <td className="px-4 py-2.5 font-medium">{tx.counterparty_name || "—"}</td>
                  <td className="px-4 py-2.5 text-gray-500 text-xs">{tx.description || "—"}</td>
                  <td className={`px-4 py-2.5 font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
                    {Number(tx.amount).toLocaleString("cs-CZ")} CZK
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {transactions.length === 0 && (
            <p className="px-4 py-8 text-center text-gray-400 text-sm">No transactions.</p>
          )}
        </div>
      )}
    </div>
  );
}
