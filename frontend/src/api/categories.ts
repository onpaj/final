import client from "./client";

export interface Category {
  id: string;
  group_id: string;
  name: string;
  is_income: boolean;
  is_system: boolean;
  color: string | null;
  sort_order: number;
}

export interface CategoryGroup {
  id: string;
  name: string;
  color: string | null;
  sort_order: number;
  categories: Category[];
}

export interface ReorderItem {
  id: string;
  sort_order: number;
}

export async function listCategoryGroups(): Promise<CategoryGroup[]> {
  const { data } = await client.get<CategoryGroup[]>("/api/categories/groups");
  return data;
}

export async function listCategories(): Promise<Category[]> {
  const { data } = await client.get<Category[]>("/api/categories");
  return data;
}

export async function createGroup(body: { name: string; color?: string }): Promise<CategoryGroup> {
  const { data } = await client.post<CategoryGroup>("/api/categories/groups", body);
  return data;
}

export async function updateGroup(id: string, body: { name?: string; color?: string }): Promise<CategoryGroup> {
  const { data } = await client.patch<CategoryGroup>(`/api/categories/groups/${id}`, body);
  return data;
}

export async function deleteGroup(id: string): Promise<void> {
  await client.delete(`/api/categories/groups/${id}`);
}

export async function reorderGroups(items: ReorderItem[]): Promise<CategoryGroup[]> {
  const { data } = await client.patch<CategoryGroup[]>("/api/categories/groups/reorder", items);
  return data;
}

export async function createCategory(body: {
  group_id: string;
  name: string;
  color?: string;
  is_income?: boolean;
}): Promise<Category> {
  const { data } = await client.post<Category>("/api/categories", body);
  return data;
}

export async function updateCategory(
  id: string,
  body: { name?: string; color?: string; is_income?: boolean }
): Promise<Category> {
  const { data } = await client.patch<Category>(`/api/categories/${id}`, body);
  return data;
}

export async function deleteCategory(id: string): Promise<void> {
  await client.delete(`/api/categories/${id}`);
}

export async function reorderCategories(items: ReorderItem[]): Promise<Category[]> {
  const { data } = await client.patch<Category[]>("/api/categories/reorder", items);
  return data;
}
