// frontend/src/pages/LeavePermissionManagement.tsx
import { useState, useEffect } from "react";
import { api } from "../api";
import { CalendarIcon, PlusIcon, TrashIcon, EyeIcon, MagnifyingGlassIcon, ArrowPathIcon } from "@heroicons/react/24/outline";
import { useAuth } from "../contexts/AuthContext";

type PayrollRun = {
    id: number;
    period: string;
    employer_id: number;
    employer_name?: string;
};

type LeavePermissionEntry = {
    worker_id: number;
    matricule: string;
    nom: string;
    prenom: string;
    leave: {
        days_taken: number;
        balance: number;
        start_date: string | null;
        end_date: string | null;
        entries: Array<{
            id: number;
            start_date: string;
            end_date: string;
            days_taken: number;
            notes: string | null;
            workflow?: WorkflowState | null;
        }>;
        pending_days_taken?: number;
    };
    permission: {
        days_taken: number;
        balance: number;
        start_date: string | null;
        end_date: string | null;
        entries: Array<{
            id: number;
            start_date: string;
            end_date: string;
            days_taken: number;
            notes: string | null;
            workflow?: WorkflowState | null;
        }>;
        pending_days_taken?: number;
    };
};

type WorkflowState = {
    overall_status: string;
    manager_status: string;
    rh_status: string;
    manager_comment?: string | null;
    rh_comment?: string | null;
};

