--
-- PostgreSQL database dump
--

-- Dumped from database version 14.12
-- Dumped by pg_dump version 14.12

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: metastore_db; Type: SCHEMA; Schema: -; Owner: postgres
--

CREATE SCHEMA metastore_db;


ALTER SCHEMA metastore_db OWNER TO postgres;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: decrypt_email(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.decrypt_email(p_encrypted text, p_key text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RETURN convert_from(decrypt_iv(decode(p_encrypted, 'hex'), p_key::bytea, '0000000000000000'::bytea, 'aes-cbc'), 'UTF8');
END;
$$;


ALTER FUNCTION public.decrypt_email(p_encrypted text, p_key text) OWNER TO postgres;

--
-- Name: encrypt_email(text, text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.encrypt_email(p_email text, p_key text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RETURN encode(encrypt_iv(p_email::bytea, p_key::bytea, '0000000000000000'::bytea, 'aes-cbc'), 'hex');
END;
$$;


ALTER FUNCTION public.encrypt_email(p_email text, p_key text) OWNER TO postgres;

--
-- Name: hash_email(text); Type: FUNCTION; Schema: public; Owner: postgres
--

CREATE FUNCTION public.hash_email(p_email text) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER
    AS $$
BEGIN
    RETURN encode(digest(lower(p_email), 'sha256'), 'hex');
END;
$$;


ALTER FUNCTION public.hash_email(p_email text) OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: analysis_result; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.analysis_result (
    id integer NOT NULL,
    analysis_type character varying(50) NOT NULL,
    city character varying(50),
    task_id integer,
    analysis_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    result_data jsonb NOT NULL
);


ALTER TABLE public.analysis_result OWNER TO postgres;

--
-- Name: analysis_result_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.analysis_result_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.analysis_result_id_seq OWNER TO postgres;

--
-- Name: analysis_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.analysis_result_id_seq OWNED BY public.analysis_result.id;


--
-- Name: city_locks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.city_locks (
    city character varying(50) NOT NULL,
    lock_time timestamp without time zone NOT NULL,
    lock_expiry timestamp without time zone NOT NULL
);


ALTER TABLE public.city_locks OWNER TO postgres;

--
-- Name: crawl_task; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawl_task (
    id integer NOT NULL,
    city character varying(50) NOT NULL,
    city_code character varying(50) NOT NULL,
    start_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    end_time timestamp without time zone,
    status character varying(20) DEFAULT 'In Progress'::character varying NOT NULL,
    total_items integer DEFAULT 0 NOT NULL,
    success_items integer DEFAULT 0 NOT NULL,
    error_message text,
    success_count integer DEFAULT 0,
    success_pages integer DEFAULT 0,
    failed_pages integer DEFAULT 0,
    total_pages integer DEFAULT 0,
    error text,
    planned_pages integer,
    expected_end_time timestamp without time zone,
    queue_position integer DEFAULT 0
);


ALTER TABLE public.crawl_task OWNER TO postgres;

--
-- Name: crawl_task_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crawl_task_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crawl_task_id_seq OWNER TO postgres;

--
-- Name: crawl_task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crawl_task_id_seq OWNED BY public.crawl_task.id;


--
-- Name: crawled_pages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawled_pages (
    id integer NOT NULL,
    task_id integer,
    page_number integer NOT NULL,
    page_url text NOT NULL,
    crawl_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    success boolean DEFAULT false NOT NULL,
    retry_count integer DEFAULT 0,
    error_message text
);


ALTER TABLE public.crawled_pages OWNER TO postgres;

--
-- Name: crawled_pages_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crawled_pages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crawled_pages_id_seq OWNER TO postgres;

--
-- Name: crawled_pages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crawled_pages_id_seq OWNED BY public.crawled_pages.id;


--
-- Name: crawler_lock; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.crawler_lock (
    id integer NOT NULL,
    lock_name character varying(50) NOT NULL,
    is_locked boolean DEFAULT false,
    locked_by character varying(100),
    locked_at timestamp without time zone,
    expires_at timestamp without time zone
);


ALTER TABLE public.crawler_lock OWNER TO postgres;

--
-- Name: crawler_lock_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.crawler_lock_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.crawler_lock_id_seq OWNER TO postgres;

--
-- Name: crawler_lock_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.crawler_lock_id_seq OWNED BY public.crawler_lock.id;


--
-- Name: current_ip; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.current_ip (
    id integer NOT NULL,
    ip text NOT NULL,
    location text,
    isp text,
    country text,
    region text,
    city text,
    last_changed timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.current_ip OWNER TO postgres;

--
-- Name: current_ip_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.current_ip_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.current_ip_id_seq OWNER TO postgres;

--
-- Name: current_ip_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.current_ip_id_seq OWNED BY public.current_ip.id;


--
-- Name: house_info; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.house_info (
    id integer NOT NULL,
    house_id character varying(50) NOT NULL,
    task_id integer NOT NULL,
    title character varying(255) NOT NULL,
    price integer NOT NULL,
    location_qu character varying(50),
    location_big character varying(50),
    location_small character varying(50),
    size double precision,
    direction character varying(50),
    room character varying(50),
    floor character varying(50),
    image character varying(255),
    link character varying(255),
    unit_price double precision,
    room_count integer,
    hall_count integer,
    bath_count integer,
    crawl_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    layout text,
    subway text,
    city_code text,
    publish_date text,
    features text,
    created_at timestamp without time zone,
    last_updated timestamp without time zone
);

ALTER TABLE public.house_info OWNER TO postgres;

--
-- Name: house_info_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.house_info_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.house_info_id_seq OWNER TO postgres;

--
-- Name: house_info_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.house_info_id_seq OWNED BY public.house_info.id;


--
-- Name: ip_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.ip_settings (
    id integer NOT NULL,
    rotation_strategy text DEFAULT 'manual'::text,
    rotation_interval integer DEFAULT 30,
    max_failures integer DEFAULT 3,
    auto_add_proxies boolean DEFAULT false,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.ip_settings OWNER TO postgres;

--
-- Name: ip_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.ip_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ip_settings_id_seq OWNER TO postgres;

--
-- Name: ip_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.ip_settings_id_seq OWNED BY public.ip_settings.id;


--
-- Name: password_resets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.password_resets (
    id integer NOT NULL,
    email_hash character varying(64) NOT NULL,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.password_resets OWNER TO postgres;

--
-- Name: password_resets_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.password_resets_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.password_resets_id_seq OWNER TO postgres;

--
-- Name: password_resets_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.password_resets_id_seq OWNED BY public.password_resets.id;


--
-- Name: proxies; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.proxies (
    id integer NOT NULL,
    ip text NOT NULL,
    port integer NOT NULL,
    username text,
    password text,
    location text,
    status text DEFAULT 'inactive'::text,
    latency integer,
    last_used timestamp without time zone,
    last_checked timestamp without time zone
);


ALTER TABLE public.proxies OWNER TO postgres;

--
-- Name: proxies_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.proxies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.proxies_id_seq OWNER TO postgres;

--
-- Name: proxies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.proxies_id_seq OWNED BY public.proxies.id;


--
-- Name: scheduled_tasks; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.scheduled_tasks (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    city character varying(50) NOT NULL,
    pages integer DEFAULT 5 NOT NULL,
    schedule character varying(100) NOT NULL,
    "time" character varying(10),
    next_run timestamp without time zone,
    status character varying(20) DEFAULT '正常'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone
);


ALTER TABLE public.scheduled_tasks OWNER TO postgres;

--
-- Name: scheduled_tasks_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.scheduled_tasks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.scheduled_tasks_id_seq OWNER TO postgres;

--
-- Name: scheduled_tasks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.scheduled_tasks_id_seq OWNED BY public.scheduled_tasks.id;


--
-- Name: system_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.system_settings (
    id integer NOT NULL,
    settings jsonb NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.system_settings OWNER TO postgres;

--
-- Name: system_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.system_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.system_settings_id_seq OWNER TO postgres;

--
-- Name: system_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.system_settings_id_seq OWNED BY public.system_settings.id;


--
-- Name: user_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_settings (
    user_id integer NOT NULL,
    settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.user_settings OWNER TO postgres;

--
-- Name: user_tokens; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token character varying(255) NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.user_tokens OWNER TO postgres;

--
-- Name: user_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.user_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_tokens_id_seq OWNER TO postgres;

--
-- Name: user_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.user_tokens_id_seq OWNED BY public.user_tokens.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(100) NOT NULL,
    email_hash character varying(64) NOT NULL,
    password_hash character varying(255) NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    is_admin boolean DEFAULT false NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login timestamp without time zone,
    avatar character varying(255) DEFAULT NULL::character varying
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.users_id_seq OWNER TO postgres;

--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: verification_session; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.verification_session (
    id integer NOT NULL,
    task_id integer,
    city_code character varying(20) NOT NULL,
    status character varying(20) NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    verification_url text,
    page_url text,
    cookies_path text,
    error_message text
);


ALTER TABLE public.verification_session OWNER TO postgres;

--
-- Name: verification_session_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.verification_session_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.verification_session_id_seq OWNER TO postgres;

--
-- Name: verification_session_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.verification_session_id_seq OWNED BY public.verification_session.id;


--
-- Name: analysis_result id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_result ALTER COLUMN id SET DEFAULT nextval('public.analysis_result_id_seq'::regclass);


--
-- Name: crawl_task id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_task ALTER COLUMN id SET DEFAULT nextval('public.crawl_task_id_seq'::regclass);


--
-- Name: crawled_pages id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawled_pages ALTER COLUMN id SET DEFAULT nextval('public.crawled_pages_id_seq'::regclass);


--
-- Name: crawler_lock id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_lock ALTER COLUMN id SET DEFAULT nextval('public.crawler_lock_id_seq'::regclass);


--
-- Name: current_ip id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.current_ip ALTER COLUMN id SET DEFAULT nextval('public.current_ip_id_seq'::regclass);


--
-- Name: house_info id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.house_info ALTER COLUMN id SET DEFAULT nextval('public.house_info_id_seq'::regclass);


--
-- Name: ip_settings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ip_settings ALTER COLUMN id SET DEFAULT nextval('public.ip_settings_id_seq'::regclass);


--
-- Name: password_resets id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_resets ALTER COLUMN id SET DEFAULT nextval('public.password_resets_id_seq'::regclass);


--
-- Name: proxies id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proxies ALTER COLUMN id SET DEFAULT nextval('public.proxies_id_seq'::regclass);


--
-- Name: scheduled_tasks id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scheduled_tasks ALTER COLUMN id SET DEFAULT nextval('public.scheduled_tasks_id_seq'::regclass);


--
-- Name: system_settings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_settings ALTER COLUMN id SET DEFAULT nextval('public.system_settings_id_seq'::regclass);


--
-- Name: user_tokens id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tokens ALTER COLUMN id SET DEFAULT nextval('public.user_tokens_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: verification_session id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verification_session ALTER COLUMN id SET DEFAULT nextval('public.verification_session_id_seq'::regclass);


--
-- Data for Name: analysis_result; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.analysis_result (id, analysis_type, city, task_id, analysis_time, result_data) FROM stdin;
\.


--
-- Data for Name: city_locks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.city_locks (city, lock_time, lock_expiry) FROM stdin;
\.


--
-- Data for Name: crawl_task; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crawl_task (id, city, city_code, start_time, end_time, status, total_items, success_items, error_message, success_count, success_pages, failed_pages, total_pages, error, planned_pages, expected_end_time, queue_position) FROM stdin;
\.


--
-- Data for Name: crawled_pages; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crawled_pages (id, task_id, page_number, page_url, crawl_time, success, retry_count, error_message) FROM stdin;
\.


--
-- Data for Name: crawler_lock; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.crawler_lock (id, lock_name, is_locked, locked_by, locked_at, expires_at) FROM stdin;
\.


--
-- Data for Name: current_ip; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.current_ip (id, ip, location, isp, country, region, city, last_changed) FROM stdin;
\.


--
-- Data for Name: house_info; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.house_info (id, house_id, task_id, title, price, location_qu, location_big, location_small, size, direction, room, floor, image, link, unit_price, room_count, hall_count, bath_count, crawl_time, layout, subway, city_code, publish_date, features, created_at, last_updated) FROM stdin;
\.


--
-- Data for Name: ip_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.ip_settings (id, rotation_strategy, rotation_interval, max_failures, auto_add_proxies, last_updated) FROM stdin;
1	manual	30	3	f	2025-05-13 07:11:18.365016
\.


--
-- Data for Name: password_resets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.password_resets (id, email_hash, token, expires_at, created_at) FROM stdin;
\.


--
-- Data for Name: proxies; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.proxies (id, ip, port, username, password, location, status, latency, last_used, last_checked) FROM stdin;
\.


--
-- Data for Name: scheduled_tasks; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.scheduled_tasks (id, name, city, pages, schedule, "time", next_run, status, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: system_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.system_settings (id, settings, updated_at) FROM stdin;
1	{"crawler": {"proxyUrl": null, "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36", "maxRetries": 3, "proxyEnabled": false, "requestInterval": 2.0}, "database": {"host": "localhost", "name": "rental_analysis", "port": 5432, "user": "postgres", "password": null}, "lastUpdated": "2025-05-13T04:34:23.364821"}	2025-05-13 04:35:31.708655
\.


--
-- Data for Name: user_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_settings (user_id, settings, updated_at) FROM stdin;
\.


--
-- Data for Name: user_tokens; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_tokens (id, user_id, token, expires_at, created_at) FROM stdin;
2	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzE2NjM0MX0.pJs-FX-RLOGESlKEFo_ZGwSXYxd3ncL1dVswQvG8fnU	2025-05-13 19:59:01.115646	2025-05-13 03:59:01.228885
3	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzE3NTIzOX0.YirlAxQ_sZ_WhAo5bEqKUoUBKNR6QFILenyd7iZFSdI	2025-05-13 22:27:19.218008	2025-05-13 06:27:19.337144
4	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzE3NTI0N30.Rnz_gvyI52hIc4Gch2fGPbXul_TfoxDc2yCTwHtEe4U	2025-05-13 22:27:27.98501	2025-05-13 06:27:28.104931
5	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzE3NTI1Nn0.-nFXgz0cc0tCjBagjWrLecqrRcqIrk8sLzxUSZTpFC8	2025-05-13 22:27:36.848565	2025-05-13 06:27:36.96248
6	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzE3NTI2Mn0.eNNA1FYV-EX7Lfro_ONiNx4n8YYJNpxACU58MZWj9xk	2025-05-13 22:27:42.303657	2025-05-13 06:27:42.419941
7	1	eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInVzZXJfaWQiOjEsImV4cCI6MTc0NzI4MDA3N30.4Y_AUEooivPaxTN2eYVwxkIn3aSSOAQ1qXUhtbrRYkc	2025-05-15 03:34:37.288444	2025-05-14 11:34:37.288711
\.


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.users (id, username, email, email_hash, password_hash, is_active, is_admin, created_at, last_login, avatar) FROM stdin;
1	admin	4f4414e9975a59a15947883b45b7793ed765e8cbb9e21f01ec948fda366d0bb8	258d8dc916db8cea2cafb6c3cd0cb0246efe061421dbd83ec3a350428cabda4f	$2b$12$Kf2eMGF4MKNZBGhoy.HeMOddKNSHjZPjVeSqUl/Z6djA2UES83Wrq	t	t	2025-05-13 03:22:51.7628	2025-05-14 11:34:37.047943	/static/avatars/admin_20250513042437.png
\.


--
-- Data for Name: verification_session; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.verification_session (id, task_id, city_code, status, created_at, updated_at, verification_url, page_url, cookies_path, error_message) FROM stdin;
\.


--
-- Name: analysis_result_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.analysis_result_id_seq', 1, false);


--
-- Name: crawl_task_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crawl_task_id_seq', 1, false);


--
-- Name: crawled_pages_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crawled_pages_id_seq', 1, false);


--
-- Name: crawler_lock_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.crawler_lock_id_seq', 2, true);


--
-- Name: current_ip_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.current_ip_id_seq', 5, true);


--
-- Name: house_info_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.house_info_id_seq', 1, false);


--
-- Name: ip_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.ip_settings_id_seq', 1, true);


--
-- Name: password_resets_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.password_resets_id_seq', 1, false);


--
-- Name: proxies_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.proxies_id_seq', 1, false);


--
-- Name: scheduled_tasks_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.scheduled_tasks_id_seq', 5, true);


--
-- Name: system_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.system_settings_id_seq', 1, true);


--
-- Name: user_tokens_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.user_tokens_id_seq', 7, true);


--
-- Name: users_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.users_id_seq', 1, true);


--
-- Name: verification_session_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.verification_session_id_seq', 1, false);


--
-- Name: analysis_result analysis_result_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_result
    ADD CONSTRAINT analysis_result_pkey PRIMARY KEY (id);


--
-- Name: city_locks city_locks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.city_locks
    ADD CONSTRAINT city_locks_pkey PRIMARY KEY (city);


--
-- Name: crawl_task crawl_task_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawl_task
    ADD CONSTRAINT crawl_task_pkey PRIMARY KEY (id);


--
-- Name: crawled_pages crawled_pages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawled_pages
    ADD CONSTRAINT crawled_pages_pkey PRIMARY KEY (id);


--
-- Name: crawled_pages crawled_pages_task_id_page_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawled_pages
    ADD CONSTRAINT crawled_pages_task_id_page_number_key UNIQUE (task_id, page_number);


--
-- Name: crawler_lock crawler_lock_lock_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_lock
    ADD CONSTRAINT crawler_lock_lock_name_key UNIQUE (lock_name);


--
-- Name: crawler_lock crawler_lock_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawler_lock
    ADD CONSTRAINT crawler_lock_pkey PRIMARY KEY (id);


--
-- Name: current_ip current_ip_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.current_ip
    ADD CONSTRAINT current_ip_pkey PRIMARY KEY (id);


--
-- Name: house_info house_info_house_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.house_info
    ADD CONSTRAINT house_info_house_id_key UNIQUE (house_id);


--
-- Name: house_info house_info_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.house_info
    ADD CONSTRAINT house_info_pkey PRIMARY KEY (id);


--
-- Name: ip_settings ip_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.ip_settings
    ADD CONSTRAINT ip_settings_pkey PRIMARY KEY (id);


--
-- Name: password_resets password_resets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_pkey PRIMARY KEY (id);


--
-- Name: password_resets password_resets_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.password_resets
    ADD CONSTRAINT password_resets_token_key UNIQUE (token);


--
-- Name: proxies proxies_ip_port_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_ip_port_key UNIQUE (ip, port);


--
-- Name: proxies proxies_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.proxies
    ADD CONSTRAINT proxies_pkey PRIMARY KEY (id);


--
-- Name: scheduled_tasks scheduled_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.scheduled_tasks
    ADD CONSTRAINT scheduled_tasks_pkey PRIMARY KEY (id);


--
-- Name: system_settings system_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.system_settings
    ADD CONSTRAINT system_settings_pkey PRIMARY KEY (id);


--
-- Name: user_settings user_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_pkey PRIMARY KEY (user_id);


--
-- Name: user_tokens user_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tokens
    ADD CONSTRAINT user_tokens_pkey PRIMARY KEY (id);


--
-- Name: user_tokens user_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tokens
    ADD CONSTRAINT user_tokens_token_key UNIQUE (token);


--
-- Name: users users_email_hash_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_hash_key UNIQUE (email_hash);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: users users_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);


--
-- Name: verification_session verification_session_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verification_session
    ADD CONSTRAINT verification_session_pkey PRIMARY KEY (id);


--
-- Name: house_info_url_city_idx; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX house_info_url_city_idx ON public.house_info USING btree (link, city_code);


--
-- Name: analysis_result analysis_result_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.analysis_result
    ADD CONSTRAINT analysis_result_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.crawl_task(id);


--
-- Name: crawled_pages crawled_pages_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.crawled_pages
    ADD CONSTRAINT crawled_pages_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.crawl_task(id);


--
-- Name: house_info house_info_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.house_info
    ADD CONSTRAINT house_info_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.crawl_task(id);


--
-- Name: user_settings user_settings_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_settings
    ADD CONSTRAINT user_settings_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: user_tokens user_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_tokens
    ADD CONSTRAINT user_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: verification_session verification_session_task_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.verification_session
    ADD CONSTRAINT verification_session_task_id_fkey FOREIGN KEY (task_id) REFERENCES public.crawl_task(id);


--
-- PostgreSQL database dump complete
--

