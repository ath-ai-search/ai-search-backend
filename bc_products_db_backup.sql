--
-- PostgreSQL database dump
--

\restrict hpQOM2cyhrp3YlbUEoXTX8dPdMVoQFQS271ORtbzJnEBgmhSYsNVmobzIr5IDtQ

-- Dumped from database version 17.9
-- Dumped by pg_dump version 17.9

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
-- Name: events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.events (
    id bigint NOT NULL,
    event_type character varying(50) NOT NULL,
    product_id character varying(255),
    user_id character varying(50),
    session_id character varying(100) NOT NULL,
    query text,
    "position" integer,
    value real,
    source character varying(50),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.events OWNER TO postgres;

--
-- Name: events_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.events_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.events_id_seq OWNER TO postgres;

--
-- Name: events_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.events_id_seq OWNED BY public.events.id;


--
-- Name: order_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.order_items (
    id bigint NOT NULL,
    order_id character varying(50),
    product_id character varying(255),
    quantity integer DEFAULT 1,
    price real,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.order_items OWNER TO postgres;

--
-- Name: order_items_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.order_items_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.order_items_id_seq OWNER TO postgres;

--
-- Name: order_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.order_items_id_seq OWNED BY public.order_items.id;


--
-- Name: orders; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.orders (
    order_id character varying(50) NOT NULL,
    user_id character varying(50),
    total_amount real,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.orders OWNER TO postgres;

--
-- Name: product_cooccurrence; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_cooccurrence (
    product_id character varying(255) NOT NULL,
    related_product_id character varying(255) NOT NULL,
    score integer DEFAULT 0,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.product_cooccurrence OWNER TO postgres;

--
-- Name: product_metrics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.product_metrics (
    product_id character varying(255) NOT NULL,
    views integer DEFAULT 0,
    impressions integer DEFAULT 0,
    clicks integer DEFAULT 0,
    add_to_cart integer DEFAULT 0,
    wishlist integer DEFAULT 0,
    orders integer DEFAULT 0,
    trending_score real DEFAULT 0,
    top_seller_score real DEFAULT 0,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.product_metrics OWNER TO postgres;

--
-- Name: user_product_scores; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_product_scores (
    user_id character varying(50) NOT NULL,
    product_id character varying(255) NOT NULL,
    score real DEFAULT 0,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.user_product_scores OWNER TO postgres;

--
-- Name: wishlist; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.wishlist (
    id bigint NOT NULL,
    user_id character varying(50),
    product_id character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.wishlist OWNER TO postgres;

--
-- Name: wishlist_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.wishlist_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.wishlist_id_seq OWNER TO postgres;

--
-- Name: wishlist_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.wishlist_id_seq OWNED BY public.wishlist.id;


--
-- Name: events id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events ALTER COLUMN id SET DEFAULT nextval('public.events_id_seq'::regclass);


--
-- Name: order_items id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items ALTER COLUMN id SET DEFAULT nextval('public.order_items_id_seq'::regclass);


--
-- Name: wishlist id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist ALTER COLUMN id SET DEFAULT nextval('public.wishlist_id_seq'::regclass);


--
-- Data for Name: events; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.events (id, event_type, product_id, user_id, session_id, query, "position", value, source, created_at) FROM stdin;
1	search	\N	\N	test-123	test_force_event	\N	\N	\N	2026-04-29 11:38:44.432764
3	search	\N	\N	local-test-001	blue shoes	\N	\N	\N	2026-04-29 11:56:48.150424
8	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:16:09.009343
9	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:18:20.211674
10	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:18:25.764864
11	add_to_cart	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:19:42.05293
12	click	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	1	\N	search	2026-04-29 12:19:42.05293
13	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	water flosser	\N	\N	\N	2026-04-29 12:19:42.05293
14	impression	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	1	\N	search	2026-04-29 12:19:42.05293
15	view	dickies-mens-water-repellent-flannel-hooded-shirt-jacket	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:29:03.399414
16	view	dickies-mens-water-repellent-flannel-hooded-shirt-jacket	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:29:44.222827
18	view	wiholl-womens-long-sleeve-crop-tops-crewneck-pullover-shirts-lightweight-sweatshirts-2024-fall-fashion-clothes	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:32:04.84084
20	view	kgjianda-steel-toe-shoes-for-men-indestructible-work-shoes-for-men-lightweight-mens-steel-toe-sneakers-comfortable-safety-toe-shoes-black-steel-toe-tennis-shoes-construction-safety-shoes	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:35:38.139265
22	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:38:18.800173
23	view	rexing-h2-4k-wi-fi-trail-camera-with-ultra-night-vision-for-hunting-games-and-wildlife-monitoring-green	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:57:40.930937
24	view	alera-bc-46-e-1-6-cu-ft-refrigerator-with-chiller-compartment-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:59:48.669703
25	view	wiholl-womens-long-sleeve-crop-tops-crewneck-pullover-shirts-lightweight-sweatshirts-2024-fall-fashion-clothes	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 13:43:47.384662
26	view	wiholl-womens-long-sleeve-crop-tops-crewneck-pullover-shirts-lightweight-sweatshirts-2024-fall-fashion-clothes	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 13:44:12.36072
30	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	test search	\N	\N	\N	2026-04-29 14:04:26.799336
32	view	apple-geek-squad-certified-refurbished-macbook-air-13-3-laptop-intel-core-i5-8gb-memory-128gb-solid-state-drive-space-gray	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:04:53.480738
33	view	luxury-faux-fur-throw-blanket	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:05:37.576423
37	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	test search	\N	\N	\N	2026-04-29 14:05:55.262556
39	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:13:12.078366
40	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:31:01.864065
41	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:45:52.431222
42	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:46:39.554173
43	add_to_cart	7717	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:48:43.878435
44	add_to_cart	7717	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:48:43.878435
45	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 14:54:40.264338
46	add_to_cart	7717	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 15:05:03.28133
47	add_to_cart	216993	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 15:10:55.747024
\.


--
-- Data for Name: order_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.order_items (id, order_id, product_id, quantity, price, created_at) FROM stdin;
\.


--
-- Data for Name: orders; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.orders (order_id, user_id, total_amount, created_at) FROM stdin;
\.


--
-- Data for Name: product_cooccurrence; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.product_cooccurrence (product_id, related_product_id, score, last_updated) FROM stdin;
\.


--
-- Data for Name: product_metrics; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.product_metrics (product_id, views, impressions, clicks, add_to_cart, wishlist, orders, trending_score, top_seller_score, updated_at) FROM stdin;
dickies-mens-water-repellent-flannel-hooded-shirt-jacket	2	0	0	0	0	0	0.8	0	2026-04-29 15:25:01.661067
216993	0	0	0	1	0	0	0.35	0	2026-04-29 15:25:01.661067
rexing-h2-4k-wi-fi-trail-camera-with-ultra-night-vision-for-hunting-games-and-wildlife-monitoring-green	1	0	0	0	0	0	0.4	0	2026-04-29 15:25:01.661067
waterpik-ultra-water-flosser-classic-blue	4	1	1	1	0	0	1.95	0	2026-04-29 15:25:01.661067
apple-geek-squad-certified-refurbished-macbook-air-13-3-laptop-intel-core-i5-8gb-memory-128gb-solid-state-drive-space-gray	1	0	0	0	0	0	0.4	0	2026-04-29 15:25:01.661067
7717	0	0	0	3	0	0	1.05	0	2026-04-29 15:25:01.661067
alera-bc-46-e-1-6-cu-ft-refrigerator-with-chiller-compartment-black	1	0	0	0	0	0	0.4	0	2026-04-29 15:25:01.661067
wiholl-womens-long-sleeve-crop-tops-crewneck-pullover-shirts-lightweight-sweatshirts-2024-fall-fashion-clothes	3	0	0	0	0	0	1.2	0	2026-04-29 15:25:01.661067
luxury-faux-fur-throw-blanket	1	0	0	0	0	0	0.4	0	2026-04-29 15:25:01.661067
delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	5	0	0	0	0	0	2	0	2026-04-29 15:25:01.661067
kgjianda-steel-toe-shoes-for-men-indestructible-work-shoes-for-men-lightweight-mens-steel-toe-sneakers-comfortable-safety-toe-shoes-black-steel-toe-tennis-shoes-construction-safety-shoes	1	0	0	0	0	0	0.4	0	2026-04-29 15:25:01.661067
\.


--
-- Data for Name: user_product_scores; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.user_product_scores (user_id, product_id, score, last_updated) FROM stdin;
\.


--
-- Data for Name: wishlist; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.wishlist (id, user_id, product_id, created_at) FROM stdin;
\.


--
-- Name: events_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.events_id_seq', 47, true);


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_items_id_seq', 1, false);


--
-- Name: wishlist_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.wishlist_id_seq', 1, false);


--
-- Name: events events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: product_cooccurrence product_cooccurrence_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_cooccurrence
    ADD CONSTRAINT product_cooccurrence_pkey PRIMARY KEY (product_id, related_product_id);


--
-- Name: product_metrics product_metrics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_metrics
    ADD CONSTRAINT product_metrics_pkey PRIMARY KEY (product_id);


--
-- Name: user_product_scores user_product_scores_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_product_scores
    ADD CONSTRAINT user_product_scores_pkey PRIMARY KEY (user_id, product_id);


--
-- Name: wishlist wishlist_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_pkey PRIMARY KEY (id);


--
-- Name: wishlist wishlist_user_id_product_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.wishlist
    ADD CONSTRAINT wishlist_user_id_product_id_key UNIQUE (user_id, product_id);


--
-- Name: idx_event_time; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_event_time ON public.events USING btree (event_type, created_at);


--
-- Name: idx_order; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_order ON public.order_items USING btree (order_id);


--
-- Name: idx_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product ON public.events USING btree (product_id);


--
-- Name: idx_product_oi; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_oi ON public.order_items USING btree (product_id);


--
-- Name: idx_product_pc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_pc ON public.product_cooccurrence USING btree (product_id);


--
-- Name: idx_product_ups; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_ups ON public.user_product_scores USING btree (product_id);


--
-- Name: idx_product_wishlist; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_product_wishlist ON public.wishlist USING btree (product_id);


--
-- Name: idx_related_pc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_related_pc ON public.product_cooccurrence USING btree (related_product_id);


--
-- Name: idx_session; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_session ON public.events USING btree (session_id);


--
-- Name: idx_user; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user ON public.events USING btree (user_id);


--
-- Name: idx_user_orders; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_orders ON public.orders USING btree (user_id);


--
-- Name: idx_user_ups; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_ups ON public.user_product_scores USING btree (user_id);


--
-- Name: idx_user_wishlist; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_user_wishlist ON public.wishlist USING btree (user_id);


--
-- PostgreSQL database dump complete
--

\unrestrict hpQOM2cyhrp3YlbUEoXTX8dPdMVoQFQS271ORtbzJnEBgmhSYsNVmobzIr5IDtQ

