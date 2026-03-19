import { useState, useRef } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
    CloudArrowUpIcon,
    XMarkIcon,
    CheckCircleIcon,
    ExclamationCircleIcon,
    DocumentArrowUpIcon,
    DocumentArrowDownIcon
} from "@heroicons/react/24/outline";
import {
    importHsHmExcel,
    downloadHsHmTemplate,
    type ExcelImportSummary
} from "../api";

interface ImportHsHmDialogProps {
    isOpen: boolean;
    onClose: () => void;
    payrollRunId: number;
    onSuccess?: () => void;
}

export default function ImportHsHmDialog({
    isOpen,
    onClose,
    payrollRunId,
    onSuccess
}: ImportHsHmDialogProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [result, setResult] = useState<ExcelImportSummary | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

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

        setIsUploading(true);
        setError(null);
        setResult(null);

        try {
            const summary = await importHsHmExcel(payrollRunId, file);
            setResult(summary);
            if (summary.successful > 0 && onSuccess) {
                onSuccess();
            }
        } catch (err: any) {
            console.error("Upload error:", err);
            // Try to extract useful error message from API
            const msg = err.response?.data?.detail || "Une erreur est survenue lors de l'importation.";
            setError(msg);
        } finally {
            setIsUploading(false);
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            await downloadHsHmTemplate(payrollRunId);
        } catch (err) {
            console.error("Failed to download template", err);
            setError("Impossible de télécharger le modèle.");
        }
    };

    return (
        <Dialog
            open={isOpen}
            onClose={handleClose}
            className="relative z-50"
        >
            <div className="fixed inset-0 bg-black/30 backdrop-blur-sm" aria-hidden="true" />

            <div className="fixed inset-0 flex items-center justify-center p-4">
                <DialogPanel className="mx-auto w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl animate-fade-in">
                    <div className="flex items-center justify-between mb-6">
                        <DialogTitle className="text-xl font-bold text-slate-900 flex items-center gap-2">
                            <DocumentArrowUpIcon className="h-6 w-6 text-primary-600" />
                            Import Variables HS HM Absences
                        </DialogTitle>
                        <button
                            onClick={handleClose}
                            disabled={isUploading}
                            className="text-slate-400 hover:text-slate-600 disabled:opacity-50 transition-colors"
                        >
                            <XMarkIcon className="h-6 w-6" />
                        </button>
                    </div>

                    {!result ? (
                        /* --- Upload State --- */
                        <div className="space-y-6">
                            <div
                                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer
                  ${file
                                        ? "border-primary-500 bg-primary-50/50"
                                        : "border-slate-300 hover:border-primary-400 hover:bg-slate-50"
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
                                        <p className="font-semibold text-slate-700">Cliquez pour sélectionner un fichier</p>
                                        <p className="text-sm text-slate-500 mt-1">ou glissez-déposez le fichier Excel ici</p>
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
                                    className="text-primary-600 text-sm font-medium hover:underline flex items-center gap-2 hover:text-primary-700 transition-colors"
                                    title="Télécharger le modèle Excel"
                                >
                                    <DocumentArrowDownIcon className="h-5 w-5" />
                                    <span>Modèle Paie (HS/HM + Absences + Avances)</span>
                                </button>

                                <div className="flex gap-3">
                                    <button
                                        onClick={handleClose}
                                        disabled={isUploading}
                                        className="px-4 py-2 text-slate-700 font-medium hover:bg-slate-50 rounded-lg transition-colors disabled:opacity-50"
                                    >
                                        Annuler
                                    </button>
                                    <button
                                        onClick={handleUpload}
                                        disabled={!file || isUploading}
                                        className="px-6 py-2 bg-primary-600 text-white font-semibold rounded-lg hover:bg-primary-700 focus:ring-4 focus:ring-primary-600/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                                    >
                                        {isUploading ? (
                                            <>
                                                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
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
                        /* --- Result State --- */
                        <div className="space-y-6 animate-slide-up">
                            <div className="bg-slate-50 rounded-xl p-5 border border-slate-100">
                                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-4">Résultat de l'import</h3>

                                <div className="grid grid-cols-3 gap-4 mb-4">
                                    <div className="text-center p-3 bg-white rounded-lg border border-slate-200 shadow-sm">
                                        <span className="block text-2xl font-bold text-slate-700">{result.total_rows}</span>
                                        <span className="text-xs text-slate-500 font-medium">Lignes lues</span>
                                    </div>
                                    <div className="text-center p-3 bg-white rounded-lg border border-green-200 shadow-sm">
                                        <span className="block text-2xl font-bold text-green-600">{result.successful}</span>
                                        <span className="text-xs text-green-600 font-medium">Réussies</span>
                                    </div>
                                    <div className="text-center p-3 bg-white rounded-lg border border-red-200 shadow-sm">
                                        <span className="block text-2xl font-bold text-red-600">{result.failed}</span>
                                        <span className="text-xs text-red-600 font-medium">Échecs</span>
                                    </div>
                                </div>

                                {result.errors.length > 0 ? (
                                    <div className="max-h-60 overflow-y-auto pr-2 space-y-2 custom-scrollbar">
                                        {result.errors.map((err, idx) => (
                                            <div key={idx} className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100">
                                                <ExclamationCircleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" />
                                                <span>{err}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center p-6 text-green-600 bg-green-50 rounded-lg border border-green-100">
                                        <CheckCircleIcon className="h-12 w-12 mb-2" />
                                        <span className="font-semibold">Tout est correct !</span>
                                    </div>
                                )}
                            </div>

                            <div className="flex justify-end pt-2">
                                <button
                                    onClick={handleClose}
                                    className="px-6 py-2 bg-slate-900 text-white font-semibold rounded-lg hover:bg-slate-800 transition-colors"
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
