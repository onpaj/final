import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Rule, deleteRule, listRules, updateRule } from "../../api/rules";
import { listCategoryGroups } from "../../api/categories";
import SlideOverPanel from "../../components/SlideOverPanel";
import RuleForm from "./RuleForm";

export default function RulesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: rules = [] } = useQuery({ queryKey: ["rules"], queryFn: listRules });
  const { data: groups = [] } = useQuery({ queryKey: ["category-groups"], queryFn: listCategoryGroups });
  const [panel, setPanel] = useState<{ rule?: Rule } | null>(null);

  const categoryById = useMemo(() => {
    const map: Record<string, string> = {};
    groups.forEach((g) => g.categories.forEach((c) => { map[c.id] = c.name; }));
    return map;
  }, [groups]);

  const remove = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  const toggle = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => updateRule(id, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t("rules.title")}</h1>
        <button
          onClick={() => setPanel({})}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700"
        >
          + {t("rules.newRule")}
        </button>
      </div>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              {[
                t("rules.colPriority"),
                t("rules.colName"),
                t("rules.colType"),
                t("rules.colMatchValue"),
                t("rules.colCategory"),
                t("rules.colHits"),
                t("rules.colEnabled"),
                "",
              ].map((h, i) => (
                <th key={i} className="px-4 py-2 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3">{r.priority}</td>
                <td className="px-4 py-3 font-medium">{r.name}</td>
                <td className="px-4 py-3 text-xs">
                  {t(`rules.matchType.${r.match_type}`, r.match_type)}
                </td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px] truncate">
                  {String(r.match_value.account ?? r.match_value.value ?? "")}
                </td>
                <td className="px-4 py-3 text-xs">{categoryById[r.category_id] ?? "—"}</td>
                <td className="px-4 py-3">{r.hit_count}</td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => toggle.mutate({ id: r.id, enabled: !r.enabled })}
                    className={`px-2 py-0.5 rounded text-xs ${
                      r.enabled ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {r.enabled ? t("rules.active") : t("rules.disabled")}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-3">
                    <button
                      onClick={() => setPanel({ rule: r })}
                      className="text-blue-500 text-xs hover:underline"
                    >
                      {t("common.edit")}
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(t("rules.deleteConfirm"))) remove.mutate(r.id);
                      }}
                      className="text-red-500 text-xs hover:underline"
                    >
                      {t("common.delete")}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SlideOverPanel
        open={panel !== null}
        onClose={() => setPanel(null)}
        title={panel?.rule ? t("rules.editRule") : t("rules.newRule")}
      >
        {panel !== null && <RuleForm rule={panel.rule} onClose={() => setPanel(null)} />}
      </SlideOverPanel>
    </div>
  );
}
