import client from "./client";

export interface CategorySummary {
  id: string;
  name: string;
  category_slug?: string;
  total: number;
  is_income: boolean;
}

export interface GroupSummary {
  name: string;
  color: string;
  group_slug?: string;
  total: number;
  categories: CategorySummary[];
}

export interface MonthlySummary {
  year: number;
  month: number;
  groups: GroupSummary[];
  income: number;
  expenses: number;
  savings_rate: number;
}

export async function getMonthlySummary(year: number, month: number, accountId?: string): Promise<MonthlySummary> {
  const { data } = await client.get("/api/analytics/monthly", {
    params: { year, month, account_id: accountId },
  });
  return data;
}

export async function getTrends(params: {
  from_year: number;
  from_month: number;
  to_year: number;
  to_month: number;
  account_id?: string;
}): Promise<Array<{ year: number; month: number; category: string; group: string; group_slug?: string; is_income: boolean; total: number }>> {
  const { data } = await client.get("/api/analytics/trends", { params });
  return data;
}
