import client from "./client";

export interface Batch {
  id: string;
  account_id: string;
  filename: string;
  parser_used: string;
  row_count: number;
  imported_count: number;
  duplicate_count: number;
  status: "processing" | "completed" | "failed";
  error_message: string | null;
  imported_at: string;
}

export async function listBatches(): Promise<Batch[]> {
  const { data } = await client.get<Batch[]>("/api/imports");
  return data;
}

export async function uploadImport(
  accountId: string,
  file: File,
  columnMapping?: Record<string, string | null>,
): Promise<{ batch_id: string }> {
  const form = new FormData();
  form.append("account_id", accountId);
  form.append("file", file);
  if (columnMapping) {
    form.append("column_mapping", JSON.stringify(columnMapping));
  }
  const { data } = await client.post<{ batch_id: string }>("/api/imports", form);
  return data;
}
