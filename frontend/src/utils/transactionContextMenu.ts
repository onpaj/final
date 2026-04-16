import type { TFunction } from "i18next";
import type { CategoryGroup } from "../api/categories";
import type { RulePrefill } from "../pages/Rules/RuleForm";

interface TransactionLike {
  id: string;
  category_id: string | null;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
}

interface ContextMenuItem {
  label: string;
  onClick?: () => void;
  children?: ContextMenuItem[];
}

interface BuildMenuOptions {
  tx: TransactionLike;
  selectedIds: string[];
  categoryGroups: CategoryGroup[];
  onCategorize: (ids: string[], categoryId: string | null) => void;
  onCreateRule: (prefill: RulePrefill) => void;
  t: TFunction;
}

export function buildTransactionContextMenuItems({
  tx,
  selectedIds,
  categoryGroups,
  onCategorize,
  onCreateRule,
  t,
}: BuildMenuOptions): ContextMenuItem[] {
  const categoryMenuItems: ContextMenuItem[] = categoryGroups.flatMap((group) => [
    { label: `__header__${group.name}` },
    ...(group.categories ?? []).map((cat) => ({
      label: cat.name,
      onClick: () => onCategorize(selectedIds, cat.id),
    })),
  ]);

  return [
    { label: t("analytics.changeCategory"), children: categoryMenuItems },
    ...(tx.category_id
      ? [{
          label: t("analytics.unassignCategory"),
          onClick: () => onCategorize(selectedIds, null),
        }]
      : []),
    {
      label: t("analytics.createRule"),
      onClick: () =>
        onCreateRule({
          name: tx.counterparty_name ?? tx.description ?? "",
          counterpartyAccount: tx.counterparty_account,
          counterpartyName: tx.counterparty_name,
          description: tx.description,
        }),
    },
  ];
}
