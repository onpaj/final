import client from "./client";

export interface Category {
  id: string;
  group_id: string;
  name: string;
  slug?: string;
  is_income: boolean;
}

export interface CategoryGroup {
  id: string;
  name: string;
  slug?: string;
  color?: string;
  sort_order: number;
  categories: Category[];
}

export async function listCategoryGroups(): Promise<CategoryGroup[]> {
  const { data } = await client.get<CategoryGroup[]>("/api/categories/groups");
  return data;
}

export async function listCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>("/api/categories");
  return data;
}
