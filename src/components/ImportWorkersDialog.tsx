import { useState, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { CloudArrowUpIcon, DocumentArrowDownIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { downloadWorkersTemplate, importWorkers, mapWorkersImportTemplate, previewWorkersImport, type WorkersImportResponse } from '../api';
import { useQueryClient } from '@tanstack/react-query';

type Props = {
    isOpen: boolean;
    onClose: () => void;
};

export default function ImportWorkersDialog({ isOpen, onClose }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<WorkersImportResponse | null>(null);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [updateExisting, setUpdateExisting] = useState(false);
    const [isPreviewing, setIsPreviewing] = useState(false);
    const [isMapping, setIsMapping] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const qc = useQueryClient();

    const handleDownloadTemplate = async (prefilled = false) => {
        try {
            await downloadWorkersTemplate({ prefilled });
        } catch (error) {
            console.error("Erreur téléchargement modèle", error);
            setErrorMessage("Erreur lors du téléchargement du modèle.");
        }
    };

    const handleImport = async () => {
        if (!file) return;

        setLoading(true);
        setResult(null);
        setErrorMessage(null);

        try {
            const response = await importWorkers(file, updateExisting);
            setResult(response);
            if (response.imported > 0 || response.updated > 0) {
                qc.invalidateQueries({ queryKey: ["workers"] });
            }
        } catch (error) {
            console.error("Erreur import", error);
            setErrorMessage("Erreur lors de l'importation. Vérifiez le rapport de prévisualisation ou le format du fichier.");
        } finally {
            setLoading(false);
        }
    };

    const handlePreview = async () => {
        if (!file) return;
        setIsPreviewing(true);
        setResult(null);
        setErrorMessage(null);
        try {
            const report = await previewWorkersImport(file, updateExisting);
            setResult({
                imported: report.created,
                updated: report.updated,
                skipped: report.skipped,
                errors: report.issues.map((issue) => issue.message),
                report,
            });
        } catch (error) {
            console.error("Erreur preview", error);
            setErrorMessage("Erreur lors de la prévisualisation du fichier.");
        } finally {
            setIsPreviewing(false);
        }
    };

    const handleMapTemplate = async () => {
        if (!file) return;
        setIsMapping(true);
        setResult(null);
        setErrorMessage(null);
        try {
            await mapWorkersImportTemplate(file);
        } catch (error) {
            console.error("Erreur mapping", error);
            setErrorMessage(error instanceof Error ? error.message : "Erreur lors du mapping du fichier.");
        } finally {
            setIsMapping(false);
        }
    };

    const handleDownloadErrorReport = () => {
        const csv = result?.report?.error_report_csv;
        if (!csv) return;
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", "rapport_erreurs_import_salaries.csv");
        document.body.appendChild(link);
        link.click();
        link.parentNode?.removeChild(link);
    };

    const handleClose = () => {
        setFile(null);
        setResult(null);
        setErrorMessage(null);
        onClose();
    };

    const report = result?.report;
    const rejectedCount = report?.failed ?? result?.errors.length ?? 0;
    const importedCount = (result?.imported ?? 0) + (result?.updated ?? 0);

    return (
        <Transition appear show={isOpen} as={Fragment}>
            <Dialog as="div" className="relative z-50" onClose={handleClose}>
                <Transition.Child
                    as={Fragment}
                    enter="ease-out duration-300"
                    enterFrom="opacity-0"
                    enterTo="opacity-100"
                    leave="ease-in duration-200"
                    leaveFrom="opacity-100"
                    leaveTo="opacity-0"
                >
                    <div className="fixed inset-0 bg-black/25" />
                </Transition.Child>

                <div className="fixed inset-0 overflow-y-auto">
                    <div className="flex min-h-full items-center justify-center p-4 text-center">
                        <Transition.Child
                            as={Fragment}
                            enter="ease-out duration-300"
                            enterFrom="opacity-0 scale-95"
                            enterTo="opacity-100 scale-100"
                            leave="ease-in duration-200"
                            leaveFrom="opacity-100 scale-100"
                            leaveTo="opacity-0 scale-95"
                        >
                            <Dialog.Panel className="w-full max-w-md transform overflow-hidden rounded-2xl bg-white p-6 text-left align-middle shadow-xl transition-all">
                                <div className="flex justify-between items-start mb-4">
                                    <Dialog.Title as="h3" className="text-lg font-medium leading-6 text-gray-900">
                                        Importer des Salariés
                                    </Dialog.Title>
                                    <button onClick={handleClose} className="text-gray-400 hover:text-gray-500">
                                        <XMarkIcon className="h-6 w-6" />
                                    </button>
                                </div>

                                <div className="mt-2 space-y-4">
                                    <p className="text-sm text-gray-500">
                                        Importez une liste de salariés depuis un fichier Excel ou CSV.
                                        Utilisez le modèle officiel pour respecter les colonnes attendues et éviter les rejets.
                                    </p>

                                    <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-sm text-blue-900">
                                        <p className="font-semibold">Aide avant import</p>
                                        <ul className="mt-2 list-disc space-y-1 pl-5">
                                            <li>Colonnes minimales: Matricule, Nom.</li>
                                            <li>Si vos colonnes sont différentes, utilisez Mapper vers modèle SIIRH avant l'import.</li>
                                            <li>Formats dates: JJ/MM/AAAA ou YYYY-MM-DD.</li>
                                            <li>Doublons contrôlés: matricule, CIN, email.</li>
                                            <li>Les lignes valides sont importées même si certaines lignes sont rejetées.</li>
                                        </ul>
                                    </div>

                                    <button
                                        onClick={() => handleDownloadTemplate(false)}
                                        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                                    >
                                        <DocumentArrowDownIcon className="h-5 w-5" />
                                        Télécharger le modèle Excel
                                    </button>

                                    <button
                                        onClick={() => handleDownloadTemplate(true)}
                                        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                                    >
                                        <DocumentArrowDownIcon className="h-5 w-5" />
                                        Exporter les salariés existants
                                    </button>

                                    <div className="flex items-center mb-4">
                                        <input
                                            id="update-existing"
                                            name="update-existing"
                                            type="checkbox"
                                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                                            checked={updateExisting}
                                            onChange={(e) => setUpdateExisting(e.target.checked)}
                                        />
                                        <label htmlFor="update-existing" className="ml-2 block text-sm text-gray-900">
                                            Mettre à jour les salariés existants (au lieu d'ignorer)
                                        </label>
                                    </div>

                                    <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-blue-500 hover:bg-blue-50 transition-colors cursor-pointer"
                                        onClick={() => fileInputRef.current?.click()}
                                    >
                                        <CloudArrowUpIcon className="h-12 w-12 text-gray-400 mx-auto mb-2" />
                                        {file ? (
                                            <p className="text-sm font-medium text-gray-900 truncate">
                                                {file.name}
                                            </p>
                                        ) : (
                                            <p className="text-sm text-gray-500">
                                                Cliquez pour sélectionner un fichier
                                            </p>
                                        )}
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            className="hidden"
                                            accept=".xlsx,.xls,.csv"
                                            onChange={(e) => {
                                                setFile(e.target.files?.[0] || null);
                                                setResult(null);
                                                setErrorMessage(null);
                                            }}
                                        />
                                    </div>

                                    {errorMessage ? (
                                        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
                                            {errorMessage}
                                        </div>
                                    ) : null}

                                    {result && (
                                        <div className={`rounded-md p-4 ${importedCount > 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                                            <div className="flex">
                                                <div className="ml-3">
                                                    <h3 className={`text-sm font-medium ${importedCount > 0 ? 'text-green-800' : 'text-red-800'}`}>
                                                        Résultat de l'import
                                                    </h3>
                                                    <div className={`mt-2 text-sm ${importedCount > 0 ? 'text-green-700' : 'text-zinc-700'}`}>
                                                        {report ? (
                                                            <div className="mb-3 grid grid-cols-2 gap-3 rounded-lg bg-white/70 p-3 text-xs sm:grid-cols-4">
                                                                <div>
                                                                    <div className="font-semibold text-gray-900">Total lignes</div>
                                                                    <div>{report.total_rows}</div>
                                                                </div>
                                                                <div>
                                                                    <div className="font-semibold text-gray-900">Importées</div>
                                                                    <div>{report.created + report.updated}</div>
                                                                </div>
                                                                <div>
                                                                    <div className="font-semibold text-gray-900">Rejetées</div>
                                                                    <div>{rejectedCount}</div>
                                                                </div>
                                                                <div>
                                                                    <div className="font-semibold text-gray-900">Ignorées</div>
                                                                    <div>{report.skipped}</div>
                                                                </div>
                                                            </div>
                                                        ) : null}
                                                        <p>
                                                            <span className="font-bold">{result.imported}</span> nouveau(x) salarié(s).
                                                            {result.updated !== undefined && result.updated > 0 && (
                                                                <span className="ml-2 font-bold text-blue-700">
                                                                    {result.updated} mis à jour.
                                                                </span>
                                                            )}
                                                            {result.skipped !== undefined && result.skipped > 0 && (
                                                                <span className="ml-2 text-amber-600">
                                                                    ({result.skipped} ignoré(s))
                                                                </span>
                                                            )}
                                                        </p>
                                                        {result.errors.length > 0 && (
                                                            <div className="mt-2">
                                                                <p className="font-semibold">Erreurs / Avertissements :</p>
                                                                <ul className="list-disc pl-5 space-y-1 max-h-32 overflow-y-auto mt-1">
                                                                    {result.errors.map((err, i) => (
                                                                        <li key={i}>{err}</li>
                                                                    ))}
                                                                </ul>
                                                                {result.report?.error_report_csv && (
                                                                    <button
                                                                        type="button"
                                                                        onClick={handleDownloadErrorReport}
                                                                        className="mt-2 text-xs font-medium text-blue-700 underline"
                                                                    >
                                                                        Télécharger le rapport d'erreurs (CSV)
                                                                    </button>
                                                                )}
                                                            </div>
                                                        )}
                                                        {report?.issues?.length ? (
                                                            <div className="mt-3 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700">
                                                                <p className="font-semibold text-gray-900">Détail des lignes rejetées</p>
                                                                <div className="mt-2 max-h-40 overflow-y-auto space-y-2">
                                                                    {report.issues.slice(0, 12).map((issue, index) => (
                                                                        <div key={`${issue.row_number}-${issue.code}-${index}`} className="border-b border-gray-100 pb-2 last:border-b-0">
                                                                            <div className="font-medium">
                                                                                Ligne {issue.row_number}{issue.column ? ` • ${issue.column}` : ""}
                                                                            </div>
                                                                            <div>{issue.message}</div>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                                {report.issues.length > 12 ? (
                                                                    <p className="mt-2 text-gray-500">
                                                                        {report.issues.length - 12} autre(s) erreur(s) disponibles dans le CSV.
                                                                    </p>
                                                                ) : null}
                                                            </div>
                                                        ) : null}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-6 flex justify-end gap-3">
                                    <button
                                        type="button"
                                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                                        onClick={handleClose}
                                    >
                                        Fermer
                                    </button>
                                    <button
                                        type="button"
                                        className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                                        onClick={handlePreview}
                                        disabled={!file || isPreviewing || loading || isMapping}
                                    >
                                        {isPreviewing ? "Prévisualisation..." : "Prévisualiser"}
                                    </button>
                                    <button
                                        type="button"
                                        className="inline-flex justify-center rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-700 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                                        onClick={handleMapTemplate}
                                        disabled={!file || isPreviewing || loading || isMapping}
                                    >
                                        {isMapping ? "Mapping..." : "Mapper vers modèle SIIRH"}
                                    </button>
                                    <button
                                        type="button"
                                        className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                                        onClick={handleImport}
                                        disabled={!file || loading || isPreviewing || isMapping}
                                    >
                                        {loading ? "Importation..." : "Importer"}
                                    </button>
                                </div>
                            </Dialog.Panel>
                        </Transition.Child>
                    </div>
                </div>
            </Dialog>
        </Transition>
    );
}
