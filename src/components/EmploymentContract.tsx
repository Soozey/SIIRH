import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { usePrint } from '../hooks/usePrint';
import ConstantsPalette from './ConstantsPalette';
import { useAuth } from '../contexts/useAuth';
import { hasModulePermission } from '../rbac';
import { 
    useWorkerDefaultContract, 
} from '../hooks/useCustomContracts';
import { useWorkerData, useEmployerData, useSystemData } from '../hooks/useConstants';
import { useDocumentTemplates, useApplyTemplate, useCreateDocumentTemplate, useDeleteDocumentTemplate } from '../hooks/useDocumentTemplates';
import { formatAriary } from "../utils/ariary";

interface WorkerSummary {
    id: number;
    nom?: string | null;
    prenom?: string | null;
    matricule?: string | null;
    poste?: string | null;
    categorie_prof?: string | null;
    nature_contrat?: string | null;
    date_embauche?: string | null;
    date_naissance?: string | null;
    lieu_naissance?: string | null;
    cin?: string | null;
    cin_delivre_le?: string | null;
    cin_lieu?: string | null;
    adresse?: string | null;
    duree_essai_jours?: number | null;
    salaire_base?: number | null;
    horaire_hebdo?: number | null;
}

interface EmployerSummary {
    id: number;
    raison_sociale?: string | null;
    forme_juridique?: string | null;
    adresse?: string | null;
    ville?: string | null;
    pays?: string | null;
    nif?: string | null;
    stat?: string | null;
    representant?: string | null;
    logo_path?: string | null;
}

interface TemplateItem {
    id: number;
    name: string;
    description?: string | null;
    content?: string;
}

interface EmploymentContractProps {
    worker: WorkerSummary;
    employer: EmployerSummary;
    onClose?: () => void;
}

