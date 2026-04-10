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

export async function createAccount(body: { name: string; bank: string; iban?: string; currency?: string }): Promise<Account> {
  const { data } = await client.post<Account>("/api/accounts", body);
  return data;
}

export async function deleteAccount(id: string): Promise<void> {
  await client.delete(`/api/accounts/${id}`);
}
