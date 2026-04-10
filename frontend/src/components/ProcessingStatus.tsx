import { useQuery } from "@tanstack/react-query";
import { listBatches } from "../api/imports";

export default function ProcessingStatus() {
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: listBatches,
    refetchInterval: 5000,
  });

  const isProcessing = batches.some((b) => b.status === "processing");
  const hasFailed = batches.some((b) => b.status === "failed");

  const color = hasFailed ? "bg-red-500" : isProcessing ? "bg-yellow-400" : "bg-green-500";
  const title = hasFailed ? "Import failed" : isProcessing ? "Processing…" : "Idle";

  return (
    <span className="flex items-center gap-2 text-sm text-gray-500" title={title}>
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {title}
    </span>
  );
}
