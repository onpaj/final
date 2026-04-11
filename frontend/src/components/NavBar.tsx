import { NavLink } from "react-router-dom";
import { useTranslation } from "react-i18next";
import ProcessingStatus from "./ProcessingStatus";
import { useDataFreshness } from "../context/DataFreshness";

export default function NavBar() {
  const { markStale } = useDataFreshness();
  const { t } = useTranslation();

  const links = [
    { to: "/", label: t("nav.analytics") },
    { to: "/imports", label: t("nav.imports") },
    { to: "/rules", label: t("nav.rules") },
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
      <div className="ml-auto">
        <ProcessingStatus onJobCompleted={markStale} />
      </div>
    </nav>
  );
}
