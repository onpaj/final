import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { listTransactions } from "../../api/transactions";
import { listCategories, type Category } from "../../api/categories";
import client from "../../api/client";

interface Props {
  categoryId: string;
  categoryName: string;
  year: number;
  month: number;
  onBack: () => void;
}

export default function CategoryDetail({ categoryId, categoryName, year, month, onBack }: Props) {
  const { t } = useTranslation();
  const dateFrom = `${year}-${String(month).padStart(2, "0")}-01`;
  const dateTo = `${year}-${String(month).padStart(2, "0")}-31`;

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [targetCategoryId, setTargetCategoryId] = useState<string>("");

  const queryClient = useQueryClient();

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId, limit: 500 }),
  });

  const { data: categories = [] } = useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  const bulkMutation = useMutation({
    mutationFn: (payload: { transaction_ids: string[]; category_id: string }) =>
      client.patch("/api/transactions/bulk-categorize", payload),
    onSuccess: () => {
      setSelected(new Set());
      setTargetCategoryId("");
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  const allSelected = transactions.length > 0 && selected.size === transactions.length;
  const someSelected = selected.size > 0 && !allSelected;

  function toggleRow(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
    } else {
      setSelected(new Set(transactions.map((tx) => tx.id)));
    }
  }

  const exportUrl = `/api/transactions/export?date_from=${dateFrom}&date_to=${dateTo}&category_id=${categoryId}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button className="text-blue-600 text-sm hover:underline" onClick={onBack}>
          {t("analytics.backToGroup")}
        </button>
        <a
          href={exportUrl}
          className="text-blue-600 text-sm hover:underline"
          download
        >
          {t("analytics.exportCsv")}
        </a>
      </div>
      <h2 className="text-xl font-bold mb-4">{categoryName}</h2>

      {selected.size > 0 && (
        <div className="flex items-center gap-3 mb-3 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-lg text-sm">
          <span className="font-medium text-blue-800">{t("analytics.selectedCount", { count: selected.size })}</span>
          <span className="text-blue-700">{t("analytics.assignTo")}</span>
          <select
            className="border border-blue-300 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-400"
            value={targetCategoryId}
            onChange={(e) => setTargetCategoryId(e.target.value)}
          >
            <option value="">{t("analytics.pickCategory")}</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
          <button
            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={selected.size === 0 || !targetCategoryId || bulkMutation.isPending}
            onClick={() =>
              bulkMutation.mutate({
                transaction_ids: Array.from(selected),
                category_id: targetCategoryId,
              })
            }
          >
            {bulkMutation.isPending ? t("analytics.applying") : t("analytics.apply")}
          </button>
          {bulkMutation.isError && (
            <p className="text-red-500 text-sm">{t("analytics.applyFailed")}</p>
          )}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="px-4 py-2 w-8">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    ref={(el) => { if (el) el.indeterminate = someSelected; }}
                    onChange={toggleAll}
                    className="cursor-pointer"
                  />
                </th>
                {[t("analytics.txDate"), t("analytics.txCounterparty"), t("analytics.txDescription"), t("analytics.txAmount")].map((h) => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => {
                const isChecked = selected.has(tx.id);
                return (
                  <tr
                    key={tx.id}
                    className={`border-t border-gray-100 hover:bg-gray-50 ${isChecked ? "bg-blue-50" : ""}`}
                  >
                    <td className="px-4 py-2.5">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleRow(tx.id)}
                        className="cursor-pointer"
                      />
                    </td>
                    <td className="px-4 py-2.5 text-gray-500">{tx.booking_date}</td>
                    <td className="px-4 py-2.5 font-medium">{tx.counterparty_name || "—"}</td>
                    <td className="px-4 py-2.5 text-gray-500 text-xs">{tx.description || "—"}</td>
                    <td className={`px-4 py-2.5 font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
                      {Number(tx.amount).toLocaleString("cs-CZ")} CZK
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {transactions.length === 0 && (
            <p className="px-4 py-8 text-center text-gray-400 text-sm">{t("analytics.noTransactions")}</p>
          )}
        </div>
      )}
    </div>
  );
}
