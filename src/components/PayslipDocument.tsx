import { useRef } from 'react';
import { PrinterIcon } from "@heroicons/react/24/outline";
import { usePrint } from '../hooks/usePrint';

// ... [Keep existing types] ...
type PayslipLine = {
    label: string;
    nombre: number | string | null;
    base: number | string | null;
    taux_sal: string | null;
    montant_sal: number;
    taux_pat: string | null;
    montant_pat: number;
};
// ... [Keep types] ...
type Totaux = {
    salaire_brut_numeraire: number;
    somme_avantages_taxables: number;
    brut: number;
    cotisations_salariales: number;
    cotisations_patronales: number;
    cotisations: number;
    irsa: number;
    debits: number;
    credits: number;
    net: number;
    computed_at?: string;
};
// ... [Continue types] ...
type Employer = {
    id: number;
    raison_sociale: string;
    adresse?: string | null;
    ville?: string | null;
    nif?: string | null;
    stat?: string | null;
    cnaps?: string | null;
    logo_path?: string | null;
};
type Worker = {
    id: number;
    matricule: string;
    nom: string;
    prenom: string;
    adresse?: string | null;
    poste?: string | null;
    categorie_prof?: string | null;
    date_embauche?: string | null;
    cnaps?: string | null;
    secteur?: string | null;
    mode_paiement?: string | null;
    etablissement?: string | null;
    departement?: string | null;
    service?: string | null;
    unite?: string | null;
    etablissement_name?: string | null;
    departement_name?: string | null;
    service_name?: string | null;
    unite_name?: string | null;
};
type HsHmData = {
    hsni_130_heures: number;
    hsi_130_heures: number;
    hsni_150_heures: number;
    hsi_150_heures: number;
    hmnh_heures: number;
    hmno_heures: number;
    hmd_heures: number;
    hmjf_heures: number;
    hsni_130_montant: number;
    hsi_130_montant: number;
    hsni_150_montant: number;
    hsi_150_montant: number;
    hmnh_montant: number;
    hmno_montant: number;
    hmd_montant: number;
    hmjf_montant: number;
    source_type: string;
};
type LeaveData = {
    taken_this_month: number;
    balance: number;
    start_date: string | null;
    end_date: string | null;
};
type PermissionData = {
    taken_this_month: number;
    balance: number;
    start_date: string | null;
    end_date: string | null;
};

export type PayslipData = {
    employer: Employer;
    worker: Worker;
    period: string;
    lines: PayslipLine[];
    totaux: Totaux;
    hs_hm?: HsHmData | null;
    leave?: LeaveData | null;
    permission?: PermissionData | null;
};

type Props = {
    data: PayslipData;
    showPrintButton?: boolean;
};

