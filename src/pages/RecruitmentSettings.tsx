import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "../api";
import { useToast } from "../components/ui/useToast";
import { useAuth } from "../contexts/useAuth";
import { sessionHasRole } from "../rbac";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface PublicationChannel {
  id: number;
  company_id: number;
  channel_type: "facebook" | "linkedin" | "site_interne" | "email" | "api_externe";
  is_active: boolean;
  default_publish: boolean;
  config: Record<string, unknown>;
  secret_fields_configured: string[];
}

interface ChannelConfigForm {
  page_name: string;
  page_id: string;
  organization_id: string;
  sender_email: string;
  audience_emails: string;
  webhook_url: string;
  publish_url: string;
  endpoint_path: string;
  notes: string;
  access_token: string;
  api_key: string;
  api_secret: string;
}

const shellCard = "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClass = "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClass = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";

const channelLabels: Record<string, string> = {
  facebook: "Facebook",
  linkedin: "LinkedIn",
  site_interne: "Site interne",
  email: "E-mail",
  api_externe: "API externe",
};

const emptyConfigForm: ChannelConfigForm = {
  page_name: "",
  page_id: "",
  organization_id: "",
  sender_email: "",
  audience_emails: "",
  webhook_url: "",
  publish_url: "",
  endpoint_path: "",
  notes: "",
  access_token: "",
  api_key: "",
  api_secret: "",
};

