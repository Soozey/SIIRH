
interface HsHmData {
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
}

interface HsHmDisplayProps {
    data: HsHmData;
    formatCurrency: (amount: number) => string;
}

export default function HsHmDisplay({ data, formatCurrency }: HsHmDisplayProps) {
    const hsHmLines = [
        { label: 'Heures Sup NI 130%', heures: data.hsni_130_heures, montant: data.hsni_130_montant, nonImposable: true },
        { label: 'Heures Sup I 130%', heures: data.hsi_130_heures, montant: data.hsi_130_montant, nonImposable: false },
        { label: 'Heures Sup NI 150%', heures: data.hsni_150_heures, montant: data.hsni_150_montant, nonImposable: true },
        { label: 'Heures Sup I 150%', heures: data.hsi_150_heures, montant: data.hsi_150_montant, nonImposable: false },
        { label: 'Heures Maj NH 30%', heures: data.hmnh_heures, montant: data.hmnh_montant, nonImposable: false },
        { label: 'Heures Maj NO 50%', heures: data.hmno_heures, montant: data.hmno_montant, nonImposable: false },
        { label: 'Heures Maj Dim 40%', heures: data.hmd_heures, montant: data.hmd_montant, nonImposable: false },
        { label: 'Heures Maj JF 200%', heures: data.hmjf_heures, montant: data.hmjf_montant, nonImposable: false },
    ];

    // Filtrer les lignes avec montant > 0
    const activeLines = hsHmLines.filter(line => line.montant > 0);

    // Si aucune ligne active, ne rien afficher
    if (activeLines.length === 0) {
        return null;
    }

    const totalNonImposable = activeLines
        .filter(l => l.nonImposable)
        .reduce((sum, l) => sum + l.montant, 0);

    const totalImposable = activeLines
        .filter(l => !l.nonImposable)
        .reduce((sum, l) => sum + l.montant, 0);

    const totalGeneral = totalNonImposable + totalImposable;

    return (
        <div className="glass-card overflow-hidden">
            <div className="px-6 py-4 bg-gradient-to-r from-primary-50 to-indigo-50 border-b border-primary-100">
                <h3 className="font-bold text-lg text-primary-900 flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Heures Supplémentaires et Majorations
                    {data.source_type === 'IMPORT' && (
                        <span className="ml-auto text-xs font-normal px-2 py-1 bg-blue-100 text-blue-700 rounded-full">
                            Importé Excel
                        </span>
                    )}
                    {data.source_type === 'MANUAL' && (
                        <span className="ml-auto text-xs font-normal px-2 py-1 bg-green-100 text-green-700 rounded-full">
                            Calcul Manuel
                        </span>
                    )}
                </h3>
            </div>

            <div className="p-6 space-y-2">
                {activeLines.map((line, index) => (
                    <div
                        key={index}
                        className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-slate-50 transition-colors"
                    >
                        <div className="flex items-center gap-3">
                            <span className="text-sm font-medium text-slate-700">
                                {line.label}
                            </span>
                            <span className="text-xs text-slate-500">
                                ({line.heures.toFixed(2)}h)
                            </span>
                            {line.nonImposable && (
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
                                    NI
                                </span>
                            )}
                        </div>
                        <div className="text-sm font-semibold text-slate-900">
                            {formatCurrency(line.montant)}
                        </div>
                    </div>
                ))}

                {/* Totaux */}
                <div className="mt-4 pt-4 border-t border-slate-200 space-y-2">
                    {totalNonImposable > 0 && (
                        <div className="flex justify-between text-sm">
                            <span className="text-amber-700 font-medium">Total Non Imposable :</span>
                            <span className="font-semibold text-amber-800">{formatCurrency(totalNonImposable)}</span>
                        </div>
                    )}
                    {totalImposable > 0 && (
                        <div className="flex justify-between text-sm">
                            <span className="text-slate-600 font-medium">Total Imposable :</span>
                            <span className="font-semibold text-slate-900">{formatCurrency(totalImposable)}</span>
                        </div>
                    )}
                    <div className="flex justify-between text-base pt-2 border-t border-slate-200">
                        <span className="text-primary-700 font-bold">TOTAL HS/HM :</span>
                        <span className="font-bold text-primary-900">{formatCurrency(totalGeneral)}</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
