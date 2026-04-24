import { useEffect, useState } from "react";
import { Combobox } from "@headlessui/react";
import { ArrowsUpDownIcon, CheckIcon, MagnifyingGlassIcon } from "@heroicons/react/24/outline";

import { api } from "../api";
import { useTheme } from "../contexts/ThemeContext";
import { useWorkerData } from "../hooks/useConstants";

interface Worker {
  id: number;
  matricule: string;
  nom: string;
  prenom: string;
  poste?: string | null;
}

function WorkerSearchOption({
  worker,
  active,
  selected,
  theme,
}: {
  worker: Worker;
  active: boolean;
  selected: boolean;
  theme: "dark" | "light";
}) {
  const { data: workerData } = useWorkerData(worker.id);
  const displayName = `${workerData?.nom || worker.nom} ${workerData?.prenom || worker.prenom}`.trim();
  const matricule = workerData?.matricule || worker.matricule;
  const meta = [matricule ? `Matricule: ${matricule}` : null, workerData?.poste || worker.poste].filter(Boolean).join(" | ");

  return (
    <>
      <div className="flex flex-col">
        <span className={`block truncate ${selected ? "font-semibold text-blue-700" : "font-normal"}`}>{displayName}</span>
        <span className={`block truncate text-xs ${active ? "text-blue-500" : theme === "light" ? "text-gray-500" : "text-slate-400"}`}>
          {meta || "Vue maître indisponible"}
        </span>
      </div>
      {selected ? (
        <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-blue-600">
          <CheckIcon className="h-4 w-4" aria-hidden="true" />
        </span>
      ) : null}
    </>
  );
}

interface Props {
  onSelect: (workerId: number) => void;
  selectedId?: number | string;
  placeholder?: string;
  className?: string;
  employerId?: number;
}

export default function WorkerSearchSelect({
  onSelect,
  selectedId,
  placeholder = "Recherche par matricule, nom ou prénom",
  className = "",
  employerId,
}: Props) {
  const { theme } = useTheme();
  const [query, setQuery] = useState("");
  const [workers, setWorkers] = useState<Worker[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedWorker, setSelectedWorker] = useState<Worker | null>(null);
  const { data: selectedWorkerData } = useWorkerData(Number(selectedId) || 0);

  useEffect(() => {
    const fetchWorkers = async () => {
      setIsLoading(true);
      try {
        const params: Record<string, string | number> = { q: query };
        if (employerId) params.employer_id = employerId;
        const res = await api.get<Worker[]>("/workers", { params });
        setWorkers(res.data);
      } catch (error) {
        console.error("Erreur de recherche salariés:", error);
      } finally {
        setIsLoading(false);
      }
    };

    const timer = setTimeout(() => {
      void fetchWorkers();
    }, 300);
    return () => clearTimeout(timer);
  }, [employerId, query]);

  useEffect(() => {
    if (selectedId) {
      const found = workers.find((worker) => worker.id === Number(selectedId));
      if (found) {
        setSelectedWorker(found);
      } else if (!selectedWorker || selectedWorker.id !== Number(selectedId)) {
        void api.get<Worker>(`/workers/${selectedId}`).then((res) => setSelectedWorker(res.data)).catch(() => undefined);
      }
    } else {
      setSelectedWorker(null);
    }
  }, [selectedId, workers]);

  return (
    <div className={`relative w-full ${className}`}>
      <Combobox
        value={selectedWorker}
        onChange={(worker: Worker | null) => {
          if (!worker) return;
          setSelectedWorker(worker);
          onSelect(worker.id);
        }}
      >
        <div className="relative">
          <div
            className={`relative w-full cursor-default overflow-hidden rounded-xl text-left shadow-sm transition-all group focus-within:border-transparent focus-within:ring-2 focus-within:ring-blue-500 sm:text-sm ${
              theme === "light" ? "border border-gray-300 bg-white" : "border border-slate-700 bg-slate-900/90"
            }`}
          >
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <MagnifyingGlassIcon className={`h-4 w-4 transition-colors group-focus-within:text-blue-500 ${theme === "light" ? "text-gray-400" : "text-slate-400"}`} />
            </div>
            <Combobox.Input
              className={`w-full border-none bg-transparent py-2.5 pl-10 pr-10 text-sm leading-5 focus:ring-0 ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}
              displayValue={(worker: Worker) =>
                worker ? `${selectedWorkerData?.matricule || worker.matricule} - ${selectedWorkerData?.nom || worker.nom} ${selectedWorkerData?.prenom || worker.prenom}` : ""
              }
              onChange={(event) => setQuery(event.target.value)}
              placeholder={placeholder}
            />
            <Combobox.Button className="absolute inset-y-0 right-0 flex items-center pr-2">
              <ArrowsUpDownIcon className={`h-4 w-4 transition-colors ${theme === "light" ? "text-gray-400 hover:text-gray-600" : "text-slate-400 hover:text-slate-200"}`} />
            </Combobox.Button>
          </div>

          <Combobox.Options
            className={`absolute mt-2 max-h-60 w-full overflow-auto rounded-xl py-2 text-base shadow-xl focus:outline-none sm:text-sm z-[100] animate-in fade-in zoom-in duration-200 ${
              theme === "light" ? "bg-white ring-1 ring-black/5" : "bg-slate-900 ring-1 ring-slate-700"
            }`}
          >
            {workers.length === 0 && !isLoading ? (
              <div className={`relative cursor-default select-none py-3 px-4 text-center italic ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>
                Aucun résultat pour "{query}"
              </div>
            ) : (
              workers.map((worker) => (
                <Combobox.Option
                  key={worker.id}
                  value={worker}
                  className={({ active }) =>
                    `relative cursor-default select-none py-3 pl-10 pr-4 transition-colors ${
                      active ? "bg-blue-50 text-blue-700" : theme === "light" ? "text-gray-900" : "text-slate-100"
                    }`
                  }
                >
                  {({ selected, active }) => <WorkerSearchOption worker={worker} active={active} selected={selected} theme={theme} />}
                </Combobox.Option>
              ))
            )}

            {isLoading ? (
              <div className={`relative flex cursor-default select-none items-center justify-center gap-3 py-3 px-4 ${theme === "light" ? "text-gray-400" : "text-slate-400"}`}>
                <div className="h-3 w-3 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                <span className="text-xs">Recherche...</span>
              </div>
            ) : null}
          </Combobox.Options>
        </div>
      </Combobox>
    </div>
  );
}
