import { useEffect, useRef, useState } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
  CloudArrowUpIcon,
  XMarkIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  DocumentArrowUpIcon,
  DocumentArrowDownIcon,
} from "@heroicons/react/24/outline";
import {
  importHsHmExcel,
  downloadHsHmTemplate,
  type PayrollOrganizationFilters,
  type ExcelImportSummary,
} from "../api";

interface ImportHsHmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  payrollRunId: number;
  employerId: number;
  employerLabel?: string | null;
  organizationFilters?: PayrollOrganizationFilters | null;
  period: string;
  onSuccess?: () => void;
}

interface ApiErrorPayload {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

export default function ImportHsHmDialog({
  isOpen,
  onClose,
  payrollRunId,
  employerId,
  employerLabel,
  organizationFilters,
  period,
  onSuccess,
}: ImportHsHmDialogProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [result, setResult] = useState<ExcelImportSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    setResult(null);
    setFile(null);
  }, [isOpen, employerId, payrollRunId]);

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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
      setResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    if (!employerId) {
      setError("Veuillez sélectionner un employeur sur la page paie avant l'import.");
      return;
    }
    setIsUploading(true);
    setError(null);
    setResult(null);

    try {
      const summary = await importHsHmExcel(payrollRunId, file, organizationFilters);
      setResult(summary);
      if (summary.successful > 0 && onSuccess) {
        onSuccess();
      }
    } catch (err: unknown) {
      const apiError = err as ApiErrorPayload;
      const msg =
        apiError.response?.data?.detail ||
        apiError.message ||
        "Une erreur est survenue lors de l'importation.";
      setError(msg);
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
      await downloadHsHmTemplate({
        payrollRunId,
        employerId,
        filters: organizationFilters,
      });
    } catch {
      setError("Impossible de telecharger le modele.");
    }
  };

  return (
    <Dialog open={isOpen} onClose={handleClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="mx-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl animate-fade-in">
          <div className="mb-6 flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2 text-xl font-bold text-slate-900">
              <DocumentArrowUpIcon className="h-6 w-6 text-primary-600" />
              Import Variables HS HM Absences
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
              <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                Employeur actif de la page paie: <span className="font-semibold text-slate-900">{employerLabel || employerId || "-"}</span>
              </div>

              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                  file ? "border-primary-500 bg-primary-50/50" : "border-slate-300 hover:border-primary-400 hover:bg-slate-50"
                }`}
                onDragOver={(e) => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  accept=".xlsx,.xls"
                  className="hidden"
                />

                <div className="mx-auto w-12 h-12 bg-white rounded-full flex items-center justify-center shadow-sm mb-3">
                  <CloudArrowUpIcon className={`h-6 w-6 ${file ? "text-primary-600" : "text-slate-400"}`} />
                </div>

                {file ? (
                  <div>
                    <p className="font-semibold text-primary-700">{file.name}</p>
                    <p className="text-sm text-slate-500 mt-1">{(file.size / 1024).toFixed(1)} KB</p>
                    <p className="text-xs text-primary-600 mt-2 hover:underline">Cliquez ou glissez pour changer</p>
                  </div>
                ) : (
                  <div>
                    <p className="font-semibold text-slate-700">Cliquez pour selectionner un fichier</p>
                    <p className="text-sm text-slate-500 mt-1">ou glissez-deposez le fichier Excel ici</p>
                  </div>
                )}
              </div>

              {error && (
                <div className="p-4 bg-red-50 text-red-700 rounded-xl text-sm border border-red-100 flex items-start gap-2">
                  <ExclamationCircleIcon className="h-5 w-5 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <div className="flex justify-between items-center pt-2">
                <button
                  onClick={handleDownloadTemplate}
                  disabled={!employerId}
                  className="text-primary-600 text-sm font-medium hover:underline flex items-center gap-2 hover:text-primary-700 transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                  title="Telecharger le modele Excel"
                >
                  <DocumentArrowDownIcon className="h-5 w-5" />
                  <span>Modele Paie (HS/HM + Absences + Avances)</span>
                </button>

                <div className="flex gap-3">
                  <button
                    onClick={handleClose}
                    className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                    disabled={isUploading}
                  >
                    Annuler
                  </button>
                  <button
                    onClick={handleUpload}
                    disabled={!file || !employerId || isUploading}
                    className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors font-medium flex items-center gap-2"
                  >
                    {isUploading && <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />}
                    Importer
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <CheckCircleIcon className="h-14 w-14 text-green-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Import termine</h3>
              <p className="text-slate-600 mb-4">
                {result.successful} ligne(s) importee(s), {result.failed} erreur(s).
              </p>
              <button
                onClick={handleClose}
                className="px-5 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                Fermer
              </button>
            </div>
          )}
        </DialogPanel>
      </div>
    </Dialog>
  );
}