function splitEmails(value: string): string[] {
  return value
    .split(/\n|,|;/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function RecruitmentSettings() {
  const toast = useToast();
  const { session } = useAuth();
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(null);
  const [editingChannel, setEditingChannel] = useState<PublicationChannel | null>(null);
  const [configForm, setConfigForm] = useState<ChannelConfigForm>(emptyConfigForm);
  const canManageSettings = sessionHasRole(session, ["admin", "rh", "recrutement"]);

  const { data: employers = [] } = useQuery({
    queryKey: ["recruitment-settings", "employers"],
    enabled: canManageSettings,
    queryFn: async () => (await api.get<Employer[]>("/employers")).data,
  });

  useEffect(() => {
    if (!selectedEmployerId && employers.length > 0) {
      queueMicrotask(() => setSelectedEmployerId(employers[0].id));
    }
  }, [employers, selectedEmployerId]);

  const { data: channels = [] } = useQuery({
    queryKey: ["recruitment-settings", "channels", selectedEmployerId],
    enabled: canManageSettings && selectedEmployerId !== null,
    queryFn: async () =>
      (await api.get<PublicationChannel[]>("/recruitment/publication-channels", { params: { employer_id: selectedEmployerId } })).data,
  });

  const saveChannelMutation = useMutation({
    mutationFn: async ({ channel, form }: { channel: PublicationChannel; form: ChannelConfigForm }) =>
      (
        await api.put<PublicationChannel>(`/recruitment/publication-channels/${channel.channel_type}`, {
          company_id: channel.company_id,
          channel_type: channel.channel_type,
          is_active: channel.is_active,
          default_publish: channel.default_publish,
          config: {
            page_name: form.page_name || null,
            page_id: form.page_id || null,
            organization_id: form.organization_id || null,
            sender_email: form.sender_email || null,
            audience_emails: splitEmails(form.audience_emails),
            webhook_url: form.webhook_url || null,
            publish_url: form.publish_url || null,
            endpoint_path: form.endpoint_path || null,
            notes: form.notes || null,
            access_token: form.access_token || null,
            api_key: form.api_key || null,
            api_secret: form.api_secret || null,
          },
        })
      ).data,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["recruitment-settings", "channels", selectedEmployerId] });
      await queryClient.invalidateQueries({ queryKey: ["recruitment", "publication-channels"] });
      toast.success("Canal enregistré", "La configuration de publication a été sauvegardée.");
      setEditingChannel(null);
      setConfigForm(emptyConfigForm);
    },
    onError: (error) => toast.error("Sauvegarde impossible", error instanceof Error ? error.message : "Erreur inattendue."),
  });

  const openConfigModal = (channel: PublicationChannel) => {
    setEditingChannel(channel);
    setConfigForm({
      page_name: String(channel.config.page_name || ""),
      page_id: String(channel.config.page_id || ""),
      organization_id: String(channel.config.organization_id || ""),
      sender_email: String(channel.config.sender_email || ""),
      audience_emails: Array.isArray(channel.config.audience_emails) ? (channel.config.audience_emails as string[]).join("\n") : "",
      webhook_url: String(channel.config.webhook_url || ""),
      publish_url: String(channel.config.publish_url || ""),
      endpoint_path: String(channel.config.endpoint_path || ""),
      notes: String(channel.config.notes || ""),
      access_token: "",
      api_key: "",
      api_secret: "",
    });
  };

  const persistChannel = (channel: PublicationChannel, patch: Partial<PublicationChannel>) => {
    saveChannelMutation.mutate({
      channel: {
        ...channel,
        ...patch,
      },
      form: {
        page_name: String(channel.config.page_name || ""),
        page_id: String(channel.config.page_id || ""),
        organization_id: String(channel.config.organization_id || ""),
        sender_email: String(channel.config.sender_email || ""),
        audience_emails: Array.isArray(channel.config.audience_emails) ? (channel.config.audience_emails as string[]).join("\n") : "",
        webhook_url: String(channel.config.webhook_url || ""),
        publish_url: String(channel.config.publish_url || ""),
        endpoint_path: String(channel.config.endpoint_path || ""),
        notes: String(channel.config.notes || ""),
        access_token: "",
        api_key: "",
        api_secret: "",
      },
    });
  };

  if (!canManageSettings) {
    return (
      <div className="rounded-[1.75rem] border border-amber-400/30 bg-amber-500/10 p-6 text-amber-100">
        <div className="text-lg font-semibold">Acc?s restreint</div>
        <p className="mt-2 text-sm text-amber-50/90">Cette page de configuration est r?serv?e aux r?les RH / recrutement autoris?s.</p>
        <Link to="/recruitment" className="mt-4 inline-flex rounded-xl border border-amber-300/40 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-amber-100">
          Retour recrutement
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(14,116,144,0.88),rgba(8,145,178,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              Paramètres recrutement
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">Publication multi-canal sécurisée</h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              Activez les canaux, stockez les secrets uniquement côté backend et préparez la publication 1 clic visible dans le module recrutement.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <select value={selectedEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value) || null)} className={inputClass}>
              {employers.map((employer) => <option key={employer.id} value={employer.id}>{employer.raison_sociale}</option>)}
            </select>
            <Link to="/recruitment" className="rounded-2xl border border-white/10 px-4 py-3 text-sm font-semibold text-white">
              Retour recrutement
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        {channels.map((channel) => (
          <div key={channel.id} className={shellCard}>
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">{channelLabels[channel.channel_type] || channel.channel_type}</h2>
                <p className="mt-1 text-sm text-slate-400">
                  {channel.channel_type === "site_interne" ? "Diffusion immédiate sur le portail interne." : "Canal configurable avec journalisation et retry."}
                </p>
              </div>
              <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${channel.is_active ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100" : "border-white/10 bg-white/5 text-slate-300"}`}>
                {channel.is_active ? "Actif" : "Inactif"}
              </span>
            </div>

            <div className="mt-5 space-y-3 text-sm text-slate-300">
              <label className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                <span>Activer le canal</span>
                <input
                  type="checkbox"
                  checked={channel.is_active}
                  onChange={(event) => persistChannel(channel, { is_active: event.target.checked })}
                  className="h-4 w-4 accent-cyan-400"
                />
              </label>
              <label className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3">
                <span>Publier par défaut</span>
                <input
                  type="checkbox"
                  checked={channel.default_publish}
                  onChange={(event) => persistChannel(channel, { default_publish: event.target.checked })}
                  className="h-4 w-4 accent-cyan-400"
                />
              </label>
            </div>

            <div className="mt-5 text-xs text-slate-400">
              Secrets configurés: {channel.secret_fields_configured.length ? channel.secret_fields_configured.join(", ") : "aucun"}
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => openConfigModal(channel)}
                className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-xs font-semibold text-cyan-100"
              >
                Configurer
              </button>
            </div>
          </div>
        ))}
      </section>

      {editingChannel ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/80 p-4">
          <div className="w-full max-w-3xl rounded-[2rem] border border-white/10 bg-slate-950 p-6 shadow-2xl shadow-slate-950/40">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-white">Configurer {channelLabels[editingChannel.channel_type] || editingChannel.channel_type}</h2>
                <p className="mt-1 text-sm text-slate-400">Les secrets saisis ici ne sont jamais renvoyés en clair au frontend.</p>
              </div>
              <button type="button" onClick={() => setEditingChannel(null)} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                Fermer
              </button>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div><label className={labelClass}>Nom / page</label><input value={configForm.page_name} onChange={(event) => setConfigForm((current) => ({ ...current, page_name: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>Page ID</label><input value={configForm.page_id} onChange={(event) => setConfigForm((current) => ({ ...current, page_id: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>Organization ID</label><input value={configForm.organization_id} onChange={(event) => setConfigForm((current) => ({ ...current, organization_id: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>E-mail expéditeur</label><input value={configForm.sender_email} onChange={(event) => setConfigForm((current) => ({ ...current, sender_email: event.target.value }))} className={inputClass} /></div>
              <div className="md:col-span-2"><label className={labelClass}>Liste e-mails destinataires</label><textarea value={configForm.audience_emails} onChange={(event) => setConfigForm((current) => ({ ...current, audience_emails: event.target.value }))} className={`${inputClass} min-h-[90px]`} placeholder="Une adresse par ligne ou séparée par virgule" /></div>
              <div><label className={labelClass}>Webhook URL</label><input value={configForm.webhook_url} onChange={(event) => setConfigForm((current) => ({ ...current, webhook_url: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>URL publication</label><input value={configForm.publish_url} onChange={(event) => setConfigForm((current) => ({ ...current, publish_url: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>Endpoint path</label><input value={configForm.endpoint_path} onChange={(event) => setConfigForm((current) => ({ ...current, endpoint_path: event.target.value }))} className={inputClass} /></div>
              <div><label className={labelClass}>Access token</label><input type="password" value={configForm.access_token} onChange={(event) => setConfigForm((current) => ({ ...current, access_token: event.target.value }))} className={inputClass} placeholder={editingChannel.secret_fields_configured.includes("access_token") ? "Secret déjà stocké" : ""} /></div>
              <div><label className={labelClass}>API key</label><input type="password" value={configForm.api_key} onChange={(event) => setConfigForm((current) => ({ ...current, api_key: event.target.value }))} className={inputClass} placeholder={editingChannel.secret_fields_configured.includes("api_key") ? "Secret déjà stocké" : ""} /></div>
              <div><label className={labelClass}>API secret</label><input type="password" value={configForm.api_secret} onChange={(event) => setConfigForm((current) => ({ ...current, api_secret: event.target.value }))} className={inputClass} placeholder={editingChannel.secret_fields_configured.includes("api_secret") ? "Secret déjà stocké" : ""} /></div>
              <div className="md:col-span-2"><label className={labelClass}>Notes</label><textarea value={configForm.notes} onChange={(event) => setConfigForm((current) => ({ ...current, notes: event.target.value }))} className={`${inputClass} min-h-[90px]`} /></div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => saveChannelMutation.mutate({ channel: editingChannel, form: configForm })}
                disabled={saveChannelMutation.isPending}
                className="rounded-2xl border border-cyan-400/30 bg-cyan-400/10 px-5 py-3 text-sm font-semibold text-cyan-100 disabled:opacity-40"
              >
                {saveChannelMutation.isPending ? "Sauvegarde..." : "Enregistrer la configuration"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
