import client from "./client";

export interface Account {
  id: string;
  name: string;
  bank: string;
  currency: string;
  is_active: boolean;
}

export async function listAccounts(): Promise<Account[]> {
  const { data } = await client.get<Account[]>("/api/accounts");
  return data;
}
