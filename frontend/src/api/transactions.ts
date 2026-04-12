import client from "./client";

export interface Transaction {
  id: string;
  account_id: string;
  booking_date: string;
  amount: number;
  currency: string;
  counterparty_name: string | null;
  counterparty_account: string | null;
  description: string | null;
  category_id: string | null;
  categorization_source: string | null;
  is_transfer: boolean;
  llm_status?: "no_rule_no_llm" | "llm_rejected" | "llm_error";
  llm_confidence?: number | null;
}

export async function listTransactions(params: {
  account_id?: string;
  date_from?: string;
  date_to?: string;
  category_id?: string;
  needs_review?: boolean;
  include_llm_status?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Transaction[]> {
  const { data } = await client.get<Transaction[]>("/api/transactions", { params });
  return data;
}

export async function bulkCategorize(
  transaction_ids: string[],
  category_id: string | null,
): Promise<void> {
  await client.patch("/api/transactions/bulk-categorize", {
    transaction_ids,
    category_id,
  });
}
