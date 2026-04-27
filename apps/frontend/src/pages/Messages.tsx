import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellAlertIcon, ChatBubbleLeftRightIcon, UserGroupIcon } from "@heroicons/react/24/outline";

import { api } from "../api";
import { useToast } from "../components/ui/useToast";
import { useAuth } from "../contexts/useAuth";
import { hasModulePermission, sessionHasRole } from "../rbac";


interface Employer {
  id: number;
  raison_sociale: string;
}

interface AppUserLight {
  id: number;
  username: string;
  full_name?: string | null;
  role_code: string;
}

interface Channel {
  id: number;
  channel_code: string;
  title: string;
  description?: string | null;
  channel_type: string;
  unread_count: number;
  member_count: number;
}

interface MessageEntry {
  id: number;
  body: string;
  message_type: string;
  created_at: string;
  attachments: Array<{ name?: string; path?: string }>;
  author?: AppUserLight | null;
  receipt_status?: string | null;
}

interface ChannelMember {
  id: number;
  user_id: number;
  member_role: string;
  is_active: boolean;
  last_read_at?: string | null;
  user?: AppUserLight | null;
}

interface ReadReceipt {
  id: number;
  message_id: number;
  user_id: number;
  status: string;
  read_at?: string | null;
  acknowledged_at?: string | null;
  user?: AppUserLight | null;
}

interface Notice {
  id: number;
  title: string;
  body: string;
  notice_type: string;
  ack_required: boolean;
  acknowledged_by_current_user: boolean;
}

interface MessagesDashboard {
  online_users: number;
  active_channels: number;
  unread_messages: number;
  pending_acknowledgements: number;
  notices: Notice[];
  channels: Channel[];
}

const cardClassName =
  "rounded-[1.75rem] border border-white/10 bg-slate-950/55 p-6 shadow-2xl shadow-slate-950/20 backdrop-blur";
const inputClassName =
  "w-full rounded-2xl border border-white/10 bg-slate-900/80 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-300/50";
const labelClassName = "mb-2 block text-xs font-semibold uppercase tracking-[0.22em] text-slate-400";

const channelTypeLabels: Record<string, string> = {
  team: "Canal d'equipe",
  broadcast: "Diffusion",
  coordination: "Coordination",
  service_note: "Note de service",
  mandatory_notice: "Affichage obligatoire",
  hr_internal: "RH interne",
  management: "Management",
  group: "Canal d'equipe",
  direct: "Echange direct",
  announcement: "Diffusion interne",
};


