import { useCallback, useEffect, useMemo, useState } from "react";
import { Dialog } from "@headlessui/react";
import { ChevronLeftIcon, ChevronRightIcon, XMarkIcon } from "@heroicons/react/24/outline";
import dayjs from "dayjs";
import "dayjs/locale/fr";

import {
  getCalendar,
  getCalendarAgenda,
  toggleCalendarDay,
  type CalendarAgendaItem,
  type CalendarDay,
  type CalendarDayStatus,
} from "../api";
import { useTheme } from "../contexts/useTheme";

dayjs.locale("fr");

interface WorkCalendarProps {
  isOpen: boolean;
  onClose: () => void;
  employerId: number;
  initialPeriod: string;
  title?: string;
  workerId?: number | null;
  editable?: boolean;
  showAgenda?: boolean;
}

const STATUS_OPTIONS: Array<{
  value: CalendarDayStatus;
  label: string;
  shortLabel: string;
  buttonClass: string;
  cellClass: string;
}> = [
  {
    value: "worked",
    label: "Travaillé",
    shortLabel: "Travaillé",
    buttonClass: "border-green-200 bg-green-50 text-green-800 hover:bg-green-100",
    cellClass: "bg-green-100 border-green-300 text-green-800 hover:bg-green-200",
  },
  {
    value: "off",
    label: "Repos",
    shortLabel: "Repos",
    buttonClass: "border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100",
    cellClass: "bg-slate-100 border-slate-300 text-slate-600 hover:bg-slate-200",
  },
  {
    value: "holiday",
    label: "Jour férié",
    shortLabel: "Férié",
    buttonClass: "border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100",
    cellClass: "bg-amber-100 border-amber-300 text-amber-800 hover:bg-amber-200",
  },
  {
    value: "closed",
    label: "Fermé",
    shortLabel: "Fermé",
    buttonClass: "border-rose-200 bg-rose-50 text-rose-800 hover:bg-rose-100",
    cellClass: "bg-rose-100 border-rose-300 text-rose-800 hover:bg-rose-200",
  },
];

const DEFAULT_STATUS_BY_WEEKDAY: Record<number, CalendarDayStatus> = {
  0: "off",
  1: "worked",
  2: "worked",
  3: "worked",
  4: "worked",
  5: "worked",
  6: "off",
};

const CATEGORY_CLASSES: Record<CalendarAgendaItem["category"], string> = {
  leave: "border-cyan-200 bg-cyan-50 text-cyan-900",
  planning: "border-violet-200 bg-violet-50 text-violet-900",
  absence: "border-amber-200 bg-amber-50 text-amber-900",
  event: "border-slate-200 bg-slate-50 text-slate-800",
};

