import { NavLink } from "react-router-dom";
import ProcessingStatus from "./ProcessingStatus";

const links = [
  { to: "/", label: "Analytics" },
  { to: "/imports", label: "Imports" },
  { to: "/rules", label: "Rules" },
  { to: "/settings", label: "Settings" },
];

export default function NavBar() {
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
        <ProcessingStatus />
      </div>
    </nav>
  );
}
