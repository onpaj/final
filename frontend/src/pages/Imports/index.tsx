import UploadForm from "./UploadForm";
import BatchHistory from "./BatchHistory";

export default function ImportsPage() {
  return (
    <div className="max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Imports</h1>
      <UploadForm />
      <BatchHistory />
    </div>
  );
}
