import { useState, useEffect } from "react";
import { Dialog } from "@headlessui/react";
import { XMarkIcon, ChevronLeftIcon, ChevronRightIcon } from "@heroicons/react/24/outline";
import { getCalendar, toggleCalendarDay } from "../api";
import dayjs from "dayjs";
import "dayjs/locale/fr";

// Configurer la locale globalement ou localement
dayjs.locale("fr");

interface WorkCalendarProps {
    isOpen: boolean;
    onClose: () => void;
    employerId: number;
    initialPeriod: string; // "YYYY-MM"
}

export default function WorkCalendar({ isOpen, onClose, employerId, initialPeriod }: WorkCalendarProps) {
    // State pour la navigation (Year/Month)
    // On stocke une date de référence (le 1er du mois)
    const [currentDate, setCurrentDate] = useState<dayjs.Dayjs>(dayjs());

    // State pour les données API
    const [daysData, setDaysData] = useState<any[]>([]);
    const [loading, setLoading] = useState(false);

    // Initialisation
    useEffect(() => {
        if (isOpen && initialPeriod) {
            // initialPeriod est "YYYY-MM"
            const d = dayjs(initialPeriod + "-01");
            if (d.isValid()) {
                setCurrentDate(d);
            }
        }
    }, [isOpen, initialPeriod]);

    // Fetch Data
    const fetchCalendar = async () => {
        setLoading(true);
        try {
            const year = currentDate.year();
            const month = currentDate.month() + 1; // 0-indexed in dayjs
            const data = await getCalendar(employerId, year, month);
            setDaysData(data);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            fetchCalendar();
        }
    }, [currentDate, isOpen]); // Refetch when month changes

    // Handlers
    const handlePrevMonth = () => {
        setCurrentDate(currentDate.subtract(1, 'month'));
    };

    const handleNextMonth = () => {
        setCurrentDate(currentDate.add(1, 'month'));
    };

    const handleToggle = async (day: any) => {
        try {
            // Optimistic update
            const newStatus = !day.is_worked;
            setDaysData(prev => prev.map(d => d.date === day.date ? { ...d, is_worked: newStatus } : d));

            await toggleCalendarDay(employerId, day.date, newStatus);
        } catch (e) {
            console.error("Error toggling day", e);
            fetchCalendar(); // Revert on error
        }
    };

    // Render Logic
    const startOfMonth = currentDate.startOf('month');
    const endOfMonth = currentDate.endOf('month');
    const daysInMonthTrigger = endOfMonth.date(); // Number of days, e.g. 31

    // Grid alignment
    // dayjs().day() -> 0=Sun, 1=Mon...
    const startDay = startOfMonth.day();
    // Adjust for Monday start (French) -> Mon=0, Sun=6
    // dayjs 0=Sun. so if 0 -> 6. if 1 -> 0. => (day + 6) % 7
    const offset = (startDay + 6) % 7;

    const blanks = Array(offset).fill(null);

    // Generate days array
    const daysArray = [];
    for (let i = 1; i <= daysInMonthTrigger; i++) {
        daysArray.push(startOfMonth.date(i)); // Clone implicit via date() setter? No, dayjs is immutable?
        // Wait, dayjs IS IMMUTABLE by default in v2? No, Check docs. "Day.js objects are immutable".
        // So startOfMonth.date(i) returns NEW object. Correct.
    }

    // Map API data to date string
    const dataMap = new Map();
    daysData.forEach(d => dataMap.set(d.date, d));

    return (
        <Dialog open={isOpen} onClose={onClose} className="relative z-50">
            <div className="fixed inset-0 bg-black/30" aria-hidden="true" />
            <div className="fixed inset-0 flex items-center justify-center p-4">
                <Dialog.Panel className="mx-auto max-w-2xl w-full bg-white rounded-xl shadow-xl overflow-hidden">
                    <div className="flex items-center justify-between p-4 border-b bg-gray-50">
                        <Dialog.Title className="text-lg font-bold text-gray-900">
                            Calendrier de Travail - {currentDate.format("MMMM YYYY")}
                        </Dialog.Title>
                        <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                            <XMarkIcon className="h-6 w-6" />
                        </button>
                    </div>

                    <div className="p-6">
                        {/* Navigation */}
                        <div className="flex justify-between items-center mb-6">
                            <button onClick={handlePrevMonth} className="p-2 border rounded hover:bg-gray-100">
                                <ChevronLeftIcon className="h-5 w-5" />
                            </button>
                            <span className="font-semibold capitalize text-lg">
                                {currentDate.format("MMMM YYYY")}
                            </span>
                            <button onClick={handleNextMonth} className="p-2 border rounded hover:bg-gray-100">
                                <ChevronRightIcon className="h-5 w-5" />
                            </button>
                        </div>

                        {/* Grid */}
                        <div className="grid grid-cols-7 gap-2 mb-2 text-center font-bold text-gray-500 text-sm">
                            <div>Lun</div>
                            <div>Mar</div>
                            <div>Mer</div>
                            <div>Jeu</div>
                            <div>Ven</div>
                            <div>Sam</div>
                            <div>Dim</div>
                        </div>

                        <div className="grid grid-cols-7 gap-2">
                            {blanks.map((_, i) => (
                                <div key={`blank-${i}`} />
                            ))}

                            {daysArray.map((dayObj) => {
                                const dateStr = dayObj.format("YYYY-MM-DD");
                                const dayInfo = dataMap.get(dateStr);
                                // Fallback preview logic if not loaded yet
                                const dayOfWeek = dayObj.day(); // 0=Sun
                                const isDefaultWorked = (dayOfWeek !== 0 && dayOfWeek !== 6);
                                const isWorked = dayInfo ? dayInfo.is_worked : isDefaultWorked;

                                return (
                                    <button
                                        key={dateStr}
                                        onClick={() => dayInfo ? handleToggle(dayInfo) : handleToggle({ date: dateStr, is_worked: !isWorked })}
                                        disabled={loading}
                                        className={`
                                            h-16 rounded-lg flex flex-col items-center justify-center border transition-colors relative
                                            ${isWorked
                                                ? "bg-green-100 border-green-300 text-green-800 hover:bg-green-200"
                                                : "bg-gray-100 border-gray-300 text-gray-500 hover:bg-gray-200"}
                                        `}
                                    >
                                        <span className="text-lg font-bold">{dayObj.date()}</span>
                                        <span className="text-xs">
                                            {isWorked ? "Travaillé" : "Off"}
                                        </span>
                                    </button>
                                );
                            })}
                        </div>

                        <div className="mt-6 p-4 bg-blue-50 text-blue-800 text-sm rounded-lg">
                            <p>ℹ️ <strong>CONSTANTE DAYSWORK :</strong> Le nombre de jours "Travaillé" (Vert) sera utilisé pour calculer la constante <code>DAYSWORK</code> dans vos formules.</p>
                        </div>
                    </div>
                </Dialog.Panel>
            </div>
        </Dialog>
    );
}