export default function WorkCalendar({
  isOpen,
  onClose,
  employerId,
  initialPeriod,
  title,
  workerId,
  editable = true,
  showAgenda = false,
}: WorkCalendarProps) {
  const { theme } = useTheme();
  const [currentDate, setCurrentDate] = useState(dayjs());
  const [daysData, setDaysData] = useState<CalendarDay[]>([]);
  const [agenda, setAgenda] = useState<CalendarAgendaItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<CalendarDayStatus>("worked");

  useEffect(() => {
    if (!isOpen || !initialPeriod) return;
    const parsed = dayjs(`${initialPeriod}-01`);
    if (parsed.isValid()) {
      setCurrentDate(parsed);
    }
  }, [initialPeriod, isOpen]);

  const fetchCalendar = useCallback(async () => {
    setLoading(true);
    try {
      const year = currentDate.year();
      const month = currentDate.month() + 1;
      const [calendarData, agendaData] = await Promise.all([
        getCalendar(employerId, year, month),
        showAgenda ? getCalendarAgenda(employerId, year, month, workerId) : Promise.resolve([] as CalendarAgendaItem[]),
      ]);
      setDaysData(calendarData);
      setAgenda(agendaData);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [currentDate, employerId, showAgenda, workerId]);

  useEffect(() => {
    if (!isOpen) return;
    void fetchCalendar();
  }, [fetchCalendar, isOpen]);

  const resolveDefaultStatus = (value: dayjs.Dayjs): CalendarDayStatus => DEFAULT_STATUS_BY_WEEKDAY[value.day()] ?? "off";

  const handleApplyStatus = async (day: CalendarDay) => {
    if (!editable) return;
    try {
      const newStatus = selectedStatus;
      setDaysData((prev) =>
        prev.map((item) =>
          item.date === day.date
            ? { ...item, status: newStatus, is_worked: newStatus === "worked", is_override: true }
            : item,
        ),
      );
      await toggleCalendarDay(employerId, day.date, newStatus);
      if (showAgenda) {
        void fetchCalendar();
      }
    } catch (error) {
      console.error("Erreur de mise à jour du calendrier", error);
      void fetchCalendar();
    }
  };

  const startOfMonth = currentDate.startOf("month");
  const endOfMonth = currentDate.endOf("month");
  const daysInMonth = endOfMonth.date();
  const offset = (startOfMonth.day() + 6) % 7;
  const blanks = Array(offset).fill(null);
  const daysArray = Array.from({ length: daysInMonth }, (_, index) => startOfMonth.date(index + 1));

  const dataMap = useMemo(() => {
    const map = new Map<string, CalendarDay>();
    daysData.forEach((entry) => map.set(entry.date, entry));
    return map;
  }, [daysData]);

  const agendaByDay = useMemo(() => {
    const map = new Map<string, CalendarAgendaItem[]>();
    agenda.forEach((item) => {
      const start = dayjs(item.date);
      const end = dayjs(item.end_date || item.date);
      let current = start;
      while (current.isSame(end, "day") || current.isBefore(end, "day")) {
        const key = current.format("YYYY-MM-DD");
        const bucket = map.get(key) ?? [];
        bucket.push(item);
        map.set(key, bucket);
        current = current.add(1, "day");
      }
    });
    return map;
  }, [agenda]);

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/40" aria-hidden="true" />
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className={`mx-auto flex max-h-[92vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl shadow-2xl ${theme === "light" ? "bg-white" : "border border-slate-700 bg-slate-900 text-slate-100"}`}>
          <div className={`flex items-center justify-between border-b p-4 ${theme === "light" ? "border-gray-200 bg-gray-50" : "border-slate-700 bg-slate-800"}`}>
            <Dialog.Title className={`text-lg font-bold ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}>
              {title || "Calendrier centralisé"} - {currentDate.format("MMMM YYYY")}
            </Dialog.Title>
            <button onClick={onClose} className={theme === "light" ? "text-gray-400 hover:text-gray-600" : "text-slate-400 hover:text-slate-200"}>
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>

          <div className="overflow-y-auto p-6">
            <div className="mb-6 flex items-center justify-between">
              <button onClick={() => setCurrentDate((value) => value.subtract(1, "month"))} className={`rounded border p-2 ${theme === "light" ? "border-gray-300 hover:bg-gray-100" : "border-slate-600 hover:bg-slate-800"}`}>
                <ChevronLeftIcon className="h-5 w-5" />
              </button>
              <span className={`text-lg font-semibold capitalize ${theme === "light" ? "text-gray-900" : "text-slate-100"}`}>{currentDate.format("MMMM YYYY")}</span>
              <button onClick={() => setCurrentDate((value) => value.add(1, "month"))} className={`rounded border p-2 ${theme === "light" ? "border-gray-300 hover:bg-gray-100" : "border-slate-600 hover:bg-slate-800"}`}>
                <ChevronRightIcon className="h-5 w-5" />
              </button>
            </div>

            {editable ? (
              <div className={`mb-6 rounded-xl border p-4 ${theme === "light" ? "border-slate-200 bg-slate-50" : "border-slate-700 bg-slate-800"}`}>
                <p className={`mb-3 text-sm font-semibold ${theme === "light" ? "text-slate-700" : "text-slate-200"}`}>Type à appliquer au clic</p>
                <div className="flex flex-wrap gap-3">
                  {STATUS_OPTIONS.map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedStatus(option.value)}
                      className={`rounded-lg border px-4 py-2 text-sm font-semibold transition ${
                        selectedStatus === option.value ? "ring-2 ring-blue-500 ring-offset-1" : ""
                      } ${option.buttonClass}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <p className={`mt-3 text-xs ${theme === "light" ? "text-slate-500" : "text-slate-400"}`}>
                  `Travaillé` alimente `DAYSWORK`. `Repos`, `Jour férié` et `Fermé` sont exclus du calcul standard.
                </p>
              </div>
            ) : null}

            <div className={`grid grid-cols-7 gap-2 text-center text-sm font-bold ${theme === "light" ? "text-gray-500" : "text-slate-400"}`}>
              <div>Lun</div>
              <div>Mar</div>
              <div>Mer</div>
              <div>Jeu</div>
              <div>Ven</div>
              <div>Sam</div>
              <div>Dim</div>
            </div>

            <div className="mt-2 grid grid-cols-7 gap-2">
              {blanks.map((_, index) => (
                <div key={`blank-${index}`} />
              ))}

              {daysArray.map((dayObj) => {
                const dateStr = dayObj.format("YYYY-MM-DD");
                const dayInfo = dataMap.get(dateStr);
                const status = dayInfo?.status ?? resolveDefaultStatus(dayObj);
                const option = STATUS_OPTIONS.find((item) => item.value === status) ?? STATUS_OPTIONS[1];
                const dayAgenda = agendaByDay.get(dateStr) ?? [];

                return (
                  <button
                    key={dateStr}
                    onClick={() =>
                      handleApplyStatus(
                        dayInfo ?? {
                          date: dateStr,
                          status,
                          is_worked: status === "worked",
                          is_override: false,
                        },
                      )
                    }
                    disabled={loading || !editable}
                    className={`relative min-h-[82px] rounded-lg border px-1 py-2 transition-colors ${option.cellClass} ${!editable ? "cursor-default" : ""}`}
                  >
                    <div className="flex flex-col items-center">
                      <span className="text-lg font-bold">{dayObj.date()}</span>
                      <span className="text-xs">{option.shortLabel}</span>
                    </div>
                    {dayInfo?.is_override ? <span className="absolute right-1 top-1 h-2 w-2 rounded-full bg-blue-500" /> : null}
                    {dayAgenda.length ? (
                      <div className="mt-2 flex flex-wrap justify-center gap-1">
                        {dayAgenda.slice(0, 3).map((item) => (
                          <span key={`${dateStr}-${item.id}`} className={`rounded-full border px-1.5 py-0.5 text-[10px] font-semibold ${CATEGORY_CLASSES[item.category]}`}>
                            {item.category === "leave" ? "Congé" : item.category === "planning" ? "Planning" : item.category === "absence" ? "Abs." : "Événement"}
                          </span>
                        ))}
                        {dayAgenda.length > 3 ? <span className="text-[10px] font-semibold">+{dayAgenda.length - 3}</span> : null}
                      </div>
                    ) : null}
                  </button>
                );
              })}
            </div>

            {showAgenda ? (
              <div className={`mt-6 rounded-xl border p-4 ${theme === "light" ? "border-slate-200 bg-slate-50" : "border-slate-700 bg-slate-800"}`}>
                <div className="mb-3 flex items-center justify-between">
                  <h3 className={`text-sm font-semibold ${theme === "light" ? "text-slate-800" : "text-slate-100"}`}>Agenda consolidé du mois</h3>
                  <span className={`text-xs ${theme === "light" ? "text-slate-500" : "text-slate-400"}`}>{agenda.length} élément(s)</span>
                </div>
                <div className="space-y-3">
                  {agenda.map((item) => (
                    <div key={item.id} className={`rounded-xl border p-3 ${theme === "light" ? "border-slate-200 bg-white" : "border-slate-700 bg-slate-900"}`}>
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={`rounded-full border px-2 py-1 text-[11px] font-semibold ${CATEGORY_CLASSES[item.category]}`}>
                              {item.category === "leave" ? "Congé" : item.category === "planning" ? "Planning" : item.category === "absence" ? "Absence" : "Événement RH"}
                            </span>
                            <span className={`text-xs ${theme === "light" ? "text-slate-500" : "text-slate-400"}`}>
                              {item.end_date && item.end_date !== item.date ? `${item.date} → ${item.end_date}` : item.date}
                            </span>
                          </div>
                          <div className={`mt-2 text-sm font-semibold ${theme === "light" ? "text-slate-900" : "text-slate-100"}`}>{item.title}</div>
                          <div className={`mt-1 text-xs ${theme === "light" ? "text-slate-600" : "text-slate-300"}`}>{[item.worker_name, item.leave_type_code, item.subtitle].filter(Boolean).join(" · ")}</div>
                        </div>
                        <span className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${theme === "light" ? "border-slate-200 bg-slate-100 text-slate-700" : "border-slate-600 bg-slate-800 text-slate-200"}`}>
                          {item.status}
                        </span>
                      </div>
                    </div>
                  ))}
                  {!agenda.length ? <div className={`rounded-xl border border-dashed p-4 text-sm ${theme === "light" ? "border-slate-300 bg-white text-slate-500" : "border-slate-600 bg-slate-900 text-slate-400"}`}>Aucun événement sur ce mois pour le périmètre courant.</div> : null}
                </div>
              </div>
            ) : null}

            <div className={`mt-6 space-y-3 rounded-lg p-4 text-sm ${theme === "light" ? "bg-blue-50 text-blue-900" : "bg-slate-800 text-slate-200"}`}>
              <p>
                <strong>Calendrier société :</strong> il reste la source unique des jours travaillés, repos, jours fériés et fermetures.
              </p>
              <p>
                Les congés, absences mensuelles, propositions de planning et événements de validation s’y superposent sans dupliquer les données métiers.
              </p>
            </div>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
}
