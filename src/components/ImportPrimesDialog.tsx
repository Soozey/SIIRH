import { useState, useRef } from "react";
import { Dialog, DialogPanel, DialogTitle } from "@headlessui/react";
import {
    CloudArrowUpIcon,
    XMarkIcon,
    ExclamationCircleIcon,
    DocumentArrowDownIcon,
    CurrencyDollarIcon
} from "@heroicons/react/24/outline";
import {
    importPrimesExcel,
    downloadPrimesTemplate,
    type PrimesImportSummary
} from "../api";

interface ImportPrimesDialogProps {
    isOpen: boolean;
    onClose: () => void;
    period: string;
    employerId: number;
    onSuccess?: () => void;
}

export default function ImportPrimesDialog({
    isOpen,
    onClose,
    period,
    employerId,
    onSuccess
}: ImportPrimesDialogProps) {
    const [file, setFile] = useState<File | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [result, setResult] = useState<PrimesImportSummary | null>(null);
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

        // Warning about method change
        const confirmed = window.confirm(
            "⚠️ ATTENTION : L'importation va écraser toutes les données saisies manuellement précédemment.\n\n" +
            "Voulez-vous continuer ?"
        );

        if (!confirmed) return;

        setIsUploading(true);
        setError(null);
        setResult(null);

        try {
            const summary = await importPrimesExcel(period, file, employerId);
            setResult(summary);
            if (summary.updated_items > 0 && onSuccess) {
                onSuccess();
            }
        } catch (err: any) {
            console.error("Upload error:", err);
            const msg = err.response?.data?.detail || "Une erreur est survenue lors de l'importation.";
            setError(msg);
        } finally {
            setIsUploading(false);
        }
    };

    const handleDownloadTemplate = async () => {
        try {
            await downloadPrimesTemplate(employerId);
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
                            <CurrencyDollarIcon className="h-6 w-6 text-primary-600" />
                            Importer Variables Primes
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
                            <p className="text-sm text-slate-500">
                                Importez un fichier Excel contenant les valeurs variables (Nombre / Base) pour les primes de la période <b>{period}</b>.
                            </p>

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
                                    <span>Modèle Primes Dynamique</span>
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
                        <div className="text-center space-y-6">
                            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                                <CloudArrowUpIcon className="h-8 w-8 text-green-600" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-slate-900">Importation réussie !</h3>
                                <p className="text-slate-500 mt-2">
                                    {result.updated_items} valeurs de primes mises à jour.
                                </p>
                            </div>

                            {result.errors && result.errors.length > 0 && (
                                <div className="mt-4 p-4 bg-amber-50 rounded-xl border border-amber-100 text-left">
                                    <h4 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
                                        <ExclamationCircleIcon className="h-5 w-5" />
                                        Avertissements ({result.errors.length})
                                    </h4>
                                    <ul className="text-sm text-amber-700 space-y-1 max-h-32 overflow-y-auto">
                                        {result.errors.map((err, i) => (
                                            <li key={i}>• {err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div className="pt-4">
                                <button
                                    onClick={handleClose}
                                    className="w-full py-3 bg-slate-900 text-white font-semibold rounded-xl hover:bg-slate-800 transition-colors"
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