export default function Messages() {
  const { session } = useAuth();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [selectedEmployerId, setSelectedEmployerId] = useState<number | null>(session?.employer_id ?? null);
  const [selectedChannelId, setSelectedChannelId] = useState<number | null>(null);
  const [selectedMembers, setSelectedMembers] = useState<number[]>([]);
  const [messageBody, setMessageBody] = useState("");
  const [messageFiles, setMessageFiles] = useState<FileList | null>(null);
  const [channelForm, setChannelForm] = useState({
    title: "",
    description: "",
    channel_type: "team",
  });
  const isSelfScoped = sessionHasRole(session, ["employe", "manager"]);
  const isInspector = sessionHasRole(session, ["inspecteur"]);
  const canWriteMessages = hasModulePermission(session, "messages", "write") || isInspector;

  const { data: employers = [], isLoading: employersLoading, isError: employersError } = useQuery({
    queryKey: ["messages", "employers"],
    enabled: !isSelfScoped,
    queryFn: async () => {
      if (isInspector) {
        return (await api.get<Employer[]>("/compliance/inspector-employers")).data;
      }
      return (await api.get<Employer[]>("/employers")).data;
    },
  });

  const effectiveEmployerId = useMemo(() => {
    if (isSelfScoped && selectedEmployerId !== null) {
      return selectedEmployerId;
    }
    if (selectedEmployerId !== null && employers.some((item) => item.id === selectedEmployerId)) {
      return selectedEmployerId;
    }
    return employers[0]?.id ?? null;
  }, [employers, isSelfScoped, selectedEmployerId]);

  const { data: dashboard } = useQuery({
    queryKey: ["messages", "dashboard", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<MessagesDashboard>("/messages/dashboard", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const channels = useMemo(() => dashboard?.channels ?? [], [dashboard]);
  const notices = dashboard?.notices ?? [];
  const onlineUsers = dashboard?.online_users ?? 0;
  const activeChannels = dashboard?.active_channels ?? 0;
  const unreadMessages = dashboard?.unread_messages ?? 0;
  const pendingAcknowledgements = dashboard?.pending_acknowledgements ?? 0;

  const effectiveChannelId = useMemo(() => {
    if (selectedChannelId !== null && channels.some((item) => item.id === selectedChannelId)) {
      return selectedChannelId;
    }
    return channels[0]?.id ?? null;
  }, [channels, selectedChannelId]);

  const { data: users = [] } = useQuery({
    queryKey: ["messages", "available-users", effectiveEmployerId],
    enabled: effectiveEmployerId !== null,
    queryFn: async () => (
      await api.get<AppUserLight[]>("/messages/available-users", {
        params: { employer_id: effectiveEmployerId },
      })
    ).data,
  });

  const { data: messages = [] } = useQuery({
    queryKey: ["messages", "channel", effectiveChannelId],
    enabled: effectiveChannelId !== null,
    queryFn: async () => (await api.get<MessageEntry[]>(`/messages/channels/${effectiveChannelId}/messages`)).data,
  });

  const { data: members = [] } = useQuery({
    queryKey: ["messages", "channel-members", effectiveChannelId],
    enabled: effectiveChannelId !== null,
    queryFn: async () => (await api.get<ChannelMember[]>(`/messages/channels/${effectiveChannelId}/members`)).data,
  });

  const { data: readReceipts = [] } = useQuery({
    queryKey: ["messages", "read-receipts", effectiveChannelId],
    enabled: effectiveChannelId !== null && canWriteMessages,
    queryFn: async () => (await api.get<ReadReceipt[]>(`/messages/channels/${effectiveChannelId}/read-receipts`)).data,
  });

  const refreshMessages = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ["messages", "dashboard"] }),
      queryClient.invalidateQueries({ queryKey: ["messages", "channel"] }),
    ]);
  };

  const createChannelMutation = useMutation({
    mutationFn: async () => {
      if (effectiveEmployerId === null) {
        throw new Error("Aucun employeur disponible.");
      }
      const title = channelForm.title.trim();
      if (!title) {
        throw new Error("Le nom du canal est obligatoire.");
      }
      if (selectedMembers.length === 0) {
        throw new Error("Selectionnez au moins un participant.");
      }
      return (
        await api.post<Channel>("/messages/channels", {
          employer_id: effectiveEmployerId,
          title,
          description: channelForm.description.trim(),
          channel_type: channelForm.channel_type,
          visibility: "internal",
          ack_required: ["mandatory_notice", "service_note", "broadcast"].includes(channelForm.channel_type),
          member_user_ids: selectedMembers,
        })
      ).data;
    },
    onSuccess: async (channel) => {
      setChannelForm({ title: "", description: "", channel_type: "team" });
      setSelectedMembers([]);
      setSelectedChannelId(channel.id);
      toast.success("Canal cree", "Le module de messagerie interne est actif.");
      await refreshMessages();
    },
    onError: (error) => {
      toast.error("Creation impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  const sendMessageMutation = useMutation({
    mutationFn: async () => {
      if (!effectiveChannelId) {
        throw new Error("Selectionnez un canal.");
      }
      if (!messageBody.trim()) {
        throw new Error("Le message est obligatoire.");
      }
      if (messageFiles && messageFiles.length > 0) {
        const formData = new FormData();
        formData.append("body", messageBody.trim());
        formData.append("message_type", "message");
        Array.from(messageFiles).forEach((file) => formData.append("attachments", file));
        return (await api.post(`/messages/channels/${effectiveChannelId}/messages/upload`, formData)).data;
      }
      return (
        await api.post(`/messages/channels/${effectiveChannelId}/messages`, {
          message_type: "message",
          body: messageBody.trim(),
          attachments: [],
        })
      ).data;
    },
    onSuccess: async () => {
      setMessageBody("");
      setMessageFiles(null);
      toast.success("Message envoye", "La conversation interne a ete mise a jour.");
      await refreshMessages();
    },
    onError: (error) => {
      toast.error("Envoi impossible", error instanceof Error ? error.message : "Erreur inattendue.");
    },
  });

  const acknowledgeNoticeMutation = useMutation({
    mutationFn: async (noticeId: number) => (await api.post(`/messages/notices/${noticeId}/ack`)).data,
    onSuccess: async () => {
      toast.success("Affichage accuse", "La prise de connaissance a ete tracee.");
      await refreshMessages();
    },
  });

  const selectedChannelLabel = useMemo(() => {
    const selected = channels.find((item) => item.id === effectiveChannelId);
    return selected?.title ?? "Aucun canal";
  }, [channels, effectiveChannelId]);

  return (
    <div className="space-y-8">
      <section className="rounded-[2.5rem] border border-cyan-400/15 bg-[linear-gradient(135deg,rgba(15,23,42,0.94),rgba(8,47,73,0.9),rgba(14,116,144,0.82))] p-8 shadow-2xl shadow-slate-950/30">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.28em] text-cyan-100">
              {isInspector ? "Boite inspection" : "Messagerie interne"}
            </div>
            <h1 className="mt-6 text-4xl font-semibold tracking-tight text-white">
              {isInspector ? "Plaintes, messages recus et suivi des echanges" : "Canaux internes, affichages et traces de lecture"}
            </h1>
            <p className="mt-3 text-sm leading-7 text-cyan-50/90">
              {isInspector
                ? "Un canal = une boite de conversation. Selectionnez une boite a gauche, lisez les messages au centre, puis repondez en bas."
                : "Module distinct du canal inspection, concu pour les echanges internes RH, management, service notes et affichages obligatoires."}
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">En ligne</div>
              <div className="mt-3 text-3xl font-semibold text-white">{onlineUsers}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Canaux</div>
              <div className="mt-3 text-3xl font-semibold text-white">{activeChannels}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Non lus</div>
              <div className="mt-3 text-3xl font-semibold text-white">{unreadMessages}</div>
            </div>
            <div className="rounded-[1.5rem] border border-white/10 bg-slate-950/30 px-5 py-4">
              <div className="text-xs uppercase tracking-[0.24em] text-cyan-100/70">Accuses</div>
              <div className="mt-3 text-3xl font-semibold text-white">{pendingAcknowledgements}</div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr_1fr]">
        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <UserGroupIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">{isInspector ? "Nouvelle boite" : "Nouveau canal"}</h2>
              <p className="text-sm text-slate-400">{isInspector ? "Creez une boite simple pour classer les echanges inspection." : "Equipe, diffusion ou coordination."}</p>
            </div>
          </div>

          {!isSelfScoped ? (
            <div className="mt-6">
              <label className={labelClassName}>Employeur</label>
              <select value={effectiveEmployerId ?? ""} onChange={(event) => setSelectedEmployerId(Number(event.target.value))} className={inputClassName}>
                <option value="">{employersLoading ? "Chargement des employeurs..." : employersError ? "Erreur de chargement" : "Selectionner un employeur"}</option>
                {employers.map((item) => (
                  <option key={item.id} value={item.id}>{item.raison_sociale}</option>
                ))}
              </select>
              {!employersLoading && !employers.length ? (
                <div className="mt-2 text-xs text-amber-200">Aucun employeur disponible pour votre perimetre.</div>
              ) : null}
            </div>
          ) : null}

          <div className="mt-6 grid gap-4">
            <input className={inputClassName} placeholder={isInspector ? "Ex: Plaintes employeurs / Karibo" : "Nom du canal"} value={channelForm.title} onChange={(event) => setChannelForm((current) => ({ ...current, title: event.target.value }))} />
            <textarea className={`${inputClassName} min-h-[120px]`} placeholder={isInspector ? "Expliquez en une phrase a quoi sert cette boite." : "Description du canal"} value={channelForm.description} onChange={(event) => setChannelForm((current) => ({ ...current, description: event.target.value }))} />
            <select className={inputClassName} value={channelForm.channel_type} onChange={(event) => setChannelForm((current) => ({ ...current, channel_type: event.target.value }))}>
              <option value="team">Canal d'equipe</option>
              <option value="broadcast">Diffusion</option>
              <option value="coordination">Coordination</option>
              <option value="service_note">Note de service</option>
              <option value="mandatory_notice">Affichage obligatoire</option>
              <option value="hr_internal">RH interne</option>
              <option value="management">Management</option>
            </select>
            <div>
              <label className={labelClassName}>Participants</label>
              <select
                multiple
                className={`${inputClassName} min-h-[180px]`}
                value={selectedMembers.map(String)}
                onChange={(event) => {
                  const values = Array.from(event.target.selectedOptions).map((option) => Number(option.value));
                  setSelectedMembers(values);
                }}
              >
                {users.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.full_name || item.username} ({item.role_code})
                  </option>
                ))}
              </select>
            </div>
            {canWriteMessages ? (
              <button type="button" onClick={() => createChannelMutation.mutate()} className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300">
                {createChannelMutation.isPending ? "Creation..." : isInspector ? "Creer la boite" : "Creer le canal"}
              </button>
            ) : (
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs text-slate-400">
                Lecture seule: creation de canal desactivee pour ce role.
              </div>
            )}
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">{isInspector ? "Boites et conversation" : "Canaux & conversation"}</h2>
              <p className="text-sm text-slate-400">{isInspector ? "Lecture des plaintes, messages et pieces jointes." : "Lecture, pieces jointes et historique."}</p>
            </div>
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[0.78fr_1.22fr]">
            <div className="space-y-3">
              {channels.length ? channels.map((channel) => (
                <button
                  key={channel.id}
                  type="button"
                  onClick={() => setSelectedChannelId(channel.id)}
                  className={`w-full rounded-[1.5rem] border p-4 text-left ${effectiveChannelId === channel.id ? "border-cyan-300/40 bg-cyan-400/10" : "border-white/10 bg-white/5"}`}
                >
                  <div className="text-sm font-semibold text-white">{channel.title}</div>
                  <div className="mt-1 text-xs uppercase tracking-[0.2em] text-cyan-300">
                    {channelTypeLabels[channel.channel_type] ?? channel.channel_type}
                  </div>
                  {channel.description ? <div className="mt-2 text-xs leading-5 text-slate-300">{channel.description}</div> : null}
                  <div className="mt-2 text-xs text-slate-400">{channel.member_count} membre(s) • {channel.unread_count} non lu(s)</div>
                </button>
              )) : <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-500">{isInspector ? "Aucune boite disponible." : "Aucun canal disponible."}</div>}
            </div>

            <div className="space-y-4">
              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <div className="text-sm font-semibold text-white">{selectedChannelLabel}</div>
                {members.length ? (
                  <div className="mt-2 text-xs text-slate-300">
                    Participants: {members.filter((item) => item.is_active).map((item) => item.user?.full_name || item.user?.username || `Utilisateur #${item.user_id}`).join(", ")}
                  </div>
                ) : null}
                <div className="mt-3 max-h-[20rem] space-y-3 overflow-y-auto pr-1">
                  {messages.length ? messages.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-slate-950/50 p-4 text-sm text-slate-300">
                      <div className="font-semibold text-white">{item.author?.full_name || item.author?.username || "Utilisateur"}</div>
                      <div className="mt-1">{item.body}</div>
                      <div className="mt-2 text-xs text-slate-500">{new Date(item.created_at).toLocaleString("fr-FR")}</div>
                      {(item.attachments ?? []).length ? (
                        <div className="mt-2 text-xs text-cyan-200">
                          Pieces jointes: {(item.attachments ?? []).map((attachment) => attachment.name || attachment.path).join(", ")}
                        </div>
                      ) : null}
                    </div>
                  )) : <div className="text-sm text-slate-500">Aucun message sur ce canal.</div>}
                </div>
              </div>

              {canWriteMessages && readReceipts.length ? (
                <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                  <div className="text-sm font-semibold text-white">Traces de lecture</div>
                  <div className="mt-3 space-y-2 text-xs text-slate-300">
                    {readReceipts.slice(0, 8).map((receipt) => (
                      <div key={receipt.id}>
                        {receipt.user?.full_name || receipt.user?.username || `Utilisateur #${receipt.user_id}`} - {receipt.status}
                        {receipt.read_at ? ` - ${new Date(receipt.read_at).toLocaleString("fr-FR")}` : ""}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <textarea className={`${inputClassName} min-h-[120px]`} value={messageBody} onChange={(event) => setMessageBody(event.target.value)} placeholder={isInspector ? "Ecrire une reponse, une demande de precision ou une consigne..." : "Votre message interne..."} />
                <input type="file" multiple className="mt-3 block w-full text-sm text-slate-300" onChange={(event) => setMessageFiles(event.target.files)} />
                <button type="button" disabled={!canWriteMessages || sendMessageMutation.isPending} onClick={() => sendMessageMutation.mutate()} className="mt-3 rounded-xl border border-white/10 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">
                  {sendMessageMutation.isPending ? "Envoi..." : isInspector ? "Envoyer la reponse" : "Envoyer"}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className={cardClassName}>
          <div className="flex items-center gap-3">
            <BellAlertIcon className="h-6 w-6 text-cyan-300" />
            <div>
              <h2 className="text-xl font-semibold text-white">Affichages et notes</h2>
              <p className="text-sm text-slate-400">Diffusions internes avec accuse de lecture.</p>
            </div>
          </div>

          <div className="mt-6 space-y-3">
            {notices.length ? notices.map((notice) => (
              <div key={notice.id} className="rounded-[1.5rem] border border-white/10 bg-white/5 p-4">
                <div className="text-sm font-semibold text-white">{notice.title}</div>
                <div className="mt-1 text-xs uppercase tracking-[0.2em] text-cyan-300">{notice.notice_type}</div>
                <div className="mt-3 text-sm text-slate-300">{notice.body}</div>
                <div className="mt-4 flex items-center justify-between gap-3">
                  <div className="text-xs text-slate-400">
                    {notice.ack_required ? (notice.acknowledged_by_current_user ? "Accuse de lecture enregistre" : "Accuse de lecture requis") : "Consultation libre"}
                  </div>
                  {notice.ack_required && !notice.acknowledged_by_current_user ? (
                    <button type="button" onClick={() => acknowledgeNoticeMutation.mutate(notice.id)} className="rounded-xl border border-white/10 px-3 py-2 text-xs font-semibold text-white">
                      Accuser reception
                    </button>
                  ) : null}
                </div>
              </div>
            )) : <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-500">Aucun affichage interne publie.</div>}
          </div>
        </div>
      </section>
    </div>
  );
}
