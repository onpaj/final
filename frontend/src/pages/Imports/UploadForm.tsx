import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAccounts } from "../../api/accounts";
import { uploadImport } from "../../api/imports";

export default function UploadForm() {
  const qc = useQueryClient();
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const mutation = useMutation({
    mutationFn: () => uploadImport(accountId, file!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["batches"] });
      setFile(null);
    },
  });

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Upload Bank Export</h2>
      <div className="flex flex-col gap-4 max-w-md">
        <select
          className="border border-gray-300 rounded px-3 py-2 text-sm"
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
        >
          <option value="">Select account…</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
        <input
          type="file"
          accept=".csv"
          className="text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
          disabled={!accountId || !file || mutation.isPending}
          onClick={() => mutation.mutate()}
        >
          {mutation.isPending ? "Uploading…" : "Import"}
        </button>
        {mutation.isSuccess && <p className="text-green-600 text-sm">Import started!</p>}
        {mutation.isError && <p className="text-red-500 text-sm">Upload failed. Check the console.</p>}
      </div>
    </div>
  );
}
