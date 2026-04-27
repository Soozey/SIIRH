import { createContext } from "react";

export type ToastVariant = "info" | "success" | "error";

export type ToastItem = {
  id: number;
  title: string;
  description?: string;
  variant: ToastVariant;
};

export type ToastContextValue = {
  push: (toast: Omit<ToastItem, "id">) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
};

export const ToastContext = createContext<ToastContextValue | undefined>(undefined);
