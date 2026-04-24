import type { ReactNode } from "react";

import Navigation from "./Navigation";
import { useTheme } from "../contexts/ThemeContext";


interface LayoutProps {
  children: ReactNode;
  className?: string;
}


export default function Layout({ children, className = "" }: LayoutProps) {
  const { theme } = useTheme();
  return (
    <div className={`layout-shell min-h-screen ${theme === "light" ? "bg-slate-50 text-slate-900" : "bg-slate-950 text-slate-100"}`}>
      <Navigation />
      <main className={`min-h-screen md:pl-80 ${className}`}>
        <div className={`layout-main min-h-screen px-4 py-20 md:px-8 md:py-8 ${
          theme === "light"
            ? "bg-[radial-gradient(circle_at_top_left,_rgba(14,116,144,0.08),_transparent_34%),radial-gradient(circle_at_bottom_right,_rgba(2,132,199,0.06),_transparent_30%),linear-gradient(180deg,_rgba(248,250,252,1),_rgba(241,245,249,1))]"
            : "bg-[radial-gradient(circle_at_top_left,_rgba(14,116,144,0.12),_transparent_32%),radial-gradient(circle_at_bottom_right,_rgba(3,105,161,0.10),_transparent_28%),linear-gradient(180deg,_rgba(2,6,23,1),_rgba(15,23,42,1))]"
        }`}>
          <div className="layout-main-content mx-auto max-w-[1680px]">{children}</div>
        </div>
      </main>
    </div>
  );
}
