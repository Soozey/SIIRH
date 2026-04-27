import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getApiErrorMessage } from "../api";
import { useAuth } from "../contexts/useAuth";

export default function ChangePassword() {
  const navigate = useNavigate();
  const { changePassword, logout, session } = useAuth();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError(null);
    if (newPassword !== confirmPassword) {
      setError("La confirmation ne correspond pas au nouveau mot de passe.");
      return;
    }
    setSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      setError(getApiErrorMessage(err, "Changement de mot de passe impossible."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#07111f] px-4 text-slate-100">
      <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-slate-950/90 p-6 shadow-2xl shadow-slate-950/40">
        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-200">Sécurité du compte</div>
        <h1 className="mt-2 text-xl font-semibold text-white">Changer le mot de passe</h1>
        <p className="mt-2 text-sm text-slate-400">
          Le compte {session?.username ?? ""} doit définir un nouveau mot de passe avant d’accéder aux modules SIIRH.
        </p>
        {error ? <div className="mt-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div> : null}
        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <input
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            placeholder="Mot de passe actuel ou temporaire"
            autoComplete="current-password"
            required
          />
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            placeholder="Nouveau mot de passe"
            autoComplete="new-password"
            required
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
            placeholder="Confirmer le nouveau mot de passe"
            autoComplete="new-password"
            required
          />
          <button
            type="submit"
            disabled={saving}
            className="w-full rounded-xl bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
          >
            {saving ? "Enregistrement..." : "Valider le nouveau mot de passe"}
          </button>
          <button type="button" onClick={() => void logout()} className="w-full rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-200">
            Se déconnecter
          </button>
        </form>
      </section>
    </main>
  );
}
