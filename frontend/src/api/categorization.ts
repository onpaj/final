import client from "./client";

export interface BatchClassificationResult {
  categorized: number;
  needs_review: number;
}

export async function runBatchClassification(): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    {},
  );
  return data;
}

export async function recategorizeBatch(
  transaction_ids: string[],
  steps: string[],
): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorize/batch",
    { transaction_ids, steps },
  );
  return data;
}
