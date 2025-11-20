import { ReactNode } from "react";

interface PageContainerProps {
  children: ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl" | "2xl" | "full";
  className?: string;
}

export default function PageContainer({ 
  children, 
  maxWidth = "full",
  className = "" 
}: PageContainerProps) {
  const maxWidthClasses = {
    sm: "max-w-sm",
    md: "max-w-md",
    lg: "max-w-lg",
    xl: "max-w-xl",
    "2xl": "max-w-2xl",
    full: "max-w-full"
  };

  return (
    <div className={`${maxWidthClasses[maxWidth]} mx-auto ${className}`}>
      {children}
    </div>
  );
}