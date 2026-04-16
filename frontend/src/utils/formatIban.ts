export function formatCzechIban(iban: string): string {
  const raw = iban.replace(/\s/g, "");
  if (!raw.startsWith("CZ") || raw.length !== 24) return iban;
  const bankCode = raw.slice(4, 8);
  const accountNumber = parseInt(raw.slice(8), 10).toString();
  return `${accountNumber}/${bankCode}`;
}
