import { useState, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { listAccounts } from "../../api/accounts";
import { uploadImport } from "../../api/imports";

interface ColumnMapping {
  date: string;
  amount: string;
  counterparty_name: string | null;
  description: string | null;
  date_format: string;
  decimal_separator: string;
  thousands_separator: string;
  separator: string;
  encoding: string;
}

const DEFAULT_MAPPING: ColumnMapping = {
  date: "",
  amount: "",
  counterparty_name: null,
  description: null,
  date_format: "%d.%m.%Y",
  decimal_separator: ",",
  thousands_separator: " ",
  separator: ";",
  encoding: "utf-8",
};

export default function UploadForm() {
  const qc = useQueryClient();
  const { data: accounts = [] } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });
  const [accountId, setAccountId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState<ColumnMapping>(DEFAULT_MAPPING);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedAccount = accounts.find((a) => a.id === accountId);
  const isGeneric = selectedAccount?.bank === "generic";

  const mutation = useMutation({
    mutationFn: () =>
      uploadImport(accountId, file!, isGeneric ? (mapping as unknown as Record<string, string | null>) : undefined),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["batches"] });
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    },
  });

  const canSubmit =
    !!accountId &&
    !!file &&
    !mutation.isPending &&
    (!isGeneric || (mapping.date.trim() !== "" && mapping.amount.trim() !== ""));

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
      <h2 className="text-lg font-semibold mb-4">Upload Bank Export</h2>
      <form
        className="flex flex-col gap-4 max-w-md"
        onSubmit={(e) => { e.preventDefault(); mutation.mutate(); }}
      >
        {accounts.length === 0 ? (
          <p className="text-sm text-gray-400">No accounts yet — add one in Settings.</p>
        ) : (
          <select
            className="border border-gray-300 rounded px-3 py-2 text-sm"
            value={accountId}
            onChange={(e) => { setAccountId(e.target.value); setMapping(DEFAULT_MAPPING); }}
          >
            <option value="">Select account…</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        )}

        {isGeneric && (
          <div className="border border-blue-100 bg-blue-50 rounded-lg p-4 flex flex-col gap-3">
            <p className="text-xs font-medium text-blue-700 uppercase tracking-wide">Column Mapping</p>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  { key: "date", label: "Date column *" },
                  { key: "amount", label: "Amount column *" },
                  { key: "counterparty_name", label: "Counterparty column" },
                  { key: "description", label: "Description column" },
                ] as const
              ).map(({ key, label }) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-gray-600">{label}</label>
                  <input
                    className="border border-gray-300 rounded px-2 py-1 text-xs"
                    placeholder={`CSV header`}
                    value={mapping[key] ?? ""}
                    onChange={(e) =>
                      setMapping((m) => ({ ...m, [key]: e.target.value || null }))
                    }
                  />
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {(
                [
                  { key: "date_format", label: "Date format" },
                  { key: "separator", label: "CSV separator" },
                  { key: "decimal_separator", label: "Decimal sep." },
                  { key: "thousands_separator", label: "Thousands sep." },
                ] as const
              ).map(({ key, label }) => (
                <div key={key} className="flex flex-col gap-1">
                  <label className="text-xs text-gray-600">{label}</label>
                  <input
                    className="border border-gray-300 rounded px-2 py-1 text-xs font-mono"
                    value={mapping[key]}
                    onChange={(e) =>
                      setMapping((m) => ({ ...m, [key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
          disabled={!canSubmit}
        >
          {mutation.isPending ? "Uploading…" : "Import"}
        </button>
        {mutation.isSuccess && <p className="text-green-600 text-sm">Import started!</p>}
        {mutation.isError && <p className="text-red-500 text-sm">Upload failed. Check the console.</p>}
      </form>
    </div>
  );
}
