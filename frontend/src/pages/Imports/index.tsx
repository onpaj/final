import { useTranslation } from "react-i18next";
import UploadForm from "./UploadForm";
import BatchHistory from "./BatchHistory";

export default function ImportsPage() {
  const { t } = useTranslation();
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">{t("imports.title")}</h1>
      <UploadForm />
      <BatchHistory />
    </div>
  );
}
