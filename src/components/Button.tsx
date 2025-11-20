import { ReactNode, ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "outline" | "danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ComponentType<{ className?: string }>;
}

export default function Button({
  children,
  variant = "primary",
  size = "md",
  loading = false,
  icon: Icon,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses = "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  const variantClasses = {
    primary: "bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500 shadow-lg hover:shadow-xl",
    secondary: "bg-gray-600 text-white hover:bg-gray-700 focus:ring-gray-500",
    outline: "border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-blue-500",
    danger: "bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
  };

  const sizeClasses = {
    sm: "px-3 py-2 text-sm",
    md: "px-4 py-3 text-sm",
    lg: "px-6 py-3 text-base"
  };

  return (
    <button
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${sizeClasses[size]}
        ${disabled || loading ? "opacity-50 cursor-not-allowed" : ""}
        ${className}
      `}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
      )}
      {Icon && !loading && <Icon className="h-4 w-4 mr-2" />}
      {children}
    </button>
  );
}