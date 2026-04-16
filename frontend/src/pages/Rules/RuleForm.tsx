import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { Rule } from "../../api/rules";
import { createRule, updateRule } from "../../api/rules";
import { listCategoryGroups } from "../../api/categories";
import { listAccounts } from "../../api/accounts";

export interface RulePrefill {
  name: string;
  counterpartyAccount: string | null;
  counterpartyName: string | null;
  description: string | null;
}

interface Props {
  rule?: Rule;
  prefill?: RulePrefill;
  onClose: () => void;
}

type MatchType = "counterparty_account_equals" | "counterparty_contains" | "description_contains";

function getInitialMatchValue(rule?: Rule): string {
  if (!rule) return "";
  if (rule.match_type === "counterparty_account_equals") {
    return (rule.match_value.account as string) ?? "";
  }
  return (rule.match_value.value as string) ?? "";
}

function buildMatchValue(type: MatchType, value: string): Record<string, string> {
  if (type === "counterparty_account_equals") return { account: value };
  return { value };
}

export default function RuleForm({ rule, prefill, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(rule?.name ?? prefill?.name ?? "");
  const [matchType, setMatchType] = useState<MatchType | "">(
    prefill ? "" : ((rule?.match_type as MatchType) ?? "counterparty_account_equals")
  );
  const [matchValue, setMatchValue] = useState(() => getInitialMatchValue(rule));
  const [categoryId, setCategoryId] = useState(rule?.category_id ?? "");
  const [priority, setPriority] = useState(rule?.priority ?? 100);
  const [enabled, setEnabled] = useState(rule?.enabled ?? true);
  const [accountId, setAccountId] = useState<string>(rule?.account_id ?? "");

  const { data: groups = [] } = useQuery({
    queryKey: ["category-groups"],
    queryFn: listCategoryGroups,
  });

  const { data: accounts = [] } = useQuery({
    queryKey: ["accounts"],
    queryFn: listAccounts,
  });

  const save = useMutation({
    mutationFn: () => {
      if (matchType === "") return Promise.reject(new Error("Select a match type"));
      const body = {
        name,
        match_type: matchType,
        match_value: buildMatchValue(matchType, matchValue),
        category_id: categoryId,
        priority,
        enabled,
        account_id: accountId !== "" ? accountId : null,
      };
      return rule ? updateRule(rule.id, body) : createRule(body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rules"] });
      onClose();
    },
  });

  const matchValueLabels: Record<MatchType, string> = {
    counterparty_account_equals: t("rules.fieldMatchValue.counterparty_account_equals"),
    counterparty_contains: t("rules.fieldMatchValue.counterparty_contains"),
    description_contains: t("rules.fieldMatchValue.description_contains"),
  };

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldName")}</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldMatchType")}</label>
        <select
          required
          value={matchType}
          onChange={(e) => {
            const newType = e.target.value as MatchType | "";
            setMatchType(newType);
            if (prefill && newType !== "") {
              if (newType === "counterparty_account_equals") {
                setMatchValue(prefill.counterpartyAccount ?? "");
              } else if (newType === "counterparty_contains") {
                setMatchValue(prefill.counterpartyName ?? "");
              } else if (newType === "description_contains") {
                setMatchValue(prefill.description ?? "");
              }
            } else if (!prefill) {
              setMatchValue("");
            }
          }}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          {prefill && (
            <option value="" disabled>
              {t("rules.matchTypePlaceholder")}
            </option>
          )}
          <option value="counterparty_account_equals">{t("rules.matchType.counterparty_account_equals")}</option>
          <option value="counterparty_contains">{t("rules.matchType.counterparty_contains")}</option>
          <option value="description_contains">{t("rules.matchType.description_contains")}</option>
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {matchType !== "" ? matchValueLabels[matchType] : t("rules.fieldMatchValue.default")}
        </label>
        <input
          required
          value={matchValue}
          onChange={(e) => setMatchValue(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {t("rules.fieldAccount")}
        </label>
        <select
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="">{t("rules.accountAny")}</option>
          {accounts.filter((a) => a.is_active).map((a) => (
            <option key={a.id} value={a.id}>
              {a.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldCategory")}</label>
        <select
          required
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        >
          <option value="">—</option>
          {groups.map((g) => (
            <optgroup key={g.id} label={g.name}>
              {g.categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("rules.fieldPriority")}</label>
        <input
          type="number"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="enabled"
          checked={enabled}
          onChange={(e) => setEnabled(e.target.checked)}
          className="rounded"
        />
        <label htmlFor="enabled" className="text-sm font-medium text-gray-700">
          {t("rules.fieldEnabled")}
        </label>
      </div>
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={save.isPending}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {t("common.save")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
