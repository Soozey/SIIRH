import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../components/ui/ToastProvider";


export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const toast = useToast();
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin123!");
  const [loading, setLoading] = useState(false);

  const redirectTo = (location.state as { from?: string } | null)?.from ?? "/";

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    try {
      await login(username, password);
      toast.success("Connexion établie", "Session sécurisée ouverte.");
      navigate(redirectTo, { replace: true });
    } catch (error: any) {
      toast.error("Connexion refusée", error?.response?.data?.detail ?? "Identifiants invalides.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050d19] text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(34,197,94,0.18),_transparent_30%),radial-gradient(circle_at_bottom_right,_rgba(6,182,212,0.22),_transparent_28%),linear-gradient(135deg,_rgba(15,23,42,0.98),_rgba(8,47,73,0.94))]" />
      <div className="relative mx-auto flex min-h-screen max-w-6xl items-center justify-center px-6 py-12">
        <div className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-[2rem] border border-white/10 bg-slate-950/60 p-8 shadow-2xl shadow-cyan-950/20 backdrop-blur-xl">
            <div className="mb-10 inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-200">
              SIIRH Production
            </div>
            <h1 className="max-w-xl text-4xl font-semibold leading-tight text-white md:text-5xl">
              Plateforme RH, paie et conformité prête pour exploitation client.
            </h1>
            <p className="mt-6 max-w-xl text-sm leading-7 text-slate-300">
              Accès sécurisé, traçabilité, contrôles métiers et données unifiées autour du moteur de paie existant.
            </p>
            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {[
                ["Paie protégée", "Aucun contournement du backend métier."],
                ["RBAC strict", "Employé, manager, RH et employeur cloisonnés."],
                ["Audit continu", "Journalisation des actions sensibles."],
              ].map(([title, text]) => (
                <div key={title} className="rounded-3xl border border-white/8 bg-white/5 p-4">
                  <div className="text-sm font-semibold text-white">{title}</div>
                  <div className="mt-2 text-xs leading-6 text-slate-300">{text}</div>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-[2rem] border border-white/10 bg-slate-950/80 p-8 shadow-2xl shadow-slate-950/40 backdrop-blur-xl">
            <div className="mb-8">
              <div className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">Connexion</div>
              <h2 className="mt-3 text-3xl font-semibold text-white">Ouvrir la session</h2>
              <p className="mt-3 text-sm leading-6 text-slate-400">
                Les écrans métier sont protégés côté serveur. Utilisez un compte autorisé.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Utilisateur</span>
                <input
                  type="text"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-4 text-sm text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20"
                  placeholder="Nom d'utilisateur"
                  autoComplete="username"
                  required
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Mot de passe</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="w-full rounded-2xl border border-slate-800 bg-slate-900/80 px-4 py-4 text-sm text-white outline-none transition focus:border-cyan-400/70 focus:ring-2 focus:ring-cyan-400/20"
                  placeholder="Mot de passe"
                  autoComplete="current-password"
                  required
                />
              </label>

              <button
                type="submit"
                disabled={loading}
                className="flex w-full items-center justify-center rounded-2xl bg-cyan-400 px-4 py-4 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-300"
              >
                {loading ? "Connexion..." : "Se connecter"}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  );
}
