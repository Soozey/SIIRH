import { useEffect, useMemo, useState } from "react";
import {
  ArrowPathIcon,
  CheckCircleIcon,
  ShieldCheckIcon,
  TrashIcon,
  UserCircleIcon,
  WrenchScrewdriverIcon,
} from "@heroicons/react/24/outline";

import {
  createAuthUser,
  deleteAuthUser,
  getUserAccessPreview,
  getUserRoleAssignments,
  listAuditLogs,
  listAuthUsers,
  listIamPermissions,
  listIamRoleActivations,
  listRoleCatalog,
  setIamRoleActivation,
  setRolePermissions,
  setUserRoleAssignments,
  updateAuthUser,
  getWorkers,
  api,
  type AppUserLight,
  type AuditLogEntry,
  type IamUserRoleAssignment,
  type RoleCatalogItem,
  type UserAccessPreview,
} from "../api";

type Employer = {
  id: number;
  raison_sociale: string;
};

type AccountForm = {
  username: string;
  full_name: string;
  password: string;
  role_code: string;
  employer_id: number | null;
  worker_id: number | null;
  is_active: boolean;
};

const ACTIONS: Array<"read" | "write" | "admin"> = ["read", "write", "admin"];
const inputClassName = "w-full rounded-xl border border-slate-700 bg-slate-900/90 px-3 py-2 text-sm text-slate-100";

function normalizeActions(actions: string[] | undefined): string[] {
  const rows = new Set((actions ?? []).map((item) => item.trim().toLowerCase()));
  if (rows.has("admin")) {
    rows.add("read");
    rows.add("write");
  }
  if (rows.has("write")) rows.add("read");
  return Array.from(rows);
}

function asActionMap(modules: Record<string, string[]>): Record<string, string[]> {
  const payload: Record<string, string[]> = {};
  Object.entries(modules).forEach(([module, actions]) => {
    payload[module] = normalizeActions(actions).filter((item) => ACTIONS.includes(item as "read" | "write" | "admin"));
  });
  return payload;
}

function emptyAccountForm(defaultRoleCode = ""): AccountForm {
  return {
    username: "",
    full_name: "",
    password: "",
    role_code: defaultRoleCode,
    employer_id: null,
    worker_id: null,
    is_active: true,
  };
}

