import { DragOverlay } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";

interface Props {
  activeId: string | null;
  count: number;
}

export default function TransactionDragOverlay({ activeId, count }: Props) {
  const { t } = useTranslation();
  return (
    <DragOverlay>
      {activeId ? (
        <div className="px-3 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg shadow-lg whitespace-nowrap">
          {t("analytics.movingTransactions", { count })}
        </div>
      ) : null}
    </DragOverlay>
  );
}
