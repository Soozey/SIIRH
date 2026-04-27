import type { ComponentType, ReactNode } from "react";

type IconComponent = ComponentType<{ className?: string }>;

type PageHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  actions?: ReactNode;
};

type StatCardProps = {
  label: string;
  value: ReactNode;
  hint?: string;
  icon?: IconComponent;
  tone?: "navy" | "emerald" | "blue" | "amber" | "red" | "slate";
};

type BadgeProps = {
  children: ReactNode;
  tone?: "success" | "warning" | "danger" | "neutral" | "info";
};

type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

const toneClasses = {
  navy: "bg-[#002147]/10 text-[#002147]",
  emerald: "bg-emerald-50 text-emerald-700",
  blue: "bg-blue-50 text-blue-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-rose-50 text-rose-700",
  slate: "bg-slate-100 text-slate-700",
};

const badgeClasses = {
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-800",
  danger: "border-rose-200 bg-rose-50 text-rose-700",
  neutral: "border-slate-200 bg-slate-100 text-slate-700",
  info: "border-blue-200 bg-blue-50 text-blue-700",
};

export function CorporatePageHeader({ eyebrow, title, subtitle, actions }: PageHeaderProps) {
  return (
    <section className="corporate-page-header">
      <div className="min-w-0">
        {eyebrow ? <div className="corporate-eyebrow">{eyebrow}</div> : null}
        <h1>{title}</h1>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {actions ? <div className="corporate-page-actions">{actions}</div> : null}
    </section>
  );
}

export function CorporateStatCard({ label, value, hint, icon: Icon, tone = "navy" }: StatCardProps) {
  return (
    <div className="corporate-stat-card">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="corporate-stat-label">{label}</div>
          <div className="corporate-stat-value">{value}</div>
        </div>
        {Icon ? (
          <div className={`corporate-stat-icon ${toneClasses[tone]}`}>
            <Icon className="h-5 w-5" />
          </div>
        ) : null}
      </div>
      {hint ? <div className="corporate-stat-hint">{hint}</div> : null}
    </div>
  );
}

export function CorporatePanel({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`corporate-panel ${className}`}>{children}</section>;
}

export function CorporateSectionHeader({ eyebrow, title, subtitle, actions }: PageHeaderProps) {
  return (
    <div className="corporate-section-header">
      <div>
        {eyebrow ? <div className="corporate-eyebrow">{eyebrow}</div> : null}
        <h2>{title}</h2>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </div>
  );
}

export function CorporateStatusBadge({ children, tone = "neutral" }: BadgeProps) {
  return <span className={`corporate-badge ${badgeClasses[tone]}`}>{children}</span>;
}

export function CorporateEmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="corporate-empty-state">
      <div className="font-semibold text-slate-900">{title}</div>
      {description ? <p>{description}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
