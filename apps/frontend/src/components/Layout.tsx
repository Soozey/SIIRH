import type { ReactNode } from "react";

import Navigation from "./Navigation";
import { useTheme } from "../contexts/useTheme";


interface LayoutProps {
  children: ReactNode;
  className?: string;
}


export default function Layout({ children, className = "" }: LayoutProps) {
  const { theme } = useTheme();
  return (
    <div className={`layout-shell min-h-screen ${theme === "light" ? "bg-[#f7f8fb] text-slate-900" : "bg-slate-950 text-slate-100"}`}>
      <Navigation />
      <main className={`min-h-screen md:pl-72 ${className}`}>
        <div className={`layout-main min-h-screen px-4 py-20 md:px-8 md:py-7 ${
          theme === "light"
            ? "bg-[#f7f8fb]"
            : "bg-[radial-gradient(circle_at_top_left,_rgba(14,116,144,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(3,105,161,0.10),_transparent_28%),linear-gradient(180deg,_rgba(2,6,23,1),_rgba(15,23,42,1))]"
        }`}>
          <div className="layout-main-content mx-auto max-w-[1680px]">{children}</div>
        </div>
      </main>
    </div>
  );
}
