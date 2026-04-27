--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: employers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.employers (
    id integer NOT NULL,
    raison_sociale character varying NOT NULL,
    adresse character varying,
    pays character varying,
    telephone character varying,
    email character varying,
    activite character varying,
    representant character varying,
    nif character varying,
    stat character varying,
    lieu_fiscal character varying,
    cnaps_num character varying,
    sm_embauche double precision,
    type_etab character varying,
    taux_pat_cnaps double precision,
    taux_pat_smie double precision,
    rcs character varying,
    ostie_num character varying,
    smie_num character varying,
    ville character varying,
    contact_rh character varying,
    type_regime_id integer,
    taux_sal_cnaps double precision DEFAULT '1'::double precision,
    plafond_cnaps_base double precision DEFAULT '0'::double precision,
    taux_pat_fmfp double precision DEFAULT '1'::double precision,
    taux_sal_smie double precision DEFAULT '0'::double precision,
    smie_forfait_sal double precision DEFAULT '0'::double precision,
    smie_forfait_pat double precision DEFAULT '0'::double precision
);


ALTER TABLE public.employers OWNER TO postgres;

--
-- Name: employers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.employers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.employers_id_seq OWNER TO postgres;

--
-- Name: employers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.employers_id_seq OWNED BY public.employers.id;


--
-- Name: payroll_runs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payroll_runs (
    id integer NOT NULL,
    employer_id integer,
    period character varying,
    generated_at date
);


ALTER TABLE public.payroll_runs OWNER TO postgres;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payroll_runs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payroll_runs_id_seq OWNER TO postgres;

--
-- Name: payroll_runs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payroll_runs_id_seq OWNED BY public.payroll_runs.id;


--
-- Name: payvars; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.payvars (
    id integer NOT NULL,
    worker_id integer NOT NULL,
    period character varying,
    conge_pris_j double precision,
    conge_restant_j double precision,
    conge_valeur double precision,
    abs_maladie_j double precision,
    abs_non_remu_h double precision,
    abs_non_remu_j double precision,
    mise_a_pied_j double precision,
    hsni_130_h double precision,
    hsi_130_h double precision,
    hsni_150_h double precision,
    hsi_150_h double precision,
    dimanche_h double precision,
    nuit_hab_h double precision,
    nuit_occ_h double precision,
    ferie_jour_h double precision,
    prime1 double precision,
    prime2 double precision,
    avantage_logement double precision,
    avantage_vehicule double precision,
    avantage_telephone double precision,
    avantage_autres double precision,
    avance_quinzaine double precision,
    avance_speciale_total double precision,
    avance_speciale_rembfixe double precision,
    avance_speciale_restant_prec double precision,
    autre_ded1 double precision,
    autre_ded2 double precision,
    autre_ded3 double precision,
    autre_ded4 double precision,
    alloc_familiale double precision
);


ALTER TABLE public.payvars OWNER TO postgres;

--
-- Name: payvars_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.payvars_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.payvars_id_seq OWNER TO postgres;

--
-- Name: payvars_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.payvars_id_seq OWNED BY public.payvars.id;


--
-- Name: type_regimes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.type_regimes (
    id integer NOT NULL,
    code character varying NOT NULL,
    label character varying NOT NULL,
    vhm double precision NOT NULL
);


ALTER TABLE public.type_regimes OWNER TO postgres;

--
-- Name: type_regimes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.type_regimes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.type_regimes_id_seq OWNER TO postgres;

--
-- Name: type_regimes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.type_regimes_id_seq OWNED BY public.type_regimes.id;


--
-- Name: workers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workers (
    id integer NOT NULL,
    employer_id integer NOT NULL,
    matricule character varying,
    nom character varying,
    prenom character varying,
    sexe character varying,
    situation_familiale character varying,
    adresse character varying,
    telephone character varying,
    email character varying,
    cin character varying,
    cin_delivre_le date,
    cin_lieu character varying,
    date_embauche date,
    nature_contrat character varying,
    duree_essai_jours integer,
    mode_paiement character varying,
    rib character varying,
    banque character varying,
    bic character varying,
    cnaps_num character varying,
    smie_agence character varying,
    smie_carte_num character varying,
    etablissement character varying,
    departement character varying,
    service character varying,
    poste character varying,
    categorie_prof character varying,
    indice character varying,
    valeur_point double precision,
    groupe_preavis integer,
    type_sortie character varying,
    jours_preavis_deja_faits integer,
    anciennete_jours integer,
    secteur character varying,
    salaire_base double precision,
    salaire_horaire double precision,
    vhm double precision,
    horaire_hebdo double precision,
    nombre_enfant integer DEFAULT 0,
    date_naissance date,
    type_regime_id integer
);


ALTER TABLE public.workers OWNER TO postgres;

--
-- Name: workers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.workers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workers_id_seq OWNER TO postgres;

--
-- Name: workers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.workers_id_seq OWNED BY public.workers.id;


--
-- Name: employers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employers ALTER COLUMN id SET DEFAULT nextval('public.employers_id_seq'::regclass);


--
-- Name: payroll_runs id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs ALTER COLUMN id SET DEFAULT nextval('public.payroll_runs_id_seq'::regclass);


--
-- Name: payvars id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payvars ALTER COLUMN id SET DEFAULT nextval('public.payvars_id_seq'::regclass);


--
-- Name: type_regimes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.type_regimes ALTER COLUMN id SET DEFAULT nextval('public.type_regimes_id_seq'::regclass);


