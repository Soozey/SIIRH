import { useState, useRef } from 'react';
import { Dialog, Transition } from '@headlessui/react';
import { Fragment } from 'react';
import { CloudArrowUpIcon, DocumentArrowDownIcon, XMarkIcon } from '@heroicons/react/24/outline';
import { api, downloadWorkersTemplate } from '../api';
import { useQueryClient } from '@tanstack/react-query';

type Props = {
    isOpen: boolean;
    onClose: () => void;
};

export default function ImportWorkersDialog({ isOpen, onClose }: Props) {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<{ imported: number; skipped?: number; updated?: number; errors: string[] } | null>(null);
    const [updateExisting, setUpdateExisting] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const qc = useQueryClient();

    const handleDownloadTemplate = async () => {
        try {
            await downloadWorkersTemplate();
        } catch (error) {
            console.error("Erreur téléchargement modèle", error);
            alert("Erreur lors du téléchargement du modèle.");
        }
    };

    const handleImport = async () => {
        if (!file) return;

        setLoading(true);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);
        formData.append('update_existing', updateExisting.toString());

        try {
            // Using /workers/import endpoint created in backend
            const response = await api.post('/workers/import', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            setResult(response.data);
            if (response.data.imported > 0) {
                qc.invalidateQueries({ queryKey: ["workers"] });
            }
        } catch (error: any) {
            console.error("Erreur import", error);
            const msg = error.response?.data?.detail || "Erreur lors de l'importation.";
            alert(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleClose = () => {
        setFile(null);
        setResult(null);
        onClose();
    };

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
                                        Importez une liste de salariés depuis un fichier Excel (.xlsx).
                                        Assurez-vous d'utiliser le modèle correct.
                                    </p>

                                    <button
                                        onClick={handleDownloadTemplate}
                                        className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
                                    >
                                        <DocumentArrowDownIcon className="h-5 w-5" />
                                        Télécharger le modèle Excel
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
                                            accept=".xlsx"
                                            onChange={(e) => setFile(e.target.files?.[0] || null)}
                                        />
                                    </div>

                                    {result && (
                                        <div className={`rounded-md p-4 ${result.imported > 0 ? 'bg-green-50' : 'bg-red-50'}`}>
                                            <div className="flex">
                                                <div className="ml-3">
                                                    <h3 className={`text-sm font-medium ${result.imported > 0 ? 'text-green-800' : 'text-red-800'}`}>
                                                        Résultat de l'import
                                                    </h3>
                                                    <div className={`mt-2 text-sm ${result.imported > 0 || (result.updated || 0) > 0 ? 'text-green-700' : 'text-zinc-700'}`}>
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
                                                            </div>
                                                        )}
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
                                        className="inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
                                        onClick={handleImport}
                                        disabled={!file || loading}
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
