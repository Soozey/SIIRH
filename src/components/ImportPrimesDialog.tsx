import { useEffect, useRef, useState } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  CloudArrowUpIcon,
  CurrencyDollarIcon,
  DocumentArrowDownIcon,
  ExclamationCircleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";

import { downloadPrimesTemplate, importPrimesExcel, type PayrollOrganizationFilters, type PrimesImportSummary } from "../api";

interface ImportPrimesDialogProps {
  isOpen: boolean;
  onClose: () => void;
  period: string;
  employerId: number;
  employerLabel?: string | null;
  organizationFilters?: PayrollOrganizationFilters | null;
  onSuccess?: () => void;
}

type ApiLikeError = {
  response?: {
    data?: {
      detail?: string;
    };
  };
};

export default function ImportPrimesDialog({
  isOpen,
  onClose,
  period,
  employerId,
  employerLabel,
  organizationFilters,
  onSuccess,
}: ImportPrimesDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<PrimesImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setResult(null);
    setFile(null);
  }, [isOpen, employerId]);

  const resetState = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setIsUploading(false);
  };

  const handleClose = () => {
    if (isUploading) return;
    resetState();
    onClose();
  };

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setFile(event.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    if (event.dataTransfer.files && event.dataTransfer.files[0]) {
      setFile(event.dataTransfer.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file || !employerId) {
      setError("Veuillez sélectionner un employeur sur la page paie avant l'import.");
      return;
    }

    const confirmed = window.confirm(
      "ATTENTION: l'importation peut ecraser des valeurs de primes deja saisies. Continuer ?"
    );
    if (!confirmed) return;

    setIsUploading(true);
    setError(null);
    setResult(null);
    try {
      const summary = await importPrimesExcel(period, file, employerId, { filters: organizationFilters });
      setResult(summary);
      if ((summary.imported ?? 0) + (summary.updated ?? 0) > 0 && onSuccess) {
        onSuccess();
      }
    } catch (err: unknown) {
      const apiError = err as ApiLikeError;
      setError(apiError?.response?.data?.detail || "Erreur lors de l'importation des primes.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleDownloadTemplate = async () => {
    if (!employerId) {
      setError("Veuillez sélectionner un employeur sur la page paie avant de télécharger le modèle.");
      return;
    }
    try {
      setError(null);
      await downloadPrimesTemplate(employerId, { filters: organizationFilters });
    } catch {
      setError("Impossible de telecharger le modele.");
    }
  };

  const handleDownloadErrorCsv = () => {
    if (!result?.report?.error_report_csv) return;
    const blob = new Blob([result.report.error_report_csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `primes_import_errors_${period}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={isOpen} onClose={handleClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="mx-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl animate-fade-in">
          <div className="mb-6 flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-slate-900">
              <CurrencyDollarIcon className="h-6 w-6 text-primary-600" />
              Importer Variables Primes
            </DialogTitle>
            <button
              onClick={handleClose}
              disabled={isUploading}
              className="text-slate-400 transition-colors hover:text-slate-600 disabled:opacity-50"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          {!result ? (
            <div className="space-y-6">
              <p className="text-sm text-slate-500">
                Importez un fichier Excel/CSV de primes pour la periode <b>{period}</b>.
              </p>

              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Employeur actif de la page paie: <span className="font-semibold text-slate-900">{employerLabel || employerId || "-"}</span>
              </div>

              <div
                className={`cursor-pointer rounded-xl border-2 border-dashed p-8 text-center transition-colors ${
                  file
                    ? "border-primary-500 bg-primary-50/50"
                    : "border-slate-300 hover:border-primary-400 hover:bg-slate-50"
                }`}
                onDragOver={(event) => event.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                />
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-sm">
                  <CloudArrowUpIcon className={`h-6 w-6 ${file ? "text-primary-600" : "text-slate-400"}`} />
                </div>
                {file ? (
                  <div>
                    <p className="font-semibold text-primary-700">{file.name}</p>
                    <p className="mt-1 text-sm text-slate-500">{(file.size / 1024).toFixed(1)} KB</p>
                    <p className="mt-2 text-xs text-primary-600">Cliquez ou glissez pour changer</p>
                  </div>
                ) : (
                  <div>
                    <p className="font-semibold text-slate-700">Cliquez pour selectionner un fichier</p>
                    <p className="mt-1 text-sm text-slate-500">ou glissez-deposez ici</p>
                  </div>
                )}
              </div>

              {error ? (
                <div className="flex items-start gap-2 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">
                  <ExclamationCircleIcon className="mt-0.5 h-5 w-5 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              ) : null}

              <div className="flex items-center justify-between pt-2">
                <button
                  onClick={handleDownloadTemplate}
                  disabled={!employerId}
                  className="flex items-center gap-2 text-sm font-medium text-primary-600 transition-colors hover:text-primary-700 hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                  title="Telecharger le modele"
                >
                  <DocumentArrowDownIcon className="h-5 w-5" />
                  <span>Telecharger le modele</span>
                </button>

                <div className="flex gap-3">
                  <button
                    onClick={handleClose}
                    disabled={isUploading}
                    className="rounded-lg px-4 py-2 font-medium text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={!file || !employerId || isUploading}
                    className="flex items-center gap-2 rounded-lg bg-primary-600 px-6 py-2 font-semibold text-white transition-all hover:bg-primary-700 focus:ring-4 focus:ring-primary-600/20 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {isUploading ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                        Importation...
                      </>
                    ) : (
                      "Importer"
                    )}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
                <CloudArrowUpIcon className="h-8 w-8 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900">Importation terminee</h3>
                <p className="mt-2 text-slate-500">
                  {(result.imported ?? 0) + (result.updated ?? 0)} lignes traitees.
                </p>
                {result.report ? (
                  <p className="mt-1 text-xs text-slate-400">
                    Creees: {result.report.created} | Maj: {result.report.updated} | Ignorees: {result.report.skipped} | Echec: {result.report.failed}
                  </p>
                ) : null}
              </div>

              {result.errors && result.errors.length > 0 ? (
                <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 p-4 text-left">
                  <h4 className="mb-2 flex items-center gap-2 font-semibold text-amber-800">
                    <ExclamationCircleIcon className="h-5 w-5" />
                    Avertissements ({result.errors.length})
                  </h4>
                  <ul className="max-h-32 space-y-1 overflow-y-auto text-sm text-amber-700">
                    {result.errors.map((item, index) => (
                      <li key={index}>- {item}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {result.report?.error_report_csv ? (
                <button
                  type="button"
                  onClick={handleDownloadErrorCsv}
                  className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-100"
                >
                  Telecharger le rapport d'erreurs (CSV)
                </button>
              ) : null}

              <div className="pt-4">
                <button
                  onClick={handleClose}
                  className="w-full rounded-xl bg-slate-900 py-3 font-semibold text-white transition-colors hover:bg-slate-800"
                >
                  Fermer
                </button>
              </div>
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