--
-- Name: workers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workers ALTER COLUMN id SET DEFAULT nextval('public.workers_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
0565ed6dbe40
\.


--
-- Data for Name: employers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.employers (id, raison_sociale, adresse, pays, telephone, email, activite, representant, nif, stat, lieu_fiscal, cnaps_num, sm_embauche, type_etab, taux_pat_cnaps, taux_pat_smie, rcs, ostie_num, smie_num, ville, contact_rh, type_regime_id, taux_sal_cnaps, plafond_cnaps_base, taux_pat_fmfp, taux_sal_smie, smie_forfait_sal, smie_forfait_pat) FROM stdin;
1	ddfefefefefefefefe	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	general	13	5	\N	\N	\N	\N	\N	2	1	0	1	0	0	0
2	rrretreytryertyetryetryetyr	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	general	13	5	\N	\N	\N	\N	\N	2	1	0	1	0	0	0
3	MMMMMKKKJJJUUUUUU	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	scolaire	8	5	\N	\N	\N	\N	\N	2	1	0	1	0	0	0
\.


--
-- Data for Name: payroll_runs; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payroll_runs (id, employer_id, period, generated_at) FROM stdin;
\.


--
-- Data for Name: payvars; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.payvars (id, worker_id, period, conge_pris_j, conge_restant_j, conge_valeur, abs_maladie_j, abs_non_remu_h, abs_non_remu_j, mise_a_pied_j, hsni_130_h, hsi_130_h, hsni_150_h, hsi_150_h, dimanche_h, nuit_hab_h, nuit_occ_h, ferie_jour_h, prime1, prime2, avantage_logement, avantage_vehicule, avantage_telephone, avantage_autres, avance_quinzaine, avance_speciale_total, avance_speciale_rembfixe, avance_speciale_restant_prec, autre_ded1, autre_ded2, autre_ded3, autre_ded4, alloc_familiale) FROM stdin;
\.


--
-- Data for Name: type_regimes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.type_regimes (id, code, label, vhm) FROM stdin;
1	TRA	Agricole	200
2	TNA	Non Agricole	173.33
\.


--
-- Data for Name: workers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.workers (id, employer_id, matricule, nom, prenom, sexe, situation_familiale, adresse, telephone, email, cin, cin_delivre_le, cin_lieu, date_embauche, nature_contrat, duree_essai_jours, mode_paiement, rib, banque, bic, cnaps_num, smie_agence, smie_carte_num, etablissement, departement, service, poste, categorie_prof, indice, valeur_point, groupe_preavis, type_sortie, jours_preavis_deja_faits, anciennete_jours, secteur, salaire_base, salaire_horaire, vhm, horaire_hebdo, nombre_enfant, date_naissance, type_regime_id) FROM stdin;
1	1	MT_883EYEYR	Rajaonarivony	Elie	\N	\N	Rue jean laborde 2	\N	\N	\N	\N	\N	\N	\N	0	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	\N	4000000	400000	173.33	46	1	\N	2
2	3	DedeDDEDeDEDED	dededeDe	Eeeeeee	\N	\N	eeeeeeee	\N	\N	\N	\N	\N	\N	\N	0	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	0	0	\N	0	20	200	46	2	\N	1
\.


--
-- Name: employers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.employers_id_seq', 3, true);


--
-- Name: payroll_runs_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payroll_runs_id_seq', 1, false);


--
-- Name: payvars_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.payvars_id_seq', 1, false);


--
-- Name: type_regimes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.type_regimes_id_seq', 2, true);


--
-- Name: workers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.workers_id_seq', 2, true);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: employers employers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employers
    ADD CONSTRAINT employers_pkey PRIMARY KEY (id);


--
-- Name: payroll_runs payroll_runs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT payroll_runs_pkey PRIMARY KEY (id);


--
-- Name: payvars payvars_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payvars
    ADD CONSTRAINT payvars_pkey PRIMARY KEY (id);


--
-- Name: type_regimes type_regimes_code_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.type_regimes
    ADD CONSTRAINT type_regimes_code_key UNIQUE (code);


--
-- Name: type_regimes type_regimes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.type_regimes
    ADD CONSTRAINT type_regimes_pkey PRIMARY KEY (id);


--
-- Name: workers workers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_pkey PRIMARY KEY (id);


--
-- Name: ix_employers_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_employers_id ON public.employers USING btree (id);


--
-- Name: ix_payroll_runs_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payroll_runs_period ON public.payroll_runs USING btree (period);


--
-- Name: ix_payvars_period; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_payvars_period ON public.payvars USING btree (period);


--
-- Name: ix_type_regimes_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_type_regimes_id ON public.type_regimes USING btree (id);


--
-- Name: ix_workers_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_workers_id ON public.workers USING btree (id);


--
-- Name: ix_workers_matricule; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_workers_matricule ON public.workers USING btree (matricule);


--
-- Name: employers employers_type_regime_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.employers
    ADD CONSTRAINT employers_type_regime_id_fkey FOREIGN KEY (type_regime_id) REFERENCES public.type_regimes(id) ON DELETE SET NULL;


--
-- Name: payroll_runs payroll_runs_employer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payroll_runs
    ADD CONSTRAINT payroll_runs_employer_id_fkey FOREIGN KEY (employer_id) REFERENCES public.employers(id);


--
-- Name: payvars payvars_worker_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.payvars
    ADD CONSTRAINT payvars_worker_id_fkey FOREIGN KEY (worker_id) REFERENCES public.workers(id);


--
-- Name: workers workers_employer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workers
    ADD CONSTRAINT workers_employer_id_fkey FOREIGN KEY (employer_id) REFERENCES public.employers(id);


--
-- PostgreSQL database dump complete
--

