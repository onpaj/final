import { useTranslation } from "react-i18next";
import type { GroupSummary } from "../../api/analytics";

interface Props {
  group: GroupSummary;
  onCategoryClick: (categoryId: string, categoryName: string) => void;
  onBack: () => void;
}

export default function GroupDetail({ group, onCategoryClick, onBack }: Props) {
  const { t } = useTranslation();

  return (
    <div>
      <button className="text-blue-600 text-sm mb-4 hover:underline" onClick={onBack}>
        {t("analytics.backToOverview")}
      </button>
      <h2 className="text-xl font-bold mb-4">{group.name}</h2>
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
            <tr>
              <th className="px-4 py-2 text-left">{t("analytics.category")}</th>
              <th className="px-4 py-2 text-right">{t("analytics.total")}</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {group.categories.map((c) => (
              <tr
                key={c.id}
                className="border-t border-gray-100 hover:bg-gray-50 cursor-pointer"
                onClick={() => onCategoryClick(c.id, c.name)}
              >
                <td className="px-4 py-3">{c.name}</td>
                <td className={`px-4 py-3 text-right font-medium ${c.is_income ? "text-green-600" : "text-gray-800"}`}>
                  {Math.abs(c.total).toLocaleString("cs-CZ")} CZK
                </td>
                <td className="px-4 py-3 text-gray-300 text-xs">→</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
