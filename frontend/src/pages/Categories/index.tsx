import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { DragEndEvent } from "@dnd-kit/core";
import {
  DndContext,
  closestCenter,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Category, CategoryGroup } from "../../api/categories";
import {
  listCategoryGroups,
  createGroup,
  updateGroup,
  deleteGroup,
  reorderGroups,
  deleteCategory,
  clearAllCategories,
  reorderCategories,
} from "../../api/categories";
import SlideOverPanel from "../../components/SlideOverPanel";
import CategoryForm from "./CategoryForm";

function SortableGroupItem({
  group,
  selected,
  editing,
  onSelect,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onDelete,
}: {
  group: CategoryGroup;
  selected: boolean;
  editing: boolean;
  onSelect: () => void;
  onStartEdit: () => void;
  onSaveEdit: (name: string, color: string) => void;
  onCancelEdit: () => void;
  onDelete: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: group.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  const [editName, setEditName] = useState(group.name);
  const [editColor, setEditColor] = useState(group.color ?? "#6366f1");

  if (editing) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 border-t border-gray-100">
        <input
          autoFocus
          value={editName}
          onChange={(e) => setEditName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") onSaveEdit(editName, editColor);
            if (e.key === "Escape") onCancelEdit();
          }}
          className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
        />
        <input
          type="color"
          value={editColor}
          onChange={(e) => setEditColor(e.target.value)}
          className="w-8 h-8 border-0 cursor-pointer rounded p-0"
        />
        <button onClick={() => onSaveEdit(editName, editColor)} className="text-blue-600 text-xs hover:underline">✓</button>
        <button onClick={onCancelEdit} className="text-gray-500 text-xs hover:underline">✕</button>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`flex items-center gap-2 px-3 py-2 border-t border-gray-100 ${
        selected ? "bg-blue-50" : "hover:bg-gray-50"
      }`}
    >
      <span {...attributes} {...listeners} className="text-gray-300 cursor-grab text-lg select-none">
        ⠿
      </span>
      {group.color && (
        <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: group.color }} />
      )}
      <span className="flex-1 text-sm font-medium truncate cursor-pointer" onClick={onSelect}>
        {group.name}
      </span>
      <button onClick={onStartEdit} className="text-gray-400 hover:text-gray-600 text-xs">✎</button>
      <button onClick={onDelete} className="text-gray-400 hover:text-red-500 text-xs">✕</button>
    </div>
  );
}

function SortableCategoryItem({
  category,
  onEdit,
  onDelete,
}: {
  category: Category;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: category.id });
  const style = { transform: CSS.Transform.toString(transform), transition };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="flex items-center gap-2 px-3 py-2 border-t border-gray-100 hover:bg-gray-50"
    >
      <span {...attributes} {...listeners} className="text-gray-300 cursor-grab text-lg select-none">
        ⠿
      </span>
      {category.color && (
        <span className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: category.color }} />
      )}
      <span className="flex-1 text-sm">{category.name}</span>
      {category.hint && (
        <span className="text-xs text-gray-400 truncate max-w-[160px]" title={category.hint}>{category.hint}</span>
      )}
      {category.is_income && (
        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">{t("categories.income")}</span>
      )}
      {category.is_system && (
        <span className="text-xs text-gray-400" title="System category">🔒</span>
      )}
      <button onClick={onEdit} className="text-gray-400 hover:text-gray-600 text-xs">✎</button>
      {!category.is_system && (
        <button onClick={onDelete} className="text-gray-400 hover:text-red-500 text-xs">✕</button>
      )}
    </div>
  );
}