export default function IamAccessManagerPanel() {
  const [roles, setRoles] = useState<RoleCatalogItem[]>([]);
  const [users, setUsers] = useState<AppUserLight[]>([]);
  const [employers, setEmployers] = useState<Employer[]>([]);
  const [activations, setActivations] = useState<Record<string, boolean>>({});
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [assignments, setAssignments] = useState<IamUserRoleAssignment[]>([]);
  const [accessPreview, setAccessPreview] = useState<UserAccessPreview | null>(null);
  const [selectedRoleCode, setSelectedRoleCode] = useState<string>("");
  const [roleModulesDraft, setRoleModulesDraft] = useState<Record<string, string[]>>({});
  const [createForm, setCreateForm] = useState<AccountForm>(emptyAccountForm());
  const [editForm, setEditForm] = useState<AccountForm>(emptyAccountForm());
  const [createWorkers, setCreateWorkers] = useState<Array<{ id: number; nom: string; prenom: string; matricule?: string | null }>>([]);
  const [editWorkers, setEditWorkers] = useState<Array<{ id: number; nom: string; prenom: string; matricule?: string | null }>>([]);
  const [deletePassword, setDeletePassword] = useState("");
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [savingRoles, setSavingRoles] = useState(false);
  const [savingPermissions, setSavingPermissions] = useState(false);
  const [savingAccount, setSavingAccount] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAll = async (keepSelectedUserId?: number | null) => {
    setLoading(true);
    setError(null);
    try {
      const [rolesRows, activationsRows, usersRows, permissionsRows, employersRows, auditRows] = await Promise.all([
        listRoleCatalog(),
        listIamRoleActivations(),
        listAuthUsers(),
        listIamPermissions(),
        api.get<Employer[]>("/employers").then((response) => response.data),
        listAuditLogs({ limit: 40 }),
      ]);

      const activationMap: Record<string, boolean> = {};
      activationsRows.forEach((row) => {
        activationMap[row.role_code] = row.is_enabled;
      });
      const modulesFromPermissions = new Set(permissionsRows.map((item) => item.module));
      const hydratedRoles = rolesRows.map((role) => {
        const modules = { ...role.modules };
        modulesFromPermissions.forEach((moduleCode) => {
          if (!modules[moduleCode]) modules[moduleCode] = [];
        });
        return { ...role, modules: asActionMap(modules) };
      });

      setRoles(hydratedRoles);
      setUsers(usersRows);
      setEmployers(employersRows);
      setActivations(activationMap);
      setAuditLogs(auditRows);
      setSelectedUserId((previous) => keepSelectedUserId ?? previous ?? usersRows[0]?.id ?? null);
      setSelectedRoleCode((previous) => previous || hydratedRoles[0]?.code || "");
      setCreateForm((current) => {
        const nextRole = current.role_code || hydratedRoles[0]?.code || "";
        return { ...current, role_code: nextRole };
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Chargement IAM impossible.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    const role = roles.find((item) => item.code === selectedRoleCode);
    if (!role) return;
    setRoleModulesDraft(asActionMap(role.modules));
  }, [roles, selectedRoleCode]);

  useEffect(() => {
    if (!selectedUserId) return;
    let cancelled = false;
    const loadUser = async () => {
      setError(null);
      try {
        const [rows, preview] = await Promise.all([
          getUserRoleAssignments(selectedUserId),
          getUserAccessPreview(selectedUserId),
        ]);
        if (cancelled) return;
        setAssignments(rows);
        setAccessPreview(preview);
      } catch (err: any) {
        if (!cancelled) {
          setError(err?.response?.data?.detail || err?.message || "Chargement utilisateur impossible.");
        }
      }
    };
    void loadUser();
    return () => {
      cancelled = true;
    };
  }, [selectedUserId]);

  const selectedUser = useMemo(
    () => users.find((item) => item.id === selectedUserId) ?? null,
    [users, selectedUserId]
  );

  useEffect(() => {
    if (!selectedUser) {
      setEditForm(emptyAccountForm(roles[0]?.code ?? ""));
      return;
    }
    setEditForm({
      username: selectedUser.username,
      full_name: selectedUser.full_name ?? "",
      password: "",
      role_code: selectedUser.role_code,
      employer_id: selectedUser.employer_id ?? null,
      worker_id: selectedUser.worker_id ?? null,
      is_active: selectedUser.is_active,
    });
  }, [selectedUser, roles]);

  useEffect(() => {
    if (!createForm.employer_id) {
      setCreateWorkers([]);
      return;
    }
    void getWorkers(createForm.employer_id).then((rows) => setCreateWorkers(rows));
  }, [createForm.employer_id]);

  useEffect(() => {
    if (!editForm.employer_id) {
      setEditWorkers([]);
      return;
    }
    void getWorkers(editForm.employer_id).then((rows) => setEditWorkers(rows));
  }, [editForm.employer_id]);

  const assignmentMap = useMemo(() => {
    const map = new Map<string, IamUserRoleAssignment>();
    assignments.forEach((row) => map.set(row.role_code, row));
    return map;
  }, [assignments]);

  const roleModules = useMemo(
    () => Object.keys(roleModulesDraft).sort((a, b) => a.localeCompare(b)),
    [roleModulesDraft]
  );

  const toggleRoleActivation = async (roleCode: string, nextValue: boolean) => {
    setStatus(null);
    setError(null);
    try {
      await setIamRoleActivation(roleCode, nextValue);
      setActivations((current) => ({ ...current, [roleCode]: nextValue }));
      setStatus(`Activation mise à jour pour ${roleCode}.`);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Mise à jour impossible.");
    }
  };

  const toggleUserRole = (role: RoleCatalogItem, checked: boolean) => {
    if (!selectedUser) return;
    setAssignments((current) => {
      const filtered = current.filter((item) => item.role_code !== role.code);
      if (!checked) return filtered;
      const requiresEmployer = ["employeur", "direction", "departement", "manager", "employe", "comptable", "juridique", "inspecteur", "recrutement"].includes(role.base_role_code || "");
      const requiresWorker = ["manager", "departement", "employe"].includes(role.base_role_code || "");
      filtered.push({
        role_code: role.code,
        is_active: true,
        employer_id: requiresEmployer ? selectedUser.employer_id ?? null : null,
        worker_id: requiresWorker ? selectedUser.worker_id ?? null : null,
      });
      return filtered.sort((a, b) => a.role_code.localeCompare(b.role_code));
    });
  };

  const saveUserAssignments = async () => {
    if (!selectedUserId) return;
    setSavingRoles(true);
    setStatus(null);
    setError(null);
    try {
      const rows = await setUserRoleAssignments(selectedUserId, assignments);
      setAssignments(rows);
      setAccessPreview(await getUserAccessPreview(selectedUserId));
      setStatus("Habilitations complémentaires sauvegardées.");
      await loadAll(selectedUserId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Sauvegarde des habilitations impossible.");
    } finally {
      setSavingRoles(false);
    }
  };

  const toggleRoleModuleAction = (moduleCode: string, action: "read" | "write" | "admin", checked: boolean) => {
    setRoleModulesDraft((current) => {
      const next = { ...current };
      const actions = new Set(normalizeActions(next[moduleCode]));
      if (checked) {
        actions.add(action);
        if (action === "write") actions.add("read");
        if (action === "admin") {
          actions.add("read");
          actions.add("write");
        }
      } else {
        actions.delete(action);
        if (action === "read") {
          actions.delete("write");
          actions.delete("admin");
        }
        if (action === "write") actions.delete("admin");
      }
      next[moduleCode] = Array.from(actions).filter((item) => ACTIONS.includes(item as "read" | "write" | "admin"));
      return next;
    });
  };

  const saveRolePermissions = async () => {
    if (!selectedRoleCode) return;
    setSavingPermissions(true);
    setStatus(null);
    setError(null);
    try {
      const response = await setRolePermissions(selectedRoleCode, roleModulesDraft);
      setRoleModulesDraft(asActionMap(response.modules));
      setRoles((current) =>
        current.map((item) => (item.code === selectedRoleCode ? { ...item, modules: asActionMap(response.modules) } : item))
      );
      setStatus(`Permissions du rôle ${selectedRoleCode} sauvegardées.`);
      await loadAll(selectedUserId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Sauvegarde des permissions impossible.");
    } finally {
      setSavingPermissions(false);
    }
  };

  const handleCreateUser = async () => {
    setSavingAccount(true);
    setStatus(null);
    setError(null);
    try {
      const created = await createAuthUser({
        username: createForm.username.trim(),
        password: createForm.password,
        full_name: createForm.full_name.trim() || null,
        role_code: createForm.role_code,
        employer_id: createForm.employer_id,
        worker_id: createForm.worker_id,
        is_active: createForm.is_active,
      });
      setStatus(`Compte créé: ${created.username}.`);
      setCreateForm(emptyAccountForm(createForm.role_code));
      await loadAll(created.id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Création du compte impossible.");
    } finally {
      setSavingAccount(false);
    }
  };

  const handleUpdateUser = async () => {
    if (!selectedUserId) return;
    setSavingAccount(true);
    setStatus(null);
    setError(null);
    try {
      const payload = {
        full_name: editForm.full_name.trim() || null,
        password: editForm.password.trim() || null,
        role_code: editForm.role_code,
        employer_id: editForm.employer_id,
        worker_id: editForm.worker_id,
        is_active: editForm.is_active,
      };
      await updateAuthUser(selectedUserId, payload);
      setStatus("Compte mis à jour.");
      setEditForm((current) => ({ ...current, password: "" }));
      await loadAll(selectedUserId);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Mise à jour du compte impossible.");
    } finally {
      setSavingAccount(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!selectedUserId || !deletePassword.trim()) return;
    setSavingAccount(true);
    setStatus(null);
    setError(null);
    try {
      await deleteAuthUser(selectedUserId, deletePassword);
      setDeletePassword("");
      setStatus("Compte désactivé et sessions révoquées.");
      await loadAll(null);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || "Suppression du compte impossible.");
    } finally {
      setSavingAccount(false);
    }
  };

  return (
    <section className="mt-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 md:p-5">
      <h2 className="inline-flex items-center gap-2 text-sm font-semibold text-slate-100">
        <ShieldCheckIcon className="h-4 w-4" />
        Administration des accès
      </h2>
      <p className="mt-1 text-xs text-slate-400">
        Comptes, rôles, droits et journal d’audit. Les suppressions exigent une ressaisie du mot de passe administrateur.
      </p>

      {error ? <div className="mt-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div> : null}
      {status ? <div className="mt-3 rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{status}</div> : null}

      {loading ? (
        <div className="mt-4 inline-flex items-center gap-2 text-sm text-slate-300">
          <ArrowPathIcon className="h-4 w-4 animate-spin" />
          Chargement des accès...
        </div>
      ) : (
        <div className="mt-4 space-y-5">
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white">
                <WrenchScrewdriverIcon className="h-4 w-4 text-cyan-300" />
                Rôles activés dans l’installation
              </div>
              <div className="mt-3 max-h-72 space-y-2 overflow-y-auto pr-1">
                {roles.map((role) => {
                  const enabled = activations[role.code] ?? role.is_active;
                  return (
                    <label key={`role-activation-${role.code}`} className="flex items-start gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(event) => void toggleRoleActivation(role.code, event.target.checked)}
                        className="mt-1"
                      />
                      <div>
                        <div className="text-slate-100">{role.label}</div>
                        <div className="text-xs text-slate-400">
                          {role.code} | portée: {role.scope}
                        </div>
                      </div>
                    </label>
                  );
                })}
              </div>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white">
                <UserCircleIcon className="h-4 w-4 text-cyan-300" />
                Comptes et rôles
              </div>

              <div className="mt-4 grid gap-5 lg:grid-cols-2">
                <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-sm font-semibold text-white">Créer un compte</div>
                  <input
                    value={createForm.username}
                    onChange={(event) => setCreateForm((current) => ({ ...current, username: event.target.value }))}
                    placeholder="Email de connexion"
                    className={inputClassName}
                  />
                  <input
                    value={createForm.full_name}
                    onChange={(event) => setCreateForm((current) => ({ ...current, full_name: event.target.value }))}
                    placeholder="Nom complet"
                    className={inputClassName}
                  />
                  <input
                    type="password"
                    value={createForm.password}
                    onChange={(event) => setCreateForm((current) => ({ ...current, password: event.target.value }))}
                    placeholder="Mot de passe initial"
                    className={inputClassName}
                  />
                  <select
                    value={createForm.role_code}
                    onChange={(event) => setCreateForm((current) => ({ ...current, role_code: event.target.value }))}
                    className={inputClassName}
                  >
                    {roles.map((role) => (
                      <option key={`create-role-${role.code}`} value={role.code}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={createForm.employer_id ?? ""}
                    onChange={(event) =>
                      setCreateForm((current) => ({
                        ...current,
                        employer_id: event.target.value ? Number(event.target.value) : null,
                        worker_id: null,
                      }))
                    }
                    className={inputClassName}
                    title="Renseignez l’employeur si le rôle est limité à une société."
                  >
                    <option value="">Aucun employeur</option>
                    {employers.map((employer) => (
                      <option key={`create-employer-${employer.id}`} value={employer.id}>
                        {employer.raison_sociale}
                      </option>
                    ))}
                  </select>
                  <select
                    value={createForm.worker_id ?? ""}
                    onChange={(event) => setCreateForm((current) => ({ ...current, worker_id: event.target.value ? Number(event.target.value) : null }))}
                    className={inputClassName}
                    title="À renseigner pour les rôles liés à un salarié précis."
                  >
                    <option value="">Aucun salarié lié</option>
                    {createWorkers.map((worker) => (
                      <option key={`create-worker-${worker.id}`} value={worker.id}>
                        {(worker.matricule || "-")} - {worker.nom} {worker.prenom}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      checked={createForm.is_active}
                      onChange={(event) => setCreateForm((current) => ({ ...current, is_active: event.target.checked }))}
                    />
                    Compte actif
                  </label>
                  <button
                    type="button"
                    onClick={() => void handleCreateUser()}
                    disabled={savingAccount || !createForm.username.trim() || !createForm.password.trim() || !createForm.role_code}
                    className="w-full rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
                  >
                    {savingAccount ? "Création..." : "Créer le compte"}
                  </button>
                </div>

                <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <div className="text-sm font-semibold text-white">Modifier le compte sélectionné</div>
                  <select
                    value={selectedUserId ?? ""}
                    onChange={(event) => setSelectedUserId(event.target.value ? Number(event.target.value) : null)}
                    className={inputClassName}
                  >
                    {users.map((user) => (
                      <option key={`iam-user-${user.id}`} value={user.id}>
                        {user.full_name || user.username} ({user.role_code})
                      </option>
                    ))}
                  </select>
                  <input value={editForm.username} className={`${inputClassName} opacity-70`} disabled />
                  <input
                    value={editForm.full_name}
                    onChange={(event) => setEditForm((current) => ({ ...current, full_name: event.target.value }))}
                    placeholder="Nom complet"
                    className={inputClassName}
                  />
                  <input
                    type="password"
                    value={editForm.password}
                    onChange={(event) => setEditForm((current) => ({ ...current, password: event.target.value }))}
                    placeholder="Nouveau mot de passe"
                    className={inputClassName}
                  />
                  <select
                    value={editForm.role_code}
                    onChange={(event) => setEditForm((current) => ({ ...current, role_code: event.target.value }))}
                    className={inputClassName}
                  >
                    {roles.map((role) => (
                      <option key={`edit-role-${role.code}`} value={role.code}>
                        {role.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={editForm.employer_id ?? ""}
                    onChange={(event) =>
                      setEditForm((current) => ({
                        ...current,
                        employer_id: event.target.value ? Number(event.target.value) : null,
                        worker_id: null,
                      }))
                    }
                    className={inputClassName}
                  >
                    <option value="">Aucun employeur</option>
                    {employers.map((employer) => (
                      <option key={`edit-employer-${employer.id}`} value={employer.id}>
                        {employer.raison_sociale}
                      </option>
                    ))}
                  </select>
                  <select
                    value={editForm.worker_id ?? ""}
                    onChange={(event) => setEditForm((current) => ({ ...current, worker_id: event.target.value ? Number(event.target.value) : null }))}
                    className={inputClassName}
                  >
                    <option value="">Aucun salarié lié</option>
                    {editWorkers.map((worker) => (
                      <option key={`edit-worker-${worker.id}`} value={worker.id}>
                        {(worker.matricule || "-")} - {worker.nom} {worker.prenom}
                      </option>
                    ))}
                  </select>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      checked={editForm.is_active}
                      onChange={(event) => setEditForm((current) => ({ ...current, is_active: event.target.checked }))}
                    />
                    Compte actif
                  </label>
                  <button
                    type="button"
                    onClick={() => void handleUpdateUser()}
                    disabled={savingAccount || !selectedUserId}
                    className="w-full rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-100 disabled:opacity-50"
                  >
                    {savingAccount ? "Enregistrement..." : "Enregistrer les changements"}
                  </button>
                  <div className="rounded-xl border border-rose-500/25 bg-rose-500/10 p-3">
                    <div className="text-xs font-semibold uppercase tracking-[0.18em] text-rose-100">Suppression logique</div>
                    <input
                      type="password"
                      value={deletePassword}
                      onChange={(event) => setDeletePassword(event.target.value)}
                      placeholder="Ressaisir votre mot de passe"
                      className={`${inputClassName} mt-3`}
                    />
                    <button
                      type="button"
                      onClick={() => void handleDeleteUser()}
                      disabled={savingAccount || !selectedUserId || !deletePassword.trim()}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-rose-500/40 px-4 py-2 text-sm font-semibold text-rose-100 disabled:opacity-50"
                    >
                      <TrashIcon className="h-4 w-4" />
                      Désactiver le compte
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white">
                <CheckCircleIcon className="h-4 w-4 text-cyan-300" />
                Habilitations complémentaires du compte
              </div>
              <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1">
                {roles.map((role) => (
                  <label key={`user-role-${role.code}`} className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-100">
                    <input
                      type="checkbox"
                      checked={assignmentMap.has(role.code)}
                      onChange={(event) => toggleUserRole(role, event.target.checked)}
                      disabled={!selectedUserId}
                    />
                    <span>{role.label}</span>
                    <span className="ml-auto text-xs text-slate-400">{role.code}</span>
                  </label>
                ))}
              </div>
              <button
                type="button"
                onClick={() => void saveUserAssignments()}
                disabled={!selectedUserId || savingRoles}
                className="mt-4 w-full rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50"
              >
                {savingRoles ? "Sauvegarde..." : "Sauvegarder les habilitations"}
              </button>
              {accessPreview ? (
                <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-xs text-slate-300">
                  <div>Rôle effectif: <span className="text-white">{accessPreview.role_label}</span></div>
                  <div>Portée: <span className="text-white">{accessPreview.role_scope}</span></div>
                  <div className="mt-2">
                    Modules: <span className="text-white">{Object.keys(accessPreview.module_permissions).join(", ") || "aucun"}</span>
                  </div>
                </div>
              ) : null}
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
              <div className="inline-flex items-center gap-2 text-sm font-semibold text-white">
                <ShieldCheckIcon className="h-4 w-4 text-cyan-300" />
                Permissions par rôle
              </div>
              <div className="mt-3">
                <select value={selectedRoleCode} onChange={(event) => setSelectedRoleCode(event.target.value)} className={inputClassName}>
                  {roles.map((role) => (
                    <option key={`permission-role-${role.code}`} value={role.code}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>
              <div className="mt-3 max-h-72 overflow-y-auto rounded-xl border border-slate-800">
                <table className="min-w-full text-left text-sm text-slate-200">
                  <thead className="bg-slate-900/80 text-slate-300">
                    <tr>
                      <th className="px-3 py-2">Module</th>
                      <th className="px-3 py-2">Voir</th>
                      <th className="px-3 py-2">Créer / modifier</th>
                      <th className="px-3 py-2">Administrer</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roleModules.map((moduleCode) => {
                      const actions = new Set(roleModulesDraft[moduleCode] ?? []);
                      return (
                        <tr key={`module-${moduleCode}`} className="border-t border-slate-800">
                          <td className="px-3 py-2">{moduleCode}</td>
                          {ACTIONS.map((action) => (
                            <td key={`${moduleCode}-${action}`} className="px-3 py-2">
                              <input
                                type="checkbox"
                                checked={actions.has(action)}
                                onChange={(event) => toggleRoleModuleAction(moduleCode, action, event.target.checked)}
                              />
                            </td>
                          ))}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <button
                type="button"
                onClick={() => void saveRolePermissions()}
                disabled={!selectedRoleCode || savingPermissions}
                className="mt-4 w-full rounded-xl border border-cyan-400/30 bg-cyan-500/10 px-4 py-2 text-sm font-semibold text-cyan-100 disabled:opacity-50"
              >
                {savingPermissions ? "Sauvegarde..." : "Sauvegarder les permissions du rôle"}
              </button>
            </div>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-950/40 p-4">
            <div className="inline-flex items-center gap-2 text-sm font-semibold text-white">
              <ShieldCheckIcon className="h-4 w-4 text-cyan-300" />
              Journal d’audit récent
            </div>
            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-left text-sm text-slate-200">
                <thead className="bg-slate-900/80 text-slate-300">
                  <tr>
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Utilisateur</th>
                    <th className="px-3 py-2">Action</th>
                    <th className="px-3 py-2">Objet</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((item) => (
                    <tr key={`audit-${item.id}`} className="border-t border-slate-800">
                      <td className="px-3 py-2 text-slate-400">{new Date(item.created_at).toLocaleString("fr-FR")}</td>
                      <td className="px-3 py-2">
                        <div>{item.actor_full_name || item.actor_username || "-"}</div>
                        <div className="text-xs text-slate-500">{item.actor_role || "-"}</div>
                      </td>
                      <td className="px-3 py-2">{item.action}</td>
                      <td className="px-3 py-2 text-slate-400">
                        {item.entity_type} #{item.entity_id}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
