import client from "./client";

export interface Transaction {
  id: string;
  account_id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  is_transfer: boolean;
}

export async function listTransactions(params: {
  account_id?: string;
  date_from?: string;
  date_to?: string;
  needs_review?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Transaction[]> {
  const { data } = await client.get<Transaction[]>("/api/transactions", { params });
  return data;
}
