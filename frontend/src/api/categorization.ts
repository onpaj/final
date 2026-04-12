import client from "./client";

export interface BatchClassificationResult {
  categorized: number;
  needs_review: number;
}

export async function runBatchClassification(): Promise<BatchClassificationResult> {
  const { data } = await client.post<BatchClassificationResult>(
    "/api/categorization/batch",
    {},
  );
  return data;
}
