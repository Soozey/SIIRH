import { useRef } from 'react';
import { PrinterIcon, IdentificationIcon } from "@heroicons/react/24/outline";
import { usePrint } from '../hooks/usePrint';

type Props = {
    worker: any;
    employer: any;
    onClose?: () => void;
};

export default function EmploymentAttestation({ worker, employer, onClose }: Props) {
    const contentRef = useRef<HTMLDivElement>(null);

    const handlePrint = usePrint(`Attestation_Emploi_${worker.nom}_${worker.prenom}`);

    const formatDate = (dateStr: string) => {
        if (!dateStr) return "....................";
        return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });
    };

    const today = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });

    return (
        <div className="flex flex-col h-full bg-gray-100 p-4 overflow-auto print:bg-white print:p-0">
            {/* Print Toolbar */}
            <div className="flex justify-between items-center mb-4 print:hidden">
                <h2 className="text-xl font-bold text-gray-800">Attestation d'Emploi</h2>
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
                <span>Les champs sont cliquables et éditables directement sur le document avant impression</span>
            </div>

            {/* Document A4 Page */}
            <div
                ref={contentRef}
                className="printable-content bg-white mx-auto shadow-lg p-[20mm] w-[210mm] min-h-0 text-black font-sans leading-relaxed print:shadow-none print:w-full print:m-0 print:p-[20mm] text-[11pt]"
                style={{ fontFamily: 'Arial, Helvetica, sans-serif' }}
            >
                {/* Header Employer & Logo */}
                <div className="mb-8 border-b-2 border-gray-800 pb-4 flex justify-between items-start">
                    <div className="flex-1">
                        <h1 className="text-xl font-bold uppercase tracking-wide mb-2">{employer?.raison_sociale || "...................."}</h1>
                        <div className="text-xs text-gray-700 space-y-1">
                            <p>{employer?.adresse || "Adresse non renseignée"}</p>
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

                {/* Title */}
                <div className="text-center mb-10">
                    <h2 className="text-2xl font-bold uppercase border-b-2 border-black inline-block pb-1 tracking-wider">Attestation d'Emploi</h2>
                </div>

                {/* Body */}
                <div className="mb-8 space-y-6 text-justify leading-normal">
                    <p contentEditable suppressContentEditableWarning>
                        Je soussigné(e), <strong>{employer?.representant || employer?.rep_nom_prenom || "[NOM DU REPRESENTANT]"}</strong>,
                        agissant en qualité de {employer?.rep_fonction || "Représentant"} de la société <strong>{employer?.raison_sociale}</strong>,
                        atteste par la présente que :
                    </p>

                    <div className="py-4 bg-gray-50 border border-gray-100 rounded-lg print:border-none print:bg-transparent">
                        <p className="text-center text-lg font-bold uppercase tracking-wide mb-1">
                            M./Mme {worker?.nom} {worker?.prenom}
                        </p>
                        <p className="text-center text-sm text-gray-600">
                            Matricule: {worker?.matricule || "N/A"}
                        </p>
                    </div>

                    <p contentEditable suppressContentEditableWarning>
                        Est employé(e) au sein de notre société depuis le <strong>{formatDate(worker?.date_embauche)}</strong>.
                    </p>

                    <p contentEditable suppressContentEditableWarning>
                        Il/Elle occupe actuellement le poste de <strong>{worker?.poste || worker?.categorie_prof || "...................."}</strong> sous contrat de type <strong>{worker?.nature_contrat || "CDI"}</strong>.
                    </p>

                    <p contentEditable suppressContentEditableWarning>
                        Cette attestation est délivrée à la demande de l'intéressé(e) pour servir et valoir ce que de droit.
                    </p>
                </div>

                {/* Footer Date & Signature */}
                <div className="mt-12 flex flex-col items-end">
                    <p contentEditable suppressContentEditableWarning className="mb-6 text-base">
                        Fait à {employer?.ville || "...................."}, le {today}
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
