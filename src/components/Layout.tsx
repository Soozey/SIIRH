import { ReactNode } from "react";
import Navigation from "./Navigation";

interface LayoutProps {
  children: ReactNode;
  className?: string;
}

export default function Layout({ children, className = "" }: LayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className={`max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8 ${className}`}>
        {children}
      </main>
    </div>
  );
}