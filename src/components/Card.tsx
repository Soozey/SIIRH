import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  padding?: "none" | "sm" | "md" | "lg";
  hover?: boolean;
}

export default function Card({ 
  children, 
  className = "", 
  padding = "md",
  hover = false 
}: CardProps) {
  const paddingClasses = {
    none: "p-0",
    sm: "p-4",
    md: "p-6",
    lg: "p-8"
  };

  return (
    <div className={`
      bg-white rounded-2xl shadow-sm border border-gray-200 
      ${paddingClasses[padding]} 
      ${hover ? "hover:shadow-md hover:border-gray-300 transition-all duration-200" : ""}
      ${className}
    `}>
      {children}
    </div>
  );
}