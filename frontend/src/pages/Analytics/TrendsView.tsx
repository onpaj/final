import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { getTrends } from "../../api/analytics";

interface Props {
  year: number;
  month: number;
}

const COLORS = ["#4CAF50", "#2196F3", "#FF9800", "#E91E63", "#9C27B0", "#009688", "#607D8B"];

export default function TrendsView({ year, month }: Props) {
  const { t } = useTranslation();
  const fromYear = month <= 6 ? year - 1 : year;
  const fromMonth = month <= 6 ? month + 6 : month - 6;

  const { data: points = [], isLoading } = useQuery({
    queryKey: ["trends", year, month],
    queryFn: () => getTrends({ from_year: fromYear, from_month: fromMonth, to_year: year, to_month: month }),
  });

  const pivoted: Record<string, Record<string, number>> = {};
  const groups = new Set<string>();
  for (const p of points) {
    const key = `${p.year}-${String(p.month).padStart(2, "0")}`;
    pivoted[key] = pivoted[key] || {};
    pivoted[key][p.group] = (pivoted[key][p.group] || 0) + Math.abs(p.total);
    if (!p.is_income) groups.add(p.group);
  }
  const chartData = Object.entries(pivoted)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, vals]) => ({ month: key, ...vals }));
  const groupList = Array.from(groups);

  if (isLoading) return <p className="text-gray-400 text-sm">{t("analytics.loadingTrends")}</p>;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4">
      <h3 className="text-sm font-semibold mb-4 text-gray-700">{t("analytics.trendsTitle")}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <XAxis dataKey="month" tick={{ fontSize: 11 }} />
          <YAxis tick={{ fontSize: 11 }} />
          <Tooltip formatter={(v: number) => `${v.toLocaleString("cs-CZ")} CZK`} />
          <Legend />
          {groupList.map((g, i) => (
            <Line key={g} type="monotone" dataKey={g} stroke={COLORS[i % COLORS.length]} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