export default function EmploymentContract({ worker, employer }: EmploymentContractProps) {
    const { session } = useAuth();
    const componentRef = useRef<HTMLDivElement>(null);
    const [isPaletteOpen, setIsPaletteOpen] = useState(false);
    const [showTemplates, setShowTemplates] = useState(false);
    const [showDeleteTemplates, setShowDeleteTemplates] = useState(false);

    const [contractTitle, setContractTitle] = useState("CONTRAT DE TRAVAIL A DUREE INDETERMINEE");
    const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
    const canReadContracts = hasModulePermission(session, "contracts", "read");
    const canWriteContracts = hasModulePermission(session, "contracts", "write");

    // Hooks pour les contrats personnalisés (ancienne méthode)
    const { data: defaultContract } = useWorkerDefaultContract(worker?.id, 'employment_contract');

    // Hooks pour les templates globaux (nouvelle méthode)
    const { data: templates } = useDocumentTemplates(employer?.id, 'contract');
    const applyTemplate = useApplyTemplate();
    const createTemplate = useCreateDocumentTemplate();
    const deleteTemplate = useDeleteDocumentTemplate();

    // Hooks pour les données des constantes
    const { data: workerData } = useWorkerData(worker?.id || 0);
    const { data: employerData } = useEmployerData(employer?.id || 0);
    const { data: systemData } = useSystemData();
    const templateRows = templates ?? [];

    // Combiner toutes les données pour le remplacement des placeholders
    const allConstantsData = useMemo(() => ({
        ...(workerData || {}),
        ...(employerData || {}),
        ...(systemData || {})
    }), [workerData, employerData, systemData]);
    const displayWorker = {
        nom: workerData?.nom || worker?.nom || "",
        prenom: workerData?.prenom || worker?.prenom || "",
        matricule: workerData?.matricule || worker?.matricule || "",
        poste: workerData?.poste || worker?.poste || "",
        categorie_prof: workerData?.categorie_prof || worker?.categorie_prof || "",
        nature_contrat: workerData?.nature_contrat || worker?.nature_contrat || "",
        date_embauche: workerData?.date_embauche || worker?.date_embauche || "",
    };
    const handlePrint = usePrint(`Contrat_Travail_${displayWorker.nom}_${displayWorker.prenom}`);

    const today = new Date().toLocaleDateString('fr-FR', {
        day: 'numeric',
        month: 'long',
        year: 'numeric'
    });

    // Fonction pour remplacer les placeholders par les vraies valeurs
    const replacePlaceholders = useCallback((content: string) => {
        if (!allConstantsData) return content;
        
        let replacedContent = content;
        
        // Remplacer tous les placeholders {{key}} par les vraies valeurs
        // Gérer les clés avec points (worker.nom) et sans points (nom)
        Object.entries(allConstantsData).forEach(([key, value]) => {
            // Remplacer les placeholders avec la clé simple
            const simpleKeyPlaceholder = `{{${key}}}`;
            const simpleKeyRegex = new RegExp(simpleKeyPlaceholder.replace(/[{}]/g, '\\$&'), 'g');
            replacedContent = replacedContent.replace(simpleKeyRegex, String(value || ''));
            
            // Remplacer aussi les placeholders avec préfixes (worker.nom, employer.raison_sociale, etc.)
            const prefixes = ['worker', 'employer', 'system', 'payroll'];
            prefixes.forEach(prefix => {
                const prefixedPlaceholder = `{{${prefix}.${key}}}`;
                const prefixedRegex = new RegExp(prefixedPlaceholder.replace(/[{}]/g, '\\$&'), 'g');
                replacedContent = replacedContent.replace(prefixedRegex, String(value || ''));
            });
        });
        
        return replacedContent;
    }, [allConstantsData]);

    // Charger le contrat par défaut au montage du composant
    useEffect(() => {
        if (defaultContract && componentRef.current && allConstantsData && !hasUnsavedChanges) {
            // Ne charger que si pas de modifications en cours
            const contentWithValues = replacePlaceholders(defaultContract.content);
            componentRef.current.innerHTML = contentWithValues;
        }
    }, [defaultContract, allConstantsData, hasUnsavedChanges, replacePlaceholders]);

    // Détecter les modifications
    const handleContentChange = () => {
        if (!canWriteContracts) return;
        setHasUnsavedChanges(true);
    };

    // Fonction pour convertir le contenu avec valeurs réelles en placeholders pour la sauvegarde
    const convertToPlaceholders = (content: string) => {
        if (!componentRef.current) return content;
        
        // Cloner le contenu pour ne pas modifier l'original
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = content;
        
        // Remplacer tous les spans de constantes par leurs placeholders
        const constantSpans = tempDiv.querySelectorAll('.inserted-constant[data-placeholder]');
        constantSpans.forEach(span => {
            const placeholder = span.getAttribute('data-placeholder');
            if (placeholder) {
                const textNode = document.createTextNode(placeholder);
                span.parentNode?.replaceChild(textNode, span);
            }
        });
        
        return tempDiv.innerHTML;
    };

    // Appliquer un template global à ce travailleur
    const handleApplyTemplate = async (template: TemplateItem) => {
        if (!worker || !componentRef.current || !canReadContracts) return;

        try {
            const result = await applyTemplate.mutateAsync({
                templateId: template.id,
                workerId: worker.id
            });

            // Appliquer le contenu avec les valeurs déjà remplacées
            componentRef.current.innerHTML = result.content;
            setContractTitle(template.name);
            setHasUnsavedChanges(true); // Marquer comme modifié pour permettre la sauvegarde
            setShowTemplates(false);
            
        } catch (error) {
            console.error('Erreur lors de l\'application du template:', error);
            alert('Erreur lors de l\'application du template: ' + (error as Error).message);
        }
    };

    // Sauvegarder le contrat actuel comme template global
    const handleSaveAsTemplate = async () => {
        if (!componentRef.current || !employer || !canWriteContracts) return;

        const templateName = prompt('Nom du template (ex: "Contrat CDI Standard"):', contractTitle);
        if (!templateName) return;

        const rawContent = componentRef.current.innerHTML;
        const contentWithPlaceholders = convertToPlaceholders(rawContent);

        const templateData = {
            employer_id: employer.id,
            name: templateName,
            description: `Template créé à partir du contrat de ${displayWorker.prenom} ${displayWorker.nom}`,
            template_type: 'contract',
            content: contentWithPlaceholders,
            is_active: true
        };

        try {
            await createTemplate.mutateAsync(templateData);
            alert(`Template "${templateName}" sauvegardé avec succès ! Il sera disponible pour tous les salariés.`);
            
        } catch (error) {
            console.error('Erreur lors de la sauvegarde du template:', error);
            alert('Erreur lors de la sauvegarde du template');
        }
    };

    // Fonction pour insérer une constante dans le texte éditable
    const handleInsertConstant = (constantKey: string, placeholder: string) => {
        if (!canWriteContracts) return;
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            
            // Vérifier si la sélection est dans le contenu éditable
            const editableContent = componentRef.current;
            if (editableContent && editableContent.contains(range.commonAncestorContainer)) {
                // Supprimer le contenu sélectionné s'il y en a
                range.deleteContents();
                
                // Extraire la vraie clé (après le point si présent)
                const realKey = constantKey.includes('.') ? constantKey.split('.', 2)[1] : constantKey;
                
                // Obtenir la vraie valeur pour l'affichage
                const realValue = allConstantsData?.[realKey] || placeholder;
                
                // Créer un élément span pour la constante
                const constantSpan = document.createElement('span');
                constantSpan.className = 'inserted-constant bg-blue-100 px-1 rounded border border-blue-300';
                constantSpan.textContent = String(realValue);
                constantSpan.title = `Constante: ${constantKey} = ${realValue}`;
                constantSpan.setAttribute('data-placeholder', placeholder);
                constantSpan.setAttribute('data-key', constantKey);
                
                // Insérer l'élément
                range.insertNode(constantSpan);
                
                // Déplacer le curseur après l'insertion
                range.setStartAfter(constantSpan);
                range.setEndAfter(constantSpan);
                selection.removeAllRanges();
                selection.addRange(range);
                
                // Marquer comme modifié
                handleContentChange();
            }
        } else {
            // Si pas de sélection, afficher un message
            alert('Veuillez d\'abord cliquer dans le texte où vous voulez insérer la constante');
        }
    };

    // Gérer le drop dans le contenu éditable
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (!canWriteContracts) return;
        
        try {
            const data = e.dataTransfer.getData('application/json');
            if (data) {
                const constantData = JSON.parse(data);
                
                // Créer une sélection à l'endroit du drop
                const range = document.caretRangeFromPoint(e.clientX, e.clientY);
                if (range) {
                    const selection = window.getSelection();
                    if (selection) {
                        selection.removeAllRanges();
                        selection.addRange(range);
                        handleInsertConstant(constantData.key, constantData.value);
                    }
                }
            }
        } catch (error: unknown) {
            console.error('Erreur lors du drop:', error);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    return (
        <div className="flex flex-col h-full bg-white rounded-lg shadow-sm">
            {/* Toolbar */}
            <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg print:hidden">
                <div>
                    <h2 className="text-lg font-semibold text-gray-800">Modèle de Contrat</h2>
                    <p className="text-sm text-gray-500">
                        {hasUnsavedChanges && <span className="text-orange-600 font-medium">Modifications non sauvegardées</span>}
                    </p>
                </div>
                <div className="flex gap-2">
                    {canWriteContracts && <button
                        onClick={() => setIsPaletteOpen(!isPaletteOpen)}
                        className={`flex items-center justify-center px-3 py-2 h-9 text-xs font-medium rounded-md transition-colors min-w-[100px] ${
                            isPaletteOpen 
                                ? 'text-white bg-blue-600 hover:bg-blue-700' 
                                : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                    >
                        {isPaletteOpen ? 'Fermer' : 'Palette'}
                    </button>}

                    {canWriteContracts && <button
                        onClick={handleSaveAsTemplate}
                        disabled={createTemplate.isPending}
                        className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-white bg-purple-600 rounded-md hover:bg-purple-700 disabled:opacity-50 min-w-[100px]"
                    >
                        {createTemplate.isPending ? 'Création...' : 'Créer'}
                    </button>}

                    {canWriteContracts && <div className="relative">
                        <button
                            onClick={() => setShowDeleteTemplates(!showDeleteTemplates)}
                            className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-white bg-red-600 rounded-md hover:bg-red-700 min-w-[100px]"
                        >
                            Supprimer
                        </button>
                        
                        {showDeleteTemplates && templateRows.length > 0 && (
                            <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                                <div className="p-2">
                                    <div className="text-xs font-medium text-gray-500 mb-2">Cliquez sur un template pour le supprimer</div>
                                    {templateRows.map((template) => (
                                        <button
                                            key={template.id}
                                            onClick={async () => {
                                                if (window.confirm(`Êtes-vous sûr de vouloir supprimer le template "${template.name}" ?`)) {
                                                    try {
                                                        await deleteTemplate.mutateAsync(template.id);
                                                        setShowDeleteTemplates(false);
                                                        alert('Template supprimé avec succès !');
                                                    } catch (error) {
                                                        console.error('Erreur suppression template:', error);
                                                        alert('Erreur lors de la suppression du template');
                                                    }
                                                }
                                            }}
                                            disabled={deleteTemplate.isPending}
                                            className="w-full text-left p-3 text-sm hover:bg-red-50 rounded border-b border-gray-100 last:border-b-0 disabled:opacity-50 group"
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1">
                                                    <div className="font-medium text-gray-900 group-hover:text-red-700">{template.name}</div>
                                                    {template.description && (
                                                        <div className="text-xs text-gray-500 mt-1">{template.description}</div>
                                                    )}
                                                </div>
                                                <div className="text-red-600 group-hover:text-red-700">
                                                    🗑️
                                                </div>
                                            </div>
                                            <div className="text-xs text-red-600 mt-1 group-hover:text-red-700">
                                                🗑️ Cliquez pour supprimer
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {showDeleteTemplates && templateRows.length === 0 && (
                            <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                                <div className="p-4 text-center text-gray-500">
                                    <div className="text-sm">Aucun template à supprimer</div>
                                    <div className="text-xs mt-1">Créez d'abord des templates</div>
                                </div>
                            </div>
                        )}
                    </div>}

                    {canWriteContracts && <button
                        onClick={() => {
                            if (componentRef.current) {
                                componentRef.current.innerHTML = `
                                    <div style="font-family: Arial; padding: 20px;">
                                        <h1 style="text-align: center;">NOUVEAU CONTRAT DE TRAVAIL</h1>
                                        <p>Cliquez ici pour commencer à éditer votre contrat...</p>
                                        <p>Utilisez la palette de constantes pour insérer des données dynamiques.</p>
                                    </div>
                                `;
                                setContractTitle("NOUVEAU CONTRAT");
                                setHasUnsavedChanges(true);
                            }
                        }}
                        className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-white bg-green-600 rounded-md hover:bg-green-700 min-w-[100px]"
                    >
                        Nouveau
                    </button>}

                    {canWriteContracts && <button
                        onClick={() => {
                            if (componentRef.current) {
                                componentRef.current.setAttribute('contenteditable', 'true');
                                componentRef.current.focus();
                            }
                        }}
                        className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-gray-700 bg-gray-200 rounded-md hover:bg-gray-300 min-w-[100px]"
                    >
                        Édition
                    </button>}

                    {canReadContracts && <div className="relative">
                        <button
                            onClick={() => setShowTemplates(!showTemplates)}
                            className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-white bg-indigo-600 rounded-md hover:bg-indigo-700 min-w-[100px]"
                        >
                            Templates
                        </button>
                        
                        {showTemplates && templateRows.length > 0 && (
                            <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                                <div className="p-2">
                                    <div className="text-xs font-medium text-gray-500 mb-2">Templates disponibles pour tous les salariés</div>
                                    {templateRows.map((template) => (
                                        <button
                                            key={template.id}
                                            onClick={() => handleApplyTemplate(template)}
                                            disabled={applyTemplate.isPending}
                                            className="w-full text-left p-3 text-sm hover:bg-gray-50 rounded border-b border-gray-100 last:border-b-0 disabled:opacity-50"
                                        >
                                            <div className="font-medium text-gray-900">{template.name}</div>
                                            {template.description && (
                                                <div className="text-xs text-gray-500 mt-1">{template.description}</div>
                                            )}
                                            <div className="text-xs text-indigo-600 mt-1">
                                                📄 Template global • Cliquez pour appliquer
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                        
                        {showTemplates && templateRows.length === 0 && (
                            <div className="absolute right-0 top-full mt-1 w-80 bg-white border border-gray-200 rounded-md shadow-lg z-10">
                                <div className="p-4 text-center text-gray-500">
                                    <div className="text-sm">Aucun template global disponible</div>
                                    <div className="text-xs mt-1">Créez un template en cliquant sur "Créer Template"</div>
                                </div>
                            </div>
                        )}
                    </div>}

                    <button
                        onClick={handlePrint}
                        className="flex items-center justify-center px-3 py-2 h-9 text-xs font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 min-w-[100px]"
                    >
                        Imprimer
                    </button>
                </div>
            </div>

            {/* Editable Content */}
            <div className="flex-1 overflow-auto p-8 bg-gray-100">
                <div
                    ref={componentRef}
                    className="printable-content mx-auto bg-white p-[20mm] shadow-lg w-[210mm] min-h-0 text-justify text-black font-sans leading-relaxed text-[11pt]"
                    contentEditable={canWriteContracts}
                    suppressContentEditableWarning
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onInput={handleContentChange}
                    style={{ fontFamily: 'Arial, Helvetica, sans-serif', outline: 'none' }}
                >
                    <style>{`
                        .inserted-constant {
                            background-color: #dbeafe !important;
                            border: 1px solid #93c5fd !important;
                            border-radius: 4px !important;
                            padding: 2px 4px !important;
                            font-weight: 500 !important;
                            color: #1e40af !important;
                            cursor: help !important;
                        }
                        .inserted-constant:hover {
                            background-color: #bfdbfe !important;
                            border-color: #60a5fa !important;
                        }
                    `}</style>
                    {/* Header Employer & Logo */}
                    <div className="mb-8 border-b-2 border-gray-800 pb-4 grid grid-cols-[1fr_auto] gap-4 items-start print:grid print:grid-cols-[1fr_150px] print:gap-8">
                        <div>
                            <h1 className="text-xl font-bold uppercase tracking-wide mb-2">{employer?.raison_sociale || "...................."}</h1>
                            <div className="text-xs text-gray-700 space-y-1">
                                <p>{employer?.adresse || "Adresse non renseignée"}</p>
                                <p>{employer?.ville} {employer?.pays}</p>
                                <p>NIF: {employer?.nif || "N/A"} - STAT: {employer?.stat || "N/A"}</p>
                            </div>
                        </div>
                        {employer?.logo_path && (
                            <div className="w-32 h-20 flex items-center justify-end relative z-0 print:w-full print:h-auto">
                                <img
                                    src={`${import.meta.env.VITE_API_URL || 'http://127.0.0.1:8001'}${employer.logo_path}`}
                                    alt="Logo"
                                    className="max-w-full max-h-full object-contain"
                                />
                            </div>
                        )}
                    </div>

                    {/* Title */}
                    <div className="text-center mb-10 relative z-10">
                        <div className="inline-block border-b-2 border-black pb-1 w-full max-w-4xl">
                            <div
                                className="text-center font-bold uppercase bg-transparent border-none text-xl tracking-wider w-full p-2 outline-none"
                                style={{ fontFamily: 'inherit', wordWrap: 'break-word', whiteSpace: 'pre-wrap' }}
                                contentEditable={canWriteContracts}
                                suppressContentEditableWarning
                                onInput={(e) => {
                                    setContractTitle(e.currentTarget.textContent || "");
                                    handleContentChange();
                                }}
                            >
                                {contractTitle}
                            </div>
                        </div>
                    </div>

                    {/* Parties */}
                    <div className="mb-6 space-y-4">
                        <p><strong>ENTRE LES SOUSSIGNES :</strong></p>

                        <p>
                            La Société <strong>{employer.raison_sociale}</strong>, {employer.forme_juridique || ""}, sise au {employer.adresse || "ADRESSE A COMPLETER"}, <br />
                            Immatriculée au NIF sous le numéro {employer.nif || "NIF A COMPLETER"} et au STAT sous le numéro {employer.stat || "STAT A COMPLETER"}, <br />
                            Représentée par <strong>{employer.representant || "[NOM REPRESENTANT]"}</strong>, en qualité de [TITRE],
                        </p>
                        <p className="text-right italic">Ci-après désignée « L'EMPLOYEUR », <br /> D'une part,</p>

                        <p><strong>ET :</strong></p>
                        <p>
                            <strong>M./Mme {displayWorker.nom} {displayWorker.prenom}</strong>, <br />
                            Né(e) le {worker.date_naissance ? new Date(worker.date_naissance).toLocaleDateString('fr-FR') : "..."} à {worker.lieu_naissance || "..."} <br />
                            Titulaire de la CIN n° {worker.cin || "..."} délivrée le {worker.cin_delivre_le ? new Date(worker.cin_delivre_le).toLocaleDateString('fr-FR') : "..."} à {worker.cin_lieu || "..."} <br />
                            Demeurant à {worker.adresse || "..."}.
                        </p>
                        <p className="text-right italic">Ci-après désigné(e) « LE SALARIE », <br /> D'autre part.</p>
                    </div>

                    <div className="mb-8 mt-8 border-b border-gray-300 pb-2">
                        <p className="font-bold">IL A ETE CONVENU ET ARRETE CE QUI SUIT :</p>
                    </div>

                    {/* Articles */}
                    <div className="space-y-6">
                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 1 : ENGAGEMENT</h3>
                            <p>
                                L'Employeur engage le Salarié à compter du <strong>{worker.date_embauche ? new Date(worker.date_embauche).toLocaleDateString('fr-FR') : "..."}</strong>, sous réserve des résultats de la visite médicale d'embauche.
                                Le présent engagement est conclu pour une durée <strong>{displayWorker.nature_contrat === 'CDD' ? 'déterminée' : 'indéterminée'}</strong>.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 2 : FONCTIONS ET ATTRIBUTIONS</h3>
                            <p>
                                Le Salarié est engagé en qualité de <strong>{displayWorker.poste || "..."}</strong>. <br />
                                Il exercera ses fonctions sous l'autorité et le contrôle de la Direction ou de toute personne désignée par celle-ci.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 3 : PERIODE D'ESSAI</h3>
                            <p>
                                Le présent contrat ne deviendra définitif qu'à l'issue d'une période d'essai de <strong>{worker.duree_essai_jours || "..."} jours</strong> de travail effectif.
                                Au cours de cette période, chacune des parties pourra rompre le contrat à tout moment, sans préavis ni indemnité.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 4 : REMUNERATION</h3>
                            <p>
        En contrepartie de ses services, le Salarié percevra un salaire mensuel de base brut de <strong>{worker.salaire_base ? formatAriary(worker.salaire_base) : "..."}</strong> pour un horaire hebdomadaire de {worker.horaire_hebdo || 40} heures.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 5 : LIEU DE TRAVAIL</h3>
                            <p>
                                Le Salarié exercera ses fonctions principalement à <strong>{employer.ville || "..."}</strong>. Toutefois, il pourra être amené à se déplacer en fonction des nécessités de service.
                            </p>
                        </div>

                        <div>
                            <h3 className="font-bold underline mb-2">ARTICLE 6 : CONGES PAYES</h3>
                            <p>
                                Le Salarié bénéficiera des congés payés conformément aux dispositions légales en vigueur et aux usages de l'entreprise (2.5 jours ouvrables par mois de travail effectif).
                            </p>
                        </div>
                    </div>

                    {/* Signatures */}
                    <div className="mt-12 avoid-break" style={{ pageBreakInside: 'avoid', breakInside: 'avoid' }}>
                        <p className="mb-6">Fait à {employer.ville || "........................"}, le {today}, en deux exemplaires originaux.</p>

                        <div className="flex justify-between items-start">
                            <div className="w-1/2">
                                <p className="font-bold mb-12">L'EMPLOYEUR</p>
                                <div className="border-t border-gray-400 w-32 pt-1">
                                    <p className="text-[10px] italic text-gray-500">(Signature et cachet)</p>
                                </div>
                            </div>
                            <div className="w-1/2 text-right flex flex-col items-end">
                                <p className="font-bold mb-12">LE SALARIE</p>
                                <div className="border-t border-gray-400 w-32 pt-1">
                                    <p className="text-[10px] italic text-gray-500">(Signature précédée de "Lu et approuvé")</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            {/* Palette de constantes */}
            <ConstantsPalette
                workerId={worker?.id}
                employerId={employer?.id}
                isOpen={canWriteContracts && isPaletteOpen}
                onClose={() => setIsPaletteOpen(false)}
                onInsertConstant={handleInsertConstant}
            />
        </div>
    );
}
