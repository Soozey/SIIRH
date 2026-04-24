import { useRef } from 'react';
import { PrinterIcon, IdentificationIcon } from "@heroicons/react/24/outline";
import { useWorkerData } from '../hooks/useConstants';
import { usePrint } from '../hooks/usePrint';

type Props = {
    worker: any;
    employer: any;
    onClose?: () => void;
};

export default function WorkCertificate({ worker, employer, onClose }: Props) {
    const contentRef = useRef<HTMLDivElement>(null);
    const { data: workerData } = useWorkerData(worker?.id || 0);
    const positionHistory = Array.isArray(worker?.position_history) ? worker.position_history : [];
    const displayWorker = {
        nom: workerData?.nom || worker?.nom || "",
        prenom: workerData?.prenom || worker?.prenom || "",
        matricule: workerData?.matricule || worker?.matricule || "",
        poste: workerData?.poste || worker?.poste || "",
        categorie_prof: workerData?.categorie_prof || worker?.categorie_prof || "",
        date_embauche: workerData?.date_embauche || worker?.date_embauche || "",
        date_debauche: worker?.date_debauche || "",
    };

    const handlePrint = usePrint(`Certificat_Travail_${displayWorker.nom}_${displayWorker.prenom}`);

    const formatDate = (dateStr: string) => {
        if (!dateStr) return "....................";
        return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    };

    const today = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });

    return (
        <div className="flex flex-col h-full bg-gray-100 p-4 overflow-auto print:bg-white print:p-0">
            <div className="flex justify-between items-center mb-4 print:hidden">
                <h2 className="text-xl font-bold text-gray-800">Certificat de Travail</h2>
                <div className="flex gap-2">
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-gray-600 bg-white border border-gray-300 rounded hover:bg-gray-50"
                        >
                            Fermer
                        </button>
                    )}
                    <button
                        onClick={handlePrint}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 shadow-sm"
                    >
                        <PrinterIcon className="h-5 w-5" />
                        Imprimer
                    </button>
                </div>
            </div>

            <div className="max-w-[210mm] mx-auto mb-2 text-xs text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-100 flex items-center gap-2 animate-pulse print:hidden w-fit">
                <IdentificationIcon className="h-3 w-3" />
                <span>Ce certificat est editable directement a l'ecran avant impression</span>
            </div>

            <div
                ref={contentRef}
                className="printable-content bg-white mx-auto shadow-lg p-[20mm] w-[210mm] min-h-0 text-black font-sans leading-relaxed print:shadow-none print:w-full print:m-0 print:p-[20mm] text-[11pt]"
                style={{ fontFamily: 'Arial, Helvetica, sans-serif' }}
            >
                <div className="mb-8 border-b-2 border-gray-800 pb-4 flex justify-between items-start">
                    <div className="flex-1">
                        <h1 className="text-xl font-bold uppercase tracking-wide mb-2">{employer?.raison_sociale || "...................."}</h1>
                        <div className="text-xs text-gray-700 space-y-1">
                            <p>{employer?.adresse || "Adresse non renseignee"}</p>
                            <p>{employer?.ville} {employer?.pays}</p>
                            <p>NIF: {employer?.nif || "N/A"} - STAT: {employer?.stat || "N/A"}</p>
                        </div>
                    </div>
                    {employer?.logo_path && (
                        <div className="ml-4 w-32 h-20 flex items-center justify-end">
                            <img
                                src={`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'}${employer.logo_path}`}
                                alt="Logo"
                                className="max-w-full max-h-full object-contain"
                            />
                        </div>
                    )}
                </div>

                <div className="text-center mb-10">
                    <h2 className="text-2xl font-bold uppercase border-b-2 border-black inline-block pb-1 tracking-wider">Certificat de Travail</h2>
                </div>

                <div className="mb-8 space-y-6 text-justify leading-normal">
                    <p contentEditable suppressContentEditableWarning>
                        Je soussigne(e), <strong>{employer?.representant || employer?.rep_nom_prenom || "[NOM DU REPRESENTANT]"}</strong>,
                        agissant en qualite de {employer?.rep_fonction || "Representant"} de la societe <strong>{employer?.raison_sociale}</strong>,
                        certifie par la presente que :
                    </p>

                    <div className="py-4 bg-gray-50 border border-gray-100 rounded-lg print:border-none print:bg-transparent">
                        <p className="text-center text-lg font-bold uppercase tracking-wide mb-1">
                            M./Mme {displayWorker.nom} {displayWorker.prenom}
                        </p>
                        <p className="text-center text-sm text-gray-600">
                            Matricule: {displayWorker.matricule || "N/A"}
                        </p>
                    </div>

                    <p contentEditable suppressContentEditableWarning>
                        A ete employe(e) au sein de notre societe du <strong>{formatDate(displayWorker.date_embauche)}</strong> au <strong>{formatDate(displayWorker.date_debauche)}</strong>.
                    </p>

                    <div className="pl-4 border-l-4 border-gray-200 print:border-l-2 print:border-black" contentEditable suppressContentEditableWarning>
                        <p className="mb-2 font-semibold italic text-sm">Postes occupes :</p>
                        {positionHistory.length > 0 ? (
                            <ul className="list-disc pl-5 space-y-2 text-sm">
                                {positionHistory
                                    .sort((a: any, b: any) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime())
                                    .map((hist: any, idx: number) => (
                                        <li key={idx}>
                                            <span className="font-bold">{hist.poste}</span> {hist.categorie_prof ? `(${hist.categorie_prof})` : ''} <br />
                                            <span className="text-gray-600">Du {formatDate(hist.start_date)} au {hist.end_date ? formatDate(hist.end_date) : formatDate(displayWorker.date_debauche)}</span>
                                        </li>
                                    ))}
                            </ul>
                        ) : (
                            <ul className="list-disc pl-5 text-sm">
                                <li>
                                    <span className="font-bold">{displayWorker.poste || "Employe(e)"}</span> {displayWorker.categorie_prof ? `(${displayWorker.categorie_prof})` : ''} <br />
                                    <span className="text-gray-600">Periode complete</span>
                                </li>
                            </ul>
                        )}
                    </div>

                    <p contentEditable suppressContentEditableWarning>
                        M./Mme {displayWorker.nom} quitte la societe libre de tout engagement et peut faire valoir ce certificat pour servir et valoir ce que de droit.
                    </p>
                </div>

                <div className="mt-12 flex flex-col items-end">
                    <p contentEditable suppressContentEditableWarning className="mb-6 text-base">
                        Fait a {employer?.ville || "...................."}, le {today}
                    </p>

                    <div className="w-64 text-center">
                        <p className="font-bold mb-16 text-base">L'Employeur</p>
                        <div className="border-t border-gray-400 w-full pt-1">
                            <p className="text-[10px] italic text-gray-500">(Signature et cachet)</p>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
