import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import ProcessingStatus from "./ProcessingStatus";
import { useDataFreshness } from "../context/DataFreshness";
import { listTransactions } from "../api/transactions";

export default function NavBar() {
  const { markStale } = useDataFreshness();
  const { t } = useTranslation();

  const { data: reviewTxs = [] } = useQuery({
    queryKey: ["transactions", "needs_review"],
    queryFn: () => listTransactions({ needs_review: true, limit: 500 }),
    staleTime: 30_000,
  });
  const reviewCount = reviewTxs.length;

  const links = [
    { to: "/", label: t("nav.analytics") },
    { to: "/imports", label: t("nav.imports") },
    { to: "/rules", label: t("nav.rules") },
    { to: "/categories", label: t("nav.categories") },
    { to: "/settings", label: t("nav.settings") },
  ];

  return (
    <nav className="flex items-center gap-1 px-6 py-3 border-b border-gray-200 bg-white">
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === "/"}
          className={({ isActive }) =>
            `px-4 py-2 rounded text-sm font-medium transition-colors ` +
            (isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100")
          }
        >
          {l.label}
        </NavLink>
      ))}
      <NavLink
        to="/review"
        className={({ isActive }) =>
          `flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-colors ` +
          (isActive ? "bg-blue-600 text-white" : "text-gray-600 hover:bg-gray-100")
        }
      >
        {t("nav.review")}
        {reviewCount > 0 && (
          <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 rounded-full text-xs font-bold bg-red-500 text-white">
            {reviewCount}
          </span>
        )}
      </NavLink>
      <div className="ml-auto">
        <ProcessingStatus onJobCompleted={markStale} />
      </div>
    </nav>
  );
}
