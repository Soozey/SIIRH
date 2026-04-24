import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { api } from "../api";
import PayslipDocument, { type PayslipData } from "../components/PayslipDocument";

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export default function Payslip() {
  const { workerId, period } = useParams();
  const [data, setData] = useState<PayslipData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!workerId || !period) {
        setIsLoading(false);
        setError("Aucun salarie ou periode selectionne.");
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const response = await api.get<PayslipData>("/payroll/preview", {
          params: { worker_id: workerId, period },
        });
        setData(response.data);
      } catch (e: unknown) {
        const apiError = e as ApiErrorPayload;
        setError(
          apiError.response?.data?.detail ||
          apiError.message ||
          "Erreur inconnue lors du chargement."
        );
      } finally {
        setIsLoading(false);
      }
    };

    void fetchData();
  }, [workerId, period]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="p-6 flex flex-col items-center gap-4 text-primary-600">
          <ArrowPathIcon className="w-10 h-10 animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 max-w-2xl mx-auto mt-10">
        <div className="bg-white p-8 border-l-4 border-red-500 shadow-lg">
          <h3 className="text-xl font-bold text-red-600 mb-2">Erreur</h3>
          <p className="text-slate-600 mb-4">Impossible de charger l'apercu du bulletin.</p>
          {error && <div className="text-sm text-red-700 font-medium">{error}</div>}
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto bg-gray-50 min-h-screen font-sans">
      <PayslipDocument data={data} showPrintButton />
    </div>
  );
}
