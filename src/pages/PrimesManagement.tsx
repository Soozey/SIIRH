import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getPrimes, createPrime, updatePrime, deletePrime } from "../api";
import type { Prime } from "../api";

const PrimesManagement: React.FC = () => {
    const { employerId } = useParams<{ employerId: string }>();

    const [primes, setPrimes] = useState<Prime[]>([]);
    // const [loading, setLoading] = useState(false);

    // Modal state
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingPrime, setEditingPrime] = useState<Partial<Prime>>({});
    const [activeField, setActiveField] = useState<string | null>(null);

    useEffect(() => {
        if (employerId) {
            fetchPrimes();
        }
    }, [employerId]);

    const fetchPrimes = async () => {
        // setLoading(true);
        try {
            const data = await getPrimes(parseInt(employerId!));
            setPrimes(data);
        } catch (error) {
            console.error("Failed to fetch primes", error);
        } finally {
            // setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!employerId) return;
        try {
            const payload = { ...editingPrime, employer_id: parseInt(employerId) };
            if (editingPrime.id) {
                await updatePrime(editingPrime.id, payload);
            } else {
                await createPrime(payload);
            }
            setIsModalOpen(false);
            fetchPrimes();
        } catch (error) {
            alert("Erreur lors de l'enregistrement");
        }
    };

    const handleDelete = async (id: number) => {
        if (confirm("Supprimer cette prime ? Les salariés affectés perdront cette configuration.")) {
            try {
                await deletePrime(id);
                fetchPrimes();
            } catch (error) {
                alert("Erreur suppression");
            }
        }
    };

    // Helper for inputs
    const handleFocus = (field: string) => {
        setActiveField(field);
    };

    return (
        <div className="p-6">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold text-gray-800">Gestion des Primes</h1>
                <button
                    onClick={() => { setEditingPrime({}); setIsModalOpen(true); }}
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                >
                    + Nouvelle Prime
                </button>
            </div>

            <div className="bg-white rounded shadow p-4">
                <table className="min-w-full">
                    <thead>
                        <tr className="bg-gray-100 border-b">
                            <th className="text-left py-2 px-4">Libellé</th>
                            <th className="text-left py-2 px-4">Formule (Nb / Op / Base / Op / Taux)</th>
                            <th className="text-left py-2 px-4">Active</th>
                            <th className="text-right py-2 px-4">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {primes
                            .sort((a, b) => a.label.localeCompare(b.label))
                            .map(p => (
                                <tr key={p.id} className="border-b hover:bg-gray-50">
                                    <td className="py-2 px-4 font-medium">{p.label}</td>
                                    <td className="py-2 px-4 text-sm text-gray-600">
                                        {(p.formula_nombre || "0")} {p.operation_1} {(p.formula_base || "0")} {p.operation_2} {(p.formula_taux || "0")}
                                    </td>
                                    <td className="py-2 px-4">
                                        {p.is_active ? <span className="text-green-600">Oui</span> : <span className="text-red-500">Non</span>}
                                    </td>
                                    <td className="py-2 px-4 text-right space-x-2">
                                        <button
                                            onClick={() => { setEditingPrime(p); setIsModalOpen(true); }}
                                            className="text-blue-600 hover:underline"
                                        >
                                            Modifier
                                        </button>
                                        <button
                                            onClick={() => handleDelete(p.id)}
                                            className="text-red-600 hover:underline"
                                        >
                                            Supprimer
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        {primes.length === 0 && (
                            <tr>
                                <td colSpan={4} className="text-center py-4 text-gray-500">Aucune prime définie.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            {isModalOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg">
                        <h2 className="text-xl font-bold mb-4">{editingPrime.id ? "Modifier Prime" : "Nouvelle Prime"}</h2>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium">Libellé</label>
                                <input
                                    type="text"
                                    className="w-full border rounded p-2"
                                    value={editingPrime.label || ""}
                                    onChange={e => setEditingPrime({ ...editingPrime, label: e.target.value })}
                                // No variables for label
                                />
                            </div>

                            <div className="grid grid-cols-3 gap-2">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500">Formule Nombre</label>
                                    <input
                                        type="text"
                                        placeholder="ex: 1, ANCIENAN..."
                                        className="w-full border rounded p-2 text-sm"
                                        value={editingPrime.formula_nombre || ""}
                                        onChange={e => setEditingPrime({ ...editingPrime, formula_nombre: e.target.value })}
                                        onFocus={() => handleFocus('formula_nombre')}
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500">Opérateur 1</label>
                                    <select
                                        className="w-full border rounded p-2 text-sm"
                                        value={editingPrime.operation_1 || "*"}
                                        onChange={e => setEditingPrime({ ...editingPrime, operation_1: e.target.value })}
                                    >
                                        <option value="*">*</option>
                                        <option value="/">/</option>
                                        <option value="+">+</option>
                                        <option value="-">-</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500">Formule Base</label>
                                    <input
                                        type="text"
                                        placeholder="ex: SALDBASE, 5000..."
                                        className="w-full border rounded p-2 text-sm"
                                        value={editingPrime.formula_base || ""}
                                        onChange={e => setEditingPrime({ ...editingPrime, formula_base: e.target.value })}
                                        onFocus={() => handleFocus('formula_base')}
                                    />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                                <div>
                                    <label className="block text-xs font-bold text-gray-500">Opérateur 2</label>
                                    <select
                                        className="w-full border rounded p-2 text-sm"
                                        value={editingPrime.operation_2 || "*"}
                                        onChange={e => setEditingPrime({ ...editingPrime, operation_2: e.target.value })}
                                    >
                                        <option value="*">*</option>
                                        <option value="/">/</option>
                                        <option value="+">+</option>
                                        <option value="-">-</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-gray-500">Formule Taux</label>
                                    <input
                                        type="text"
                                        placeholder="ex: 1, 0.05..."
                                        className="w-full border rounded p-2 text-sm"
                                        value={editingPrime.formula_taux || ""}
                                        onChange={e => setEditingPrime({ ...editingPrime, formula_taux: e.target.value })}
                                        onFocus={() => handleFocus('formula_taux')}
                                    />
                                </div>
                            </div>

                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox"
                                        checked={editingPrime.is_active !== false}
                                        onChange={e => setEditingPrime({ ...editingPrime, is_active: e.target.checked })}
                                    />
                                    Active
                                </label>
                            </div>

                            <div className="bg-blue-50 p-3 rounded text-xs text-blue-800">
                                <div className="font-bold mb-2">Variables disponibles (cliquez pour insérer) :</div>
                                <div className="flex flex-wrap gap-2">
                                    {["SALDBASE", "SALHORAI", "SALJOURN", "ANCIENAN", "NOMBRENF", "DAYSWORK", "SME"].map(v => (
                                        <button
                                            key={v}
                                            type="button"
                                            onClick={() => {
                                                // Find active input? Complex since state is managed.
                                                // Better approach: User clicks input -> sets "activeField". User clicks chip -> appends to activeField.
                                                if (activeField) {
                                                    setEditingPrime(prev => ({
                                                        ...prev,
                                                        [activeField]: (prev[activeField as keyof Prime] || "") + v
                                                    }));
                                                } else {
                                                    alert("Veuillez cliquer d'abord dans un champ de formule (Nombre, Base ou Taux).");
                                                }
                                            }}
                                            className="bg-white border border-blue-200 px-2 py-1 rounded hover:bg-blue-100 transition-colors"
                                        >
                                            {v}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        <div className="mt-6 flex justify-end gap-3">
                            <button
                                onClick={() => setIsModalOpen(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                            >
                                Annuler
                            </button>
                            <button
                                onClick={handleSave}
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Enregistrer
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PrimesManagement;
