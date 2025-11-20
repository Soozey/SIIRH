import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { api } from "../api";
import {
  DocumentTextIcon,
  BuildingOfficeIcon,
  UserIcon,
  IdentificationIcon,
  CurrencyDollarIcon,
  CalculatorIcon,
  BanknotesIcon,
  ArrowPathIcon
} from "@heroicons/react/24/outline";

export default function Payslip() {
  const { workerId, period } = useParams();
  const [data, setData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      try {
        const r = await api.get(`/payroll/preview`, { params: { worker_id: workerId, period } });
        setData(r.data);
      } catch (error) {
        console.error("Erreur lors du chargement:", error);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [workerId, period]);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-MG', {
      style: 'currency',
      currency: 'MGA',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const formatPeriod = (period: string) => {
    const [year, month] = period.split('-');
    const monthNames = [
      'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin',
      'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'
    ];
    return `${monthNames[parseInt(month) - 1]} ${year}`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center">
          <ArrowPathIcon className="h-12 w-12 text-blue-600 animate-spin mx-auto mb-4" />
          <p className="text-gray-600 text-lg">Chargement du bulletin...</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center">
          <DocumentTextIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">Bulletin non trouvé</h3>
          <p className="text-gray-600">Impossible de charger les données du bulletin.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-green-600 rounded-2xl p-6 mb-6 shadow-lg">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-white/20 rounded-xl backdrop-blur-sm">
                <DocumentTextIcon className="h-8 w-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl md:text-3xl font-bold text-white">
                  Bulletin de Paie
                </h1>
                <p className="text-blue-100 mt-1">
                  {formatPeriod(period || '')} • Travailleur ID: {workerId}
                </p>
              </div>
            </div>
            <div className="bg-white/20 backdrop-blur-sm rounded-xl px-4 py-2">
              <span className="text-white font-semibold text-sm">
                Période: {period}
              </span>
            </div>
          </div>
        </div>

        {/* Informations Entreprise & Salarié */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          {/* Entreprise */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-100 rounded-lg">
                <BuildingOfficeIcon className="h-6 w-6 text-blue-600" />
              </div>
              <h2 className="text-lg font-bold text-gray-900">Entreprise</h2>
            </div>
            <div className="space-y-2">
              <div>
                <p className="font-semibold text-gray-900 text-lg">
                  {data.employer?.raison_sociale}
                </p>
              </div>
              {data.employer?.nif && (
                <div className="flex items-center gap-2 text-gray-600">
                  <IdentificationIcon className="h-4 w-4" />
                  <span>NIF: {data.employer.nif}</span>
                </div>
              )}
              {data.employer?.adresse && (
                <div className="text-gray-600 text-sm">
                  {data.employer.adresse}
                </div>
              )}
            </div>
          </div>

          {/* Salarié */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-green-100 rounded-lg">
                <UserIcon className="h-6 w-6 text-green-600" />
              </div>
              <h2 className="text-lg font-bold text-gray-900">Salarié</h2>
            </div>
            <div className="space-y-2">
              <div>
                <p className="font-semibold text-gray-900 text-lg">
                  {data.worker?.prenom} {data.worker?.nom}
                </p>
              </div>
              <div className="flex items-center gap-2 text-gray-600">
                <IdentificationIcon className="h-4 w-4" />
                <span>Matricule: {data.worker?.matricule}</span>
              </div>
              {data.worker?.secteur && (
                <div className="inline-flex items-center gap-1 bg-gray-100 text-gray-700 px-2 py-1 rounded-full text-xs font-medium">
                  Secteur: {data.worker.secteur}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Tableau des lignes du bulletin */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden mb-6">
          {/* En-tête du tableau */}
          <div className="bg-gradient-to-r from-gray-50 to-blue-50 border-b border-gray-200">
            <div className="grid grid-cols-6 gap-4 p-4 font-semibold text-gray-900 text-sm">
              <div className="col-span-2">Désignation</div>
              <div className="text-center">Nombre</div>
              <div className="text-center">Base</div>
              <div className="text-center">Taux Sal.</div>
              <div className="text-center">Montant sal.</div>
              <div className="text-center">Taux Pat.</div>
            </div>
          </div>

          {/* Lignes du tableau */}
          <div className="divide-y divide-gray-100">
            {data.lines?.map((ln: any, i: number) => (
              <div
                key={i}
                className="grid grid-cols-6 gap-4 p-4 hover:bg-gray-50 transition-colors text-sm"
              >
                <div className="col-span-2 font-medium text-gray-900">
                  {ln.label}
                </div>
                <div className="text-center text-gray-600">
                  {ln.nombre ?? "-"}
                </div>
                <div className="text-center text-gray-600">
                  {ln.base ? formatCurrency(ln.base) : "-"}
                </div>
                <div className="text-center text-gray-600">
                  {ln.taux_sal ? `${ln.taux_sal}%` : "-"}
                </div>
                <div className="text-center font-semibold text-blue-600">
                  {ln.montant_sal ? formatCurrency(ln.montant_sal) : "-"}
                </div>
                <div className="text-center text-gray-600">
                  {ln.taux_pat ? `${ln.taux_pat}%` : "-"}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Totaux */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {/* Total Brut */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CalculatorIcon className="h-5 w-5 text-blue-600" />
              <h3 className="font-semibold text-gray-900">Total Brut</h3>
            </div>
            <p className="text-2xl font-bold text-blue-600">
              {data.totaux?.brut ? formatCurrency(data.totaux.brut) : formatCurrency(0)}
            </p>
          </div>

          {/* Cotisations */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <BanknotesIcon className="h-5 w-5 text-orange-600" />
              <h3 className="font-semibold text-gray-900">Cotisations</h3>
            </div>
            <p className="text-2xl font-bold text-orange-600">
              {data.totaux?.cotisations ? formatCurrency(data.totaux.cotisations) : formatCurrency(0)}
            </p>
          </div>

          {/* IRSA */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CurrencyDollarIcon className="h-5 w-5 text-purple-600" />
              <h3 className="font-semibold text-gray-900">IRSA</h3>
            </div>
            <p className="text-2xl font-bold text-purple-600">
              {data.totaux?.irsa ? formatCurrency(data.totaux.irsa) : formatCurrency(0)}
            </p>
          </div>

          {/* Net à Payer */}
          <div className="bg-white rounded-2xl shadow-sm border border-green-200 p-4 bg-gradient-to-r from-green-50 to-emerald-50">
            <div className="flex items-center gap-2 mb-2">
              <BanknotesIcon className="h-5 w-5 text-green-600" />
              <h3 className="font-semibold text-gray-900">Net à Payer</h3>
            </div>
            <p className="text-2xl font-bold text-green-600">
              {data.totaux?.net ? formatCurrency(data.totaux.net) : formatCurrency(0)}
            </p>
          </div>
        </div>

        {/* Résumé textuel */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-4">
            <DocumentTextIcon className="h-6 w-6 text-gray-600" />
            <h2 className="text-lg font-bold text-gray-900">Résumé</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 text-center">
            <div>
              <p className="text-sm text-gray-600">Salaire Brut</p>
              <p className="font-semibold text-gray-900">
                {data.totaux?.brut ? formatCurrency(data.totaux.brut) : formatCurrency(0)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Cotisations</p>
              <p className="font-semibold text-gray-900">
                {data.totaux?.cotisations ? formatCurrency(data.totaux.cotisations) : formatCurrency(0)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">IRSA</p>
              <p className="font-semibold text-gray-900">
                {data.totaux?.irsa ? formatCurrency(data.totaux.irsa) : formatCurrency(0)}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Net à Payer</p>
              <p className="font-semibold text-green-600">
                {data.totaux?.net ? formatCurrency(data.totaux.net) : formatCurrency(0)}
              </p>
            </div>
          </div>
        </div>

        {/* Bouton d'impression */}
        <div className="flex justify-center mt-6">
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-2 bg-blue-600 text-white hover:bg-blue-700 px-6 py-3 rounded-xl font-medium transition-colors shadow-lg"
          >
            <DocumentTextIcon className="h-5 w-5" />
            Imprimer le Bulletin
          </button>
        </div>
      </div>
    </div>
  );
}