import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { Category } from "../../api/categories";
import { createCategory, updateCategory } from "../../api/categories";

interface Props {
  groupId: string;
  category?: Category;
  onClose: () => void;
}

export default function CategoryForm({ groupId, category, onClose }: Props) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState(category?.name ?? "");
  const [color, setColor] = useState(category?.color ?? "#6366f1");
  const [isIncome, setIsIncome] = useState(category?.is_income ?? false);
  const [isIgnored, setIsIgnored] = useState(category?.is_ignored ?? false);
  const [hint, setHint] = useState(category?.hint ?? "");

  const save = useMutation({
    mutationFn: () =>
      category
        ? updateCategory(category.id, { name, color, is_income: isIncome, is_ignored: isIgnored, hint: hint || null })
        : createCategory({ group_id: groupId, name, color, is_income: isIncome, is_ignored: isIgnored, hint: hint || null }),
    onSuccess: () => {
      qc.refetchQueries({ queryKey: ["category-groups"] });
      onClose();
    },
  });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        save.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("categories.fieldName")}</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("categories.fieldColor")}</label>
        <input
          type="color"
          value={color ?? "#6366f1"}
          onChange={(e) => setColor(e.target.value)}
          className="w-full h-10 border border-gray-300 rounded cursor-pointer p-1"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">{t("categories.fieldHint")}</label>
        <textarea
          value={hint}
          onChange={(e) => setHint(e.target.value)}
          rows={2}
          placeholder={t("categories.fieldHintPlaceholder")}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm resize-none"
        />
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_income"
          checked={isIncome}
          onChange={(e) => setIsIncome(e.target.checked)}
          className="rounded"
        />
        <label htmlFor="is_income" className="text-sm font-medium text-gray-700">
          {t("categories.fieldIsIncome")}
        </label>
      </div>
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          id="is_ignored"
          checked={isIgnored}
          onChange={(e) => setIsIgnored(e.target.checked)}
          className="rounded"
        />
        <label htmlFor="is_ignored" className="text-sm font-medium text-gray-700">
          {t("categories.fieldIsIgnored")}
        </label>
      </div>
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={save.isPending}
          className="flex-1 bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {t("common.save")}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="flex-1 border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}
