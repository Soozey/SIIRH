import { useEffect, useState } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import { api } from "../api";
import { ArrowLeftIcon, PrinterIcon, ArrowPathIcon, FunnelIcon } from "@heroicons/react/24/outline";
import PayslipDocument, { type PayslipData } from "../components/PayslipDocument";

export default function PayslipsBulk() {
    const { employerId, period } = useParams();
    const [searchParams] = useSearchParams();
    const [dataList, setDataList] = useState<PayslipData[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Récupérer les filtres organisationnels depuis l'URL
    const etablissement = searchParams.get('etablissement');
    const departement = searchParams.get('departement');
    const service = searchParams.get('service');
    const unite = searchParams.get('unite');

    const hasFilters = etablissement || departement || service || unite;

    useEffect(() => {
        const fetchData = async () => {
            if (!employerId || !period) return;
            setIsLoading(true);
            setError(null);
            try {
                // Construire les paramètres avec les filtres organisationnels
                const params: any = { 
                    employer_id: employerId, 
                    period 
                };
                
                // Ajouter les filtres organisationnels s'ils existent
                if (etablissement) params.etablissement = etablissement;
                if (departement) params.departement = departement;
                if (service) params.service = service;
                if (unite) params.unite = unite;

                const res = await api.get<PayslipData[]>("/payroll/bulk-preview", {
                    params
                });
                setDataList(res.data);
            } catch (err: any) {
                console.error("Erreur bulk loading:", err);
                setError("Impossible de charger les bulletins.");
            } finally {
                setIsLoading(false);
            }
        };
        fetchData();
    }, [employerId, period, etablissement, departement, service, unite]);

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <ArrowPathIcon className="h-12 w-12 animate-spin text-primary-600 mx-auto mb-4" />
                    <p className="text-lg font-medium text-slate-600">Génération des bulletins en cours...</p>
                    <p className="text-sm text-slate-400">Cela peut prendre quelques secondes.</p>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-8 max-w-2xl mx-auto">
                <div className="bg-red-50 text-red-700 p-4 rounded-xl border border-red-200">
                    {error}
                </div>
                <Link to="/payroll" className="mt-4 inline-block text-primary-600 hover:underline">
                    Retour
                </Link>
            </div>
        );
    }

    return (
        <div className="bg-gray-100 min-h-screen pb-10 print:bg-white print:pb-0">
            {/* Barre de navigation (masquée à l'impression) */}
            <div className="bg-white border-b border-gray-200 p-4 sticky top-0 z-10 print:hidden shadow-sm mb-8">
                <div className="max-w-7xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link to="/payroll" className="p-2 hover:bg-gray-100 rounded-full transition-colors">
                            <ArrowLeftIcon className="h-6 w-6 text-gray-600" />
                        </Link>
                        <div>
                            <h1 className="text-xl font-bold text-gray-800">Impression en masse</h1>
                            <div className="flex items-center gap-2">
                                <p className="text-sm text-gray-500">
                                    {dataList.length} bulletins générés pour {period}
                                </p>
                                {hasFilters && (
                                    <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                                        <FunnelIcon className="h-3 w-3" />
                                        Filtré
                                    </div>
                                )}
                            </div>
                            {hasFilters && (
                                <div className="text-xs text-gray-400 mt-1">
                                    Filtres: {[
                                        etablissement && `Établissement: ${etablissement}`,
                                        departement && `Département: ${departement}`,
                                        service && `Service: ${service}`,
                                        unite && `Unité: ${unite}`
                                    ].filter(Boolean).join(' • ')}
                                </div>
                            )}
                        </div>
                    </div>
                    <button
                        onClick={() => window.print()}
                        className="flex items-center gap-2 bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 transition shadow-lg font-medium"
                    >
                        <PrinterIcon className="h-5 w-5" />
                        Imprimer tout
                    </button>
                </div>
            </div>

            {/* Liste des bulletins */}
            <div className="max-w-[210mm] mx-auto print:max-w-none print:w-full bulk-print-container">
                {dataList.length === 0 ? (
                    <div className="text-center py-20 text-gray-500">
                        Aucun bulletin trouvé pour cette période.
                    </div>
                ) : (
                    dataList.map((payslipData, index) => (
                        <div key={`${payslipData.worker.id}-${index}`} className="mb-8 print:mb-0 print:break-after-page">
                            <PayslipDocument data={payslipData} showPrintButton={false} />
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
