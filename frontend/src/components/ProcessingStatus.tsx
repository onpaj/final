import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { listBatches } from "../api/imports";

interface Props {
  onJobCompleted?: () => void;
}

export default function ProcessingStatus({ onJobCompleted }: Props) {
  const { data: batches = [] } = useQuery({
    queryKey: ["batches"],
    queryFn: listBatches,
    refetchInterval: 5000,
  });

  const prevStatusRef = useRef<Record<string, string>>({});

  useEffect(() => {
    batches.forEach((b) => {
      const prev = prevStatusRef.current[b.id];
      if (prev === "processing" && b.status === "completed") {
        onJobCompleted?.();
      }
      prevStatusRef.current[b.id] = b.status;
    });
  }, [batches, onJobCompleted]);

  const latest = batches[0];
  const isProcessing = latest?.status === "processing";
  const hasFailed = latest?.status === "failed";

  const color = isProcessing ? "bg-yellow-400" : hasFailed ? "bg-red-500" : "bg-green-500";
  const title = isProcessing ? "Processing…" : hasFailed ? "Import failed" : "Idle";

  return (
    <span className="flex items-center gap-2 text-sm text-gray-500" title={title}>
      <span className={`w-2 h-2 rounded-full ${color}`} />
      {title}
    </span>
  );
}
