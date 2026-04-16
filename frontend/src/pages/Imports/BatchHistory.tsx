import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { listBatches, type Batch } from "../../api/imports";
import { listAccounts } from "../../api/accounts";
import { listCategoryGroups } from "../../api/categories";
import type { CategoryGroup } from "../../api/categories";
import { bulkCategorize } from "../../api/transactions";
import { buildTransactionContextMenuItems } from "../../utils/transactionContextMenu";
import client from "../../api/client";
import ContextMenu from "../../components/ContextMenu";
import TransactionDetailModal from "../../components/TransactionDetailModal";
import SlideOverPanel from "../../components/SlideOverPanel";
import RuleForm, { type RulePrefill } from "../Rules/RuleForm";

const STATUS_BADGE: Record<Batch["status"], string> = {
  processing: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

interface BatchTx {
  id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  is_transfer: boolean;
}

function CategorizationBadge({ tx }: { tx: BatchTx }) {
  const { t } = useTranslation();
  if (tx.is_transfer) {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
        {t("imports.badgeTransfer")}
      </span>
    );
  }
  if (tx.categorization_source === "rule") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
        {t("imports.badgeRule")}
      </span>
    );
  }
  if (tx.categorization_source === "llm") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-purple-100 text-purple-700">
        {t("imports.badgeLlm")}
      </span>
    );
  }
  if (tx.categorization_source === "manual") {
    return (
      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
        {t("imports.badgeManual")}
      </span>
    );
  }
  return <span className="text-gray-400 text-xs">—</span>;
}

