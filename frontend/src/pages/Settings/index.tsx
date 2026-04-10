import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createAccount, deleteAccount, listAccounts } from "../../api/accounts";
import client from "../../api/client";

function LlmCostSection() {
  const { data: rows = [] } = useQuery({
    queryKey: ["llm-cost"],
    queryFn: async () => (await client.get("/api/settings/llm-cost")).data,
  });

  const total = rows.reduce((sum: number, r: any) => sum + r.estimated_cost_usd, 0);

  return (
    <section className="bg-white border border-gray-200 rounded-lg overflow-hidden mt-6">
      <h2 className="text-lg font-semibold px-6 py-4 border-b">LLM Usage</h2>
      <div className="px-6 py-4">
        <p className="text-sm text-gray-500 mb-4">
          Total estimated cost: <strong className="text-gray-800">${total.toFixed(4)}</strong>
        </p>
        {rows.length === 0 ? (
          <p className="text-sm text-gray-400">No LLM calls recorded yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                {["Month", "Model", "Calls", "Tokens In", "Tokens Out", "Est. Cost"].map((h) => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r: any) => (
                <tr key={`${r.year}-${r.month}-${r.model}`} className="border-t border-gray-100">
                  <td className="px-4 py-2">{r.year}-{String(r.month).padStart(2, "0")}</td>
                  <td className="px-4 py-2 font-mono text-xs">{r.model}</td>
                  <td className="px-4 py-2">{r.calls}</td>
                  <td className="px-4 py-2">{r.prompt_tokens?.toLocaleString()}</td>
                  <td className="px-4 py-2">{r.completion_tokens?.toLocaleString()}</td>
                  <td className="px-4 py-2">${r.estimated_cost_usd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}

export default function SettingsPage() {
  const qc = useQueryClient();
  const { data: accounts = [], isLoading } = useQuery({ queryKey: ["accounts"], queryFn: listAccounts });

  const [name, setName] = useState("");
  const [bank, setBank] = useState("partners");
  const [iban, setIban] = useState("");
  const [currency, setCurrency] = useState("CZK");

  const create = useMutation({
    mutationFn: () => createAccount({ name, bank, iban: iban || undefined, currency }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["accounts"] });
      setName("");
      setIban("");
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteAccount(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["accounts"] }),
  });

  return (
    <div className="max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Settings</h1>

      <section className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Add Account</h2>
        <form
          className="flex flex-col gap-3 max-w-md"
          onSubmit={(e) => { e.preventDefault(); create.mutate(); }}
        >
          <div className="flex flex-col gap-1">
            <label htmlFor="acc-name" className="text-sm text-gray-600">Name</label>
            <input
              id="acc-name"
              className="border border-gray-300 rounded px-3 py-2 text-sm"
              placeholder="e.g. Partners CZK"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="acc-bank" className="text-sm text-gray-600">Bank type</label>
            <select
              id="acc-bank"
              className="border border-gray-300 rounded px-3 py-2 text-sm"
              value={bank}
              onChange={(e) => setBank(e.target.value)}
            >
              <option value="partners">Partners Bank</option>
              <option value="generic">Generic CSV</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="acc-iban" className="text-sm text-gray-600">IBAN (optional)</label>
            <input
              id="acc-iban"
              className="border border-gray-300 rounded px-3 py-2 text-sm font-mono"
              placeholder="CZ00 0000 0000 0000 0000 0000"
              value={iban}
              onChange={(e) => setIban(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="acc-currency" className="text-sm text-gray-600">Currency</label>
            <select
              id="acc-currency"
              className="border border-gray-300 rounded px-3 py-2 text-sm"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              <option value="CZK">CZK</option>
              <option value="EUR">EUR</option>
              <option value="USD">USD</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={!name || create.isPending}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50 self-start"
          >
            {create.isPending ? "Adding…" : "Add Account"}
          </button>
          {create.isError && <p className="text-red-500 text-sm">Failed to create account.</p>}
        </form>
      </section>

      <section className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <h2 className="text-lg font-semibold px-6 py-4 border-b">Accounts</h2>
        {isLoading && <p className="px-6 py-4 text-sm text-gray-400">Loading…</p>}
        {!isLoading && accounts.length === 0 && (
          <p className="px-6 py-8 text-sm text-gray-400">No accounts yet.</p>
        )}
        {accounts.length > 0 && (
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
              <tr>
                {["Name", "Bank", "IBAN", "Currency", ""].map((h) => (
                  <th key={h} className="px-4 py-2 text-left">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {accounts.map((a) => (
                <tr key={a.id} className="border-t border-gray-100">
                  <td className="px-4 py-3 font-medium">{a.name}</td>
                  <td className="px-4 py-3 text-gray-500">{a.bank}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-400">{a.iban ?? "—"}</td>
                  <td className="px-4 py-3">{a.currency}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      className="text-red-400 hover:text-red-600 text-xs"
                      onClick={() => remove.mutate(a.id)}
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <LlmCostSection />
    </div>
  );
}
