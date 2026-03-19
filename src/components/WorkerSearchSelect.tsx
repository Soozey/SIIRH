import { useState, useEffect } from 'react';
import { Combobox } from '@headlessui/react';
import {
    CheckIcon,
    ArrowsUpDownIcon,
    MagnifyingGlassIcon
} from '@heroicons/react/24/outline';
import { api } from '../api';

interface Worker {
    id: number;
    matricule: string;
    nom: string;
    prenom: string;
}

interface Props {
    onSelect: (workerId: number) => void;
    selectedId?: number | string;
    placeholder?: string;
    className?: string;
    employerId?: number; // Optional: filter by employer if provided
}

export default function WorkerSearchSelect({
    onSelect,
    selectedId,
    placeholder = "Recherche par matr nom prénom",
    className = "",
    employerId
}: Props) {
    const [query, setQuery] = useState('');
    const [workers, setWorkers] = useState<Worker[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null);

    // Fetch workers based on query
    useEffect(() => {
        const fetchWorkers = async () => {
            setIsLoading(true);
            try {
                const params: any = { q: query };
                if (employerId) params.employer_id = employerId;
                const res = await api.get('/workers', { params });
                setWorkers(res.data);
            } catch (error) {
                console.error("Error fetching workers for select:", error);
            } finally {
                setIsLoading(false);
            }
        };

        const timer = setTimeout(() => {
            fetchWorkers();
        }, 300);

        return () => clearTimeout(timer);
    }, [query, employerId]);

    // Sync selectedWorker with selectedId
    useEffect(() => {
        if (selectedId) {
            // First check in current list
            const found = workers.find(w => w.id === Number(selectedId));
            if (found) {
                setSelectedWorker(found);
            } else if (!selectedWorker || selectedWorker.id !== Number(selectedId)) {
                // Fetch single worker if not found or mismatch
                api.get(`/workers/${selectedId}`).then(res => setSelectedWorker(res.data)).catch(() => { });
            }
        } else {
            setSelectedWorker(null);
        }
    }, [selectedId, workers]);

    return (
        <div className={`relative w-full ${className}`}>
            <Combobox value={selectedWorker} onChange={(w: Worker | null) => {
                if (w) {
                    setSelectedWorker(w);
                    onSelect(w.id);
                }
            }}>
                <div className="relative">
                    <div className="relative w-full cursor-default overflow-hidden rounded-xl bg-white text-left border border-gray-300 focus:outline-none focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-transparent sm:text-sm transition-all shadow-sm group">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                            <MagnifyingGlassIcon className="h-4 w-4 text-gray-400 group-focus-within:text-blue-500 transition-colors" aria-hidden="true" />
                        </div>
                        <Combobox.Input
                            className="w-full border-none py-2.5 pl-10 pr-10 text-sm leading-5 text-gray-900 focus:ring-0 bg-transparent"
                            displayValue={(worker: Worker) => worker ? `${worker.matricule} - ${worker.nom} ${worker.prenom}` : ''}
                            onChange={(event) => setQuery(event.target.value)}
                            placeholder={placeholder}
                        />
                        <Combobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
                            <ArrowsUpDownIcon className="h-4 w-4 text-gray-400 hover:text-gray-600 transition-colors" aria-hidden="true" />
                        </Combobox.Button>
                    </div>
                    <Combobox.Options className="absolute mt-2 max-h-60 w-full overflow-auto rounded-xl bg-white py-2 text-base shadow-xl ring-1 ring-black/5 focus:outline-none sm:text-sm z-[100] animate-in fade-in zoom-in duration-200">
                        {workers.length === 0 && !isLoading ? (
                            <div className="relative cursor-default select-none py-3 px-4 text-gray-500 italic text-center">
                                Aucun résultat pour "{query}"
                            </div>
                        ) : (
                            workers.map((worker) => (
                                <Combobox.Option
                                    key={worker.id}
                                    className={({ active }) =>
                                        `relative cursor-default select-none py-3 pl-10 pr-4 transition-colors ${active ? 'bg-blue-50 text-blue-700' : 'text-gray-900'
                                        }`
                                    }
                                    value={worker}
                                >
                                    {({ selected, active }) => (
                                        <>
                                            <div className="flex flex-col">
                                                <span className={`block truncate ${selected ? 'font-semibold text-blue-700' : 'font-normal'}`}>
                                                    {worker.nom} {worker.prenom}
                                                </span>
                                                <span className={`block truncate text-xs ${active ? 'text-blue-500' : 'text-gray-500'}`}>
                                                    Matricule: {worker.matricule}
                                                </span>
                                            </div>
                                            {selected ? (
                                                <span
                                                    className={`absolute inset-y-0 left-0 flex items-center pl-3 ${active ? 'text-blue-600' : 'text-blue-600'
                                                        }`}
                                                >
                                                    <CheckIcon className="h-4 w-4" aria-hidden="true" />
                                                </span>
                                            ) : null}
                                        </>
                                    )}
                                </Combobox.Option>
                            ))
                        )}
                        {isLoading && (
                            <div className="relative cursor-default select-none py-3 px-4 text-gray-400 flex items-center justify-center gap-3">
                                <div className="animate-spin h-3 w-3 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                                <span className="text-xs">Recherche...</span>
                            </div>
                        )}
                    </Combobox.Options>
                </div>
            </Combobox>
        </div>
    );
}
