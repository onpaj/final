import client from "./client";

export interface Rule {
  id: string;
  name: string;
  priority: number;
  match_type: string;
  match_value: Record<string, unknown>;
  category_id: string;
  enabled: boolean;
  hit_count: number;
}

export async function listRules(): Promise<Rule[]> {
  const { data } = await client.get<Rule[]>("/api/rules");
  return data;
}

export async function createRule(
  body: Omit<Rule, "id" | "hit_count">
): Promise<Rule> {
  const { data } = await client.post<Rule>("/api/rules", body);
  return data;
}

export async function updateRule(
  id: string,
  body: Partial<Omit<Rule, "id" | "hit_count">>
): Promise<Rule> {
  const { data } = await client.patch<Rule>(`/api/rules/${id}`, body);
  return data;
}

export async function deleteRule(id: string): Promise<void> {
  await client.delete(`/api/rules/${id}`);
}