export default function CategoriesPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: groups = [] } = useQuery({ queryKey: ["category-groups"], queryFn: listCategoryGroups });

  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null);
  const [addingGroup, setAddingGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState("");
  const [newGroupColor, setNewGroupColor] = useState("#6366f1");
  const [categoryPanel, setCategoryPanel] = useState<{ groupId: string; category?: Category } | null>(null);
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null);
  const [replacementCategoryId, setReplacementCategoryId] = useState<string>("");

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }));
  const selectedGroup = groups.find((g) => g.id === selectedGroupId) ?? null;

  const refetchGroups = () => qc.refetchQueries({ queryKey: ["category-groups"] });

  const addGroup = useMutation({
    mutationFn: (vars: { name: string; color: string }) => createGroup(vars),
    onSuccess: () => {
      refetchGroups();
      setAddingGroup(false);
      setNewGroupName("");
    },
  });

  const patchGroup = useMutation({
    mutationFn: (vars: { id: string; name: string; color: string }) =>
      updateGroup(vars.id, { name: vars.name, color: vars.color }),
    onSuccess: () => {
      refetchGroups();
      setEditingGroupId(null);
    },
  });

  const removeGroup = useMutation({
    mutationFn: deleteGroup,
    onSuccess: () => {
      refetchGroups();
      setSelectedGroupId(null);
    },
  });

  const reorderGroupsMutation = useMutation({
    mutationFn: reorderGroups,
    onSuccess: () => refetchGroups(),
  });

  const removeCategory = useMutation({
    mutationFn: ({ id, replacementId }: { id: string; replacementId?: string }) =>
      deleteCategory(id, replacementId),
    onSuccess: () => {
      refetchGroups();
      setDeletingCategory(null);
      setReplacementCategoryId("");
    },
  });

  const reorderCategoriesMutation = useMutation({
    mutationFn: reorderCategories,
    onSuccess: () => refetchGroups(),
  });

  const clearAll = useMutation({
    mutationFn: clearAllCategories,
    onSuccess: () => {
      refetchGroups();
      setSelectedGroupId(null);
    },
  });

  function handleGroupDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = groups.findIndex((g) => g.id === active.id);
    const newIndex = groups.findIndex((g) => g.id === over.id);
    const reordered = arrayMove(groups, oldIndex, newIndex);
    reorderGroupsMutation.mutate(reordered.map((g, i) => ({ id: g.id, sort_order: i })));
  }

  function handleCategoryDragEnd(event: DragEndEvent) {
    if (!selectedGroup) return;
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const cats = selectedGroup.categories;
    const oldIndex = cats.findIndex((c) => c.id === active.id);
    const newIndex = cats.findIndex((c) => c.id === over.id);
    const reordered = arrayMove(cats, oldIndex, newIndex);
    reorderCategoriesMutation.mutate(reordered.map((c, i) => ({ id: c.id, sort_order: i })));
  }

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t("categories.title")}</h1>
        <button
          onClick={() => {
            if (window.confirm(t("categories.clearAllConfirm"))) {
              clearAll.mutate();
            }
          }}
          disabled={clearAll.isPending}
          className="text-sm text-red-600 hover:text-red-800 disabled:opacity-50"
        >
          {t("categories.clearAll")}
        </button>
      </div>
      <div className="flex gap-6">
        {/* Left: Groups */}
        <div className="w-80 flex-shrink-0">
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100">
              <span className="text-sm font-semibold text-gray-700">{t("categories.groupsTitle")}</span>
            </div>
            <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleGroupDragEnd}>
              <SortableContext items={groups.map((g) => g.id)} strategy={verticalListSortingStrategy}>
                {groups.map((g) => (
                  <SortableGroupItem
                    key={g.id}
                    group={g}
                    selected={selectedGroupId === g.id}
                    editing={editingGroupId === g.id}
                    onSelect={() => setSelectedGroupId(g.id)}
                    onStartEdit={() => setEditingGroupId(g.id)}
                    onSaveEdit={(name, color) => patchGroup.mutate({ id: g.id, name, color })}
                    onCancelEdit={() => setEditingGroupId(null)}
                    onDelete={() => removeGroup.mutate(g.id)}
                  />
                ))}
              </SortableContext>
            </DndContext>
            {addingGroup ? (
              <div className="flex items-center gap-2 px-3 py-2 border-t border-gray-100">
                <input
                  autoFocus
                  value={newGroupName}
                  onChange={(e) => setNewGroupName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && newGroupName.trim()) addGroup.mutate({ name: newGroupName, color: newGroupColor });
                    if (e.key === "Escape") setAddingGroup(false);
                  }}
                  placeholder={t("categories.fieldName")}
                  className="flex-1 border border-gray-300 rounded px-2 py-1 text-sm"
                />
                <input
                  type="color"
                  value={newGroupColor}
                  onChange={(e) => setNewGroupColor(e.target.value)}
                  className="w-8 h-8 border-0 cursor-pointer rounded p-0"
                />
                <button
                  onClick={() => { if (newGroupName.trim()) addGroup.mutate({ name: newGroupName, color: newGroupColor }); }}
                  className="text-blue-600 text-xs hover:underline"
                >
                  ✓
                </button>
                <button onClick={() => setAddingGroup(false)} className="text-gray-500 text-xs hover:underline">✕</button>
              </div>
            ) : (
              <button
                onClick={() => setAddingGroup(true)}
                className="w-full px-4 py-2 text-sm text-blue-600 hover:bg-gray-50 text-left border-t border-gray-100"
              >
                + {t("categories.newGroup")}
              </button>
            )}
          </div>
        </div>

        {/* Right: Categories */}
        <div className="flex-1">
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-700">
                {selectedGroup ? selectedGroup.name : t("categories.categoriesTitle")}
              </span>
              {selectedGroup && (
                <button
                  onClick={() => setCategoryPanel({ groupId: selectedGroup.id })}
                  className="text-sm text-blue-600 hover:underline"
                >
                  + {t("categories.newCategory")}
                </button>
              )}
            </div>
            {!selectedGroup ? (
              <p className="px-4 py-8 text-sm text-gray-400 text-center">{t("categories.selectGroup")}</p>
            ) : (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleCategoryDragEnd}>
                <SortableContext
                  items={selectedGroup.categories.map((c) => c.id)}
                  strategy={verticalListSortingStrategy}
                >
                  {selectedGroup.categories.map((c) => (
                    <SortableCategoryItem
                      key={c.id}
                      category={c}
                      onEdit={() => setCategoryPanel({ groupId: selectedGroup.id, category: c })}
                      onDelete={() => { setDeletingCategory(c); setReplacementCategoryId(""); }}
                    />
                  ))}
                </SortableContext>
              </DndContext>
            )}
          </div>
        </div>
      </div>

      <SlideOverPanel
        open={categoryPanel !== null}
        onClose={() => setCategoryPanel(null)}
        title={categoryPanel?.category ? t("categories.editCategory") : t("categories.newCategory")}
      >
        {categoryPanel && (
          <CategoryForm
            groupId={categoryPanel.groupId}
            category={categoryPanel.category}
            onClose={() => setCategoryPanel(null)}
          />
        )}
      </SlideOverPanel>

      {deletingCategory && (
        <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-96 max-w-full mx-4">
            <h2 className="text-base font-semibold text-gray-900 mb-1">
              {t("categories.deleteCategory")}
            </h2>
            <p className="text-sm text-gray-500 mb-4">
              <span className="font-medium">{deletingCategory.name}</span>
              {" — "}{t("categories.deleteCategoryHint")}
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {t("categories.reassignTo")}
              </label>
              <select
                value={replacementCategoryId}
                onChange={(e) => setReplacementCategoryId(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              >
                <option value="">{t("categories.reassignNone")}</option>
                {groups.flatMap((g) =>
                  g.categories
                    .filter((c) => c.id !== deletingCategory.id)
                    .map((c) => (
                      <option key={c.id} value={c.id}>
                        {g.name} / {c.name}
                      </option>
                    ))
                )}
              </select>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() =>
                  removeCategory.mutate({
                    id: deletingCategory.id,
                    replacementId: replacementCategoryId || undefined,
                  })
                }
                disabled={removeCategory.isPending}
                className="flex-1 bg-red-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {t("categories.confirmDelete")}
              </button>
              <button
                onClick={() => setDeletingCategory(null)}
                className="flex-1 border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
              >
                {t("common.cancel")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
