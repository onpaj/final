import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import TransactionTable from "./TransactionTable";
import CategorySidebar from "./CategorySidebar";
import TransactionDragOverlay from "./TransactionDragOverlay";

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
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);
  const [assignTarget, setAssignTarget] = useState<string>("");

  const queryClient = useQueryClient();

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  const allCategories = categoryGroups.flatMap((g) => g.categories ?? []);

  function invalidateAndClear() {
    setSelected(new Set());
    setAssignTarget("");
    queryClient.invalidateQueries({ queryKey: ["transactions"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) =>
      bulkCategorize(Array.from(selected), category_id),
    onSuccess: invalidateAndClear,
  });

  const clearMutation = useMutation({
    mutationFn: () => bulkCategorize(Array.from(selected), null),
    onSuccess: invalidateAndClear,
  });

  function toggleRow(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    const allSelected = transactions.length > 0 && selected.size === transactions.length;
    setSelected(allSelected ? new Set() : new Set(transactions.map((tx) => tx.id)));
  }

  function handleDragStart(event: DragStartEvent) {
    const draggedId = event.active.id as string;
    setActiveId(draggedId);
    if (!selected.has(draggedId)) {
      setSelected(new Set([draggedId]));
    }
  }

  function handleDragOver(event: DragOverEvent) {
    setOverId(event.over ? (event.over.id as string) : null);
  }

  function handleDragEnd(event: DragEndEvent) {
    const targetId = event.over ? (event.over.id as string) : null;
    if (targetId && targetId !== categoryId) {
      assignMutation.mutate(targetId);
    }
    setActiveId(null);
    setOverId(null);
  }

  const exportUrl = `/api/transactions/export?date_from=${dateFrom}&date_to=${dateTo}&category_id=${categoryId}`;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button className="text-blue-600 text-sm hover:underline" onClick={onBack}>
          {t("analytics.backToGroup")}
        </button>
        <a href={exportUrl} className="text-blue-600 text-sm hover:underline" download>
          {t("analytics.exportCsv")}
        </a>
      </div>
      <h2 className="text-xl font-bold mb-4">{categoryName}</h2>

      {selected.size > 0 && (
        <div className="mb-3 flex flex-wrap items-center gap-3 bg-blue-50 border border-blue-200 rounded-lg px-4 py-2.5 text-sm">
          <span className="text-blue-700 font-medium">
            {t("analytics.selectedCount", { count: selected.size })}
          </span>
          <span className="text-gray-500">{t("analytics.assignTo")}</span>
          <select
            className="border border-gray-300 rounded px-2 py-1 text-sm"
            value={assignTarget}
            onChange={(e) => setAssignTarget(e.target.value)}
          >
            <option value="">{t("analytics.pickCategory")}</option>
            {allCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
          <button
            className="bg-blue-600 text-white px-3 py-1 rounded text-sm font-medium disabled:opacity-50"
            disabled={!assignTarget || assignMutation.isPending}
            onClick={() => assignMutation.mutate(assignTarget)}
          >
            {assignMutation.isPending ? t("analytics.applying") : t("analytics.apply")}
          </button>
          <button
            className="bg-white border border-gray-300 text-gray-700 px-3 py-1 rounded text-sm font-medium disabled:opacity-50 hover:bg-gray-50"
            disabled={clearMutation.isPending}
            onClick={() => clearMutation.mutate()}
          >
            {clearMutation.isPending ? t("analytics.clearingCategory") : t("analytics.clearCategory")}
          </button>
          {(assignMutation.isError || clearMutation.isError) && (
            <span className="text-red-500">
              {assignMutation.isError ? t("analytics.applyFailed") : t("analytics.clearFailed")}
            </span>
          )}
        </div>
      )}

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : (
        <DndContext onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <TransactionTable
                transactions={transactions}
                selected={selected}
                activeId={activeId}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
              />
            </div>
            <div className="lg:w-72 flex-shrink-0 lg:sticky lg:top-4 lg:self-start">
              <CategorySidebar
                categoryGroups={categoryGroups}
                currentCategoryId={categoryId}
                overId={overId}
              />
            </div>
          </div>
          <TransactionDragOverlay activeId={activeId} count={selected.size} />
        </DndContext>
      )}
    </div>
  );
}
