import { useState, useEffect } from "react";
import { api } from "../api";
import {
    ChartBarIcon,
    PlusIcon,
    XMarkIcon,
    ArrowPathIcon,
    ArrowDownTrayIcon,
    EyeIcon,
    TableCellsIcon,
    BuildingOfficeIcon,
    AdjustmentsHorizontalIcon,
    FunnelIcon,
    IdentificationIcon,
    MagnifyingGlassIcon,
    ExclamationTriangleIcon
} from "@heroicons/react/24/outline";

interface Field {
    id: string;
    label: string;
    category: string;
}

interface OrganizationalData {
    etablissements: string[];
    departements: string[];
    services: string[];
    unites: string[];
}

export default function Reporting() {
    const [employers, setEmployers] = useState<any[]>([]);
    const [selectedEmployerId, setSelectedEmployerId] = useState<number | "">("");
    const [startPeriod, setStartPeriod] = useState(new Date().toISOString().substring(0, 7));
    const [endPeriod, setEndPeriod] = useState(new Date().toISOString().substring(0, 7));

    const [availableFields, setAvailableFields] = useState<Field[]>([]);
    const [selectedFields, setSelectedFields] = useState<Field[]>([]);
    const [isLoadingMeta, setIsLoadingMeta] = useState(false);

    // Filtres structurels organisationnels
    const [filterEtab, setFilterEtab] = useState("");
    const [filterDept, setFilterDept] = useState("");
    const [filterService, setFilterService] = useState("");
    const [filterUnite, setFilterUnite] = useState("");
    
    // Données organisationnelles pour les filtres en cascade
    const [orgData, setOrgData] = useState<OrganizationalData>({
        etablissements: [],
        departements: [],
        services: [],
        unites: []
    });
    const [isLoadingOrgData, setIsLoadingOrgData] = useState(false);

    const [reportData, setReportData] = useState<any[]>([]);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isExporting, setIsExporting] = useState(false);
    const [isExportingPdf, setIsExportingPdf] = useState(false);
    const [activeCategory, setActiveCategory] = useState<string>("Identité");

    // NEW: Matricule-based search and filtering
    const [matriculeSearch, setMatriculeSearch] = useState("");
    const [workerNameSearch, setWorkerNameSearch] = useState("");
    const [showMatriculeColumn, setShowMatriculeColumn] = useState(true);
    const [groupByMatricule, setGroupByMatricule] = useState(false);
    const [homonymDetected, setHomonymDetected] = useState(false);

    // Load employers
    useEffect(() => {
        const fetchEmployers = async () => {
            try {
                const res = await api.get("/employers");
                setEmployers(res.data);
                if (res.data.length > 0) setSelectedEmployerId(res.data[0].id);
            } catch (err) {
                console.error("Erreur chargement employeurs:", err);
            }
        };
        fetchEmployers();
    }, []);

    // Load metadata when employer changes
    useEffect(() => {
        if (selectedEmployerId) {
            setIsLoadingMeta(true);
            api.get(`/reporting/metadata`, { params: { employer_id: selectedEmployerId } })
                .then(res => {
                    setAvailableFields(res.data.fields);
                    // Sélection par défaut étendue pour un aperçu plus complet avec matricules
                    if (selectedFields.length === 0) {
                        const defaults = res.data.fields.filter((f: Field) =>
                            [
                                // Identité de base avec matricule
                                "matricule", "nom", "prenom", "poste",
                                // Salaire de base
                                "salaire_base", "Salaire de base",
                                // Principales rubriques de gains
                                "HS Non Imposable 130%", "HS Imposable 130%", "HS Non Imposable 150%", "HS Imposable 150%",
                                // Retenues principales
                                "Cotisation CNaPS", "Cotisation SMIE", "IRSA",
                                // Résultats essentiels
                                "brut_total", "net_a_payer", "cout_total_employeur"
                            ].includes(f.id)
                        );
                        setSelectedFields(defaults);
                        
                        // Vérifier si le matricule est disponible dans les champs
                        const hasMatricule = defaults.some((f: Field) => f.id === "matricule");
                        setShowMatriculeColumn(hasMatricule);
                    }
                })
                .catch(err => console.error("Erreur chargement metadata:", err))
                .finally(() => setIsLoadingMeta(false));
        }
    }, [selectedEmployerId]);

    // Charger les données organisationnelles quand l'employeur change
    useEffect(() => {
        if (!selectedEmployerId) return;
        
        const fetchOrgData = async () => {
            setIsLoadingOrgData(true);
            try {
                const response = await api.get(`/employers/${selectedEmployerId}/organizational-data/workers`);
                setOrgData(response.data);
            } catch (error) {
                console.error('Erreur chargement données organisationnelles:', error);
                // Réinitialiser les données en cas d'erreur
                setOrgData({
                    etablissements: [],
                    departements: [],
                    services: [],
                    unites: []
                });
            } finally {
                setIsLoadingOrgData(false);
            }
        };

        fetchOrgData();
        // Réinitialiser les filtres quand l'employeur change
        setFilterEtab("");
        setFilterDept("");
        setFilterService("");
        setFilterUnite("");
    }, [selectedEmployerId]);

    // Charger les données filtrées quand les filtres changent (filtrage en cascade)
    useEffect(() => {
        if (!selectedEmployerId) return;
        
        const fetchFilteredData = async () => {
            try {
                const params: any = {};
                if (filterEtab) params.etablissement = filterEtab;
                if (filterDept) params.departement = filterDept;
                if (filterService) params.service = filterService;
                
                const response = await api.get(`/employers/${selectedEmployerId}/organizational-data/filtered`, {
                    params
                });
                
                // Mettre à jour seulement les niveaux inférieurs
                setOrgData(prevData => ({
                    etablissements: prevData.etablissements, // Garder la liste complète des établissements
                    departements: filterEtab ? response.data.departements : prevData.departements,
                    services: (filterEtab || filterDept) ? response.data.services : prevData.services,
                    unites: (filterEtab || filterDept || filterService) ? response.data.unites : prevData.unites
                }));
            } catch (error) {
                console.error('Erreur chargement données filtrées:', error);
            }
        };

        // Déclencher le filtrage seulement si au moins un filtre est appliqué
        if (filterEtab || filterDept || filterService) {
            fetchFilteredData();
        }
    }, [selectedEmployerId, filterEtab, filterDept, filterService]);

    const handleOrganizationalFilterChange = (field: string, value: string) => {
        switch (field) {
            case 'etablissement':
                setFilterEtab(value);
                // Réinitialiser les filtres inférieurs
                setFilterDept("");
                setFilterService("");
                setFilterUnite("");
                break;
            case 'departement':
                setFilterDept(value);
                // Réinitialiser les filtres inférieurs
                setFilterService("");
                setFilterUnite("");
                break;
            case 'service':
                setFilterService(value);
                // Réinitialiser les filtres inférieurs
                setFilterUnite("");
                break;
            case 'unite':
                setFilterUnite(value);
                break;
        }
    };

    const handleAddField = (field: Field) => {
        if (!selectedFields.find(f => f.id === field.id)) {
            setSelectedFields([...selectedFields, field]);
        }
    };

    const handleRemoveField = (fieldId: string) => {
        setSelectedFields(selectedFields.filter(f => f.id !== fieldId));
    };

    const handleGenerate = async () => {
        if (!selectedEmployerId) return;
        setIsGenerating(true);
        setReportData([]);
        setHomonymDetected(false);
        try {
            const res = await api.post("/reporting/generate", {
                employer_id: selectedEmployerId,
                start_period: startPeriod,
                end_period: endPeriod,
                columns: selectedFields.map(f => f.id),
                etablissement: filterEtab || undefined,
                departement: filterDept || undefined,
                service: filterService || undefined,
                unite: filterUnite || undefined,
                // NEW: Matricule-based search parameters
                matricule_search: matriculeSearch || undefined,
                worker_name_search: workerNameSearch || undefined,
                include_matricule: showMatriculeColumn,
                group_by_matricule: groupByMatricule
            });
            
            setReportData(res.data);
            
            // NEW: Detect homonyms in the report data
            if (res.data && res.data.length > 0) {
                const nameGroups: { [name: string]: any[] } = {};
                res.data.forEach((worker: any) => {
                    const fullName = `${worker.prenom || ''} ${worker.nom || ''}`.trim().toLowerCase();
                    if (!nameGroups[fullName]) {
                        nameGroups[fullName] = [];
                    }
                    nameGroups[fullName].push(worker);
                });
                
                const hasHomonyms = Object.values(nameGroups).some(group => group.length > 1);
                setHomonymDetected(hasHomonyms);
            }
        } catch (e) {
            console.error(e);
            alert("Erreur lors de la génération du rapport");
        } finally {
            setIsGenerating(false);
        }
    };

    const handleExportExcel = async () => {
        if (!selectedEmployerId) return;
        setIsExporting(true);
        try {
            const res = await api.post("/reporting/export-excel", {
                employer_id: selectedEmployerId,
                start_period: startPeriod,
                end_period: endPeriod,
                columns: selectedFields.map(f => f.id),
                etablissement: filterEtab || undefined,
                departement: filterDept || undefined,
                service: filterService || undefined,
                unite: filterUnite || undefined,
                // NEW: Always include matricules in exports for traceability (Requirement 8.2)
                matricule_search: matriculeSearch || undefined,
                worker_name_search: workerNameSearch || undefined,
                include_matricule: true, // Force matricule inclusion in exports
                group_by_matricule: groupByMatricule
            }, { responseType: 'blob' });

            const url = window.URL.createObjectURL(new Blob([res.data]));
            const link = document.createElement('a');
            link.href = url;
            const filename = `Reporting_${startPeriod}_au_${endPeriod}${matriculeSearch ? '_matricule_' + matriculeSearch : ''}${workerNameSearch ? '_nom_' + workerNameSearch : ''}.xlsx`;
            link.setAttribute('download', filename);
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (e) {
            console.error(e);
            alert("Erreur lors de l'export Excel");
        } finally {
            setIsExporting(false);
        }
    };

    const handleExportPdf = async () => {
        if (!selectedEmployerId) return;
        setIsExportingPdf(true);
        try {
            const res = await api.post("/generated-documents/reporting", {
                employer_id: selectedEmployerId,
                start_period: startPeriod,
                end_period: endPeriod,
                columns: selectedFields.map(f => f.id),
                etablissement: filterEtab || undefined,
                departement: filterDept || undefined,
                service: filterService || undefined,
                unite: filterUnite || undefined,
                matricule_search: matriculeSearch || undefined,
                worker_name_search: workerNameSearch || undefined,
                include_matricule: true,
                group_by_matricule: groupByMatricule
            }, { responseType: 'blob' });

            const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `Reporting_${startPeriod}_au_${endPeriod}.pdf`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            console.error(e);
            alert("Erreur lors de l'export PDF");
        } finally {
            setIsExportingPdf(false);
        }
    };

    const categories = Array.from(new Set(availableFields.map(f => f.category)));
    const filteredAvailable = availableFields.filter(f => f.category === activeCategory);

    return (
        <>
            <style>{`
                .glass-card {
                    background: rgba(255, 255, 255, 0.95);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 16px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }
                
                .glass-input {
                    background: rgba(255, 255, 255, 0.9);
                    backdrop-filter: blur(5px);
                    border: 1px solid rgba(226, 232, 240, 0.8);
                    border-radius: 8px;
                    transition: all 0.2s ease;
                }
                
                .glass-input:focus {
                    background: rgba(255, 255, 255, 1);
                    border-color: #3b82f6;
                    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
                    outline: none;
                }
                
                .btn-primary {
                    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                    color: white;
                    border: none;
                    transition: all 0.2s ease;
                }
                
                .btn-primary:hover:not(:disabled) {
                    background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
                    transform: translateY(-1px);
                }
                
                .custom-scrollbar {
                    scrollbar-width: thin;
                    scrollbar-color: #cbd5e1 #f1f5f9;
                }
                
                .custom-scrollbar::-webkit-scrollbar {
                    width: 6px;
                    height: 6px;
                }
                
                .custom-scrollbar::-webkit-scrollbar-track {
                    background: #f1f5f9;
                    border-radius: 3px;
                }
                
                .custom-scrollbar::-webkit-scrollbar-thumb {
                    background: #cbd5e1;
                    border-radius: 3px;
                }
                
                .custom-scrollbar::-webkit-scrollbar-thumb:hover {
                    background: #94a3b8;
                }
                
                .animate-fade-in {
                    animation: fadeIn 0.5s ease-in-out;
                }
                
                .animate-slide-up {
                    animation: slideUp 0.3s ease-out;
                }
                
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                
                @keyframes slideUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>
        <div className="min-h-screen p-6 md:p-10 max-w-[1600px] mx-auto space-y-8 animate-fade-in">
            {/* Header */}
            <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-blue-600 to-indigo-700 p-8 shadow-2xl shadow-blue-500/20">
                <div className="relative z-10 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
                    <div className="flex items-center gap-6">
                        <div className="p-4 bg-white/20 backdrop-blur-md rounded-2xl border border-white/10">
                            <ChartBarIcon className="h-10 w-10 text-white" />
                        </div>
                        <div>
                            <h1 className="text-3xl font-bold text-white tracking-tight">Reporting Dynamique</h1>
                            <p className="text-blue-100 mt-1 text-lg">Construisez vos rapports personnalisés sur mesure</p>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
                {/* Left Sidebar: Configuration */}
                <div className="xl:col-span-1 space-y-6">
                    <div className="glass-card p-6 space-y-6 sticky top-24">
                        <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                            <AdjustmentsHorizontalIcon className="h-6 w-6 text-blue-500" />
                            Configuration
                        </h2>

                        {/* Employeur & Période */}
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-semibold text-slate-700 mb-2">Employeur</label>
                                <div className="relative">
                                    <BuildingOfficeIcon className="absolute left-3 top-3 h-5 w-5 text-slate-400" />
                                    <select
                                        value={selectedEmployerId}
                                        onChange={(e) => setSelectedEmployerId(Number(e.target.value))}
                                        className="glass-input w-full pl-10 pr-4 py-2.5 text-slate-700"
                                    >
                                        {employers.map(emp => (
                                            <option key={emp.id} value={emp.id}>{emp.raison_sociale}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Début</label>
                                    <input
                                        type="month"
                                        value={startPeriod}
                                        onChange={(e) => setStartPeriod(e.target.value)}
                                        className="glass-input w-full px-3 py-2.5 text-sm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-semibold text-slate-700 mb-2">Fin</label>
                                    <input
                                        type="month"
                                        value={endPeriod}
                                        onChange={(e) => setEndPeriod(e.target.value)}
                                        className="glass-input w-full px-3 py-2.5 text-sm"
                                    />
                                </div>
                            </div>

                            <div className="pt-4 border-t border-slate-100 mb-2">
                                <div className="flex items-center gap-2">
                                    <FunnelIcon className="h-4 w-4 text-slate-400" />
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Filtres Organisationnels</span>
                                    {(filterEtab || filterDept || filterService || filterUnite) && (
                                        <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                                            {[filterEtab, filterDept, filterService, filterUnite].filter(Boolean).length} actif{[filterEtab, filterDept, filterService, filterUnite].filter(Boolean).length > 1 ? 's' : ''}
                                        </span>
                                    )}
                                </div>
                            </div>

                            {isLoadingOrgData ? (
                                <div className="flex items-center justify-center py-8">
                                    <ArrowPathIcon className="h-5 w-5 animate-spin text-slate-400" />
                                    <span className="ml-2 text-sm text-slate-500">Chargement...</span>
                                </div>
                            ) : (
                                <div className="space-y-3">
                                    {/* Etablissement */}
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-500 mb-1">Etablissement</label>
                                        <select
                                            value={filterEtab}
                                            onChange={(e) => handleOrganizationalFilterChange('etablissement', e.target.value)}
                                            className="glass-input w-full px-3 py-2 text-sm"
                                        >
                                            <option value="">Tous les établissements</option>
                                            {orgData.etablissements.map((item, index) => (
                                                <option key={index} value={item}>
                                                    {item}
                                                </option>
                                            ))}
                                        </select>
                                    </div>

                                    {/* Département */}
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-500 mb-1">
                                            Département
                                            {filterEtab && (
                                                <span className="text-xs text-blue-600 ml-1">
                                                    (filtré par {filterEtab})
                                                </span>
                                            )}
                                        </label>
                                        <select
                                            value={filterDept}
                                            onChange={(e) => handleOrganizationalFilterChange('departement', e.target.value)}
                                            disabled={!filterEtab}
                                            className={`glass-input w-full px-3 py-2 text-sm ${
                                                !filterEtab ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                                            }`}
                                        >
                                            <option value="">
                                                {!filterEtab 
                                                    ? 'Sélectionnez d\'abord un établissement' 
                                                    : 'Tous les départements'
                                                }
                                            </option>
                                            {orgData.departements.map((item, index) => (
                                                <option key={index} value={item}>
                                                    {item}
                                                </option>
                                            ))}
                                        </select>
                                        {!filterEtab && (
                                            <p className="text-xs text-gray-500 mt-1">
                                                Sélectionnez un établissement pour voir les départements
                                            </p>
                                        )}
                                    </div>

                                    {/* Service */}
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-500 mb-1">
                                            Service
                                            {(filterEtab || filterDept) && (
                                                <span className="text-xs text-blue-600 ml-1">
                                                    (filtre par {[filterEtab, filterDept].filter(Boolean).join(" -> ")})
                                                </span>
                                            )}
                                        </label>
                                        <select
                                            value={filterService}
                                            onChange={(e) => handleOrganizationalFilterChange('service', e.target.value)}
                                            disabled={!filterEtab && !filterDept}
                                            className={`glass-input w-full px-3 py-2 text-sm ${
                                                !filterEtab && !filterDept ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                                            }`}
                                        >
                                            <option value="">
                                                {!filterEtab && !filterDept
                                                    ? 'Sélectionnez d\'abord un niveau supérieur' 
                                                    : 'Tous les services'
                                                }
                                            </option>
                                            {orgData.services.map((item, index) => (
                                                <option key={index} value={item}>
                                                    {item}
                                                </option>
                                            ))}
                                        </select>
                                        {!filterEtab && !filterDept && (
                                            <p className="text-xs text-gray-500 mt-1">
                                                Sélectionnez un niveau supérieur pour voir les services
                                            </p>
                                        )}
                                    </div>

                                    {/* Unité */}
                                    <div>
                                        <label className="block text-xs font-semibold text-slate-500 mb-1">
                                            Unité
                                            {(filterEtab || filterDept || filterService) && (
                                                <span className="text-xs text-blue-600 ml-1">
                                                    (filtre par {[filterEtab, filterDept, filterService].filter(Boolean).join(" -> ")})
                                                </span>
                                            )}
                                        </label>
                                        <select
                                            value={filterUnite}
                                            onChange={(e) => handleOrganizationalFilterChange('unite', e.target.value)}
                                            disabled={!filterEtab && !filterDept && !filterService}
                                            className={`glass-input w-full px-3 py-2 text-sm ${
                                                !filterEtab && !filterDept && !filterService ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : ''
                                            }`}
                                        >
                                            <option value="">
                                                {!filterEtab && !filterDept && !filterService
                                                    ? 'Sélectionnez d\'abord un niveau supérieur' 
                                                    : 'Toutes les unités'
                                                }
                                            </option>
                                            {orgData.unites.map((item, index) => (
                                                <option key={index} value={item}>
                                                    {item}
                                                </option>
                                            ))}
                                        </select>
                                        {!filterEtab && !filterDept && !filterService && (
                                            <p className="text-xs text-gray-500 mt-1">
                                                Sélectionnez un niveau supérieur pour voir les unités
                                            </p>
                                        )}
                                    </div>

                                    {/* Bouton de réinitialisation des filtres */}
                                    {(filterEtab || filterDept || filterService || filterUnite) && (
                                        <div className="pt-2">
                                            <button
                                                onClick={() => {
                                                    setFilterEtab("");
                                                    setFilterDept("");
                                                    setFilterService("");
                                                    setFilterUnite("");
                                                }}
                                                className="text-xs text-red-600 hover:text-red-700 font-medium flex items-center gap-1"
                                            >
                                                <XMarkIcon className="h-3 w-3" />
                                                Effacer tous les filtres
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* NEW: Matricule-based Search and Options */}
                        <div className="pt-4 border-t border-slate-100 space-y-4">
                            <div className="flex items-center gap-2 mb-3">
                                <IdentificationIcon className="h-4 w-4 text-slate-400" />
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Recherche par Matricule</span>
                            </div>
                            
                            {/* Matricule Search */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-1">Matricule spécifique</label>
                                <div className="relative">
                                    <IdentificationIcon className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                    <input
                                        type="text"
                                        value={matriculeSearch}
                                        onChange={(e) => setMatriculeSearch(e.target.value)}
                                        placeholder="Ex: MAT001, MAT002..."
                                        className="glass-input w-full pl-9 pr-3 py-2 text-sm"
                                    />
                                </div>
                            </div>

                            {/* Worker Name Search */}
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 mb-1">Recherche par nom</label>
                                <div className="relative">
                                    <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
                                    <input
                                        type="text"
                                        value={workerNameSearch}
                                        onChange={(e) => setWorkerNameSearch(e.target.value)}
                                        placeholder="Nom ou prénom du salarié..."
                                        className="glass-input w-full pl-9 pr-3 py-2 text-sm"
                                    />
                                </div>
                            </div>

                            {/* Matricule Display Options */}
                            <div className="space-y-2">
                                <label className="flex items-center gap-2 text-xs text-slate-600">
                                    <input
                                        type="checkbox"
                                        checked={showMatriculeColumn}
                                        onChange={(e) => setShowMatriculeColumn(e.target.checked)}
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    Afficher la colonne matricule
                                </label>
                                
                                <label className="flex items-center gap-2 text-xs text-slate-600">
                                    <input
                                        type="checkbox"
                                        checked={groupByMatricule}
                                        onChange={(e) => setGroupByMatricule(e.target.checked)}
                                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    Regrouper par matricule (audit)
                                </label>
                            </div>

                            {/* Clear Search */}
                            {(matriculeSearch || workerNameSearch) && (
                                <button
                                    onClick={() => {
                                        setMatriculeSearch("");
                                        setWorkerNameSearch("");
                                    }}
                                    className="text-xs text-red-600 hover:text-red-700 font-medium flex items-center gap-1"
                                >
                                    <XMarkIcon className="h-3 w-3" />
                                    Effacer la recherche
                                </button>
                            )}
                        </div>

                        {/* NEW: Historical Search Section (Requirement 8.5) */}
                        <div className="pt-4 border-t border-slate-100 space-y-4">
                            <div className="flex items-center gap-2 mb-3">
                                <ArrowPathIcon className="h-4 w-4 text-slate-400" />
                                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Recherche Historique</span>
                            </div>
                            
                            <div className="bg-blue-50 p-3 rounded-lg">
                                <p className="text-xs text-blue-700 mb-2 font-medium">
                                    Astuce : utilisez la recherche par matricule ou nom ci-dessus pour retrouver l'historique complet d'un salarié, même si son nom a changé.
                                </p>
                                <p className="text-xs text-blue-600">
                                    Les matricules garantissent la continuité de l'historique lors des changements de nom (mariage, correction, etc.).
                                </p>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="pt-4 border-t border-slate-100 space-y-3">
                            <button
                                onClick={handleGenerate}
                                disabled={isGenerating || selectedFields.length === 0}
                                className="w-full btn-primary py-3 rounded-xl font-semibold flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                            >
                                {isGenerating ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <EyeIcon className="h-5 w-5" />}
                                Générer l'aperçu
                            </button>
                            <button
                                onClick={handleExportExcel}
                                disabled={isExporting || selectedFields.length === 0}
                                className="w-full py-3 bg-emerald-600 text-white font-semibold rounded-xl hover:bg-emerald-700 transition-colors flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
                            >
                                {isExporting ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <TableCellsIcon className="h-5 w-5" />}
                                Exporter en Excel
                            </button>
                            <button
                                onClick={handleExportPdf}
                                disabled={isExportingPdf || selectedFields.length === 0}
                                className="w-full py-3 bg-rose-600 text-white font-semibold rounded-xl hover:bg-rose-700 transition-colors flex items-center justify-center gap-2 shadow-md disabled:opacity-50"
                            >
                                {isExportingPdf ? <ArrowPathIcon className="h-5 w-5 animate-spin" /> : <ArrowDownTrayIcon className="h-5 w-5" />}
                                Exporter en PDF
                            </button>
                        </div>
                    </div>
                </div>

                {/* Center: Column Builder */}
                <div className="xl:col-span-3 space-y-8">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        {/* Library of fields */}
                        <div className="glass-card overflow-hidden flex flex-col h-[600px]">
                            <div className="bg-slate-50 p-4 border-b border-slate-200">
                                <h3 className="font-bold text-slate-800">Bibliothèque de Variables</h3>
                            </div>
                            <div className="flex flex-1 overflow-hidden">
                                {/* Vertical Tabs for Categories */}
                                <div className="w-1/3 bg-slate-50/50 border-r border-slate-100 overflow-y-auto">
                                    {categories.map(cat => (
                                        <button
                                            key={cat}
                                            onClick={() => setActiveCategory(cat)}
                                            className={`w-full text-left px-4 py-3 text-sm font-medium transition-colors border-l-4 ${activeCategory === cat
                                                ? "bg-white text-blue-600 border-blue-600 shadow-sm"
                                                : "text-slate-600 border-transparent hover:bg-slate-100"
                                                }`}
                                        >
                                            {cat}
                                        </button>
                                    ))}
                                </div>
                                {/* Fields List */}
                                <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-2">
                                    {isLoadingMeta ? (
                                        <div className="flex justify-center py-10"><ArrowPathIcon className="h-8 w-8 text-slate-300 animate-spin" /></div>
                                    ) : filteredAvailable.map(field => {
                                        const isSelected = selectedFields.find(f => f.id === field.id);
                                        return (
                                            <button
                                                key={field.id}
                                                onClick={() => handleAddField(field)}
                                                disabled={!!isSelected}
                                                className={`w-full flex items-center justify-between p-3 rounded-xl border transition-all ${isSelected
                                                    ? "bg-slate-50 border-slate-100 text-slate-400 cursor-not-allowed"
                                                    : "bg-white border-slate-200 text-slate-700 hover:border-blue-400 hover:shadow-md group"
                                                    }`}
                                            >
                                                <span className="text-sm font-medium">{field.label}</span>
                                                {!isSelected && <PlusIcon className="h-4 w-4 text-slate-400 group-hover:text-blue-500" />}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>

                        {/* Selected Fields */}
                        <div className="glass-card flex flex-col h-[600px]">
                            <div className="bg-blue-50 p-4 border-b border-blue-100 flex justify-between items-center">
                                <h3 className="font-bold text-blue-900">Colonnes Sélectionnées ({selectedFields.length})</h3>
                                <div className="flex gap-2">
                                    <button
                                        onClick={() => {
                                            // Sélectionner toutes les rubriques de paie comme dans l'export Excel
                                            const payrollFields = availableFields.filter(f => 
                                                ['Identité', 'Base', 'Gains', 'Retenues', 'Charges Patronales', 'Résultats'].includes(f.category)
                                            );
                                            setSelectedFields(payrollFields);
                                        }}
                                        className="text-xs text-blue-600 hover:underline font-semibold px-2 py-1 bg-blue-100 rounded"
                                    >
                                        Etat de Paie Complet
                                    </button>
                                    <button
                                        onClick={() => setSelectedFields([])}
                                        className="text-xs text-blue-600 hover:underline font-semibold"
                                    >
                                        Tout effacer
                                    </button>
                                </div>
                            </div>
                            <div className="flex-1 p-4 overflow-y-auto custom-scrollbar space-y-2">
                                {selectedFields.length === 0 ? (
                                    <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-4">
                                        <AdjustmentsHorizontalIcon className="h-12 w-12 opacity-20" />
                                        <p className="text-sm italic">Aucune colonne sélectionnée</p>
                                    </div>
                                ) : selectedFields.map((field, index) => (
                                    <div
                                        key={field.id}
                                        className="flex items-center gap-3 p-3 bg-white border border-blue-100 rounded-xl shadow-sm group animate-in slide-in-from-right-2 duration-200"
                                        style={{ animationDelay: `${index * 50}ms` }}
                                    >
                                        <div className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold">
                                            {index + 1}
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-bold text-slate-800 truncate">{field.label}</p>
                                            <p className="text-[10px] uppercase tracking-wider text-slate-400">{field.category}</p>
                                        </div>
                                        <button
                                            onClick={() => handleRemoveField(field.id)}
                                            className="p-1 hover:bg-red-50 text-slate-300 hover:text-red-500 rounded-lg transition-colors"
                                        >
                                            <XMarkIcon className="h-5 w-5" />
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>

                    {/* Preview Table */}
                    {reportData.length > 0 && (
                        <div className="glass-card overflow-hidden animate-slide-up">
                            {/* NEW: Homonym Detection Alert (Requirement 8.4) */}
                            {homonymDetected && (
                                <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-4">
                                    <div className="flex items-center">
                                        <ExclamationTriangleIcon className="h-5 w-5 text-amber-400 mr-2" />
                                        <div>
                                            <h4 className="text-sm font-medium text-amber-800">
                                                Homonymes détectés dans les résultats
                                            </h4>
                                            <p className="text-sm text-amber-700 mt-1">
                                                Plusieurs salariés portent le même nom. Les matricules permettent de les distinguer clairement.
                                                {!showMatriculeColumn && (
                                                    <span className="font-medium"> Activez l'affichage des matricules pour plus de clarté.</span>
                                                )}
                                            </p>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div className="bg-slate-800 p-4 flex justify-between items-center">
                                <h3 className="text-white font-bold flex items-center gap-2">
                                    <EyeIcon className="h-5 w-5 text-blue-400" />
                                    Aperçu de l'Etat de Paie
                                    {groupByMatricule && (
                                        <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded-full ml-2">
                                            Regroupé par matricule
                                        </span>
                                    )}
                                </h3>
                                <span className="text-slate-400 text-sm">{reportData.length} salariés • {selectedFields.length} rubriques</span>
                            </div>
                            
                            {/* Tableau avec groupement des colonnes par catégorie */}
                            <div className="overflow-x-auto max-h-[600px] overflow-y-auto custom-scrollbar">
                                <table className="w-full text-left border-collapse">
                                    <thead className="sticky top-0 z-20">
                                        {/* En-tête de groupement par catégorie */}
                                        <tr className="bg-gradient-to-r from-slate-700 to-slate-800">
                                            {/* Matricule column header if enabled */}
                                            {showMatriculeColumn && (
                                                <th className="p-3 text-center text-xs font-bold text-white uppercase tracking-wider border-r border-slate-600">
                                                    Matricule
                                                </th>
                                            )}
                                            {(() => {
                                                const categories = ['Identité', 'Base', 'Gains', 'Retenues', 'Charges Patronales', 'Résultats', 'Autres'];
                                                return categories.map(category => {
                                                    const fieldsInCategory = selectedFields.filter(f => f.category === category);
                                                    if (fieldsInCategory.length === 0) return null;
                                                    return (
                                                        <th 
                                                            key={category} 
                                                            colSpan={fieldsInCategory.length}
                                                            className="p-3 text-center text-xs font-bold text-white uppercase tracking-wider border-r border-slate-600 last:border-r-0"
                                                        >
                                                            {category}
                                                        </th>
                                                    );
                                                });
                                            })()}
                                        </tr>
                                        
                                        {/* En-tête des colonnes */}
                                        <tr className="bg-slate-100 border-b border-slate-200 shadow-sm">
                                            {/* Matricule column if enabled */}
                                            {showMatriculeColumn && (
                                                <th className="p-3 text-xs font-bold text-slate-600 uppercase tracking-wider min-w-[100px] border-r border-slate-200 text-center">
                                                    Matricule
                                                </th>
                                            )}
                                            {selectedFields.map(field => {
                                                const isMonetary = ['Gains', 'Retenues', 'Charges Patronales', 'Résultats'].includes(field.category);
                                                return (
                                                    <th key={field.id} className={`p-3 text-xs font-bold text-slate-600 uppercase tracking-wider min-w-[120px] border-r border-slate-200 last:border-r-0 ${isMonetary ? 'text-right' : 'text-left'}`}>
                                                        <div className="truncate" title={field.label}>
                                                            {field.label}
                                                        </div>
                                                    </th>
                                                );
                                            })}
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 bg-white">
                                        {reportData.map((row, i) => (
                                            <tr key={i} className="hover:bg-blue-50/30 transition-colors group">
                                                {/* Matricule column if enabled */}
                                                {showMatriculeColumn && (
                                                    <td className="p-3 text-sm border-r border-slate-100 text-center font-mono text-slate-700 bg-slate-50/50">
                                                        <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-bold">
                                                            {row.matricule || 'N/A'}
                                                        </span>
                                                    </td>
                                                )}
                                                {selectedFields.map((field) => {
                                                    const val = row[field.id];
                                                    const isNumeric = typeof val === 'number';
                                                    const isMonetary = ['Gains', 'Retenues', 'Charges Patronales', 'Résultats'].includes(field.category);
                                                    const isZero = isNumeric && val === 0;
                                                    
                                                    return (
                                                        <td 
                                                            key={field.id} 
                                                            className={`p-3 text-sm border-r border-slate-100 last:border-r-0 ${
                                                                isMonetary ? 'text-right font-mono' : 'text-left'
                                                            } ${
                                                                isZero ? 'text-slate-300' : 
                                                                isNumeric ? 'text-slate-700 font-medium' : 
                                                                'text-slate-600'
                                                            } ${
                                                                field.category === 'Résultats' ? 'bg-blue-50/50 font-bold' : ''
                                                            }`}
                                                        >
                                                            {isNumeric ? (
                                                                isZero ? '-' : val.toLocaleString('fr-FR', { 
                                                                    minimumFractionDigits: isMonetary ? 2 : 0,
                                                                    maximumFractionDigits: isMonetary ? 2 : 0
                                                                })
                                                            ) : (val || "-")}
                                                        </td>
                                                    );
                                                })}
                                            </tr>
                                        ))}
                                    </tbody>
                                    
                                    {/* Ligne de totaux si plus de 5 salariés */}
                                    {reportData.length > 5 && (
                                        <tfoot className="sticky bottom-0 z-10">
                                            <tr className="bg-gradient-to-r from-slate-700 to-slate-800 text-white font-bold">
                                                {/* Matricule column for totals */}
                                                {showMatriculeColumn && (
                                                    <td className="p-3 text-sm font-bold border-r border-slate-600 text-center">
                                                        -
                                                    </td>
                                                )}
                                                {selectedFields.map((field, fieldIndex) => {
                                                    const isNumeric = ['Gains', 'Retenues', 'Charges Patronales', 'Résultats'].includes(field.category);
                                                    
                                                    if (fieldIndex === 0) {
                                                        return (
                                                            <td key={field.id} className="p-3 text-sm font-bold border-r border-slate-600">
                                                                TOTAUX ({reportData.length} salariés)
                                                            </td>
                                                        );
                                                    }
                                                    
                                                    if (isNumeric) {
                                                        const total = reportData.reduce((sum, row) => {
                                                            const val = row[field.id];
                                                            return sum + (typeof val === 'number' ? val : 0);
                                                        }, 0);
                                                        
                                                        return (
                                                            <td key={field.id} className="p-3 text-sm font-bold text-right font-mono border-r border-slate-600 last:border-r-0">
                                                                {total.toLocaleString('fr-FR', { minimumFractionDigits: 2 })}
                                                            </td>
                                                        );
                                                    }
                                                    
                                                    return (
                                                        <td key={field.id} className="p-3 text-sm border-r border-slate-600 last:border-r-0">
                                                            -
                                                        </td>
                                                    );
                                                })}
                                            </tr>
                                        </tfoot>
                                    )}
                                </table>
                            </div>
                            
                            {/* Résumé statistique */}
                            <div className="bg-slate-50 p-4 border-t border-slate-200">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                                    <div className="bg-white p-3 rounded-lg shadow-sm">
                                        <div className="text-2xl font-bold text-blue-600">{reportData.length}</div>
                                        <div className="text-xs text-slate-500 uppercase tracking-wide">
                                            Salariés
                                            {showMatriculeColumn && (
                                                <div className="text-xs text-blue-600 mt-1">avec matricules</div>
                                            )}
                                        </div>
                                    </div>
                                    <div className="bg-white p-3 rounded-lg shadow-sm">
                                        <div className="text-2xl font-bold text-green-600">
                                            {reportData.reduce((sum, row) => sum + (row.brut_total || 0), 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                                        </div>
                                        <div className="text-xs text-slate-500 uppercase tracking-wide">Total Brut (Ar)</div>
                                    </div>
                                    <div className="bg-white p-3 rounded-lg shadow-sm">
                                        <div className="text-2xl font-bold text-purple-600">
                                            {reportData.reduce((sum, row) => sum + (row.net_a_payer || 0), 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                                        </div>
                                        <div className="text-xs text-slate-500 uppercase tracking-wide">Total Net (Ar)</div>
                                    </div>
                                    <div className="bg-white p-3 rounded-lg shadow-sm">
                                        <div className="text-2xl font-bold text-orange-600">
                                            {reportData.reduce((sum, row) => sum + (row.cout_total_employeur || 0), 0).toLocaleString('fr-FR', { maximumFractionDigits: 0 })}
                                        </div>
                                        <div className="text-xs text-slate-500 uppercase tracking-wide">Coût Total (Ar)</div>
                                    </div>
                                </div>
                                
                                {/* Additional info for matricule-based features */}
                                {(matriculeSearch || workerNameSearch || homonymDetected) && (
                                    <div className="mt-4 pt-4 border-t border-slate-200">
                                        <div className="flex flex-wrap gap-2 justify-center">
                                            {matriculeSearch && (
                                                <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                                                    Filtré par matricule: {matriculeSearch}
                                                </span>
                                            )}
                                            {workerNameSearch && (
                                                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                                                    Filtré par nom: {workerNameSearch}
                                                </span>
                                            )}
                                            {homonymDetected && (
                                                <span className="px-3 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-medium">
                                                    Homonymes détectés
                                                </span>
                                            )}
                                            {groupByMatricule && (
                                                <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-xs font-medium">
                                                    Regroupé par matricule
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
        </>
    );
}