export default function PayslipDocument({ data, showPrintButton = false }: Props) {
    const { employer, worker, totaux, lines, period } = data;
    const contentRef = useRef<HTMLDivElement>(null); // NEW: Ref for PDF generation



    // Guard clauses for missing objects (prevent red box crash)
    if (!data || !employer || !worker || !totaux || !lines) {
        return (
            <div className="p-8 text-center text-red-600 border-2 border-red-200 bg-red-50 rounded-lg">
                <p className="font-bold">Erreur de données</p>
                <p>Les informations du bulletin sont incomplètes ou invalides.</p>
                <p className="text-xs text-gray-500 mt-2">
                    Missing:
                    {!employer && " Employer"}
                    {!worker && " Worker"}
                    {!totaux && " Totaux"}
                    {!lines && " Lines"}
                </p>
            </div>
        );
    }

    const formatCurrency = (amount: number | string | null, isIRSA: boolean = false) => {
        if (amount === null || amount === undefined || amount === "") return "";
        const n = typeof amount === "string" ? Number(amount) : amount;
        if (isNaN(n)) return "";
        
        // Pour l'IRSA, si c'est un entier, forcer l'affichage avec ,00
        if (isIRSA && Number.isInteger(Math.abs(n))) {
            return new Intl.NumberFormat("fr-MG", {
                style: "currency",
                currency: "MGA",
                maximumFractionDigits: 2,
                minimumFractionDigits: 2,
            }).format(n);
        }
        
        return new Intl.NumberFormat("fr-MG", {
            style: "currency",
            currency: "MGA",
            maximumFractionDigits: 2,
            minimumFractionDigits: 2,
        }).format(n);
    };

    const formatDate = (dateStr?: string | null) => {
        if (!dateStr) return "-";
        if (dateStr.includes("/")) return dateStr;
        try {
            return new Date(dateStr).toLocaleDateString("fr-FR");
        } catch {
            return dateStr;
        }
    };

    const formatOrganizationalInfo = (worker: Worker) => {
        const orgInfo = [];
        // Utiliser les noms si disponibles, sinon fallback sur les IDs
        if (worker.etablissement_name && worker.etablissement_name.trim()) {
            orgInfo.push(`Établissement: ${worker.etablissement_name}`);
        } else if (worker.etablissement && worker.etablissement.trim()) {
            orgInfo.push(`Établissement: ${worker.etablissement}`);
        }
        
        if (worker.departement_name && worker.departement_name.trim()) {
            orgInfo.push(`Département: ${worker.departement_name}`);
        } else if (worker.departement && worker.departement.trim()) {
            orgInfo.push(`Département: ${worker.departement}`);
        }
        
        if (worker.service_name && worker.service_name.trim()) {
            orgInfo.push(`Service: ${worker.service_name}`);
        } else if (worker.service && worker.service.trim()) {
            orgInfo.push(`Service: ${worker.service}`);
        }
        
        if (worker.unite_name && worker.unite_name.trim()) {
            orgInfo.push(`Unité: ${worker.unite_name}`);
        } else if (worker.unite && worker.unite.trim()) {
            orgInfo.push(`Unité: ${worker.unite}`);
        }
        
        return orgInfo;
    };

    const formatRate = (rate: string | number | null) => {
        if (rate === null || rate === undefined || rate === "") return "";
        if (typeof rate === "string" && rate.includes("%")) return rate;

        const num = typeof rate === "string" ? parseFloat(rate) : rate;
        if (isNaN(num)) return rate; // Return original if not a number

        // Heuristic: If strictly between -1 and 1 (exclusive of 0), show as percentage
        // UPDATE: Also include 1 explicitly as 100%
        if ((Math.abs(num) > 0 && Math.abs(num) < 1) || Math.abs(num) === 1) {
            return new Intl.NumberFormat("fr-MG", {
                style: "percent",
                minimumFractionDigits: 0,
                maximumFractionDigits: 2
            }).format(num);
        }
        return num.toString();
    };

    const calculateSeniority = (dateEmbauche?: string | null, currentPeriod?: string) => {
        if (!dateEmbauche || !currentPeriod) return "-";
        try {
            const start = new Date(dateEmbauche);
            // Period is YYYY-MM. Assume end of month.
            const [year, month] = currentPeriod.split('-').map(Number);
            const end = new Date(year, month, 0); // Last day of month

            let years = end.getFullYear() - start.getFullYear();
            let months = end.getMonth() - start.getMonth();

            if (months < 0) {
                years--;
                months += 12;
            }

            if (years > 0) return `${years} ans ${months} mois`;
            return `${months} mois`;
        } catch {
            return "-";
        }
    };

    // Calculs d'affichage
    let hsni_total = 0;
    lines.forEach(l => {
        if (l.label && l.label.toLowerCase().includes("non imposable")) {
            hsni_total += l.montant_sal;
        }
    });
    const rim_estime = totaux.brut - totaux.cotisations_salariales - hsni_total;

    let avance_total = 0;

    lines.forEach(l => {
        if (!l) return;
        const lbl = (l.label || "").toLowerCase();
        if (lbl.includes("avance")) {
            avance_total += Math.abs(l.montant_sal);
        }
    });

    const footerCotisationLines = lines.filter(l => {
        if (!l) return false;
        const lbl = (l.label || "").toLowerCase();
        // Inclusion des cotisations uniquement pour le détail
        return lbl.includes("cotisation") || lbl.includes("fmfp") || lbl.includes("cnaps") || lbl.includes("smie");
    });

    const otherDeductionLines = lines.filter(l => {
        if (!l) return false;
        const lbl = (l.label || "").toLowerCase();
        return lbl.includes("déduction") || lbl.includes("deduction") || lbl.includes("autre ded");
    });

    // Determine Title
    // Si lignes d'indemnités de rupture présentes OU date_debauche dans le mois (si on avait la logique de date ici)
    // Mais la présence des lignes est le signe le plus fiable d'un solde de tout compte calculé.
    const hasTerminationIndemnity = lines.some(l =>
        l.label && l.label.toLowerCase().includes("indemnité compensatrice")
    );

    // Titre dynamique
    const documentTitle = hasTerminationIndemnity ? "Solde de tout compte" : "Bulletin de Paie";


    const handlePrint = usePrint(`${documentTitle.replace(/ /g, '_')}_${worker.matricule}_${period}`);

    return (
        <div className="max-w-[210mm] mx-auto">

            {/* Print Button */}
            {showPrintButton && (
                <div className="mb-4 print:hidden flex justify-end">
                    <button
                        onClick={handlePrint}
                        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm"
                    >
                        <PrinterIcon className="h-5 w-5" />
                        Imprimer
                    </button>
                </div>
            )}

            <div
                ref={contentRef}
                className="printable-content border border-gray-400 p-4 rounded-lg bg-white shadow-sm print:shadow-none print:border-none print:p-0 text-[11px] leading-snug font-sans text-gray-900"
            >

                {/* HEADER */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                    {/* Employer Details */}
                    <div className="border border-gray-400 rounded p-2 flex items-start gap-3">
                        {employer.logo_path && (
                            <div className="flex-shrink-0 w-24 h-16 flex items-center justify-center">
                                <img
                                    src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}${employer.logo_path}`}
                                    alt="Logo"
                                    className="max-w-full max-h-full object-contain"
                                />
                            </div>
                        )}
                        <div className="flex-grow">
                            <h2 className="font-bold text-base uppercase mb-1">{employer.raison_sociale}</h2>
                            <div className="space-y-[2px]">
                                <p>{employer.adresse || "-"}</p>
                                <p>{employer.ville || ""}</p>
                                <div className="flex flex-wrap gap-x-2">
                                    <p>NIF: {employer.nif || "-"}</p>
                                    <p>STAT: {employer.stat || "-"}</p>
                                </div>
                                <p>CNaPS: {employer.cnaps || "-"}</p>
                                
                                {/* Informations organisationnelles du salarié */}
                                {formatOrganizationalInfo(worker).length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-gray-200">
                                        <p className="text-xs font-semibold text-gray-700 mb-1">Affectation:</p>
                                        <div className="space-y-[1px]">
                                            {formatOrganizationalInfo(worker).map((info, index) => (
                                                <p key={index} className="text-xs text-gray-800">{info}</p>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Worker Details */}
                    <div className="border border-gray-400 rounded p-2">
                        <h2 className="font-bold text-sm uppercase mb-1 border-b border-gray-200 pb-1">{documentTitle}</h2>
                        <div className="grid grid-cols-[80px_1fr] gap-x-2 gap-y-[2px]">
                            <span className="font-semibold text-gray-600">Matricule:</span>
                            <span className="font-bold text-black">{worker.matricule}</span>

                            <span className="font-semibold text-gray-600">Nom:</span>
                            <span className="font-bold text-black">{worker.nom} {worker.prenom}</span>

                            <span className="font-semibold text-gray-600">Adresse:</span>
                            <span>{worker.adresse || "-"}</span>

                            <span className="font-semibold text-gray-600">Catégorie:</span>
                            <span>{worker.categorie_prof || "-"}</span>

                            <span className="font-semibold text-gray-600">Fonction:</span>
                            <span>{worker.poste || "-"}</span>

                            <span className="font-semibold text-gray-600">Embauche:</span>
                            <span>{formatDate(worker.date_embauche)}</span>

                            <span className="font-semibold text-gray-600">Ancienneté:</span>
                            <span>{calculateSeniority(worker.date_embauche, period)}</span>
                        </div>
                    </div>
                </div>

                {/* Period & Info Bar */}
                <div className="bg-gray-100 border-y border-gray-400 py-1 px-4 mb-4 flex justify-between items-center font-semibold text-xs">
                    <div>
                        Période du: <span className="text-black">{period ? `01/${period.split('-')[1]}/${period.split('-')[0]}` : "-"}</span> au <span className="text-black">{period ? `${new Date(Number(period.split('-')[0]), Number(period.split('-')[1]), 0).getDate()}/${period.split('-')[1]}/${period.split('-')[0]}` : "-"}</span>
                    </div>
                    <div>
                        Paiement: {worker.mode_paiement || "Virement Bancaire"}
                    </div>
                    <div>
                        Devise: MGA (Ariary)
                    </div>
                </div>

                {/* MAIN TABLE */}
                <table className="w-full border-collapse mb-4 text-[10px]">
                    <thead>
                        <tr className="bg-gray-100 border border-gray-400 text-[9px] uppercase tracking-wider">
                            <th className="border border-gray-400 px-1 py-1 text-left w-[30%]">Rubriques</th>
                            <th className="border border-gray-400 px-1 py-1 text-center w-[8%]">Nombre</th>
                            <th className="border border-gray-400 px-1 py-1 text-right w-[12%]">Base</th>
                            <th className="border border-gray-400 px-1 py-1 text-right w-[8%]">Taux Sal.</th>
                            <th className="border border-gray-400 px-1 py-1 text-right w-[12%]">Montant Sal.</th>
                            <th className="border border-gray-400 px-1 py-1 text-right w-[8%]">Taux Pat.</th>
                            <th className="border border-gray-400 px-1 py-1 text-right w-[12%]">Montant Pat.</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lines.filter(l => {
                            if (!l) return false;
                            const lbl = (l.label || "").toLowerCase();
                            // Exclusion des lignes de pied de page (cotisations, irsa, avance, autres déductions)
                            const isFooterItem = lbl.includes("cotisation") ||
                                lbl.includes("fmfp") ||
                                lbl.includes("cnaps") ||
                                lbl.includes("smie") ||
                                lbl.includes("irsa") ||
                                lbl.includes("déduction") ||
                                lbl.includes("deduction") ||
                                lbl.includes("autre ded");

                            // Keep if not footer item AND has values
                            return !isFooterItem && (l.montant_sal !== 0 || l.montant_pat !== 0 || l.nombre);
                        }).map((line, idx) => (
                            <tr key={idx} className="border-b border-gray-200">
                                <td className="border-x border-gray-400 px-2 py-[2px]">{line.label}</td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-center">{line.nombre || ""}</td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-right">{formatCurrency(line.base)}</td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-right">{formatRate(line.taux_sal)}</td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-right text-gray-800 font-medium">
                                    {line.montant_sal !== 0 ? formatCurrency(line.montant_sal) : ""}
                                </td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-right">{formatRate(line.taux_pat)}</td>
                                <td className="border-x border-gray-400 px-2 py-[2px] text-right text-gray-600">
                                    {line.montant_pat !== 0 ? formatCurrency(line.montant_pat) : ""}
                                </td>
                            </tr>
                        ))}

                        {/* VIDES POUR REMPLIR LA PAGE si besoin */}
                        <tr key="row-spacer" className="h-4 border-l border-r border-gray-300">
                            <td className="border-r border-gray-300"></td><td></td><td></td><td></td><td></td><td></td><td></td>
                        </tr>

                        {/* --- FOOTER DES TOTAUX --- */}

                        {/* 1. Brut en numéraire */}
                        <tr key="row-brut-numeraire" className="border-t-2 border-gray-800 font-bold bg-gray-50/50">
                            <td className="border border-gray-300 px-2 py-1 text-right bg-white" colSpan={4}>Brut en numéraire</td>
                            <td className="border border-gray-300 px-2 py-1 text-right">{formatCurrency(totaux.salaire_brut_numeraire)}</td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                        </tr>

                        {/* 2. Avantages en nature */}
                        <tr key="row-av-nature" className="border-b border-gray-300">
                            <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>Avantages en nature taxables</td>
                            <td className="border border-gray-300 px-2 py-1 text-right">{formatCurrency(totaux.somme_avantages_taxables)}</td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                        </tr>

                        {/* 3. Total Brut */}
                        <tr key="row-total-brut" className="border-t border-gray-800 font-bold">
                            <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>TOTAL BRUT</td>
                            <td className="border border-gray-300 px-2 py-1 text-right">{formatCurrency(totaux.brut)}</td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                        </tr>

                        {/* DÉTAIL DES COTISATIONS */}
                        {footerCotisationLines.map((line, idx) => (
                            <tr key={`cotis-${idx}`} className="border-b border-gray-300 text-xs">
                                <td className="border border-gray-300 px-2 py-1 font-medium">{line.label}</td>
                                <td className="border border-gray-300 px-2 py-1 text-center">{line.nombre || ""}</td>
                                <td className="border border-gray-300 px-2 py-1 text-right text-xs">{formatCurrency(line.base)}</td>
                                <td className="border border-gray-300 px-2 py-1 text-right text-xs">{line.taux_sal}</td>
                                <td className="border border-gray-300 px-2 py-1 text-right text-red-600">
                                    {line.montant_sal !== 0 ? formatCurrency(line.montant_sal) : ""}
                                </td>
                                <td className="border border-gray-300 px-2 py-1 text-right font-semibold text-slate-700">{line.taux_pat}</td>
                                <td className="border border-gray-300 px-2 py-1 text-right font-semibold text-slate-700">
                                    {line.montant_pat !== 0 ? formatCurrency(line.montant_pat) : ""}
                                </td>
                            </tr>
                        ))}

                        {/* 4. Total Cotisations */}
                        <tr key="row-cotisations" className="border-b border-gray-300 bg-gray-50/50 italic">
                            <td className="border border-gray-300 px-2 py-1 text-right font-semibold" colSpan={4}>Total Cotisations</td>
                            <td className="border border-gray-300 px-2 py-1 text-right text-red-600 font-bold">-{formatCurrency(totaux.cotisations_salariales)}</td>
                            <td className="border border-gray-300 px-2 py-1 text-right font-medium" colSpan={1}>Total Patronal:</td>
                            <td className="border border-gray-300 px-2 py-1 text-right font-bold">{formatCurrency(totaux.cotisations_patronales)}</td>
                        </tr>

                        {/* 5. Revenu Imposable */}
                        <tr key="row-rim" className="border-b border-gray-300">
                            <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>Revenu Imposable</td>
                            <td className="border border-gray-300 px-2 py-1 text-right">{formatCurrency(rim_estime)}</td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                        </tr>

                        {/* 6. IRSA */}
                        <tr key="row-irsa" className="border-b border-gray-300">
                            <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>IRSA</td>
                            <td className="border border-gray-300 px-2 py-1 text-right text-red-600">-{formatCurrency(totaux.irsa, true)}</td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                        </tr>

                        {/* 7. Avance sur salaire */}
                        {avance_total > 0 && (
                            <tr key="row-avance" className="border-b border-gray-300">
                                <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>Avance sur salaire</td>
                                <td className="border border-gray-300 px-2 py-1 text-right text-red-600">-{formatCurrency(avance_total)}</td>
                                <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                                <td className="border border-gray-300 px-2 py-1 bg-gray-100"></td>
                            </tr>
                        )}

                        {/* 8. Autres Déductions */}
                        {otherDeductionLines.map((line, idx) => (
                            <tr key={`deduc-${idx}`} className="border-b border-gray-300">
                                <td className="border border-gray-300 px-2 py-1 text-right" colSpan={4}>{line.label}</td>
                                <td className="border border-gray-300 px-2 py-1 text-right text-red-600">
                                    {line.montant_sal !== 0 ? formatCurrency(line.montant_sal) : ""}
                                </td>
                                <td className="border border-gray-300 px-2 py-1 text-right border-gray-300 bg-gray-100"></td>
                                <td className="border border-gray-300 px-2 py-1 text-right border-gray-300 bg-gray-100"></td>
                            </tr>
                        ))}

                        {/* 9. NET A PAYER */}
                        <tr key="row-net" className="bg-gray-100 border-t-2 border-gray-800 font-bold text-sm">
                            <td className="border border-gray-400 px-4 py-2 text-right" colSpan={4}>NET A PAYER</td>
                            <td className="border border-gray-400 px-2 py-2 text-right text-green-700 text-base">{formatCurrency(totaux.net)}</td>
                            <td className="border border-gray-400 px-2 py-2 text-right text-[10px] align-middle" colSpan={1}>Charges Soc. Globales</td>
                            <td className="border border-gray-400 px-2 py-2 text-right text-[10px]">{formatCurrency(totaux.cotisations)}</td>
                        </tr>

                    </tbody>
                </table>

                {/* Leave & Permission Summary Tables */}
                {(data.leave || data.permission) && (
                    <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {/* Leave Summary */}
                        {data.leave && (
                            <div className="border border-gray-400 rounded-lg overflow-hidden">
                                <div className="bg-blue-100 px-3 py-2 font-bold text-sm border-b border-gray-400">
                                    Congés
                                </div>
                                <table className="w-full text-xs">
                                    <tbody>
                                        <tr className="border-b border-gray-300">
                                            <td className="px-3 py-2 font-medium">Congé pris ce mois</td>
                                            <td className="px-3 py-2 text-right font-bold">{data.leave.taken_this_month} jour(s)</td>
                                        </tr>
                                        <tr className="border-b border-gray-300">
                                            <td className="px-3 py-2 font-medium">Congé restant</td>
                                            <td className="px-3 py-2 text-right font-bold text-green-700">{data.leave.balance} jour(s)</td>
                                        </tr>
                                        {data.leave.start_date && (
                                            <tr>
                                                <td className="px-3 py-2 font-medium">Dates</td>
                                                <td className="px-3 py-2 text-right">{data.leave.start_date}</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}

                        {/* Permission Summary */}
                        {data.permission && (
                            <div className="border border-gray-400 rounded-lg overflow-hidden">
                                <div className="bg-orange-100 px-3 py-2 font-bold text-sm border-b border-gray-400">
                                    Permissions Exceptionnelles
                                </div>
                                <table className="w-full text-xs">
                                    <tbody>
                                        <tr className="border-b border-gray-300">
                                            <td className="px-3 py-2 font-medium">Permission prise ce mois</td>
                                            <td className="px-3 py-2 text-right font-bold">{data.permission.taken_this_month} jour(s)</td>
                                        </tr>
                                        <tr>
                                            <td className="px-3 py-2 font-medium">Permission restante (année)</td>
                                            <td className="px-3 py-2 text-right font-bold text-green-700">{data.permission.balance} jour(s)</td>
                                        </tr>
                                        {data.permission.start_date && (
                                            <tr>
                                                <td className="px-3 py-2 font-medium">Dates</td>
                                                <td className="px-3 py-2 text-right">{data.permission.start_date}</td>
                                            </tr>
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}

                {/* Pied de page */}
                <div className="mt-8 flex justify-between text-xs text-gray-500">
                    <div>
                        <p>Pour l'employeur,</p>
                        <p className="mt-8 italic">(Signature et Cachet)</p>
                    </div>
                    <div>
                        <p>Pour le salarié,</p>
                        <p className="mt-8 italic">(Précédé de la mention "Lu et approuvé")</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
