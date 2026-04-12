import { useDraggable } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";
import type { Transaction } from "../../api/transactions";

interface DraggableRowProps {
  transaction: Transaction;
  isChecked: boolean;
  isDragActive: boolean;
  onToggle: () => void;
  onContextMenu: (e: React.MouseEvent, tx: Transaction) => void;
}

function DraggableRow({ transaction: tx, isChecked, isDragActive, onToggle, onContextMenu }: DraggableRowProps) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({ id: tx.id });

  return (
    <tr
      ref={setNodeRef}
      className={[
        "border-t border-gray-100",
        isDragging ? "opacity-40" : "hover:bg-gray-50",
        isChecked && !isDragging ? "bg-blue-50" : "",
      ].join(" ")}
      style={{ cursor: isDragActive ? "grabbing" : "grab" }}
      onContextMenu={(e) => onContextMenu(e, tx)}
      {...attributes}
      {...listeners}
    >
      <td className="px-4 py-2.5" onPointerDown={(e) => e.stopPropagation()}>
        <input
          type="checkbox"
          checked={isChecked}
          onChange={onToggle}
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
}

interface Props {
  transactions: Transaction[];
  selected: Set<string>;
  activeId: string | null;
  onToggleRow: (id: string) => void;
  onToggleAll: () => void;
  onContextMenu: (e: React.MouseEvent, tx: Transaction) => void;
}

export default function TransactionTable({ transactions, selected, activeId, onToggleRow, onToggleAll, onContextMenu }: Props) {
  const { t } = useTranslation();
  const allSelected = transactions.length > 0 && selected.size === transactions.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
          <tr>
            <th className="px-4 py-2 w-8">
              <input
                type="checkbox"
                checked={allSelected}
                ref={(el) => { if (el) el.indeterminate = someSelected; }}
                onChange={onToggleAll}
                className="cursor-pointer"
              />
            </th>
            {[t("analytics.txDate"), t("analytics.txCounterparty"), t("analytics.txDescription"), t("analytics.txAmount")].map((h) => (
              <th key={h} className="px-4 py-2 text-left">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {transactions.map((tx) => (
            <DraggableRow
              key={tx.id}
              transaction={tx}
              isChecked={selected.has(tx.id)}
              isDragActive={activeId !== null}
              onToggle={() => onToggleRow(tx.id)}
              onContextMenu={onContextMenu}
            />
          ))}
        </tbody>
      </table>
      {transactions.length === 0 && (
        <p className="px-4 py-8 text-center text-gray-400 text-sm">{t("analytics.noTransactions")}</p>
      )}
    </div>
  );
}
