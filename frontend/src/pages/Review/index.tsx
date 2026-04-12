import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { DndContext, type DragEndEvent, type DragOverEvent, type DragStartEvent } from "@dnd-kit/core";
import { listTransactions, bulkCategorize } from "../../api/transactions";
import { listCategoryGroups } from "../../api/categories";
import TransactionTable from "../Analytics/TransactionTable";
import CategorySidebar from "../Analytics/CategorySidebar";
import TransactionDragOverlay from "../Analytics/TransactionDragOverlay";

export default function ReviewPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [overId, setOverId] = useState<string | null>(null);

  const { data: transactions = [], isLoading } = useQuery({
    queryKey: ["transactions", "needs_review"],
    queryFn: () => listTransactions({ needs_review: true, include_llm_status: true, limit: 500 }),
  });

  const { data: categoryGroups = [] } = useQuery({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });

  function invalidateAndClear() {
    setSelected(new Set());
    queryClient.invalidateQueries({ queryKey: ["transactions", "needs_review"] });
  }

  const assignMutation = useMutation({
    mutationFn: (category_id: string) =>
      bulkCategorize(Array.from(selected), category_id),
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
    if (targetId) {
      assignMutation.mutate(targetId);
    }
    setActiveId(null);
    setOverId(null);
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-gray-900">{t("review.title")}</h1>
        {!isLoading && transactions.length > 0 && (
          <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-sm font-medium bg-red-100 text-red-700">
            {transactions.length}
          </span>
        )}
      </div>

      {isLoading ? (
        <p className="text-gray-400 text-sm">{t("common.loading")}</p>
      ) : transactions.length === 0 ? (
        <p className="text-gray-500 text-sm">{t("review.empty")}</p>
      ) : (
        <DndContext onDragStart={handleDragStart} onDragOver={handleDragOver} onDragEnd={handleDragEnd}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="flex-1 min-w-0">
              <TransactionTable
                transactions={transactions}
                selected={selected}
                activeId={activeId}
                showReasonColumn={true}
                onToggleRow={toggleRow}
                onToggleAll={toggleAll}
              />
            </div>
            <div className="lg:w-72 flex-shrink-0 lg:sticky lg:top-4 lg:self-start">
              <CategorySidebar
                categoryGroups={categoryGroups}
                currentCategoryId=""
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
