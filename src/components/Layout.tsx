import type { ReactNode } from "react";

import Navigation from "./Navigation";


interface LayoutProps {
  children: ReactNode;
  className?: string;
}


export default function Layout({ children, className = "" }: LayoutProps) {
  return (
    <div className="min-h-screen bg-[#07111f] text-slate-100">
      <Navigation />
      <main className={`min-h-screen md:pl-80 ${className}`}>
        <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(6,182,212,0.10),_transparent_24%),radial-gradient(circle_at_bottom_right,_rgba(249,115,22,0.08),_transparent_24%),linear-gradient(180deg,_rgba(7,17,31,1),_rgba(15,23,42,1))] px-4 py-20 md:px-8 md:py-8">
          <div className="mx-auto max-w-[1600px]">{children}</div>
        </div>
      </main>
    </div>
  );
}