function BatchTransactions({ batchId, onCreateRule }: { batchId: string; onCreateRule: (p: RulePrefill) => void }) {
  const { t } = useTranslation();
  const { data: txs = [], isLoading } = useQuery<BatchTx[]>({
    queryKey: ["batch-transactions", batchId],
    queryFn: async () => (await client.get(`/api/imports/${batchId}/transactions`)).data,
  });
  const queryClient = useQueryClient();
  const { data: categoryGroups = [] } = useQuery<CategoryGroup[]>({
    queryKey: ["categoryGroups"],
    queryFn: listCategoryGroups,
  });
  const allCategories = categoryGroups.flatMap((g) => g.categories ?? []);

  const categorizeMutation = useMutation({
    mutationFn: ({ ids, categoryId }: { ids: string[]; categoryId: string | null }) =>
      bulkCategorize(ids, categoryId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["batch-transactions", batchId] }),
  });

  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; tx: BatchTx } | null>(null);
  const [detailTxId, setDetailTxId] = useState<string | null>(null);

  if (isLoading) return <p className="text-xs text-gray-400">{t("imports.loadingTx")}</p>;
  if (txs.length === 0) return <p className="text-xs text-gray-400">{t("imports.noTxFound")}</p>;

  return (
    <>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-gray-400 uppercase text-xs">
            <th className="pr-4 py-1 text-left">{t("common.date")}</th>
            <th className="pr-4 py-1 text-left">{t("analytics.txCounterparty")}</th>
            <th className="pr-4 py-1 text-left">{t("analytics.txCounterpartyAccount")}</th>
            <th className="pr-4 py-1 text-right">{t("analytics.txAmount")}</th>
            <th className="pr-4 py-1 text-left">{t("common.currency")}</th>
            <th className="pr-4 py-1 text-left">{t("imports.colClassification")}</th>
            <th className="pr-4 py-1 text-left">{t("common.category")}</th>
          </tr>
        </thead>
        <tbody>
          {txs.map((tx) => (
            <tr
              key={tx.id}
              className="border-t border-gray-100 hover:bg-gray-50 cursor-context-menu"
              onContextMenu={(e) => { e.preventDefault(); setContextMenu({ x: e.clientX, y: e.clientY, tx }); }}
            >
              <td className="pr-4 py-1 text-gray-500">{tx.booking_date}</td>
              <td className="pr-4 py-1">{tx.counterparty_name || "—"}</td>
              <td className="pr-4 py-1 text-gray-400 font-mono text-xs">{tx.counterparty_account || "—"}</td>
              <td className={`pr-4 py-1 text-right font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
                {tx.amount.toLocaleString("cs-CZ")}
              </td>
              <td className="pr-4 py-1 text-gray-400">{tx.currency}</td>
              <td className="pr-4 py-1"><CategorizationBadge tx={tx} /></td>
              <td className="pr-4 py-1">
                {(() => {
                  const cat = allCategories.find((c) => c.id === tx.category_id);
                  if (!cat) return <span className="text-gray-300">—</span>;
                  const bg = cat.color ? `${cat.color}22` : "#e5e7eb";
                  const fg = cat.color ?? "#6b7280";
                  return (
                    <span
                      className="inline-block px-2 py-0.5 rounded text-xs font-medium"
                      style={{ backgroundColor: bg, color: fg }}
                    >
                      {cat.name}
                    </span>
                  );
                })()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          items={buildTransactionContextMenuItems({
            tx: contextMenu.tx,
            selectedIds: [contextMenu.tx.id],
            categoryGroups,
            onCategorize: (ids, categoryId) => categorizeMutation.mutate({ ids, categoryId }),
            onCreateRule,
            onShowDetails: (id) => setDetailTxId(id),
            t,
          })}
          onClose={() => setContextMenu(null)}
        />
      )}
      <TransactionDetailModal txId={detailTxId} onClose={() => setDetailTxId(null)} />
    </>
  );
}

export default function BatchHistory() {
  const { t } = useTranslation();
  const statusLabel = (s: Batch["status"]): string => {
    if (s === "processing") return t("status.processing");
    if (s === "failed") return t("status.failed");
    return t("status.completed");
  };
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [rulePrefill, setRulePrefill] = useState<RulePrefill | null>(null);
  const { data: batches = [], isLoading, isError } = useQuery({
    queryKey: ["batches"],
    queryFn: listBatches,
    refetchInterval: 3000,
  });
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const accountName = (id: string) => accounts.find((a) => a.id === id)?.name ?? id;

  const retry = useMutation({
    mutationFn: (id: string) => client.post(`/api/imports/${id}/retry`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["batches"] }),
    onError: () => alert(t("imports.retryFailed")),
  });

  if (isLoading) return <p className="text-gray-400 text-sm">{t("imports.loadingHistory")}</p>;
  if (isError) return <p className="text-red-500 text-sm px-6 py-4">{t("imports.historyFailed")}</p>;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <h2 className="text-lg font-semibold px-6 py-4 border-b">{t("imports.historyTitle")}</h2>
      {batches.length === 0 ? (
        <p className="px-6 py-8 text-gray-400 text-sm">{t("imports.noImports")}</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              {[
                t("imports.historyColFile"),
                t("imports.historyColAccount"),
                t("imports.historyColRows"),
                t("imports.historyColImported"),
                t("imports.historyColDuplicates"),
                t("common.status"),
                t("common.date"),
              ].map((h) => (
                <th key={h} className="px-4 py-2 text-left">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {batches.map((b) => (
              <React.Fragment key={b.id}>
                <tr
                  className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpanded(expanded === b.id ? null : b.id)}
                >
                  <td className="px-4 py-3 font-mono text-xs">{b.filename}</td>
                  <td className="px-4 py-3 text-gray-500">{accountName(b.account_id)}</td>
                  <td className="px-4 py-3">{b.row_count}</td>
                  <td className="px-4 py-3 text-green-700">{b.imported_count}</td>
                  <td className="px-4 py-3 text-gray-400">{b.duplicate_count}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_BADGE[b.status]}`} title={b.error_message ?? undefined}>
                      {statusLabel(b.status)}
                    </span>
                    {b.status === "failed" && (
                      <button
                        className="ml-2 text-blue-500 text-xs hover:underline"
                        onClick={(e) => { e.stopPropagation(); retry.mutate(b.id); }}
                        disabled={retry.isPending && retry.variables === b.id}
                      >
                        {t("common.retry")}
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{new Date(b.imported_at).toLocaleDateString("cs-CZ")}</td>
                </tr>
                {expanded === b.id && (
                  <tr key={`${b.id}-detail`}>
                    <td colSpan={7} className="px-4 py-3 bg-gray-50">
                      <BatchTransactions batchId={b.id} onCreateRule={setRulePrefill} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}

      <SlideOverPanel
        open={rulePrefill !== null}
        onClose={() => setRulePrefill(null)}
        title={t("rules.newRule")}
      >
        {rulePrefill && (
          <RuleForm prefill={rulePrefill} onClose={() => setRulePrefill(null)} />
        )}
      </SlideOverPanel>
    </div>
  );
}
