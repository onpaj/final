import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listBatches, type Batch } from "../../api/imports";
import { listAccounts } from "../../api/accounts";
import client from "../../api/client";

const STATUS_BADGE: Record<Batch["status"], string> = {
  processing: "bg-yellow-100 text-yellow-800",
  completed: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
};

function BatchTransactions({ batchId }: { batchId: string }) {
  const { data: txs = [], isLoading } = useQuery({
    queryKey: ["batch-transactions", batchId],
    queryFn: async () => (await client.get(`/api/imports/${batchId}/transactions`)).data,
  });

  if (isLoading) return <p className="text-xs text-gray-400">Loading transactions…</p>;
  if (txs.length === 0) return <p className="text-xs text-gray-400">No transactions found.</p>;

  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="text-gray-400 uppercase text-xs">
          <th className="pr-4 py-1 text-left">Date</th>
          <th className="pr-4 py-1 text-left">Counterparty</th>
          <th className="pr-4 py-1 text-right">Amount</th>
          <th className="pr-4 py-1 text-left">Currency</th>
        </tr>
      </thead>
      <tbody>
        {txs.map((tx: any) => (
          <tr key={tx.id} className="border-t border-gray-100">
            <td className="pr-4 py-1 text-gray-500">{tx.booking_date}</td>
            <td className="pr-4 py-1">{tx.counterparty_name || "—"}</td>
            <td className={`pr-4 py-1 text-right font-medium ${tx.amount < 0 ? "text-red-500" : "text-green-600"}`}>
              {tx.amount.toLocaleString("cs-CZ")}
            </td>
            <td className="pr-4 py-1 text-gray-400">{tx.currency}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function BatchHistory() {
  const qc = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);
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
    onError: () => alert("Retry failed — the original file may no longer be available."),
  });

  if (isLoading) return <p className="text-gray-400 text-sm">Loading…</p>;
  if (isError) return <p className="text-red-500 text-sm px-6 py-4">Failed to load import history.</p>;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <h2 className="text-lg font-semibold px-6 py-4 border-b">Import History</h2>
      {batches.length === 0 ? (
        <p className="px-6 py-8 text-gray-400 text-sm">No imports yet.</p>
      ) : (
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
            <tr>
              {["File", "Account", "Rows", "Imported", "Duplicates", "Status", "Date"].map((h) => (
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
                      {b.status}
                    </span>
                    {b.status === "failed" && (
                      <button
                        className="ml-2 text-blue-500 text-xs hover:underline"
                        onClick={(e) => { e.stopPropagation(); retry.mutate(b.id); }}
                        disabled={retry.isPending && retry.variables === b.id}
                      >
                        Retry
                      </button>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-400">{new Date(b.imported_at).toLocaleDateString()}</td>
                </tr>
                {expanded === b.id && (
                  <tr key={`${b.id}-detail`}>
                    <td colSpan={7} className="px-4 py-3 bg-gray-50">
                      <BatchTransactions batchId={b.id} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
