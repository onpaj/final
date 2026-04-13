import { useDroppable } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";
import type { CategoryGroup } from "../../api/categories";

interface DroppableCategoryProps {
  id: string;
  name: string;
  isCurrent: boolean;
  isOver: boolean;
}

function DroppableCategory({ id, name, isCurrent, isOver }: DroppableCategoryProps) {
  const { setNodeRef } = useDroppable({ id, disabled: isCurrent });

  return (
    <div
      ref={setNodeRef}
      className={[
        "px-3 py-2 rounded-md text-sm transition-colors border",
        isCurrent
          ? "bg-blue-100 text-blue-700 font-medium border-transparent"
          : isOver
          ? "bg-blue-50 border-blue-400 text-blue-800"
          : "text-gray-700 border-transparent hover:bg-gray-50",
      ].join(" ")}
    >
      {isCurrent && <span className="mr-1.5 text-blue-400">●</span>}
      {name}
    </div>
  );
}

interface Props {
  categoryGroups: CategoryGroup[];
  currentCategoryId: string;
  overId: string | null;
}

export default function CategorySidebar({ categoryGroups, currentCategoryId, overId }: Props) {
  const { t } = useTranslation();

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-8rem)]">
      <p className="text-xs text-gray-500 uppercase tracking-wide font-medium px-1">
        {t("analytics.dropToReassign")}
      </p>
      {categoryGroups.map((group) => (
        <div key={group.id}>
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1 px-1">
            {group.name}
          </p>
          <div className="flex flex-col gap-0.5">
            {group.categories.map((cat) => (
              <DroppableCategory
                key={cat.id}
                id={cat.id}
                name={cat.name}
                isCurrent={cat.id === currentCategoryId}
                isOver={overId === cat.id}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
