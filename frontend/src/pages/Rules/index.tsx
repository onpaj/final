import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { deleteRule, listRules } from "../../api/rules";

export default function RulesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: rules = [] } = useQuery({
    queryKey: ["rules"],
    queryFn: listRules,
  });

  const remove = useMutation({
    mutationFn: deleteRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">{t("rules.title")}</h1>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              {[t("rules.colPriority"), t("rules.colName"), t("rules.colType"), t("rules.colHits"), t("common.status"), ""].map((h) => (
                <th key={h} className="px-4 py-2 text-left">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr
                key={r.id}
                className="border-t border-gray-100 hover:bg-gray-50"
              >
                <td className="px-4 py-3">{r.priority}</td>
                <td className="px-4 py-3 font-medium">{r.name}</td>
                <td className="px-4 py-3 font-mono text-xs">{r.match_type}</td>
                <td className="px-4 py-3">{r.hit_count}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs ${
                      r.enabled
                        ? "bg-green-100 text-green-700"
                        : "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {r.enabled ? t("rules.active") : t("rules.disabled")}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <button
                    className="text-red-500 text-xs hover:underline"
                    onClick={() => remove.mutate(r.id)}
                  >
                    {t("common.delete")}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