export default function LeavePermissionManagement() {
    const { session } = useAuth();
    const [payrollRuns, setPayrollRuns] = useState<PayrollRun[]>([]);
    const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
    const [data, setData] = useState<LeavePermissionEntry[]>([]);
    const [loading, setLoading] = useState(false);
    const [viewingWorker, setViewingWorker] = useState<LeavePermissionEntry | null>(null);
    const [search, setSearch] = useState("");

    // Load payroll runs
    useEffect(() => {
        api.get("/payroll/runs").then((res) => {
            setPayrollRuns(res.data);
            if (res.data.length > 0) {
                setSelectedRunId(res.data[0].id);
            }
        });
    }, []);

    // Load data when run is selected
    useEffect(() => {
        if (selectedRunId) {
            loadData();
        }
    }, [selectedRunId]);

    const loadData = async () => {
        if (!selectedRunId) return;
        setLoading(true);
        try {
            const res = await api.get(`/leaves/${selectedRunId}/all`);
            setData(res.data);
        } catch (error) {
            console.error("Error loading leave/permission data:", error);
        } finally {
            setLoading(false);
        }
    };

    const [addModal, setAddModal] = useState<{
        isOpen: boolean;
        type: 'leave' | 'permission';
        workerId: number | null;
        startDate: string;
        endDate: string;
        daysTaken: number | string;
    }>({
        isOpen: false,
        type: 'leave',
        workerId: null,
        startDate: '',
        endDate: '',
        daysTaken: ''
    });

    const [adjustmentModal, setAdjustmentModal] = useState<{
        isOpen: boolean;
        workerId: number | null;
        workerName: string;
        currentInitial: number | string;
    }>({
        isOpen: false,
        workerId: null,
        workerName: '',
        currentInitial: 0
    });

    // Auto-calculate days when dates change
    useEffect(() => {
        if (addModal.isOpen && addModal.startDate && addModal.endDate) {
            const days = calculateBusinessDays(addModal.startDate, addModal.endDate);
            setAddModal(prev => ({ ...prev, daysTaken: days }));
        }
    }, [addModal.startDate, addModal.endDate, addModal.isOpen]);

    const calculateBusinessDays = (startStr: string, endStr: string) => {
        const start = new Date(startStr);
        const end = new Date(endStr);

        if (isNaN(start.getTime()) || isNaN(end.getTime()) || start > end) return 0;

        let count = 0;
        const cur = new Date(start);
        while (cur <= end) {
            const dayOfWeek = cur.getDay();
            // Count Mon(1) to Sat(6). Exclude Sun(0).
            if (dayOfWeek !== 0) {
                count++;
            }
            cur.setDate(cur.getDate() + 1);
        }
        return count;
    };

    const handleAddLeave = (workerId: number) => {
        setAddModal({
            isOpen: true,
            type: 'leave',
            workerId,
            startDate: '',
            endDate: '',
            daysTaken: ''
        });
    };

    const handleAddPermission = (workerId: number) => {
        setAddModal({
            isOpen: true,
            type: 'permission',
            workerId,
            startDate: '',
            endDate: '',
            daysTaken: ''
        });
    };

    const handleSaveEntry = async () => {
        if (!addModal.workerId || !selectedRunId) return;
        const period = payrollRuns.find((r) => r.id === selectedRunId)?.period;
        if (!period) return;

        try {
            const endpoint = addModal.type === 'leave' ? '/leaves/leave' : '/leaves/permission';
            await api.post(endpoint, {
                worker_id: addModal.workerId,
                period,
                start_date: addModal.startDate,
                end_date: addModal.endDate,
                days_taken: Number(addModal.daysTaken),
                notes: null,
            });
            setAddModal(prev => ({ ...prev, isOpen: false }));
            loadData();
        } catch (error) {
            console.error("Error adding entry:", error);
            alert("Erreur lors de l'ajout");
        }
    };

    const handleAdjustBalance = (worker: LeavePermissionEntry) => {
        // We need to fetch the worker to get the current solde_conge_initial
        setLoading(true);
        api.get(`/workers/${worker.worker_id}`).then(res => {
            setAdjustmentModal({
                isOpen: true,
                workerId: worker.worker_id,
                workerName: `${worker.prenom} ${worker.nom}`,
                currentInitial: res.data.solde_conge_initial || 0
            });
        }).catch(err => {
            console.error("Error fetching worker for adjustment:", err);
            alert("Erreur lors de la récupération des données du travailleur");
        }).finally(() => {
            setLoading(false);
        });
    };

    const saveAdjustment = async () => {
        if (!adjustmentModal.workerId) return;
        try {
            await api.patch(`/workers/${adjustmentModal.workerId}`, {
                solde_conge_initial: Number(adjustmentModal.currentInitial) || 0
            });
            setAdjustmentModal(prev => ({ ...prev, isOpen: false }));
            loadData(); // Reload leave data to reflect new balance
        } catch (error) {
            console.error("Error saving adjustment:", error);
            alert("Erreur lors de la sauvegarde de l'ajustement");
        }
    };

    const handleDeleteLeave = async (leaveId: number) => {
        if (!confirm("Supprimer ce congé ?")) return;
        try {
            await api.delete(`/leaves/leave/${leaveId}`);
            loadData();
        } catch (error) {
            console.error("Error deleting leave:", error);
        }
    };

    const handleDeletePermission = async (permId: number) => {
        if (!confirm("Supprimer cette permission ?")) return;
        try {
            await api.delete(`/leaves/permission/${permId}`);
            loadData();
        } catch (error) {
            console.error("Error deleting permission:", error);
        }
    };

    const canReviewAsManager = ["admin", "rh", "manager"].includes(session?.role_code || "");
    const canReviewAsRh = ["admin", "rh"].includes(session?.role_code || "");

    const getWorkflowTone = (workflow?: WorkflowState | null) => {
        const status = workflow?.overall_status || "legacy";
        if (status === "approved") return "bg-emerald-100 text-emerald-800 border-emerald-200";
        if (status === "rejected") return "bg-rose-100 text-rose-800 border-rose-200";
        if (status === "pending_rh") return "bg-amber-100 text-amber-800 border-amber-200";
        return "bg-slate-100 text-slate-700 border-slate-200";
    };

    const getWorkflowLabel = (workflow?: WorkflowState | null) => {
        const status = workflow?.overall_status || "legacy";
        if (status === "approved") return "Validé";
        if (status === "rejected") return "Refusé";
        if (status === "pending_rh") return "En attente RH";
        if (status === "pending_manager") return "En attente manager";
        return "Historique";
    };

    const reviewRequest = async (
        type: "leave" | "permission",
        entryId: number,
        stage: "manager" | "rh",
        approved: boolean
    ) => {
        try {
            await api.post(`/leaves/${type}/${entryId}/review/${stage}`, {
                approved,
                comment: null,
            });
            await loadData();
            setViewingWorker(null);
        } catch (error) {
            console.error("Error reviewing request:", error);
            alert("Erreur lors du traitement de la demande");
        }
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 p-8">
            <div className="max-w-7xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <h1 className="text-4xl font-bold text-gray-900 mb-2 flex items-center gap-3">
                        <CalendarIcon className="h-10 w-10 text-blue-600" />
                        Gestion Congés & Permissions
                    </h1>
                    <p className="text-gray-600">Gérez les congés et permissions exceptionnelles par période de paie</p>
                </div>

                {/* Payroll Run Selector & Search */}
                <div className="bg-white rounded-2xl shadow-lg p-6 mb-6 flex flex-col md:flex-row md:items-end gap-6">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Période de Paie</label>
                        <select
                            value={selectedRunId || ""}
                            onChange={(e) => {
                                const val = Number(e.target.value);
                                setSelectedRunId(val);
                            }}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        >
                            <option value="" disabled>Sélectionnez une période</option>
                            {payrollRuns.map((run) => (
                                <option key={run.id} value={run.id}>
                                    {run.period} ({run.employer_name || 'N/A'})
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="flex-1">
                        <label className="block text-sm font-medium text-gray-700 mb-2">Recherche</label>
                        <div className="relative">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
                            </div>
                            <input
                                type="text"
                                placeholder="Recherche par matr nom prénom"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            />
                        </div>
                    </div>
                </div>

                {/* Data Table */}
                {loading ? (
                    <div className="text-center py-12">
                        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                        <p className="mt-4 text-gray-600">Chargement...</p>
                    </div>
                ) : (
                    <div className="bg-white rounded-2xl shadow-lg overflow-hidden">
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead className="bg-gradient-to-r from-blue-600 to-purple-600 text-white">
                                    <tr>
                                        <th className="px-4 py-3 text-left text-sm font-semibold">Matricule</th>
                                        <th className="px-4 py-3 text-left text-sm font-semibold">Nom & Prénom</th>
                                        <th className="px-4 py-3 text-center text-sm font-semibold" colSpan={2}>
                                            Congés
                                        </th>
                                        <th className="px-4 py-3 text-center text-sm font-semibold" colSpan={2}>
                                            Permissions
                                        </th>
                                    </tr>
                                    <tr className="bg-blue-500 text-white text-xs">
                                        <th className="px-4 py-2"></th>
                                        <th className="px-4 py-2"></th>
                                        <th className="px-4 py-2 text-center">Pris / Solde</th>
                                        <th className="px-4 py-2 text-center">Actions</th>
                                        <th className="px-4 py-2 text-center">Pris / Solde</th>
                                        <th className="px-4 py-2 text-center">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-gray-200">
                                    {data.filter(entry => {
                                        const s = search.toLowerCase();
                                        return entry.nom?.toLowerCase().includes(s) ||
                                            entry.prenom?.toLowerCase().includes(s) ||
                                            entry.matricule?.toLowerCase().includes(s);
                                    }).map((entry) => (
                                        <tr key={entry.worker_id} className="hover:bg-blue-50 transition-colors">
                                            <td className="px-4 py-3 text-sm font-medium text-gray-900">{entry.matricule}</td>
                                            <td className="px-4 py-3 text-sm text-gray-900">
                                                <div className="flex items-center gap-2">
                                                    <span>{entry.nom} {entry.prenom}</span>
                                                    <button
                                                        onClick={() => setViewingWorker(entry)}
                                                        className="text-gray-400 hover:text-blue-600 transition-colors p-1 rounded-full hover:bg-blue-50"
                                                        title="Voir détails"
                                                    >
                                                        <EyeIcon className="h-5 w-5" />
                                                    </button>
                                                </div>
                                            </td>
                                            {/* Leave */}
                                            <td className="px-4 py-3 text-center">
                                                <div className="text-sm">
                                                    <div className="font-bold text-blue-700">{entry.leave.days_taken}j pris</div>
                                                    <div className="text-green-700">Solde: {entry.leave.balance}j</div>
                                                    {(entry.leave.pending_days_taken || 0) > 0 && (
                                                        <div className="text-amber-700">En attente: {entry.leave.pending_days_taken}j</div>
                                                    )}
                                                    {entry.leave.entries.map((l) => (
                                                        <div key={l.id} className="text-xs text-gray-600 mt-1 flex items-center justify-center gap-2 flex-wrap">
                                                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 font-medium ${getWorkflowTone(l.workflow)}`}>
                                                                {getWorkflowLabel(l.workflow)}
                                                            </span>
                                                            <span>
                                                                {l.start_date} → {l.end_date} ({l.days_taken}j)
                                                            </span>
                                                            <button
                                                                onClick={() => handleDeleteLeave(l.id)}
                                                                className="text-red-600 hover:text-red-800"
                                                            >
                                                                <TrashIcon className="h-3 w-3" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <button
                                                    onClick={() => handleAddLeave(entry.worker_id)}
                                                    className="inline-flex items-center gap-1 px-3 py-1 bg-blue-600 text-white text-xs rounded-lg hover:bg-blue-700 transition-colors"
                                                >
                                                    <PlusIcon className="h-4 w-4" />
                                                    Ajouter
                                                </button>
                                            </td>
                                            {/* Permission */}
                                            <td className="px-4 py-3 text-center">
                                                <div className="text-sm">
                                                    <div className="font-bold text-orange-700">{entry.permission.days_taken}j pris</div>
                                                    <div className="text-green-700">Solde: {entry.permission.balance}j</div>
                                                    {(entry.permission.pending_days_taken || 0) > 0 && (
                                                        <div className="text-amber-700">En attente: {entry.permission.pending_days_taken}j</div>
                                                    )}
                                                    {entry.permission.entries.map((p) => (
                                                        <div key={p.id} className="text-xs text-gray-600 mt-1 flex items-center justify-center gap-2 flex-wrap">
                                                            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 font-medium ${getWorkflowTone(p.workflow)}`}>
                                                                {getWorkflowLabel(p.workflow)}
                                                            </span>
                                                            <span>
                                                                {p.start_date} → {p.end_date} ({p.days_taken}j)
                                                            </span>
                                                            <button
                                                                onClick={() => handleDeletePermission(p.id)}
                                                                className="text-red-600 hover:text-red-800"
                                                            >
                                                                <TrashIcon className="h-3 w-3" />
                                                            </button>
                                                        </div>
                                                    ))}
                                                </div>
                                            </td>
                                            <td className="px-4 py-3 text-center">
                                                <button
                                                    onClick={() => handleAddPermission(entry.worker_id)}
                                                    className="inline-flex items-center gap-1 px-3 py-1 bg-orange-600 text-white text-xs rounded-lg hover:bg-orange-700 transition-colors"
                                                >
                                                    <PlusIcon className="h-4 w-4" />
                                                    Ajouter
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {/* Details Modal */}
                {viewingWorker && (
                    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
                        <div className="bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] overflow-y-auto">
                            <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-2xl">
                                <div>
                                    <h2 className="text-2xl font-bold text-gray-900">Détails des absences</h2>
                                    <p className="text-gray-600">{viewingWorker.nom} {viewingWorker.prenom} ({viewingWorker.matricule})</p>
                                </div>
                                <button
                                    onClick={() => setViewingWorker(null)}
                                    className="text-gray-400 hover:text-gray-600 p-2 rounded-full hover:bg-gray-200 transition-colors"
                                >
                                    <span className="text-2xl">&times;</span>
                                </button>
                            </div>

                            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-8">
                                {/* Congés Section */}
                                <div className="bg-blue-50 rounded-xl p-5 border border-blue-100">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="text-lg font-bold text-blue-800 flex items-center gap-2">
                                            <span className="w-2 h-8 bg-blue-600 rounded-full"></span>
                                            Congés
                                        </h3>
                                        <div className="text-right">
                                            <div className="text-xs text-blue-600 uppercase font-semibold">Solde</div>
                                            <div className="flex items-center gap-2">
                                                <div className="text-2xl font-bold text-blue-900">{viewingWorker.leave.balance} j</div>
                                                <button
                                                    onClick={() => handleAdjustBalance(viewingWorker)}
                                                    className="p-1 text-blue-400 hover:text-blue-600 hover:bg-blue-100 rounded transition-colors"
                                                    title="Ajuster le solde initial"
                                                >
                                                    <ArrowPathIcon className="h-4 w-4" />
                                                </button>
                                            </div>
                                        </div>
                                    </div>

                                    {viewingWorker.leave.entries.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic text-center py-4">Aucun congé ce mois-ci</p>
                                    ) : (
                                        <div className="bg-white rounded-lg shadow-sm border border-blue-100 overflow-hidden">
                                            <table className="w-full text-sm text-left">
                                                <thead className="bg-blue-100 text-blue-800">
                                                    <tr>
                                                        <th className="px-3 py-2">Début</th>
                                                        <th className="px-3 py-2">Fin</th>
                                                        <th className="px-3 py-2 text-center">Jours</th>
                                                        <th className="px-3 py-2 text-center">Statut</th>
                                                        <th className="px-3 py-2 text-center">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-blue-50">
                                                    {viewingWorker.leave.entries.map(entry => (
                                                        <tr key={entry.id} className="hover:bg-blue-50">
                                                            <td className="px-3 py-2">{entry.start_date}</td>
                                                            <td className="px-3 py-2">{entry.end_date}</td>
                                                            <td className="px-3 py-2 text-center font-bold">{entry.days_taken}</td>
                                                            <td className="px-3 py-2 text-center">
                                                                <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-medium ${getWorkflowTone(entry.workflow)}`}>
                                                                    {getWorkflowLabel(entry.workflow)}
                                                                </span>
                                                            </td>
                                                            <td className="px-3 py-2 text-center">
                                                                <div className="flex items-center justify-center gap-2">
                                                                    {canReviewAsManager && entry.workflow?.overall_status === "pending_manager" && (
                                                                        <>
                                                                            <button
                                                                                onClick={() => reviewRequest("leave", entry.id, "manager", true)}
                                                                                className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
                                                                            >
                                                                                Valider
                                                                            </button>
                                                                            <button
                                                                                onClick={() => reviewRequest("leave", entry.id, "manager", false)}
                                                                                className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                                                                            >
                                                                                Refuser
                                                                            </button>
                                                                        </>
                                                                    )}
                                                                    {canReviewAsRh && entry.workflow?.overall_status === "pending_rh" && (
                                                                        <>
                                                                            <button
                                                                                onClick={() => reviewRequest("leave", entry.id, "rh", true)}
                                                                                className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
                                                                            >
                                                                                RH OK
                                                                            </button>
                                                                            <button
                                                                                onClick={() => reviewRequest("leave", entry.id, "rh", false)}
                                                                                className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                                                                            >
                                                                                RH KO
                                                                            </button>
                                                                        </>
                                                                    )}
                                                                    <button
                                                                        onClick={() => {
                                                                            if (confirm('Supprimer ?')) handleDeleteLeave(entry.id).then(() => setViewingWorker(null));
                                                                        }}
                                                                        className="text-red-500 hover:text-red-700"
                                                                    >
                                                                        <TrashIcon className="h-4 w-4" />
                                                                    </button>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>

                                {/* Permissions Section */}
                                <div className="bg-orange-50 rounded-xl p-5 border border-orange-100">
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="text-lg font-bold text-orange-800 flex items-center gap-2">
                                            <span className="w-2 h-8 bg-orange-600 rounded-full"></span>
                                            Permissions
                                        </h3>
                                        <div className="text-right">
                                            <div className="text-xs text-orange-600 uppercase font-semibold">Solde Annuel</div>
                                            <div className="text-2xl font-bold text-orange-900">{viewingWorker.permission.balance} j</div>
                                        </div>
                                    </div>

                                    {viewingWorker.permission.entries.length === 0 ? (
                                        <p className="text-sm text-gray-500 italic text-center py-4">Aucune permission ce mois-ci</p>
                                    ) : (
                                        <div className="bg-white rounded-lg shadow-sm border border-orange-100 overflow-hidden">
                                            <table className="w-full text-sm text-left">
                                                <thead className="bg-orange-100 text-orange-800">
                                                    <tr>
                                                        <th className="px-3 py-2">Début</th>
                                                        <th className="px-3 py-2">Fin</th>
                                                        <th className="px-3 py-2 text-center">Jours</th>
                                                        <th className="px-3 py-2 text-center">Statut</th>
                                                        <th className="px-3 py-2 text-center">Action</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-orange-50">
                                                    {viewingWorker.permission.entries.map(entry => (
                                                        <tr key={entry.id} className="hover:bg-orange-50">
                                                            <td className="px-3 py-2">{entry.start_date}</td>
                                                            <td className="px-3 py-2">{entry.end_date}</td>
                                                            <td className="px-3 py-2 text-center font-bold">{entry.days_taken}</td>
                                                            <td className="px-3 py-2 text-center">
                                                                <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-medium ${getWorkflowTone(entry.workflow)}`}>
                                                                    {getWorkflowLabel(entry.workflow)}
                                                                </span>
                                                            </td>
                                                            <td className="px-3 py-2 text-center">
                                                                <div className="flex items-center justify-center gap-2">
                                                                    {canReviewAsManager && entry.workflow?.overall_status === "pending_manager" && (
                                                                        <>
                                                                            <button
                                                                                onClick={() => reviewRequest("permission", entry.id, "manager", true)}
                                                                                className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
                                                                            >
                                                                                Valider
                                                                            </button>
                                                                            <button
                                                                                onClick={() => reviewRequest("permission", entry.id, "manager", false)}
                                                                                className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                                                                            >
                                                                                Refuser
                                                                            </button>
                                                                        </>
                                                                    )}
                                                                    {canReviewAsRh && entry.workflow?.overall_status === "pending_rh" && (
                                                                        <>
                                                                            <button
                                                                                onClick={() => reviewRequest("permission", entry.id, "rh", true)}
                                                                                className="rounded-lg bg-emerald-600 px-2 py-1 text-xs font-semibold text-white hover:bg-emerald-700"
                                                                            >
                                                                                RH OK
                                                                            </button>
                                                                            <button
                                                                                onClick={() => reviewRequest("permission", entry.id, "rh", false)}
                                                                                className="rounded-lg bg-rose-600 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                                                                            >
                                                                                RH KO
                                                                            </button>
                                                                        </>
                                                                    )}
                                                                    <button
                                                                        onClick={() => {
                                                                            if (confirm('Supprimer ?')) handleDeletePermission(entry.id).then(() => setViewingWorker(null));
                                                                        }}
                                                                        className="text-red-500 hover:text-red-700"
                                                                    >
                                                                        <TrashIcon className="h-4 w-4" />
                                                                    </button>
                                                                </div>
                                                            </td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div className="p-6 bg-gray-50 rounded-b-2xl border-t border-gray-100 flex justify-end">
                                <button
                                    onClick={() => setViewingWorker(null)}
                                    className="px-6 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                                >
                                    Fermer
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Add Entry Modal */}
                {addModal.isOpen && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50 backdrop-blur-sm">
                        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden transform transition-all scale-100 opacity-100">
                            <div className="p-6">
                                <h2 className={`text-xl font-bold mb-6 flex items-center gap-2 ${addModal.type === 'leave' ? 'text-blue-800' : 'text-orange-800'}`}>
                                    {addModal.type === 'leave' ? (
                                        <>
                                            <span className="w-2 h-8 bg-blue-600 rounded-full"></span>
                                            Ajouter un Congé
                                        </>
                                    ) : (
                                        <>
                                            <span className="w-2 h-8 bg-orange-600 rounded-full"></span>
                                            Ajouter une Permission
                                        </>
                                    )}
                                </h2>

                                <div className="space-y-4">
                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Date de début</label>
                                        <input
                                            type="date"
                                            className="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            value={addModal.startDate}
                                            onChange={e => setAddModal(prev => ({ ...prev, startDate: e.target.value }))}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">Date de fin</label>
                                        <input
                                            type="date"
                                            className="w-full border border-gray-300 rounded-lg p-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                                            value={addModal.endDate}
                                            onChange={e => setAddModal(prev => ({ ...prev, endDate: e.target.value }))}
                                        />
                                    </div>

                                    <div>
                                        <label className="block text-sm font-medium text-gray-700 mb-1">
                                            Jours (Calcul auto: Lun-Sam)
                                        </label>
                                        <input
                                            type="number"
                                            step="0.5"
                                            className="w-full border border-gray-300 rounded-lg p-2 bg-gray-50 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-bold text-gray-900"
                                            value={addModal.daysTaken}
                                            onChange={e => setAddModal(prev => ({ ...prev, daysTaken: e.target.value }))}
                                        />
                                        <p className="text-xs text-gray-500 mt-1 italic">Vous pouvez modifier ce montant manuellement.</p>
                                    </div>
                                </div>

                                <div className="mt-8 flex justify-end gap-3">
                                    <button
                                        onClick={() => setAddModal(prev => ({ ...prev, isOpen: false }))}
                                        className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors font-medium"
                                    >
                                        Annuler
                                    </button>
                                    <button
                                        onClick={handleSaveEntry}
                                        className={`px-6 py-2 text-white rounded-lg transition-colors font-medium shadow-sm ${addModal.type === 'leave'
                                            ? 'bg-blue-600 hover:bg-blue-700'
                                            : 'bg-orange-600 hover:bg-orange-700'
                                            }`}
                                    >
                                        Enregistrer
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
            {/* Adjustment Modal */}
            {adjustmentModal.isOpen && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[60] p-4">
                    <div className="bg-white rounded-2xl shadow-xl w-full max-w-md">
                        <div className="p-6 border-b border-gray-100">
                            <h3 className="text-lg font-bold text-gray-900">Ajuster le solde de congé</h3>
                            <p className="text-sm text-gray-500">{adjustmentModal.workerName}</p>
                        </div>
                        <div className="p-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                                Solde initial / Reprise de solde (jours)
                            </label>
                            <input
                                type="number"
                                step="0.5"
                                value={adjustmentModal.currentInitial}
                                onChange={(e) => setAdjustmentModal(prev => ({ ...prev, currentInitial: e.target.value }))}
                                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-bold text-lg"
                            />
                            <p className="mt-2 text-xs text-gray-400 italic">
                                Ce montant sera ajouté au total des jours acquis depuis l'embauche.
                            </p>
                        </div>
                        <div className="p-6 bg-gray-50 rounded-b-2xl flex justify-end gap-3">
                            <button
                                onClick={() => setAdjustmentModal(prev => ({ ...prev, isOpen: false }))}
                                className="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
                            >
                                Annuler
                            </button>
                            <button
                                onClick={saveAdjustment}
                                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-md"
                            >
                                Enregistrer
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
