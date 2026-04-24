import type { AuthSession } from "./api";

export type AppModule =
  | "recruitment"
  | "contracts"
  | "workforce"
  | "organization"
  | "payroll"
  | "time_absence"
  | "declarations"
  | "compliance"
  | "messages"
  | "employee_portal"
  | "talents"
  | "people_ops"
  | "sst"
  | "reporting"
  | "master_data";

type RouteRule = {
  pathPrefix: string;
  module: AppModule;
  action?: "read" | "write" | "admin";
};

export const ROUTE_RBAC_RULES: RouteRule[] = [
  { pathPrefix: "/recruitment", module: "recruitment" },
  { pathPrefix: "/contracts", module: "contracts" },
  { pathPrefix: "/employers", module: "workforce" },
  { pathPrefix: "/workers", module: "workforce" },
  { pathPrefix: "/organization", module: "organization" },
  { pathPrefix: "/payroll", module: "payroll" },
  { pathPrefix: "/payslip", module: "payroll" },
  { pathPrefix: "/payslip-bulk", module: "payroll" },
  { pathPrefix: "/primes", module: "payroll" },
  { pathPrefix: "/hs", module: "time_absence" },
  { pathPrefix: "/absences", module: "time_absence" },
  { pathPrefix: "/leaves", module: "time_absence" },
  { pathPrefix: "/declarations", module: "declarations" },
  { pathPrefix: "/inspection", module: "compliance" },
  { pathPrefix: "/messages", module: "messages" },
  { pathPrefix: "/employee-portal", module: "employee_portal" },
  { pathPrefix: "/employee-360", module: "workforce" },
  { pathPrefix: "/people-ops", module: "people_ops" },
  { pathPrefix: "/talents", module: "talents" },
  { pathPrefix: "/sst", module: "sst" },
  { pathPrefix: "/reporting", module: "reporting" },
  { pathPrefix: "/data-transfer", module: "master_data", action: "admin" },
];

export function getSessionRoles(session: AuthSession | null): string[] {
  if (!session) return [];
  const rows = new Set<string>();
  if (session.role_code) rows.add(session.role_code);
  for (const code of session.assigned_role_codes ?? []) {
    if (code) rows.add(code);
  }
  return Array.from(rows);
}

export function sessionHasRole(session: AuthSession | null, roleCodes: string[]): boolean {
  const roles = new Set(getSessionRoles(session).map((item) => item.trim().toLowerCase()));
  return roleCodes.some((role) => roles.has(role.trim().toLowerCase()));
}

export function hasModulePermission(
  session: AuthSession | null,
  module: AppModule,
  action: "read" | "write" | "admin" = "read"
): boolean {
  if (!session) return false;
  const permissions = session.module_permissions;
  if (!permissions) return true;
  const globalActions = permissions["*"] ?? [];
  if (globalActions.includes("admin") || globalActions.includes(action)) return true;
  const moduleActions = permissions[module] ?? [];
  if (moduleActions.includes("admin") || moduleActions.includes(action)) return true;

  const roles = new Set(getSessionRoles(session).map((item) => item.trim().toLowerCase()));
  if ((roles.has("inspecteur") || roles.has("inspection_travail"))) {
    if (action === "read" && ["contracts", "workforce", "declarations", "compliance", "messages", "employee_portal", "reporting"].includes(module)) {
      return true;
    }
  }
  return false;
}

export function canAccessPath(session: AuthSession | null, path: string): boolean {
  if (!session) return false;
  if (path === "/" || path.startsWith("/login")) return true;
  const match = ROUTE_RBAC_RULES
    .filter((item) => path.startsWith(item.pathPrefix))
    .sort((a, b) => b.pathPrefix.length - a.pathPrefix.length)[0];
  if (!match) return true;
  return hasModulePermission(session, match.module, match.action ?? "read");
}
