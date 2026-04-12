import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import client from "../../api/client";
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

  const queryClient = useQueryClient();

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", categoryId, year, month],
    queryFn: () => listTransactions({ date_from: dateFrom, date_to: dateTo, category_id: categoryId, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  const bulkMutation = useMutation({
    mutationFn: (payload: { transaction_ids: string[]; category_id: string }) =>
      client.patch("/api/transactions/bulk-categorize", payload),
    onSuccess: () => {
      setSelected(new Set());
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
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
      bulkMutation.mutate({
        transaction_ids: Array.from(selected),
        category_id: targetId,
      });
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

      {bulkMutation.isError && (
        <p className="mb-3 text-red-500 text-sm">{t("analytics.applyFailed")}</p>
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
