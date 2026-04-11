import { useTranslation } from "react-i18next";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import type { MonthlySummary } from "../../api/analytics";

interface Props {
  summary: MonthlySummary;
  onGroupClick: (groupName: string, groupSlug?: string) => void;
}

export default function MonthSummary({ summary, onGroupClick }: Props) {
  const { t } = useTranslation();
  const expenseGroups = summary.groups.filter((g) => g.total < 0);
  const pieData = expenseGroups.map((g) => ({
    name: t("cat." + (g.group_slug ?? ""), { defaultValue: g.name }),
    value: Math.abs(g.total),
    color: g.color,
  }));

  return (
    <div>
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: t("analytics.income"), value: summary.income, color: "text-green-600", raw: false },
          { label: t("analytics.expenses"), value: Math.abs(summary.expenses), color: "text-red-500", raw: false },
          { label: t("analytics.savingsRate"), value: `${(summary.savings_rate * 100).toFixed(0)}%`, color: "text-blue-600", raw: true },
        ].map(({ label, value, color, raw }) => (
          <div key={label} className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-xs text-gray-500 uppercase mb-1">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>
              {raw ? value : `${Number(value).toLocaleString("cs-CZ")} CZK`}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-4 text-gray-700">{t("analytics.spendingByGroup")}</h3>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={60} outerRadius={90}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.color || "#ccc"} />
                ))}
              </Pie>
              <Tooltip formatter={(v) => typeof v === "number" ? `${v.toLocaleString("cs-CZ")} CZK` : v} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <h3 className="text-sm font-semibold px-4 py-3 border-b text-gray-700">{t("analytics.groups")}</h3>
          <table className="w-full text-sm">
            <tbody>
              {summary.groups.map((g) => (
                <tr
                  key={g.name}
                  className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => onGroupClick(g.name, g.group_slug)}
                >
                  <td className="px-4 py-2.5">
                    <span className="inline-block w-2 h-2 rounded-full mr-2" style={{ background: g.color }} />
                    {t("cat." + (g.group_slug ?? ""), { defaultValue: g.name })}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-medium ${g.total >= 0 ? "text-green-600" : "text-gray-800"}`}>
                    {Math.abs(g.total).toLocaleString("cs-CZ")} CZK
                  </td>
                  <td className="px-4 py-2.5 text-gray-300 text-xs">→</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
