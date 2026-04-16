import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import Modal from "./Modal";
import { getTransactionDetails } from "../api/transactions";
import { formatCzechIban } from "../utils/formatIban";

interface Props {
  txId: string | null;
  onClose: () => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-2 text-sm">
      <dt className="w-40 flex-shrink-0 text-gray-500">{label}</dt>
      <dd className="text-gray-900 break-all">{value}</dd>
    </div>
  );
}

export default function TransactionDetailModal({ txId, onClose }: Props) {
  const { t } = useTranslation();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["transaction", "details", txId],
    queryFn: () => getTransactionDetails(txId!),
    enabled: txId !== null,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <Modal open={txId !== null} onClose={onClose} title={t("transaction.detailTitle")}>
      {isLoading && (
        <p className="text-sm text-gray-400 text-center py-8">{t("common.loading")}</p>
      )}
      {isError && (
        <p className="text-sm text-red-500 text-center py-8">{t("transaction.loadError")}</p>
      )}
      {data && (
        <div className="space-y-6">
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
              {t("transaction.sectionTransaction")}
            </h3>
            <dl className="space-y-2">
              <Row label="ID" value={<span className="font-mono text-xs">{data.id}</span>} />
              <Row label={t("analytics.txDate")} value={data.booking_date} />
              {data.value_date && (
                <Row label={t("transaction.valueDate")} value={data.value_date} />
              )}
              <Row
                label={t("analytics.txAmount")}
                value={`${Number(data.amount).toLocaleString("cs-CZ")} ${data.currency}`}
              />
              <Row
                label={t("transaction.ownAccount")}
                value={
                  data.account.iban
                    ? `${data.account.name} · ${formatCzechIban(data.account.iban)}`
                    : data.account.name
                }
              />
              {data.counterparty_name && (
                <Row label={t("analytics.txCounterparty")} value={data.counterparty_name} />
              )}
              {data.counterparty_account && (
                <Row
                  label={t("analytics.txCounterpartyAccount")}
                  value={formatCzechIban(data.counterparty_account)}
                />
              )}
              {data.description && (
                <Row label={t("analytics.txDescription")} value={data.description} />
              )}
              {data.raw_reference && (
                <Row label={t("transaction.rawReference")} value={data.raw_reference} />
              )}
            </dl>
          </section>

          {data.transfer_pair && (
            <section>
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                {t("transaction.transferPair")}
              </h3>
              <dl className="space-y-2">
                <Row
                  label="ID"
                  value={<span className="font-mono text-xs">{data.transfer_pair.id}</span>}
                />
                <Row label={t("analytics.txDate")} value={data.transfer_pair.booking_date} />
                <Row
                  label={t("analytics.txAmount")}
                  value={`${Number(data.transfer_pair.amount).toLocaleString("cs-CZ")} ${data.currency}`}
                />
                <Row
                  label={t("transaction.ownAccount")}
                  value={
                    data.transfer_pair.account.iban
                      ? `${data.transfer_pair.account.name} · ${formatCzechIban(data.transfer_pair.account.iban)}`
                      : data.transfer_pair.account.name
                  }
                />
              </dl>
            </section>
          )}

          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
              {t("transaction.sectionCategorization")}
            </h3>
            <dl className="space-y-2">
              <Row
                label={t("analytics.category")}
                value={data.category?.name ?? t("transaction.uncategorized")}
              />
              {data.categorization_source && (
                <Row
                  label={t("transaction.categorizationSource")}
                  value={t(`transaction.source_${data.categorization_source}`)}
                />
              )}
              {data.applied_rule && (
                <Row label={t("transaction.appliedRule")} value={data.applied_rule.name} />
              )}
              {data.confidence != null && (
                <Row
                  label={t("transaction.confidence")}
                  value={`${(Number(data.confidence) * 100).toFixed(0)}%`}
                />
              )}
            </dl>
          </section>
        </div>
      )}
    </Modal>
  );
}
