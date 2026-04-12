import { useEffect, useRef, useState } from "react";
import ReactDOM from "react-dom";

interface ContextMenuItem {
  label: string;
  onClick?: () => void;
  children?: ContextMenuItem[];
}

interface Props {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export default function ContextMenu({ x, y, items, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const submenuRef = useRef<HTMLDivElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [submenu, setSubmenu] = useState<{ label: string; top: number; left: number } | null>(null);

  const menuWidth = 220;
  const submenuWidth = 220;
  const menuHeight = items.length * 36;
  const left = Math.min(x, window.innerWidth - menuWidth - 8);
  const top = Math.min(y, window.innerHeight - menuHeight - 8);

  useEffect(() => {
    function handleMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      const inMain = ref.current?.contains(target);
      const inSub = submenuRef.current?.contains(target);
      if (!inMain && !inSub) onClose();
    }
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [onClose]);

  function openSubmenu(label: string, itemEl: HTMLElement) {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    const rect = itemEl.getBoundingClientRect();
    const subLeft =
      rect.right + submenuWidth <= window.innerWidth - 8
        ? rect.right
        : rect.left - submenuWidth;
    setSubmenu({ label, top: rect.top, left: subLeft });
  }

  function scheduleClose() {
    closeTimer.current = setTimeout(() => setSubmenu(null), 100);
  }

  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }

  const activeItem = submenu ? items.find((i) => i.label === submenu.label) : null;

  return (
    <>
      {ReactDOM.createPortal(
        <div
          ref={ref}
          style={{ position: "fixed", top, left, zIndex: 9999 }}
          className="bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[180px]"
        >
          {items.map((item) =>
            item.children ? (
              <div
                key={item.label}
                onMouseEnter={(e) => openSubmenu(item.label, e.currentTarget)}
                onMouseLeave={scheduleClose}
                className="px-4 py-2 text-sm hover:bg-gray-100 flex items-center justify-between cursor-default select-none"
              >
                <span>{item.label}</span>
                <span className="text-gray-400 ml-2 text-xs">▶</span>
              </div>
            ) : (
              <button
                key={item.label}
                onClick={() => {
                  item.onClick?.();
                  onClose();
                }}
                className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
              >
                {item.label}
              </button>
            )
          )}
        </div>,
        document.body
      )}
      {submenu && activeItem?.children &&
        ReactDOM.createPortal(
          <div
            ref={submenuRef}
            style={{ position: "fixed", top: submenu.top, left: submenu.left, zIndex: 10000 }}
            className="bg-white border border-gray-200 rounded shadow-lg py-1 min-w-[180px] max-h-96 overflow-y-auto"
            onMouseEnter={cancelClose}
            onMouseLeave={scheduleClose}
          >
            {activeItem.children.map((child) =>
              child.label.startsWith("__header__") ? (
                <div
                  key={child.label}
                  className="px-4 py-1 text-xs font-semibold text-gray-400 uppercase tracking-wide"
                >
                  {child.label.slice("__header__".length)}
                </div>
              ) : (
                <button
                  key={child.label}
                  onClick={() => {
                    child.onClick?.();
                    onClose();
                  }}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-gray-100"
                >
                  {child.label}
                </button>
              )
            )}
          </div>,
          document.body
        )}
    </>
  );
}
