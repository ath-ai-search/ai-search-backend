--
-- PostgreSQL database dump
--

\restrict GkE4UtdsFPr5h1oSDxAvHQrvSm72R8kufaaDNfh5RA5YyXAt0T6H51WoiDSsFK3

-- Dumped from database version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.13 (Ubuntu 16.13-0ubuntu0.24.04.1)

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
    id bigint NOT NULL,
    product_id character varying(255),
    impressions integer,
    views integer,
    clicks integer,
    carts integer,
    purchases integer,
    wishlist integer
);


ALTER TABLE public.product_metrics OWNER TO postgres;

--
-- Name: product_metrics_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.product_metrics_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.product_metrics_id_seq OWNER TO postgres;

--
-- Name: product_metrics_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.product_metrics_id_seq OWNED BY public.product_metrics.id;


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
-- Name: product_metrics id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.product_metrics ALTER COLUMN id SET DEFAULT nextval('public.product_metrics_id_seq'::regclass);


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
48	view	delonghi-nespresso-vertuo-plus-deluxe-coffee-and-espresso-maker-by-delonghi-matte-black-with-aeroccino-milk-frother-matte-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 11:59:51.209102
49	add_to_cart	7717	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:01:46.98849
50	view	jamie-young-co-shoreline-coastal-seagrass-metal-pendant-in-natural	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:02:16.57656
51	view	alpine-8-single-voice-coil-4-ohm-loaded-subwoofer-enclosure-with-integrated-120w-amp-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:04:41.443746
52	add_to_cart	4304	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:05:03.171502
53	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	test query	\N	\N	\N	2026-04-29 12:09:17.778194
54	view	alpine-8-single-voice-coil-4-ohm-loaded-subwoofer-enclosure-with-integrated-120w-amp-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:19:00.675451
55	wishlist	alpine-8-single-voice-coil-4-ohm-loaded-subwoofer-enclosure-with-integrated-120w-amp-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:19:10.109965
56	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	running shoes for men	\N	\N	\N	2026-04-29 12:26:01.415515
57	wishlist	nike-mens-running-shoes-azb0cd2pbbpz-p	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:26:47.095407
58	view	nike-mens-running-shoes-azb0cd2pbbpz-p	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:27:43.293732
59	view	coavoo-sbr20-39-37-inch-1000mm-2pcs-linear-rails-4pcs-20mm-sbr20uu-bearing-blocks-20mm-linear-motion-slide-guide-rails-with-ball-bearings-sliding-block-as-heavy-duty-cnc-kit	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:28:59.120648
60	wishlist	coavoo-sbr20-39-37-inch-1000mm-2pcs-linear-rails-4pcs-20mm-sbr20uu-bearing-blocks-20mm-linear-motion-slide-guide-rails-with-ball-bearings-sliding-block-as-heavy-duty-cnc-kit	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:29:09.40228
61	view	coavoo-sbr20-39-37-inch-1000mm-2pcs-linear-rails-4pcs-20mm-sbr20uu-bearing-blocks-20mm-linear-motion-slide-guide-rails-with-ball-bearings-sliding-block-as-heavy-duty-cnc-kit	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:29:53.560753
62	view	coavoo-sbr20-39-37-inch-1000mm-2pcs-linear-rails-4pcs-20mm-sbr20uu-bearing-blocks-20mm-linear-motion-slide-guide-rails-with-ball-bearings-sliding-block-as-heavy-duty-cnc-kit	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:31:22.534294
63	wishlist	coavoo-sbr20-39-37-inch-1000mm-2pcs-linear-rails-4pcs-20mm-sbr20uu-bearing-blocks-20mm-linear-motion-slide-guide-rails-with-ball-bearings-sliding-block-as-heavy-duty-cnc-kit	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:31:32.236793
64	view	athmile-womens-long-sleeve-color-block-sweatshirt-fall-2024-casual-oversized-knitted-crewneck-pullover-shirts	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:39:55.514718
65	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men	\N	\N	\N	2026-04-29 12:40:09.347704
66	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men	\N	\N	\N	2026-04-29 12:40:31.165133
67	add_to_cart	285911	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:40:50.870088
68	wishlist	kgjianda-steel-toe-shoes-for-men-indestructible-work-shoes-for-men-lightweight-mens-steel-toe-sneakers-comfortable-safety-toe-shoes-black-steel-toe-tennis-shoes-construction-safety-shoes	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:41:05.146351
69	view	tanming-womens-high-waist-pleated-long-denim-skirt	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:48:44.465657
70	add_to_cart	202609	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:49:22.132017
71	wishlist	tanming-womens-high-waist-pleated-long-denim-skirt	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:49:40.458465
72	view	tanming-womens-high-waist-pleated-long-denim-skirt	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-29 12:52:39.221341
73	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	dress for boy	\N	\N	\N	2026-04-30 04:40:30.831225
74	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	dress for women	\N	\N	\N	2026-04-30 04:58:42.718695
75	add_to_cart	365312	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 05:02:06.403815
77	add_to_cart	180006	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 05:09:27.587507
79	view	epson-expression-premium-wireless-color-photo-printer-with-adf-scanner-and-copier-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 05:14:26.078348
80	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men	\N	\N	\N	2026-04-30 05:15:25.686229
81	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men casual	\N	\N	\N	2026-04-30 05:23:49.865818
82	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men casual	\N	\N	\N	2026-04-30 05:25:17.557082
83	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men casual	\N	\N	\N	2026-04-30 05:26:31.553377
84	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men casual	\N	\N	\N	2026-04-30 05:27:17.472805
85	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men casual	\N	\N	\N	2026-04-30 05:29:19.236645
86	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes	\N	\N	\N	2026-04-30 05:33:33.370733
87	view	epson-expression-premium-wireless-color-photo-printer-with-adf-scanner-and-copier-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:04:22.557548
88	add_to_cart	53785	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:04:58.272647
89	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:28:53.564771
90	view	asus-rog-strix-go-2-4-electro-punk-wireless-gaming-headphones-with-usb-c-2-4-ghz-adapter-ai-powered-noise-cancelling-microphone-over-ear-headphones-for-pc-mac-nintendo-switch-and-ps4	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:29:59.748286
91	wishlist	46808	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:30:05.478775
92	add_to_cart	46808	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:30:18.08614
93	wishlist	46808	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:30:18.086145
94	view	best-sellers	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:33:06.78223
95	click	faherty-mens-legend-sweater-shirt-azb0cqh751db-p	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	browse	2026-04-30 06:33:10.503417
96	add_to_cart	239084	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:33:34.497701
97	wishlist	239084	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:33:40.799328
98	wishlist	239084	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:33:57.152995
99	view	osp-home-furnishings-megan-office-chair-blue-brushed-grey	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:44:38.667105
100	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes	\N	\N	\N	2026-04-30 06:48:06.657013
101	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes	\N	\N	\N	2026-04-30 06:48:34.192759
102	view	yarnow-kickboxing-shoes-men-s-kung-fu-shoes-taichi-training-shoes-breathable-comfortable-cotton-sole	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:50:26.275328
103	view	yarnow-kickboxing-shoes-men-s-kung-fu-shoes-taichi-training-shoes-breathable-comfortable-cotton-sole	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:51:12.894636
104	view	yarnow-kickboxing-shoes-men-s-kung-fu-shoes-taichi-training-shoes-breathable-comfortable-cotton-sole	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 06:51:53.204834
105	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:00:06.847975
106	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:02:51.110951
107	add_to_cart	6725	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:03:57.116595
108	wishlist	6725	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:04:02.822754
109	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:11:20.015857
110	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:13:40.771761
111	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:14:52.274148
112	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:20:10.17284
113	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes for men	\N	\N	\N	2026-04-30 07:22:57.438201
114	click	279300	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	3	\N	browse	2026-04-30 07:23:02.884161
115	add_to_cart	279300	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:23:39.188155
116	wishlist	279300	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:23:48.882554
117	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 07:26:14.029408
118	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:23:51.38353
119	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:24:48.990986
120	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:27:53.264163
121	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:29:18.036255
122	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:32:24.020811
123	view	yccafgaanm-fashion-letter-cute-brooch-women-men-rhinestone-silver-color-metal-pin-suit-shirt-jewelry-accessories-color-h-g	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:47:29.306941
124	add_to_cart	117360	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:48:33.009973
125	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:55:01.967028
126	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:57:24.088761
127	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:58:04.491873
128	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:58:29.153308
129	view	waterpik-ultra-water-flosser-classic-blue	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:59:11.776511
130	add_to_cart	6725	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 08:59:49.249623
131	add_to_cart	6725	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:00:17.554239
132	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:01:18.499824
133	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:01:51.147673
134	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:09:05.231489
135	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:11:54.073006
136	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:13:42.603806
137	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:16:17.007439
138	view	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:19:09.384674
139	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:26:40.725197
140	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:28:07.162155
141	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:32:12.769693
142	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:39:36.009992
143	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:45:11.059059
144	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:47:43.751322
145	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:48:05.122641
146	view	jbl-xtreme-2-portable-bluetooth-speaker-black	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 09:54:43.441222
147	search	\N	\N	39e4e450-5e6b-487b-805e-87177fb641b3	shoes	\N	\N	\N	2026-04-30 10:00:06.867896
148	click	278063	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	2	\N	browse	2026-04-30 10:00:10.597485
149	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 10:00:40.800184
150	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	\N	\N	pdp	2026-04-30 10:05:57.350782
151	impression	259384	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	1	\N	\N	2026-04-30 10:05:57.366112
152	impression	258886	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	2	\N	\N	2026-04-30 10:05:57.366118
153	impression	278116	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	3	\N	\N	2026-04-30 10:05:57.36612
154	impression	258845	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	4	\N	\N	2026-04-30 10:05:57.366122
155	impression	258885	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	5	\N	\N	2026-04-30 10:05:57.366124
156	impression	259243	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	6	\N	\N	2026-04-30 10:05:57.366125
157	impression	259379	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	7	\N	\N	2026-04-30 10:05:57.366127
158	impression	259258	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	8	\N	\N	2026-04-30 10:05:57.366129
159	impression	258917	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	9	\N	\N	2026-04-30 10:06:03.080478
160	impression	259261	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	10	\N	\N	2026-04-30 10:06:03.080483
161	impression	278229	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	11	\N	\N	2026-04-30 10:06:03.080485
162	impression	258918	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	12	\N	\N	2026-04-30 10:06:03.080487
163	impression	259220	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	13	\N	\N	2026-04-30 10:06:03.080489
164	impression	259397	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	14	\N	\N	2026-04-30 10:06:03.080491
165	impression	278050	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	15	\N	\N	2026-04-30 10:06:03.080492
166	impression	166489	\N	39e4e450-5e6b-487b-805e-87177fb641b3	\N	16	\N	\N	2026-04-30 10:06:03.080494
167	impression	330113	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:16:38.810359
168	impression	314747	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:16:38.810365
169	impression	314801	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:16:38.810367
170	impression	330109	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:16:38.810368
171	impression	314195	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:16:38.81037
172	impression	330093	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:16:38.810372
173	impression	311978	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:16:38.810374
174	impression	330103	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:16:38.810375
175	impression	259384	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:16:38.846106
176	impression	258886	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:16:38.846111
177	impression	278116	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:16:38.846113
178	impression	258845	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:16:38.846115
179	impression	258885	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:16:38.846117
180	impression	259243	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:16:38.846119
181	impression	259379	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:16:38.84612
182	impression	259258	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:16:38.846122
183	impression	258917	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:17:36.566295
184	impression	259261	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:17:36.5663
185	impression	278229	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	11	\N	\N	2026-04-30 10:17:36.566302
186	impression	258918	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	12	\N	\N	2026-04-30 10:17:36.566304
187	impression	259220	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	13	\N	\N	2026-04-30 10:17:36.566306
188	impression	259397	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	14	\N	\N	2026-04-30 10:17:36.566307
189	impression	278050	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	15	\N	\N	2026-04-30 10:17:36.566309
190	impression	166489	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	16	\N	\N	2026-04-30 10:17:36.566311
191	impression	278228	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	17	\N	\N	2026-04-30 10:19:14.562378
192	impression	166091	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	18	\N	\N	2026-04-30 10:19:14.562383
193	impression	161526	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	19	\N	\N	2026-04-30 10:19:14.562385
194	impression	162163	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	20	\N	\N	2026-04-30 10:19:14.562387
195	impression	179873	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	21	\N	\N	2026-04-30 10:19:14.562389
196	impression	110029	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	22	\N	\N	2026-04-30 10:19:14.562391
197	impression	280491	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	23	\N	\N	2026-04-30 10:19:14.562392
198	impression	278226	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	24	\N	\N	2026-04-30 10:19:14.562394
199	impression	164923	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	25	\N	\N	2026-04-30 10:19:22.565388
200	impression	161403	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	26	\N	\N	2026-04-30 10:19:22.565393
201	impression	330369	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	27	\N	\N	2026-04-30 10:19:22.565395
202	impression	110022	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	28	\N	\N	2026-04-30 10:19:22.565397
203	impression	164306	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	29	\N	\N	2026-04-30 10:19:22.565398
204	impression	259257	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	30	\N	\N	2026-04-30 10:19:22.5654
205	impression	259255	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	31	\N	\N	2026-04-30 10:19:22.565402
206	impression	278296	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	32	\N	\N	2026-04-30 10:19:22.565404
207	impression	259256	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	33	\N	\N	2026-04-30 10:19:36.570611
208	impression	166586	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	34	\N	\N	2026-04-30 10:19:36.570616
209	impression	162310	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	35	\N	\N	2026-04-30 10:19:36.570618
210	impression	84970	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	36	\N	\N	2026-04-30 10:19:36.570619
211	impression	161975	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	37	\N	\N	2026-04-30 10:19:36.570621
212	impression	85161	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	38	\N	\N	2026-04-30 10:19:36.570623
213	impression	165707	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	39	\N	\N	2026-04-30 10:19:36.570625
214	impression	163148	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	40	\N	\N	2026-04-30 10:19:36.570626
215	impression	280465	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	41	\N	\N	2026-04-30 10:19:38.580901
216	impression	109998	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	42	\N	\N	2026-04-30 10:19:38.580929
217	impression	102503	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	43	\N	\N	2026-04-30 10:19:38.580933
218	impression	110004	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	44	\N	\N	2026-04-30 10:19:38.580936
219	impression	164800	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	45	\N	\N	2026-04-30 10:19:38.580939
220	impression	162109	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	46	\N	\N	2026-04-30 10:19:38.580941
221	impression	102560	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	47	\N	\N	2026-04-30 10:19:38.580943
222	impression	102596	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	48	\N	\N	2026-04-30 10:19:38.580945
223	impression	161548	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	49	\N	\N	2026-04-30 10:19:42.578565
224	impression	109962	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	50	\N	\N	2026-04-30 10:19:42.57857
225	impression	163853	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	51	\N	\N	2026-04-30 10:19:42.578572
226	impression	85102	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	52	\N	\N	2026-04-30 10:19:42.578573
227	impression	160787	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	53	\N	\N	2026-04-30 10:19:42.578575
228	impression	330309	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	54	\N	\N	2026-04-30 10:19:42.578577
229	impression	161535	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	55	\N	\N	2026-04-30 10:19:42.578578
230	impression	165614	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	56	\N	\N	2026-04-30 10:19:42.57858
231	impression	164798	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	57	\N	\N	2026-04-30 10:19:52.561178
232	impression	259402	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	58	\N	\N	2026-04-30 10:19:52.561183
233	impression	280394	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	59	\N	\N	2026-04-30 10:19:52.561185
234	impression	163694	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	60	\N	\N	2026-04-30 10:19:52.561187
235	impression	163626	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	61	\N	\N	2026-04-30 10:19:52.561188
236	impression	102493	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	62	\N	\N	2026-04-30 10:19:52.56119
237	impression	85143	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	63	\N	\N	2026-04-30 10:19:52.561192
238	impression	324946	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	64	\N	\N	2026-04-30 10:19:52.561194
239	impression	259384	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:23:41.788279
240	impression	258886	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:23:41.788301
241	impression	278116	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:23:41.788306
242	impression	258845	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:23:41.788309
243	impression	258885	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:23:41.788312
244	impression	259243	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:23:41.788316
245	impression	259379	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:23:41.788319
246	impression	259258	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:23:41.788323
247	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:23:41.800699
248	view	adidas-unisex-adult-dame-extply-2	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:23:43.446303
249	impression	330113	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:23:43.450595
250	impression	314747	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:23:43.4506
251	impression	314801	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:23:43.450602
252	impression	330109	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:23:43.450604
253	impression	314195	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:23:43.450606
254	impression	330093	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:23:43.450607
255	impression	311978	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:23:43.450609
256	impression	330103	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:23:43.450611
257	impression	258917	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:24:01.858675
258	impression	259261	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:24:01.858765
259	impression	278229	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	11	\N	\N	2026-04-30 10:24:01.858772
260	impression	258918	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	12	\N	\N	2026-04-30 10:24:01.858775
261	impression	259220	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	13	\N	\N	2026-04-30 10:24:01.858779
262	impression	259397	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	14	\N	\N	2026-04-30 10:24:01.858783
263	impression	278050	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	15	\N	\N	2026-04-30 10:24:01.858785
264	impression	166489	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	16	\N	\N	2026-04-30 10:24:01.858788
265	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	shoes	\N	\N	\N	2026-04-30 10:25:04.219109
266	click	279300	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	browse	2026-04-30 10:29:58.508684
267	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:30:25.024941
268	impression	259384	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:30:25.028718
269	impression	258886	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:30:25.028723
270	impression	278116	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:30:25.028725
271	impression	258845	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:30:25.028727
272	impression	258885	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:30:25.028729
273	impression	259243	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:30:25.028731
274	impression	259379	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:30:25.028732
275	impression	259258	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:30:25.028734
276	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:30:25.70239
277	impression	279588	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:30:26.013697
278	impression	285911	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:30:26.013703
279	impression	280135	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:30:26.013704
280	impression	286078	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:30:26.013706
281	impression	285116	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:30:26.013708
282	impression	280082	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:30:26.01371
283	impression	345425	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:30:26.013711
284	impression	347716	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:30:26.013713
285	impression	279456	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:30:47.718867
286	impression	286122	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:30:47.718873
287	impression	347654	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:30:47.718875
288	impression	285813	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:30:47.718877
289	impression	285640	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:30:47.718879
290	impression	286095	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:30:47.718882
291	impression	279284	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:30:47.718884
292	impression	286022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:30:47.718886
293	impression	345424	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:30:51.719148
294	impression	286335	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:30:51.719154
295	impression	285671	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:30:51.719156
296	impression	345426	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:30:51.719158
297	impression	279337	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 10:30:51.719159
298	impression	347664	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 10:30:51.719161
299	impression	286021	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 10:30:51.719163
300	impression	279270	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 10:30:51.719165
301	impression	364911	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 10:30:55.719188
302	impression	347697	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 10:30:55.719193
303	impression	285492	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 10:30:55.719195
304	impression	285440	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 10:30:55.719197
305	impression	286104	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 10:30:55.719199
306	impression	285792	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 10:30:55.719201
307	impression	345431	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 10:30:55.719203
308	impression	286318	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 10:30:55.719204
309	impression	279704	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 10:31:55.726539
310	impression	279457	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 10:31:55.726544
311	impression	279789	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 10:31:55.726546
312	impression	279612	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 10:31:55.726548
313	impression	285850	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 10:31:55.726549
314	impression	285084	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 10:31:55.726551
315	impression	279678	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 10:31:55.726553
316	impression	286238	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 10:31:55.726555
317	impression	279456	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:44:36.512775
318	impression	347654	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:44:36.512781
319	impression	345426	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:44:36.512783
320	impression	279612	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:44:36.512785
321	impression	285084	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:44:36.512787
322	impression	279391	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:44:36.512789
323	impression	286227	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:44:36.51279
324	impression	286246	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:44:36.512792
325	impression	285731	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:44:36.512794
326	impression	286058	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:44:36.512796
327	impression	286267	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:44:36.512798
328	impression	286258	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:44:36.512799
329	impression	286090	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:44:36.512801
330	impression	285857	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:44:36.512803
331	impression	285095	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:44:36.512805
332	impression	286019	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:44:36.512806
333	impression	286156	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:44:36.512808
334	impression	345457	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:44:36.51281
335	impression	364885	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:44:36.512812
336	impression	280124	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:44:36.512814
337	view	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:44:36.518346
338	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:44:38.0567
339	impression	330369	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:44:38.063807
340	impression	109998	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:44:38.063812
341	impression	330309	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:44:38.063814
342	impression	280006	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:44:38.063816
343	impression	14417	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:44:38.063818
344	impression	330322	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:44:38.063819
345	impression	328529	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:44:38.063821
346	impression	249773	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:44:38.063823
347	impression	179356	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:44:38.063825
348	impression	320841	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:44:38.063826
349	click	adrianna-papell-womens-embroidered-sheath-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 10:45:16.182135
350	view	exlura-womens-casual-long-sleeve-sweatshirts-hoodies-loose-button-pullover-top-trendy-fall-outfits-with-pocket	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:46:09.686474
351	impression	178768	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:46:09.694769
352	impression	178767	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:46:09.694775
353	impression	178536	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:46:09.694777
354	impression	328976	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:46:09.694779
355	impression	320934	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:46:09.694781
356	impression	178091	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:46:09.694783
357	impression	354407	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:46:09.694785
358	impression	178893	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:46:09.694787
359	impression	320998	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:46:09.694789
360	impression	178971	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:46:09.694791
361	impression	178701	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:46:19.693433
362	impression	181301	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:46:19.693438
363	impression	179040	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:46:19.69344
364	impression	178282	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:46:19.693442
365	impression	328986	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:46:19.693444
366	impression	328982	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:46:19.693445
367	impression	328948	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:46:19.693447
368	impression	178885	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:46:19.693449
369	impression	178811	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:46:19.69345
370	impression	318805	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:46:19.693452
371	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:46:39.449977
372	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:46:39.734387
373	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:46:39.734393
374	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:46:39.734395
375	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:46:39.734397
376	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:46:39.734398
377	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:46:39.7344
378	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:46:39.734402
379	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:46:39.734404
380	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:46:39.734405
381	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:46:39.734407
392	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:47:20.511782
403	impression	324921	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:47:24.522141
404	impression	273518	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:47:24.522146
405	impression	358361	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:47:24.522148
406	impression	367922	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:47:24.52215
407	impression	6169	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:47:24.522152
408	impression	358866	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:47:24.522154
409	impression	2770	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:47:24.522155
410	impression	271019	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:47:24.522157
411	impression	272939	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:47:24.522159
412	impression	323022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:47:24.52216
414	impression	324921	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:49:16.81381
415	impression	273518	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:49:16.813815
416	impression	358361	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:49:16.813817
417	impression	367922	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:49:16.813819
418	impression	6169	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:49:16.81382
419	impression	358866	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:49:16.813822
420	impression	2770	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:49:16.813824
421	impression	271019	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:49:16.813825
422	impression	272939	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:49:16.813827
423	impression	323022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:49:16.813829
424	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:49:16.813831
425	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:49:16.813832
426	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:49:16.813834
427	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:49:16.813836
428	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:49:16.813837
429	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:49:16.813839
430	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:49:16.813841
431	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:49:16.813842
432	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:49:16.813844
433	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:49:16.813846
434	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:49:17.765431
445	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:52:19.0636
456	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:53:13.040664
467	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:53:13.811006
382	impression	324921	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:46:57.44576
383	impression	273518	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:46:57.445765
384	impression	358361	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:46:57.445767
385	impression	367922	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:46:57.445768
386	impression	6169	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:46:57.44577
387	impression	358866	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:46:57.445772
388	impression	2770	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:46:57.445774
389	impression	271019	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:46:57.445775
390	impression	272939	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:46:57.445777
391	impression	323022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:46:57.445779
393	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:47:20.78604
394	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:47:20.786045
395	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:47:20.786047
396	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:47:20.786048
397	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:47:20.78605
398	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:47:20.786052
399	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:47:20.786053
400	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:47:20.786055
401	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:47:20.786057
402	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:47:20.786059
413	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:49:16.795487
435	impression	330369	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:49:17.768028
436	impression	109998	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:49:17.768033
437	impression	330309	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:49:17.768035
438	impression	280006	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:49:17.768037
439	impression	14417	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:49:17.768039
440	impression	330322	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:49:17.76804
441	impression	328529	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:49:17.768042
442	impression	249773	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:49:17.768044
443	impression	179356	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:49:17.768046
444	impression	320841	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:49:17.768047
446	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:52:19.073035
447	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:52:19.07304
448	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:52:19.073042
449	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:52:19.073044
450	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:52:19.073046
451	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:52:19.073048
452	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:52:19.073049
453	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:52:19.073051
454	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:52:19.073053
455	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:52:19.073055
457	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:53:13.050454
458	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:53:13.05046
459	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:53:13.050462
460	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:53:13.050464
461	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:53:13.050468
462	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:53:13.050472
463	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:53:13.050476
464	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:53:13.05048
465	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:53:13.050483
466	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:53:13.050487
468	impression	330369	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:53:13.821317
469	impression	109998	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:53:13.821322
470	impression	330309	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:53:13.821324
471	impression	280006	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:53:13.821326
472	impression	14417	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:53:13.821328
473	impression	330322	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:53:13.82133
474	impression	328529	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:53:13.821332
475	impression	249773	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:53:13.821333
476	impression	179356	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:53:13.821335
477	impression	320841	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:53:13.821337
478	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:53:58.653825
479	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:53:58.664809
480	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:53:58.664814
481	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:53:58.664816
482	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:53:58.664817
483	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:53:58.664819
484	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:53:58.664821
485	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:53:58.664823
486	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:53:58.664824
487	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:53:58.664826
488	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:53:58.664828
489	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:54:01.788716
490	impression	330369	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:54:01.836361
491	impression	109998	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:54:01.836365
492	impression	330309	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:54:01.836367
493	impression	280006	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:54:01.836369
494	impression	14417	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:54:01.836371
495	impression	330322	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:54:01.836373
496	impression	328529	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:54:01.836375
497	impression	249773	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:54:01.836376
498	impression	179356	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:54:01.836378
499	impression	320841	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:54:01.83638
500	impression	5144	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:55:31.976464
501	impression	2669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:55:31.976472
502	impression	7296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:55:31.976476
503	impression	386883	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:55:31.976479
504	impression	5742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:55:31.976482
505	impression	11312	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:55:31.976486
506	impression	359279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:55:31.976489
507	impression	343661	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:55:31.976492
508	impression	2161	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:55:31.976495
509	impression	353209	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:55:31.976499
510	view	insignia-usb-microphone-bb6328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:55:31.985672
511	click	202595	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	browse	2026-04-30 10:55:55.893799
512	impression	202753	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 10:56:03.631146
513	impression	266496	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 10:56:03.631151
514	impression	202606	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 10:56:03.631153
515	impression	267833	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 10:56:03.631155
516	impression	266792	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 10:56:03.631156
517	impression	202897	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 10:56:03.631158
518	impression	266719	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 10:56:03.63116
519	impression	202719	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 10:56:03.631162
520	impression	328537	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 10:56:03.631163
521	impression	202577	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 10:56:03.631165
522	impression	268043	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 10:56:07.611276
523	impression	266473	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 10:56:07.611282
524	impression	266446	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 10:56:07.611284
525	impression	202735	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 10:56:07.611285
526	impression	202569	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 10:56:07.611287
527	impression	202615	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 10:56:07.611289
528	impression	202746	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 10:56:07.611291
529	impression	202776	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 10:56:07.611293
530	impression	202602	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 10:56:07.611295
531	impression	202909	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 10:56:07.611296
532	view	womens-tulle-skirt-long-black-layered-maxi-midi-high-low-skirts-for-special-occasion-women	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:56:40.497679
533	impression	266418	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 10:56:40.518059
534	impression	202769	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 10:56:40.518064
535	impression	266461	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 10:56:40.518066
536	impression	320976	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 10:56:40.518067
537	impression	267841	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 10:56:40.518069
538	impression	202901	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 10:56:40.518071
539	impression	202833	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 10:56:40.518072
540	impression	266444	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 10:56:40.518074
541	impression	202674	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 10:56:40.518076
542	impression	275303	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 10:56:40.518077
543	impression	202686	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 10:56:40.518079
544	impression	202925	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 10:56:40.518081
545	impression	267247	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 10:56:40.518082
546	impression	202715	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 10:56:40.518084
547	impression	267675	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 10:56:40.518086
548	impression	266477	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 10:56:40.518087
549	impression	266541	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 10:56:40.518089
550	impression	202921	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 10:56:40.518091
551	impression	202727	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 10:56:40.518092
552	impression	202603	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 10:56:40.518094
553	add_to_cart	202595	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 10:57:58.77426
554	view	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	\N	\N	pdp	2026-04-30 10:59:07.510325
555	impression	259384	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	1	\N	\N	2026-04-30 10:59:07.545695
556	impression	258886	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	2	\N	\N	2026-04-30 10:59:07.545701
557	impression	278116	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	3	\N	\N	2026-04-30 10:59:07.545703
558	impression	258845	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	4	\N	\N	2026-04-30 10:59:07.545706
559	impression	258885	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	5	\N	\N	2026-04-30 10:59:07.545708
560	impression	259243	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	6	\N	\N	2026-04-30 10:59:07.545709
561	impression	259379	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	7	\N	\N	2026-04-30 10:59:07.545711
562	impression	259258	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	8	\N	\N	2026-04-30 10:59:07.545714
563	impression	258917	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	9	\N	\N	2026-04-30 10:59:07.545717
564	impression	259261	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	10	\N	\N	2026-04-30 10:59:07.54572
565	impression	278229	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	11	\N	\N	2026-04-30 10:59:43.195857
566	impression	258918	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	12	\N	\N	2026-04-30 10:59:43.195862
567	impression	259220	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	13	\N	\N	2026-04-30 10:59:43.195865
568	impression	259397	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	14	\N	\N	2026-04-30 10:59:43.195866
569	impression	278050	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	15	\N	\N	2026-04-30 10:59:43.195868
570	impression	166489	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	16	\N	\N	2026-04-30 10:59:43.19587
571	impression	278228	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	17	\N	\N	2026-04-30 10:59:43.195872
572	impression	166091	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	18	\N	\N	2026-04-30 10:59:43.195874
573	impression	161526	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	19	\N	\N	2026-04-30 10:59:43.195875
574	impression	162163	\N	73924bed-c859-4a61-8e07-e0a4ed2eb63e	\N	20	\N	\N	2026-04-30 10:59:43.195877
575	click	202927	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	browse	2026-04-30 11:00:37.139066
576	impression	268609	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:00:44.83485
577	impression	268258	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:00:44.834855
578	impression	268387	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:00:44.834857
579	impression	267803	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:00:44.834859
580	impression	268081	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:00:44.834861
581	impression	263185	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:00:44.834863
582	impression	268352	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:00:44.834864
583	impression	268559	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:00:44.834866
584	impression	261475	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:00:44.834868
585	impression	262302	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:00:44.834869
586	impression	268419	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:01:06.983219
587	impression	202810	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:01:06.983224
588	impression	268165	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:01:06.983226
589	impression	202795	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:01:06.983228
590	impression	268324	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:01:06.98323
591	impression	266887	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:01:06.983232
592	impression	268510	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:01:06.983233
593	impression	267091	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:01:06.983235
594	impression	268201	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:01:06.983237
595	impression	267479	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:01:06.983239
596	view	astr-the-label-womens-divine-skirt	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:01:07.005947
597	impression	268609	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:01:14.979547
598	impression	268258	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:01:14.979553
599	impression	268387	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:01:14.979555
600	impression	267803	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:01:14.979557
601	impression	268081	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:01:14.979558
602	impression	263185	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:01:14.97956
603	impression	268352	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:01:14.979562
604	impression	268559	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:01:14.979563
605	impression	261475	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:01:14.979565
606	impression	262302	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:01:14.979567
607	impression	262743	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 11:01:18.98572
608	impression	261785	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 11:01:18.985725
609	impression	261604	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 11:01:18.985727
610	impression	260590	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 11:01:18.985728
611	impression	268241	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 11:01:18.98573
612	impression	267577	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 11:01:18.985732
613	impression	266656	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 11:01:18.985734
614	impression	202782	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 11:01:18.985735
615	impression	267858	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 11:01:18.985737
616	impression	202558	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 11:01:18.985739
617	impression	267108	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 11:01:20.975582
618	impression	267058	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 11:01:20.975587
619	impression	202618	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 11:01:20.975589
620	impression	202933	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 11:01:20.97559
621	impression	250018	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 11:01:20.975592
622	impression	268019	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 11:01:20.975594
623	impression	268519	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 11:01:20.975596
624	impression	202905	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 11:01:20.975597
625	impression	268397	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 11:01:20.975599
626	impression	267279	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 11:01:20.975601
627	impression	258053	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	51	\N	\N	2026-04-30 11:01:22.977509
628	impression	268789	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	52	\N	\N	2026-04-30 11:01:22.977515
629	impression	268734	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	53	\N	\N	2026-04-30 11:01:22.977517
630	impression	267223	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	54	\N	\N	2026-04-30 11:01:22.977519
631	impression	268456	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	55	\N	\N	2026-04-30 11:01:22.977521
632	impression	268200	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	56	\N	\N	2026-04-30 11:01:22.977522
633	impression	266694	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	57	\N	\N	2026-04-30 11:01:22.977524
634	impression	202770	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	58	\N	\N	2026-04-30 11:01:22.977526
635	impression	249982	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	59	\N	\N	2026-04-30 11:01:22.977528
636	impression	266424	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	60	\N	\N	2026-04-30 11:01:22.977529
647	impression	202711	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	81	\N	\N	2026-04-30 11:01:28.972
648	impression	202706	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	82	\N	\N	2026-04-30 11:01:28.972006
649	impression	268436	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	83	\N	\N	2026-04-30 11:01:28.972008
650	impression	297300	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	84	\N	\N	2026-04-30 11:01:28.972009
651	impression	266597	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	85	\N	\N	2026-04-30 11:01:28.972011
652	impression	202764	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	86	\N	\N	2026-04-30 11:01:28.972013
653	impression	202557	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	87	\N	\N	2026-04-30 11:01:28.972015
654	impression	266642	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	88	\N	\N	2026-04-30 11:01:28.972016
655	impression	268499	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	89	\N	\N	2026-04-30 11:01:28.972018
656	impression	268517	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	90	\N	\N	2026-04-30 11:01:28.97202
658	view	unisex-kung-fu-martial-arts-tai-chi-trainer-shoes-chinese-tai-chi-wu-shu-shoes-leather-taekwondo-shoes-martial-arts-boxing-shoes	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:03:29.156078
669	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	shoes	\N	\N	\N	2026-04-30 11:21:10.301084
672	click	popilush-shapewear-dress-ruched-bodycon-deep-v-neck-maxi-formal-dresses-built-in-shapewear-sleeveless-long-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 11:22:17.892027
678	impression	320782	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:22:29.617357
679	impression	320806	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:22:29.617362
680	impression	320803	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:22:29.617364
681	impression	354589	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:22:29.617366
682	impression	266793	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:22:29.617367
683	impression	320798	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:22:29.617369
684	impression	320808	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:22:29.617371
685	impression	320807	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:22:29.617373
686	impression	202669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:22:29.617374
687	impression	320781	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:22:29.617376
637	impression	264089	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	61	\N	\N	2026-04-30 11:01:27.253553
638	impression	268455	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	62	\N	\N	2026-04-30 11:01:27.253558
639	impression	202746	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	63	\N	\N	2026-04-30 11:01:27.25356
640	impression	327567	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	64	\N	\N	2026-04-30 11:01:27.253562
641	impression	202808	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	65	\N	\N	2026-04-30 11:01:27.253564
642	impression	268181	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	66	\N	\N	2026-04-30 11:01:27.253565
643	impression	268047	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	67	\N	\N	2026-04-30 11:01:27.253567
644	impression	202614	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	68	\N	\N	2026-04-30 11:01:27.253569
645	impression	267741	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	69	\N	\N	2026-04-30 11:01:27.253571
646	impression	268505	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	70	\N	\N	2026-04-30 11:01:27.253572
657	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	shoes	\N	\N	\N	2026-04-30 11:02:39.24464
659	impression	312012	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:03:29.435632
660	impression	312143	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:03:29.435637
661	impression	312310	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:03:29.435639
662	impression	312172	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:03:29.435641
663	impression	346156	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:03:29.435642
664	impression	311980	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:03:29.435644
665	impression	346329	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:03:29.435646
666	impression	346199	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:03:29.435648
667	impression	352595	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:03:29.435649
668	impression	346245	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:03:29.435651
670	click	popilush-shapewear-dress-faux-leather-dresses-for-women-mock-neck-dress-night-club-outfits-for-women	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 11:22:09.619063
671	view	fashion-jewelry-shoes	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:22:09.619068
673	impression	320804	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:22:25.616903
674	impression	320779	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:22:25.616931
675	impression	180095	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:22:25.616935
676	impression	237138	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:22:25.616938
677	impression	266617	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:22:25.616941
688	impression	329211	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 11:22:51.615886
689	impression	266745	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 11:22:51.615891
690	impression	308412	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 11:22:51.615893
691	impression	320778	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 11:22:51.615895
692	impression	237137	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 11:22:51.615897
693	view	popilush-shapewear-dress-ruched-bodycon-deep-v-neck-maxi-formal-dresses-built-in-shapewear-sleeveless-long-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:22:55.519507
694	impression	263765	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:22:55.527588
695	impression	262854	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:22:55.527593
696	impression	265809	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:22:55.527595
697	impression	237121	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:22:55.527597
698	impression	237152	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:22:55.527599
699	impression	320804	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:23:01.530838
700	impression	320779	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:23:01.530843
701	impression	180095	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:23:01.530845
702	impression	237138	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:23:01.530847
703	impression	266617	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:23:01.530849
704	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	dresses	\N	\N	\N	2026-04-30 11:24:02.639025
705	click	300870	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	browse	2026-04-30 11:25:52.703899
706	impression	300972	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:25:56.379668
707	impression	301137	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:25:56.379673
708	impression	300622	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:25:56.379675
709	impression	300473	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:25:56.379677
710	impression	300842	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:25:56.379678
711	impression	300457	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:25:58.373666
712	impression	301401	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:25:58.373671
713	impression	300635	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:25:58.373673
714	impression	300532	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:25:58.373675
715	impression	300773	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:25:58.373677
716	impression	300662	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:27:01.513187
717	impression	300408	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:27:01.513193
718	impression	366577	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:27:01.513195
719	impression	300627	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:27:01.513197
720	impression	300703	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:27:01.513198
721	view	makemechic-womens-maternity-dresses-striped-flounce-sleeve-flowy-nursing-dress-ruffle-pregnancy-dresses	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:27:01.521797
722	impression	300972	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:27:03.524722
723	impression	301137	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:27:03.524727
724	impression	300622	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:27:03.524729
725	impression	300473	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:27:03.524731
726	impression	300842	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:27:03.524733
728	impression	263765	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:27:32.641951
727	view	popilush-shapewear-dress-ruched-bodycon-deep-v-neck-maxi-formal-dresses-built-in-shapewear-sleeveless-long-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:27:32.637242
733	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	shoes	\N	\N	\N	2026-04-30 11:28:21.130016
735	view	fashion-jewelry-shoes	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:44:48.750459
737	impression	324503	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:45:20.507665
738	impression	181413	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:45:20.50767
739	impression	260644	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:45:20.507672
740	impression	180976	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:45:20.507674
741	impression	327667	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:45:20.507675
742	impression	324499	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:45:20.507677
743	impression	354317	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:45:20.507679
744	impression	259951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:45:20.507681
745	impression	259585	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:45:20.507682
746	impression	311781	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:45:20.507684
747	impression	178773	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 11:45:20.507686
748	impression	322860	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 11:45:20.507688
749	impression	327664	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 11:45:20.507689
750	impression	327683	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 11:45:20.507691
751	impression	178702	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 11:45:20.507693
752	impression	241955	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 11:45:20.507695
753	impression	178768	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 11:45:20.507696
754	impression	260003	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 11:45:20.507698
755	impression	178971	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 11:45:20.5077
756	impression	260251	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 11:45:20.507701
778	impression	181149	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	61	\N	\N	2026-04-30 11:45:22.475053
779	impression	323140	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	62	\N	\N	2026-04-30 11:45:22.475058
780	impression	327549	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	63	\N	\N	2026-04-30 11:45:22.47506
781	impression	179008	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	64	\N	\N	2026-04-30 11:45:22.475062
782	impression	267101	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	65	\N	\N	2026-04-30 11:45:22.475063
783	impression	328966	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	66	\N	\N	2026-04-30 11:45:22.475065
784	impression	266910	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	67	\N	\N	2026-04-30 11:45:22.475067
785	impression	261385	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	68	\N	\N	2026-04-30 11:45:22.475068
786	impression	259800	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	69	\N	\N	2026-04-30 11:45:22.47507
787	impression	259633	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	70	\N	\N	2026-04-30 11:45:22.475072
798	impression	278221	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	81	\N	\N	2026-04-30 11:45:30.476523
799	impression	318864	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	82	\N	\N	2026-04-30 11:45:30.476528
800	impression	178347	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	83	\N	\N	2026-04-30 11:45:30.47653
801	impression	301469	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	84	\N	\N	2026-04-30 11:45:30.476532
802	impression	318850	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	85	\N	\N	2026-04-30 11:45:30.476534
803	impression	260164	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	86	\N	\N	2026-04-30 11:45:30.476536
804	impression	327752	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	87	\N	\N	2026-04-30 11:45:30.476537
805	impression	323157	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	88	\N	\N	2026-04-30 11:45:30.476539
806	impression	120378	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	89	\N	\N	2026-04-30 11:45:30.476541
807	impression	311678	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	90	\N	\N	2026-04-30 11:45:30.476543
729	impression	262854	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:27:32.641955
730	impression	265809	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:27:32.641957
731	impression	237121	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:27:32.641959
732	impression	237152	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:27:32.641961
734	search	\N	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	shoes	\N	\N	\N	2026-04-30 11:43:39.662864
736	click	eevee-womens-casual-crop-hoodie-sweatshirt-long-sleeve-cute-cropped-plain-workout-drawstring-hooded-pullover-top	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 11:45:04.472709
757	impression	260215	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 11:45:21.850221
758	impression	181155	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 11:45:21.850226
759	impression	260631	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 11:45:21.850228
760	impression	260046	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 11:45:21.85023
761	impression	327600	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 11:45:21.850232
762	impression	322864	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 11:45:21.850233
763	impression	260430	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 11:45:21.850235
764	impression	328982	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 11:45:21.850237
765	impression	327587	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 11:45:21.850239
766	impression	325469	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 11:45:21.85024
767	impression	261382	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	41	\N	\N	2026-04-30 11:45:21.850242
768	impression	301114	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	42	\N	\N	2026-04-30 11:45:21.850244
769	impression	328972	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	43	\N	\N	2026-04-30 11:45:21.850246
770	impression	325461	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	44	\N	\N	2026-04-30 11:45:21.850247
771	impression	318798	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	45	\N	\N	2026-04-30 11:45:21.850249
772	impression	311615	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	46	\N	\N	2026-04-30 11:45:21.850251
773	impression	178994	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	47	\N	\N	2026-04-30 11:45:21.850253
774	impression	327598	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	48	\N	\N	2026-04-30 11:45:21.850254
775	impression	178379	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	49	\N	\N	2026-04-30 11:45:21.850256
776	impression	314141	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	50	\N	\N	2026-04-30 11:45:21.850258
777	impression	324488	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	51	\N	\N	2026-04-30 11:45:21.85026
788	impression	285207	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	71	\N	\N	2026-04-30 11:45:24.476957
789	impression	281131	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	72	\N	\N	2026-04-30 11:45:24.476962
790	impression	311172	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	73	\N	\N	2026-04-30 11:45:24.476964
791	impression	260738	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	74	\N	\N	2026-04-30 11:45:24.476966
792	impression	322843	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	75	\N	\N	2026-04-30 11:45:24.476968
793	impression	179895	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	76	\N	\N	2026-04-30 11:45:24.47697
794	impression	260264	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	77	\N	\N	2026-04-30 11:45:24.476971
795	impression	259871	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	78	\N	\N	2026-04-30 11:45:24.476973
796	impression	354333	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	79	\N	\N	2026-04-30 11:45:24.476975
797	impression	354323	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	80	\N	\N	2026-04-30 11:45:24.476977
808	view	eevee-womens-casual-crop-hoodie-sweatshirt-long-sleeve-cute-cropped-plain-workout-drawstring-hooded-pullover-top	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:45:38.60746
809	impression	328948	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:45:38.609272
810	impression	328953	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:45:38.609276
811	impression	178806	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:45:38.609279
812	impression	354380	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:45:38.60928
813	impression	354379	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:45:38.609282
814	impression	325529	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:45:38.609284
815	impression	328951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:45:38.609286
816	impression	178916	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:45:38.609287
817	impression	178922	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:45:38.609289
818	impression	327744	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:45:38.609291
819	impression	324503	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:45:50.612159
820	impression	181413	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:45:50.612164
821	impression	260644	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:45:50.612166
822	impression	180976	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:45:50.612168
823	impression	327667	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:45:50.61217
824	impression	324499	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:45:50.612171
825	impression	354317	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:45:50.612173
826	impression	259951	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:45:50.612175
827	impression	259585	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:45:50.612177
828	impression	311781	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:45:50.612179
829	impression	178773	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 11:45:54.611168
830	impression	322860	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 11:45:54.611173
831	impression	327664	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 11:45:54.611175
832	impression	327683	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 11:45:54.611177
833	impression	178702	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 11:45:54.611179
834	impression	241955	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 11:45:54.61118
835	impression	178768	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 11:45:54.611182
836	impression	260003	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 11:45:54.611184
837	impression	178971	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 11:45:54.611186
838	impression	260251	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 11:45:54.611187
839	impression	260215	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 11:45:56.602037
840	impression	181155	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 11:45:56.602042
841	impression	260631	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 11:45:56.602044
842	impression	260046	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 11:45:56.602046
843	impression	327600	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 11:45:56.602048
844	impression	322864	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 11:45:56.602049
845	impression	260430	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 11:45:56.602051
846	impression	328982	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 11:45:56.602053
847	impression	327587	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 11:45:56.602055
848	impression	325469	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 11:45:56.602056
859	click	202595	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	browse	2026-04-30 11:46:22.866892
870	impression	267093	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	61	\N	\N	2026-04-30 11:46:30.603247
871	impression	268737	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	62	\N	\N	2026-04-30 11:46:30.603252
872	impression	266393	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	63	\N	\N	2026-04-30 11:46:30.603254
873	impression	267753	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	64	\N	\N	2026-04-30 11:46:30.603256
874	impression	267062	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	65	\N	\N	2026-04-30 11:46:30.603257
875	impression	268759	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	66	\N	\N	2026-04-30 11:46:30.603259
876	impression	266398	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	67	\N	\N	2026-04-30 11:46:30.603261
877	impression	266477	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	68	\N	\N	2026-04-30 11:46:30.603263
878	impression	267259	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	69	\N	\N	2026-04-30 11:46:30.603265
879	impression	266612	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	70	\N	\N	2026-04-30 11:46:30.603267
890	view	womens-tulle-skirt-long-black-layered-maxi-midi-high-low-skirts-for-special-occasion-women	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:47:26.986956
901	view	womens-tulle-skirt-long-black-layered-maxi-midi-high-low-skirts-for-special-occasion-women	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:55:53.319749
922	impression	267060	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 11:55:57.06567
923	impression	202689	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 11:55:57.065676
924	impression	266998	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 11:55:57.065678
925	impression	267226	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 11:55:57.065679
926	impression	268339	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 11:55:57.065681
927	impression	267079	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 11:55:57.065683
928	impression	202651	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 11:55:57.065685
929	impression	268145	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 11:55:57.065686
930	impression	202687	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 11:55:57.065688
931	impression	202925	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 11:55:57.06569
933	impression	355037	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 11:57:39.040054
934	impression	329228	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 11:57:39.040059
935	impression	354913	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 11:57:39.040061
936	impression	354956	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 11:57:39.040063
937	impression	180095	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 11:57:39.040065
938	impression	329236	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 11:57:39.040067
939	impression	237158	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 11:57:39.040069
940	impression	355051	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 11:57:39.040071
941	impression	355010	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 11:57:39.040072
942	impression	355030	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 11:57:39.040074
944	impression	329291	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:58:33.523603
945	impression	354973	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:58:33.523609
946	impression	329285	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:58:33.523611
947	impression	329277	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:58:33.523613
948	impression	329278	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:58:33.523614
949	impression	355018	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:58:33.523616
950	impression	300891	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:58:33.523618
951	impression	355028	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:58:33.52362
952	impression	354919	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:58:33.523622
953	impression	355032	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:58:33.523624
849	impression	261382	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	41	\N	\N	2026-04-30 11:45:58.603976
850	impression	301114	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	42	\N	\N	2026-04-30 11:45:58.603981
851	impression	328972	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	43	\N	\N	2026-04-30 11:45:58.603983
852	impression	325461	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	44	\N	\N	2026-04-30 11:45:58.603985
853	impression	318798	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	45	\N	\N	2026-04-30 11:45:58.603987
854	impression	311615	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	46	\N	\N	2026-04-30 11:45:58.603989
855	impression	178994	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	47	\N	\N	2026-04-30 11:45:58.60399
856	impression	327598	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	48	\N	\N	2026-04-30 11:45:58.603992
857	impression	178379	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	49	\N	\N	2026-04-30 11:45:58.603994
858	impression	314141	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	50	\N	\N	2026-04-30 11:45:58.603996
860	impression	267755	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	51	\N	\N	2026-04-30 11:46:28.605052
861	impression	266399	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	52	\N	\N	2026-04-30 11:46:28.605057
862	impression	267630	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	53	\N	\N	2026-04-30 11:46:28.605059
863	impression	267829	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	54	\N	\N	2026-04-30 11:46:28.605061
864	impression	266811	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	55	\N	\N	2026-04-30 11:46:28.605062
865	impression	268709	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	56	\N	\N	2026-04-30 11:46:28.605064
866	impression	267289	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	57	\N	\N	2026-04-30 11:46:28.605066
867	impression	266983	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	58	\N	\N	2026-04-30 11:46:28.605068
868	impression	267463	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	59	\N	\N	2026-04-30 11:46:28.605069
869	impression	267338	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	60	\N	\N	2026-04-30 11:46:28.605071
880	impression	267108	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	71	\N	\N	2026-04-30 11:47:20.603703
881	impression	267430	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	72	\N	\N	2026-04-30 11:47:20.603709
882	impression	268045	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	73	\N	\N	2026-04-30 11:47:20.603711
883	impression	266541	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	74	\N	\N	2026-04-30 11:47:20.603713
884	impression	267771	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	75	\N	\N	2026-04-30 11:47:20.603715
885	impression	266662	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	76	\N	\N	2026-04-30 11:47:20.603717
886	impression	267695	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	77	\N	\N	2026-04-30 11:47:20.603718
887	impression	202829	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	78	\N	\N	2026-04-30 11:47:20.60372
888	impression	202921	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	79	\N	\N	2026-04-30 11:47:20.603722
889	impression	266480	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	80	\N	\N	2026-04-30 11:47:20.603724
891	impression	267624	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:47:27.263424
892	impression	268480	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:47:27.26343
893	impression	268656	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:47:27.263432
894	impression	268080	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:47:27.263434
895	impression	267330	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:47:27.263436
896	impression	267396	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:47:27.263437
897	impression	267400	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:47:27.263439
898	impression	202679	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:47:27.263441
899	impression	202686	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:47:27.263442
900	impression	267388	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:47:27.263444
902	impression	267624	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:55:53.354838
903	impression	268480	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:55:53.354843
904	impression	268656	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:55:53.354845
905	impression	268080	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:55:53.354847
906	impression	267330	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:55:53.354849
907	impression	267396	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:55:53.35485
908	impression	267400	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:55:53.354852
909	impression	202679	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:55:53.354854
910	impression	202686	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:55:53.354856
911	impression	267388	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:55:53.354858
912	impression	202873	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:55:53.354859
913	impression	267920	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:55:53.354861
914	impression	202786	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:55:53.354863
915	impression	268296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:55:53.354864
916	impression	266725	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:55:53.354866
917	impression	266999	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:55:53.354868
918	impression	267922	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:55:53.35487
919	impression	268357	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:55:53.354871
920	impression	258906	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:55:53.354873
921	impression	268051	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:55:53.354875
932	click	womens-plus-size-maxi-dress-elegant-v-neck-ruffle-sleeves-bodycon-mermaid-dresses-evening-gown	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 11:57:25.33628
943	view	womens-plus-size-maxi-dress-elegant-v-neck-ruffle-sleeves-bodycon-mermaid-dresses-evening-gown	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:58:33.231862
954	view	women-sexy-backless-halter-long-maxi-dress-deep-v-neck-ruffle-evening-dress-bodycon-party-cocktail-dresses	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 11:59:00.603708
955	impression	329228	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 11:59:00.612458
956	impression	329267	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 11:59:00.612465
957	impression	329241	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 11:59:00.612468
958	impression	329259	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 11:59:00.612469
959	impression	300891	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 11:59:00.612471
960	impression	237169	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 11:59:00.612473
961	impression	237130	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 11:59:00.612475
962	impression	237118	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 11:59:00.612477
963	impression	329234	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 11:59:00.612479
964	impression	329277	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 11:59:00.612481
975	click	brabic-womens-seamless-sleeveless-v-neck-bodysuit-shapewear-tummy-control	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 11:59:33.064109
986	view	spanx-seamless-power-thong-bodysuit-soft-seamless-shapewear-for-women-adjustable-straps-with-snap-closure	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 12:00:05.082931
997	impression	110052	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:00:11.097173
998	impression	320806	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:00:11.097179
999	impression	320799	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:00:11.097181
1000	impression	320807	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:00:11.097183
1001	impression	354589	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:00:11.097184
1002	impression	321945	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:00:11.097186
1003	impression	320808	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:00:11.097188
1004	impression	110104	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:00:11.09719
1005	impression	320779	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:00:11.097192
1006	impression	110030	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:00:11.097193
1008	impression	262043	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 12:00:47.09399
1009	impression	264823	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 12:00:47.093995
1010	impression	328120	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 12:00:47.093997
1011	impression	263170	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 12:00:47.093998
1012	impression	325885	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 12:00:47.094
1013	impression	266185	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 12:00:47.094002
1014	impression	262669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 12:00:47.094004
1015	impression	265326	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 12:00:47.094005
1016	impression	265614	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 12:00:47.094007
1017	impression	265323	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 12:00:47.094009
1028	impression	264901	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	41	\N	\N	2026-04-30 12:00:53.412245
1029	impression	265092	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	42	\N	\N	2026-04-30 12:00:53.41225
1030	impression	261953	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	43	\N	\N	2026-04-30 12:00:53.412252
1031	impression	263070	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	44	\N	\N	2026-04-30 12:00:53.412254
1032	impression	328826	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	45	\N	\N	2026-04-30 12:00:53.412256
1033	impression	262142	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	46	\N	\N	2026-04-30 12:00:53.412257
1034	impression	262613	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	47	\N	\N	2026-04-30 12:00:53.412259
1035	impression	324754	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	48	\N	\N	2026-04-30 12:00:53.412261
1036	impression	322281	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	49	\N	\N	2026-04-30 12:00:53.412263
1037	impression	262296	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	50	\N	\N	2026-04-30 12:00:53.412264
1038	view	adrianna-papell-womens-bell-sleeve-tie-front-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 12:05:50.106567
1059	impression	265948	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:05:52.11028
1060	impression	265022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:05:52.110286
1061	impression	265580	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:05:52.11029
1062	impression	322152	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:05:52.110293
1063	impression	262051	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:05:52.110296
1064	impression	262579	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:05:52.110299
1065	impression	264887	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:05:52.110302
1066	impression	322341	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:05:52.110305
1067	impression	263515	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:05:52.110308
1068	impression	263259	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:05:52.11031
1079	click	petticoat-skirt-for-women-under-dress-elastic-waist-chiffon-petticoat-puffy-tutu-tulle-skirt	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:06:38.406053
1090	click	carhartt-mens-rugged-flex-relaxed-fit-flannel-fleece-lined-hooded-shirt-jac	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:07:02.147633
965	impression	180072	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:59:08.608653
966	impression	329205	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:59:08.608658
967	impression	329215	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:59:08.60866
968	impression	237137	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:59:08.608662
969	impression	327476	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:59:08.608664
970	impression	329236	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:59:08.608666
971	impression	264753	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:59:08.608667
972	impression	237158	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:59:08.608669
973	impression	329289	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:59:08.608671
974	impression	329270	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:59:08.608673
976	impression	320784	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 11:59:43.084485
977	impression	320799	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 11:59:43.084491
978	impression	320801	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 11:59:43.084493
979	impression	320782	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 11:59:43.084495
980	impression	320778	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 11:59:43.084497
981	impression	320776	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 11:59:43.084498
982	impression	320783	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 11:59:43.0845
983	impression	180292	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 11:59:43.084502
984	impression	354553	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 11:59:43.084504
985	impression	354554	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 11:59:43.084506
987	impression	322053	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 12:00:05.468478
988	impression	322570	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 12:00:05.468484
989	impression	320798	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 12:00:05.468486
990	impression	320801	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 12:00:05.468488
991	impression	320776	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 12:00:05.46849
992	impression	110051	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 12:00:05.468492
993	impression	320792	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 12:00:05.468493
994	impression	308412	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 12:00:05.468495
995	impression	327762	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 12:00:05.468497
996	impression	354563	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 12:00:05.468498
1007	click	adrianna-papell-womens-bell-sleeve-tie-front-dress	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:00:35.372134
1018	impression	262723	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 12:00:51.094464
1019	impression	265548	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 12:00:51.094469
1020	impression	265460	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 12:00:51.094471
1021	impression	262382	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 12:00:51.094473
1022	impression	263702	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 12:00:51.094475
1023	impression	322765	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 12:00:51.094477
1024	impression	262150	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 12:00:51.094478
1025	impression	263199	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 12:00:51.09448
1026	impression	265691	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 12:00:51.094482
1027	impression	265193	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 12:00:51.094483
1039	impression	265717	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:05:50.12059
1040	impression	262419	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:05:50.120595
1041	impression	264452	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:05:50.120597
1042	impression	264153	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:05:50.120599
1043	impression	263189	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:05:50.1206
1044	impression	263375	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:05:50.120602
1045	impression	262479	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:05:50.120604
1046	impression	265316	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:05:50.120606
1047	impression	265336	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:05:50.120608
1048	impression	265525	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:05:50.12061
1049	impression	265948	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:05:50.120611
1050	impression	265022	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:05:50.120613
1051	impression	265580	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:05:50.120615
1052	impression	322152	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:05:50.120617
1053	impression	262051	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:05:50.120618
1054	impression	262579	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:05:50.12062
1055	impression	264887	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:05:50.120622
1056	impression	322341	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:05:50.120624
1057	impression	263515	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:05:50.120625
1058	impression	263259	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:05:50.120627
1069	impression	262043	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 12:06:02.541095
1070	impression	264823	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 12:06:02.541101
1071	impression	328120	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 12:06:02.541105
1072	impression	263170	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 12:06:02.541108
1073	impression	325885	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 12:06:02.541111
1074	impression	266185	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 12:06:02.541114
1075	impression	262669	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 12:06:02.541645
1076	impression	265326	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 12:06:02.541662
1077	impression	265614	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 12:06:02.541665
1078	impression	265323	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 12:06:02.541667
1080	impression	266753	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	41	\N	\N	2026-04-30 12:06:58.488888
1081	impression	266725	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	42	\N	\N	2026-04-30 12:06:58.488894
1082	impression	266384	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	43	\N	\N	2026-04-30 12:06:58.488896
1083	impression	266683	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	44	\N	\N	2026-04-30 12:06:58.488898
1084	impression	327567	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	45	\N	\N	2026-04-30 12:06:58.4889
1085	impression	266999	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	46	\N	\N	2026-04-30 12:06:58.488902
1086	impression	202666	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	47	\N	\N	2026-04-30 12:06:58.488903
1087	impression	267247	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	48	\N	\N	2026-04-30 12:06:58.488905
1088	impression	266938	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	49	\N	\N	2026-04-30 12:06:58.488928
1089	impression	266638	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	50	\N	\N	2026-04-30 12:06:58.488932
1091	impression	285687	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	61	\N	\N	2026-04-30 12:07:20.126585
1092	impression	285481	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	62	\N	\N	2026-04-30 12:07:20.12659
1093	impression	281064	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	63	\N	\N	2026-04-30 12:07:20.126592
1094	impression	282619	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	64	\N	\N	2026-04-30 12:07:20.126594
1095	impression	118490	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	65	\N	\N	2026-04-30 12:07:20.126595
1096	impression	285306	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	66	\N	\N	2026-04-30 12:07:20.126597
1097	impression	238664	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	67	\N	\N	2026-04-30 12:07:20.126599
1098	impression	281871	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	68	\N	\N	2026-04-30 12:07:20.1266
1099	impression	239379	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	69	\N	\N	2026-04-30 12:07:20.126602
1100	impression	239464	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	70	\N	\N	2026-04-30 12:07:20.126604
1101	impression	279501	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	71	\N	\N	2026-04-30 12:07:20.126606
1102	impression	239942	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	72	\N	\N	2026-04-30 12:07:20.126607
1103	impression	282224	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	73	\N	\N	2026-04-30 12:07:20.126609
1104	impression	280775	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	74	\N	\N	2026-04-30 12:07:20.126611
1105	impression	281353	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	75	\N	\N	2026-04-30 12:07:20.126613
1106	impression	286927	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	76	\N	\N	2026-04-30 12:07:20.126614
1107	impression	282459	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	77	\N	\N	2026-04-30 12:07:20.126616
1108	impression	79708	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	78	\N	\N	2026-04-30 12:07:20.126618
1109	impression	285689	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	79	\N	\N	2026-04-30 12:07:20.12662
1110	impression	285852	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	80	\N	\N	2026-04-30 12:07:20.126621
1111	impression	286086	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	81	\N	\N	2026-04-30 12:07:56.116685
1112	impression	286063	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	82	\N	\N	2026-04-30 12:07:56.11669
1113	impression	280784	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	83	\N	\N	2026-04-30 12:07:56.116692
1114	impression	239129	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	84	\N	\N	2026-04-30 12:07:56.116693
1115	impression	254789	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	85	\N	\N	2026-04-30 12:07:56.116695
1116	impression	281290	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	86	\N	\N	2026-04-30 12:07:56.116697
1117	impression	285808	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	87	\N	\N	2026-04-30 12:07:56.116699
1118	impression	280049	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	88	\N	\N	2026-04-30 12:07:56.116701
1119	impression	285662	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	89	\N	\N	2026-04-30 12:07:56.116702
1120	impression	285336	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	90	\N	\N	2026-04-30 12:07:56.116704
1121	impression	269757	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	91	\N	\N	2026-04-30 12:07:56.116706
1122	impression	285593	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	92	\N	\N	2026-04-30 12:07:56.116708
1123	impression	285458	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	93	\N	\N	2026-04-30 12:07:56.11671
1124	impression	285349	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	94	\N	\N	2026-04-30 12:07:56.116711
1125	impression	118505	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	95	\N	\N	2026-04-30 12:07:56.116713
1126	impression	285764	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	96	\N	\N	2026-04-30 12:07:56.116715
1127	impression	239160	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	97	\N	\N	2026-04-30 12:07:56.116717
1128	impression	282573	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	98	\N	\N	2026-04-30 12:07:56.116719
1129	impression	286266	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	99	\N	\N	2026-04-30 12:07:56.11672
1130	impression	281229	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	100	\N	\N	2026-04-30 12:07:56.116722
1131	impression	298594	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	101	\N	\N	2026-04-30 12:07:58.108748
1132	impression	285664	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	102	\N	\N	2026-04-30 12:07:58.108754
1133	impression	280893	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	103	\N	\N	2026-04-30 12:07:58.108756
1134	impression	239648	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	104	\N	\N	2026-04-30 12:07:58.108758
1135	impression	329810	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	105	\N	\N	2026-04-30 12:07:58.10876
1136	impression	280787	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	106	\N	\N	2026-04-30 12:07:58.108761
1137	impression	238908	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	107	\N	\N	2026-04-30 12:07:58.108763
1138	impression	285405	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	108	\N	\N	2026-04-30 12:07:58.108765
1139	impression	285085	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	109	\N	\N	2026-04-30 12:07:58.108767
1140	impression	239130	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	110	\N	\N	2026-04-30 12:07:58.108769
1141	view	carhartt-mens-rugged-flex-relaxed-fit-flannel-fleece-lined-hooded-shirt-jac	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	pdp	2026-04-30 12:08:10.161824
1142	impression	279729	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 12:08:10.169246
1143	impression	285387	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 12:08:10.169252
1144	impression	285392	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 12:08:10.169253
1145	impression	238832	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 12:08:10.169255
1146	impression	238686	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 12:08:10.169257
1147	impression	283557	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 12:08:10.169258
1148	impression	285383	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 12:08:10.16926
1149	impression	286269	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 12:08:10.169262
1150	impression	285344	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 12:08:10.169264
1151	impression	279452	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 12:08:10.169266
1162	impression	282785	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:08:16.174468
1163	impression	238691	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:08:16.174474
1164	impression	283519	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:08:16.174476
1165	impression	239989	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:08:16.174478
1166	impression	284243	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:08:16.174479
1167	impression	286555	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:08:16.174481
1168	impression	284009	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:08:16.174483
1169	impression	285618	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:08:16.174485
1170	impression	285471	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:08:16.174486
1171	impression	286615	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:08:16.174488
1173	impression	261742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 12:08:48.17757
1174	impression	297861	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 12:08:48.177575
1175	impression	299555	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 12:08:48.177577
1176	impression	296943	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 12:08:48.177579
1177	impression	296650	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 12:08:48.177581
1178	impression	266992	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 12:08:48.177583
1179	impression	267726	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 12:08:48.177584
1180	impression	267538	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 12:08:48.177586
1181	impression	267157	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 12:08:48.177588
1182	impression	250102	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 12:08:48.177589
1204	impression	261742	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	21	\N	\N	2026-04-30 12:13:29.014437
1205	impression	297861	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	22	\N	\N	2026-04-30 12:13:29.014442
1206	impression	299555	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	23	\N	\N	2026-04-30 12:13:29.014445
1207	impression	296943	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	24	\N	\N	2026-04-30 12:13:29.014446
1208	impression	296650	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	25	\N	\N	2026-04-30 12:13:29.014448
1209	impression	266992	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	26	\N	\N	2026-04-30 12:13:29.01445
1210	impression	267726	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	27	\N	\N	2026-04-30 12:13:29.014452
1211	impression	267538	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	28	\N	\N	2026-04-30 12:13:29.014453
1212	impression	267157	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	29	\N	\N	2026-04-30 12:13:29.014455
1213	impression	250102	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	30	\N	\N	2026-04-30 12:13:29.014457
1215	impression	202658	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 12:14:16.747404
1216	impression	266715	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 12:14:16.74741
1217	impression	262129	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 12:14:16.747412
1218	impression	268709	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 12:14:16.747414
1219	impression	202877	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 12:14:16.747416
1220	impression	267958	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 12:14:16.747417
1221	impression	268720	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 12:14:16.747419
1222	impression	268167	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 12:14:16.747421
1223	impression	270903	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 12:14:16.747423
1224	impression	266703	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 12:14:16.747424
1235	click	astr-the-label-womens-divine-skirt	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:15:48.741616
1152	impression	279729	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	1	\N	\N	2026-04-30 12:08:12.167
1153	impression	285387	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	2	\N	\N	2026-04-30 12:08:12.167005
1154	impression	285392	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	3	\N	\N	2026-04-30 12:08:12.167007
1155	impression	238832	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	4	\N	\N	2026-04-30 12:08:12.167009
1156	impression	238686	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	5	\N	\N	2026-04-30 12:08:12.167011
1157	impression	283557	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	6	\N	\N	2026-04-30 12:08:12.167012
1158	impression	285383	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	7	\N	\N	2026-04-30 12:08:12.167014
1159	impression	286269	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	8	\N	\N	2026-04-30 12:08:12.167016
1160	impression	285344	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	9	\N	\N	2026-04-30 12:08:12.167017
1161	impression	279452	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	10	\N	\N	2026-04-30 12:08:12.167019
1172	click	lioness-womens-hamptons-skirt	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:08:36.481566
1183	impression	297181	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	31	\N	\N	2026-04-30 12:13:17.732128
1184	impression	268734	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	32	\N	\N	2026-04-30 12:13:17.732133
1185	impression	267297	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	33	\N	\N	2026-04-30 12:13:17.732135
1186	impression	202810	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	34	\N	\N	2026-04-30 12:13:17.732137
1187	impression	268676	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	35	\N	\N	2026-04-30 12:13:17.732139
1188	impression	268220	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	36	\N	\N	2026-04-30 12:13:17.73214
1189	impression	250071	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	37	\N	\N	2026-04-30 12:13:17.732142
1190	impression	268371	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	38	\N	\N	2026-04-30 12:13:17.732144
1191	impression	354304	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	39	\N	\N	2026-04-30 12:13:17.732146
1192	impression	268107	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	40	\N	\N	2026-04-30 12:13:17.732147
1193	impression	267283	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:13:17.732149
1194	impression	267378	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:13:17.732151
1195	impression	267926	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:13:17.732152
1196	impression	267273	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:13:17.732154
1197	impression	267857	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:13:17.732156
1198	impression	267121	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:13:17.732157
1199	impression	268344	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:13:17.732159
1200	impression	268067	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:13:17.732161
1201	impression	267950	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:13:17.732162
1202	impression	267832	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:13:17.732164
1203	impression	268722	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:13:17.732166
1214	click	tanming-womens-high-waist-pleated-long-denim-skirt	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	\N	\N	browse	2026-04-30 12:14:00.765092
1225	impression	267135	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	11	\N	\N	2026-04-30 12:15:10.758119
1226	impression	202897	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	12	\N	\N	2026-04-30 12:15:10.758124
1227	impression	324740	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	13	\N	\N	2026-04-30 12:15:10.758126
1228	impression	267075	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	14	\N	\N	2026-04-30 12:15:10.758128
1229	impression	202564	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	15	\N	\N	2026-04-30 12:15:10.75813
1230	impression	268088	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	16	\N	\N	2026-04-30 12:15:10.758132
1231	impression	267711	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	17	\N	\N	2026-04-30 12:15:10.758134
1232	impression	267827	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	18	\N	\N	2026-04-30 12:15:10.758135
1233	impression	268211	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	19	\N	\N	2026-04-30 12:15:10.758137
1234	impression	266653	\N	8f30ab83-7db0-4e94-93ef-92c0b705d79d	\N	20	\N	\N	2026-04-30 12:15:10.758139
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

COPY public.product_metrics (id, product_id, impressions, views, clicks, carts, purchases, wishlist) FROM stdin;
1	365312	0	0	0	1	0	0
2	180006	0	0	0	1	0	0
3	epson-expression-premium-wireless-color-photo-printer-with-adf-scanner-and-copier-black	2	2	0	0	0	0
4	53785	0	0	0	1	0	0
6	asus-rog-strix-go-2-4-electro-punk-wireless-gaming-headphones-with-usb-c-2-4-ghz-adapter-ai-powered-noise-cancelling-microphone-over-ear-headphones-for-pc-mac-nintendo-switch-and-ps4	1	1	0	0	0	0
7	46808	0	0	0	1	0	2
8	best-sellers	1	1	0	0	0	0
9	faherty-mens-legend-sweater-shirt-azb0cqh751db-p	0	0	1	0	0	0
38	330113	2	0	0	0	0	0
10	239084	0	0	0	1	0	2
11	osp-home-furnishings-megan-office-chair-blue-brushed-grey	1	1	0	0	0	0
32	278229	4	0	0	0	0	0
12	yarnow-kickboxing-shoes-men-s-kung-fu-shoes-taichi-training-shoes-breathable-comfortable-cotton-sole	3	3	0	0	0	0
33	258918	4	0	0	0	0	0
34	259220	4	0	0	0	0	0
35	259397	4	0	0	0	0	0
36	278050	4	0	0	0	0	0
37	166489	4	0	0	0	0	0
46	278228	2	0	0	0	0	0
47	166091	2	0	0	0	0	0
56	330369	5	0	0	0	0	0
16	dinggu-steel-toe-shoes-for-men-safety-mens-work-shoes-comfortable-indestructible-construction-shoes-leather	8	8	0	0	0	0
17	yccafgaanm-fashion-letter-cute-brooch-women-men-rhinestone-silver-color-metal-pin-suit-shirt-jewelry-accessories-color-h-g	1	1	0	0	0	0
18	117360	0	0	0	1	0	0
13	waterpik-ultra-water-flosser-classic-blue	11	11	0	0	0	0
14	6725	0	0	0	3	0	1
19	celestron-starsense-explorer-102mm-refractor-telescope-silver-black	6	6	0	0	0	0
21	rocking-shoes-shoes-thick-buffer-shoes-cushion-platform-women-mesh-shoes-bottom-sneaker-insoles-women-arch-support	9	9	0	0	0	0
39	314747	2	0	0	0	0	0
40	314801	2	0	0	0	0	0
41	330109	2	0	0	0	0	0
42	314195	2	0	0	0	0	0
5	jbl-xtreme-2-portable-bluetooth-speaker-black	10	10	0	0	0	0
20	278063	0	0	1	0	0	0
43	330093	2	0	0	0	0	0
44	311978	2	0	0	0	0	0
45	330103	2	0	0	0	0	0
15	279300	0	0	2	1	0	1
30	258917	4	0	0	0	0	0
31	259261	4	0	0	0	0	0
71	109998	5	0	0	0	0	0
83	330309	5	0	0	0	0	0
50	179873	1	0	0	0	0	0
51	110029	1	0	0	0	0	0
52	280491	1	0	0	0	0	0
53	278226	1	0	0	0	0	0
54	164923	1	0	0	0	0	0
55	161403	1	0	0	0	0	0
57	110022	1	0	0	0	0	0
58	164306	1	0	0	0	0	0
59	259257	1	0	0	0	0	0
60	259255	1	0	0	0	0	0
61	278296	1	0	0	0	0	0
62	259256	1	0	0	0	0	0
63	166586	1	0	0	0	0	0
64	162310	1	0	0	0	0	0
65	84970	1	0	0	0	0	0
66	161975	1	0	0	0	0	0
67	85161	1	0	0	0	0	0
68	165707	1	0	0	0	0	0
69	163148	1	0	0	0	0	0
70	280465	1	0	0	0	0	0
72	102503	1	0	0	0	0	0
73	110004	1	0	0	0	0	0
74	164800	1	0	0	0	0	0
75	162109	1	0	0	0	0	0
76	102560	1	0	0	0	0	0
77	102596	1	0	0	0	0	0
78	161548	1	0	0	0	0	0
79	109962	1	0	0	0	0	0
80	163853	1	0	0	0	0	0
81	85102	1	0	0	0	0	0
82	160787	1	0	0	0	0	0
84	161535	1	0	0	0	0	0
85	165614	1	0	0	0	0	0
86	164798	1	0	0	0	0	0
87	259402	1	0	0	0	0	0
88	280394	1	0	0	0	0	0
89	163694	1	0	0	0	0	0
90	163626	1	0	0	0	0	0
91	102493	1	0	0	0	0	0
92	85143	1	0	0	0	0	0
93	324946	1	0	0	0	0	0
94	adidas-unisex-adult-dame-extply-2	1	1	0	0	0	0
48	161526	2	0	0	0	0	0
49	162163	2	0	0	0	0	0
95	279588	1	0	0	0	0	0
96	285911	1	0	0	0	0	0
97	280135	1	0	0	0	0	0
98	286078	1	0	0	0	0	0
99	285116	1	0	0	0	0	0
100	280082	1	0	0	0	0	0
101	345425	1	0	0	0	0	0
102	347716	1	0	0	0	0	0
104	286122	1	0	0	0	0	0
106	285813	1	0	0	0	0	0
107	285640	1	0	0	0	0	0
108	286095	1	0	0	0	0	0
109	279284	1	0	0	0	0	0
110	286022	1	0	0	0	0	0
111	345424	1	0	0	0	0	0
112	286335	1	0	0	0	0	0
113	285671	1	0	0	0	0	0
115	279337	1	0	0	0	0	0
116	347664	1	0	0	0	0	0
117	286021	1	0	0	0	0	0
118	279270	1	0	0	0	0	0
119	364911	1	0	0	0	0	0
120	347697	1	0	0	0	0	0
121	285492	1	0	0	0	0	0
122	285440	1	0	0	0	0	0
123	286104	1	0	0	0	0	0
124	285792	1	0	0	0	0	0
125	345431	1	0	0	0	0	0
126	286318	1	0	0	0	0	0
127	279704	1	0	0	0	0	0
128	279457	1	0	0	0	0	0
129	279789	1	0	0	0	0	0
131	285850	1	0	0	0	0	0
133	279678	1	0	0	0	0	0
134	286238	1	0	0	0	0	0
103	279456	2	0	0	0	0	0
105	347654	2	0	0	0	0	0
114	345426	2	0	0	0	0	0
130	279612	2	0	0	0	0	0
132	285084	2	0	0	0	0	0
135	279391	1	0	0	0	0	0
136	286227	1	0	0	0	0	0
137	286246	1	0	0	0	0	0
138	285731	1	0	0	0	0	0
139	286058	1	0	0	0	0	0
140	286267	1	0	0	0	0	0
141	286258	1	0	0	0	0	0
142	286090	1	0	0	0	0	0
143	285857	1	0	0	0	0	0
144	285095	1	0	0	0	0	0
145	286019	1	0	0	0	0	0
146	286156	1	0	0	0	0	0
147	345457	1	0	0	0	0	0
148	364885	1	0	0	0	0	0
149	280124	1	0	0	0	0	0
157	adrianna-papell-womens-embroidered-sheath-dress	0	0	1	0	0	0
158	exlura-womens-casual-long-sleeve-sweatshirts-hoodies-loose-button-pullover-top-trendy-fall-outfits-with-pocket	1	1	0	0	0	0
160	178767	1	0	0	0	0	0
161	178536	1	0	0	0	0	0
162	328976	1	0	0	0	0	0
163	320934	1	0	0	0	0	0
164	178091	1	0	0	0	0	0
165	354407	1	0	0	0	0	0
166	178893	1	0	0	0	0	0
167	320998	1	0	0	0	0	0
169	178701	1	0	0	0	0	0
170	181301	1	0	0	0	0	0
171	179040	1	0	0	0	0	0
172	178282	1	0	0	0	0	0
173	328986	1	0	0	0	0	0
176	178885	1	0	0	0	0	0
177	178811	1	0	0	0	0	0
178	318805	1	0	0	0	0	0
174	328982	3	0	0	0	0	0
175	328948	2	0	0	0	0	0
159	178768	3	0	0	0	0	0
168	178971	3	0	0	0	0	0
22	259384	5	0	0	0	0	0
150	280006	4	0	0	0	0	0
151	14417	4	0	0	0	0	0
152	330322	4	0	0	0	0	0
153	328529	4	0	0	0	0	0
154	249773	4	0	0	0	0	0
155	179356	4	0	0	0	0	0
156	320841	4	0	0	0	0	0
180	5144	7	0	0	0	0	0
23	258886	5	0	0	0	0	0
24	278116	5	0	0	0	0	0
25	258845	5	0	0	0	0	0
26	258885	5	0	0	0	0	0
27	259243	5	0	0	0	0	0
28	259379	5	0	0	0	0	0
29	259258	5	0	0	0	0	0
242	202927	0	0	1	0	0	0
253	268419	1	0	0	0	0	0
255	268165	1	0	0	0	0	0
256	202795	1	0	0	0	0	0
257	268324	1	0	0	0	0	0
258	266887	1	0	0	0	0	0
259	268510	1	0	0	0	0	0
260	267091	1	0	0	0	0	0
261	268201	1	0	0	0	0	0
262	267479	1	0	0	0	0	0
243	268609	2	0	0	0	0	0
244	268258	2	0	0	0	0	0
245	268387	2	0	0	0	0	0
246	267803	2	0	0	0	0	0
247	268081	2	0	0	0	0	0
248	263185	2	0	0	0	0	0
249	268352	2	0	0	0	0	0
190	324921	3	0	0	0	0	0
191	273518	3	0	0	0	0	0
192	358361	3	0	0	0	0	0
193	367922	3	0	0	0	0	0
194	6169	3	0	0	0	0	0
195	358866	3	0	0	0	0	0
196	2770	3	0	0	0	0	0
197	271019	3	0	0	0	0	0
198	272939	3	0	0	0	0	0
199	323022	3	0	0	0	0	0
275	267058	1	0	0	0	0	0
276	202618	1	0	0	0	0	0
277	202933	1	0	0	0	0	0
278	250018	1	0	0	0	0	0
279	268019	1	0	0	0	0	0
280	268519	1	0	0	0	0	0
281	202905	1	0	0	0	0	0
282	268397	1	0	0	0	0	0
283	267279	1	0	0	0	0	0
294	264089	1	0	0	0	0	0
295	268455	1	0	0	0	0	0
297	202808	1	0	0	0	0	0
298	268181	1	0	0	0	0	0
299	268047	1	0	0	0	0	0
300	202614	1	0	0	0	0	0
301	267741	1	0	0	0	0	0
302	268505	1	0	0	0	0	0
313	unisex-kung-fu-martial-arts-tai-chi-trainer-shoes-chinese-tai-chi-wu-shu-shoes-leather-taekwondo-shoes-martial-arts-boxing-shoes	1	1	0	0	0	0
334	320803	1	0	0	0	0	0
336	266793	1	0	0	0	0	0
181	2669	7	0	0	0	0	0
182	7296	7	0	0	0	0	0
183	386883	7	0	0	0	0	0
184	5742	7	0	0	0	0	0
185	11312	7	0	0	0	0	0
186	359279	7	0	0	0	0	0
187	343661	7	0	0	0	0	0
188	2161	7	0	0	0	0	0
189	353209	7	0	0	0	0	0
340	202669	1	0	0	0	0	0
341	320781	1	0	0	0	0	0
351	237152	2	0	0	0	0	0
327	320804	2	0	0	0	0	0
330	237138	2	0	0	0	0	0
331	266617	2	0	0	0	0	0
352	300870	0	0	1	0	0	0
358	300457	1	0	0	0	0	0
359	301401	1	0	0	0	0	0
360	300635	1	0	0	0	0	0
361	300532	1	0	0	0	0	0
362	300773	1	0	0	0	0	0
363	300662	1	0	0	0	0	0
364	300408	1	0	0	0	0	0
365	366577	1	0	0	0	0	0
366	300627	1	0	0	0	0	0
367	300703	1	0	0	0	0	0
368	makemechic-womens-maternity-dresses-striped-flounce-sleeve-flowy-nursing-dress-ruffle-pregnancy-dresses	1	1	0	0	0	0
353	300972	2	0	0	0	0	0
354	301137	2	0	0	0	0	0
355	300622	2	0	0	0	0	0
356	300473	2	0	0	0	0	0
357	300842	2	0	0	0	0	0
326	popilush-shapewear-dress-ruched-bodycon-deep-v-neck-maxi-formal-dresses-built-in-shapewear-sleeveless-long-dress	2	2	1	0	0	0
370	324503	2	0	0	0	0	0
371	181413	2	0	0	0	0	0
274	267108	2	0	0	0	0	0
329	180095	3	0	0	0	0	0
332	320782	2	0	0	0	0	0
337	320798	2	0	0	0	0	0
328	320779	3	0	0	0	0	0
333	320806	2	0	0	0	0	0
335	354589	2	0	0	0	0	0
338	320808	2	0	0	0	0	0
339	320807	2	0	0	0	0	0
296	327567	2	0	0	0	0	0
254	202810	2	0	0	0	0	0
179	insignia-usb-microphone-bb6328951	7	7	0	0	0	0
201	202753	1	0	0	0	0	0
202	266496	1	0	0	0	0	0
203	202606	1	0	0	0	0	0
204	267833	1	0	0	0	0	0
205	266792	1	0	0	0	0	0
207	266719	1	0	0	0	0	0
208	202719	1	0	0	0	0	0
209	328537	1	0	0	0	0	0
210	202577	1	0	0	0	0	0
211	268043	1	0	0	0	0	0
212	266473	1	0	0	0	0	0
213	266446	1	0	0	0	0	0
214	202735	1	0	0	0	0	0
215	202569	1	0	0	0	0	0
216	202615	1	0	0	0	0	0
218	202776	1	0	0	0	0	0
219	202602	1	0	0	0	0	0
220	202909	1	0	0	0	0	0
222	266418	1	0	0	0	0	0
223	202769	1	0	0	0	0	0
224	266461	1	0	0	0	0	0
225	320976	1	0	0	0	0	0
226	267841	1	0	0	0	0	0
227	202901	1	0	0	0	0	0
228	202833	1	0	0	0	0	0
229	266444	1	0	0	0	0	0
230	202674	1	0	0	0	0	0
231	275303	1	0	0	0	0	0
235	202715	1	0	0	0	0	0
236	267675	1	0	0	0	0	0
240	202727	1	0	0	0	0	0
241	202603	1	0	0	0	0	0
237	266477	2	0	0	0	0	0
250	268559	2	0	0	0	0	0
251	261475	2	0	0	0	0	0
252	262302	2	0	0	0	0	0
264	262743	1	0	0	0	0	0
265	261785	1	0	0	0	0	0
266	261604	1	0	0	0	0	0
267	260590	1	0	0	0	0	0
268	268241	1	0	0	0	0	0
269	267577	1	0	0	0	0	0
270	266656	1	0	0	0	0	0
271	202782	1	0	0	0	0	0
272	267858	1	0	0	0	0	0
273	202558	1	0	0	0	0	0
284	258053	1	0	0	0	0	0
285	268789	1	0	0	0	0	0
287	267223	1	0	0	0	0	0
288	268456	1	0	0	0	0	0
289	268200	1	0	0	0	0	0
290	266694	1	0	0	0	0	0
291	202770	1	0	0	0	0	0
292	249982	1	0	0	0	0	0
293	266424	1	0	0	0	0	0
217	202746	2	0	0	0	0	0
303	202711	1	0	0	0	0	0
304	202706	1	0	0	0	0	0
305	268436	1	0	0	0	0	0
306	297300	1	0	0	0	0	0
307	266597	1	0	0	0	0	0
308	202764	1	0	0	0	0	0
309	202557	1	0	0	0	0	0
310	266642	1	0	0	0	0	0
311	268499	1	0	0	0	0	0
312	268517	1	0	0	0	0	0
314	312012	1	0	0	0	0	0
315	312143	1	0	0	0	0	0
316	312310	1	0	0	0	0	0
317	312172	1	0	0	0	0	0
318	346156	1	0	0	0	0	0
319	311980	1	0	0	0	0	0
320	346329	1	0	0	0	0	0
321	346199	1	0	0	0	0	0
322	352595	1	0	0	0	0	0
323	346245	1	0	0	0	0	0
324	popilush-shapewear-dress-faux-leather-dresses-for-women-mock-neck-dress-night-club-outfits-for-women	0	0	1	0	0	0
342	329211	1	0	0	0	0	0
343	266745	1	0	0	0	0	0
347	263765	2	0	0	0	0	0
348	262854	2	0	0	0	0	0
349	265809	2	0	0	0	0	0
350	237121	2	0	0	0	0	0
325	fashion-jewelry-shoes	2	2	0	0	0	0
200	202595	0	0	2	1	0	0
238	266541	2	0	0	0	0	0
239	202921	2	0	0	0	0	0
232	202686	3	0	0	0	0	0
233	202925	2	0	0	0	0	0
221	womens-tulle-skirt-long-black-layered-maxi-midi-high-low-skirts-for-special-occasion-women	3	3	0	0	0	0
346	237137	2	0	0	0	0	0
345	320778	2	0	0	0	0	0
344	308412	2	0	0	0	0	0
234	267247	2	0	0	0	0	0
286	268734	2	0	0	0	0	0
206	202897	2	0	0	0	0	0
263	astr-the-label-womens-divine-skirt	1	1	1	0	0	0
408	181149	1	0	0	0	0	0
409	323140	1	0	0	0	0	0
410	327549	1	0	0	0	0	0
411	179008	1	0	0	0	0	0
412	267101	1	0	0	0	0	0
413	328966	1	0	0	0	0	0
414	266910	1	0	0	0	0	0
415	261385	1	0	0	0	0	0
416	259800	1	0	0	0	0	0
417	259633	1	0	0	0	0	0
428	278221	1	0	0	0	0	0
429	318864	1	0	0	0	0	0
430	178347	1	0	0	0	0	0
431	301469	1	0	0	0	0	0
432	318850	1	0	0	0	0	0
433	260164	1	0	0	0	0	0
434	327752	1	0	0	0	0	0
435	323157	1	0	0	0	0	0
436	120378	1	0	0	0	0	0
437	311678	1	0	0	0	0	0
378	259585	2	0	0	0	0	0
379	311781	2	0	0	0	0	0
380	178773	2	0	0	0	0	0
381	322860	2	0	0	0	0	0
382	327664	2	0	0	0	0	0
383	327683	2	0	0	0	0	0
384	178702	2	0	0	0	0	0
385	241955	2	0	0	0	0	0
386	260003	2	0	0	0	0	0
387	260251	2	0	0	0	0	0
407	324488	1	0	0	0	0	0
418	285207	1	0	0	0	0	0
419	281131	1	0	0	0	0	0
420	311172	1	0	0	0	0	0
421	260738	1	0	0	0	0	0
422	322843	1	0	0	0	0	0
423	179895	1	0	0	0	0	0
424	260264	1	0	0	0	0	0
425	259871	1	0	0	0	0	0
426	354333	1	0	0	0	0	0
427	354323	1	0	0	0	0	0
369	eevee-womens-casual-crop-hoodie-sweatshirt-long-sleeve-cute-cropped-plain-workout-drawstring-hooded-pullover-top	1	1	1	0	0	0
438	328953	1	0	0	0	0	0
439	178806	1	0	0	0	0	0
440	354380	1	0	0	0	0	0
441	354379	1	0	0	0	0	0
442	325529	1	0	0	0	0	0
443	328951	1	0	0	0	0	0
444	178916	1	0	0	0	0	0
445	178922	1	0	0	0	0	0
446	327744	1	0	0	0	0	0
372	260644	2	0	0	0	0	0
373	180976	2	0	0	0	0	0
374	327667	2	0	0	0	0	0
375	324499	2	0	0	0	0	0
376	354317	2	0	0	0	0	0
377	259951	2	0	0	0	0	0
388	260215	2	0	0	0	0	0
389	181155	2	0	0	0	0	0
390	260631	2	0	0	0	0	0
391	260046	2	0	0	0	0	0
392	327600	2	0	0	0	0	0
393	322864	2	0	0	0	0	0
394	260430	2	0	0	0	0	0
395	327587	2	0	0	0	0	0
396	325469	2	0	0	0	0	0
397	261382	2	0	0	0	0	0
398	301114	2	0	0	0	0	0
399	328972	2	0	0	0	0	0
400	325461	2	0	0	0	0	0
401	318798	2	0	0	0	0	0
402	311615	2	0	0	0	0	0
403	178994	2	0	0	0	0	0
404	327598	2	0	0	0	0	0
405	178379	2	0	0	0	0	0
406	314141	2	0	0	0	0	0
447	267755	1	0	0	0	0	0
448	266399	1	0	0	0	0	0
449	267630	1	0	0	0	0	0
450	267829	1	0	0	0	0	0
451	266811	1	0	0	0	0	0
453	267289	1	0	0	0	0	0
454	266983	1	0	0	0	0	0
455	267463	1	0	0	0	0	0
456	267338	1	0	0	0	0	0
457	267093	1	0	0	0	0	0
458	268737	1	0	0	0	0	0
459	266393	1	0	0	0	0	0
460	267753	1	0	0	0	0	0
461	267062	1	0	0	0	0	0
462	268759	1	0	0	0	0	0
463	266398	1	0	0	0	0	0
464	267259	1	0	0	0	0	0
465	266612	1	0	0	0	0	0
466	267430	1	0	0	0	0	0
467	268045	1	0	0	0	0	0
468	267771	1	0	0	0	0	0
469	266662	1	0	0	0	0	0
470	267695	1	0	0	0	0	0
471	202829	1	0	0	0	0	0
472	266480	1	0	0	0	0	0
473	267624	2	0	0	0	0	0
474	268480	2	0	0	0	0	0
475	268656	2	0	0	0	0	0
476	268080	2	0	0	0	0	0
477	267330	2	0	0	0	0	0
478	267396	2	0	0	0	0	0
479	267400	2	0	0	0	0	0
480	202679	2	0	0	0	0	0
481	267388	2	0	0	0	0	0
482	202873	1	0	0	0	0	0
483	267920	1	0	0	0	0	0
484	202786	1	0	0	0	0	0
485	268296	1	0	0	0	0	0
488	267922	1	0	0	0	0	0
489	268357	1	0	0	0	0	0
490	258906	1	0	0	0	0	0
491	268051	1	0	0	0	0	0
492	267060	1	0	0	0	0	0
493	202689	1	0	0	0	0	0
494	266998	1	0	0	0	0	0
495	267226	1	0	0	0	0	0
496	268339	1	0	0	0	0	0
486	266725	2	0	0	0	0	0
487	266999	2	0	0	0	0	0
452	268709	2	0	0	0	0	0
497	267079	1	0	0	0	0	0
498	202651	1	0	0	0	0	0
499	268145	1	0	0	0	0	0
500	202687	1	0	0	0	0	0
502	355037	1	0	0	0	0	0
504	354913	1	0	0	0	0	0
505	354956	1	0	0	0	0	0
508	355051	1	0	0	0	0	0
509	355010	1	0	0	0	0	0
510	355030	1	0	0	0	0	0
501	womens-plus-size-maxi-dress-elegant-v-neck-ruffle-sleeves-bodycon-mermaid-dresses-evening-gown	1	1	1	0	0	0
511	329291	1	0	0	0	0	0
512	354973	1	0	0	0	0	0
513	329285	1	0	0	0	0	0
515	329278	1	0	0	0	0	0
516	355018	1	0	0	0	0	0
518	355028	1	0	0	0	0	0
519	354919	1	0	0	0	0	0
520	355032	1	0	0	0	0	0
521	women-sexy-backless-halter-long-maxi-dress-deep-v-neck-ruffle-evening-dress-bodycon-party-cocktail-dresses	1	1	0	0	0	0
503	329228	2	0	0	0	0	0
514	329277	2	0	0	0	0	0
517	300891	2	0	0	0	0	0
522	329267	1	0	0	0	0	0
523	329241	1	0	0	0	0	0
524	329259	1	0	0	0	0	0
525	237169	1	0	0	0	0	0
526	237130	1	0	0	0	0	0
527	237118	1	0	0	0	0	0
528	329234	1	0	0	0	0	0
506	329236	2	0	0	0	0	0
507	237158	2	0	0	0	0	0
529	180072	1	0	0	0	0	0
530	329205	1	0	0	0	0	0
531	329215	1	0	0	0	0	0
532	327476	1	0	0	0	0	0
533	264753	1	0	0	0	0	0
534	329289	1	0	0	0	0	0
535	329270	1	0	0	0	0	0
536	brabic-womens-seamless-sleeveless-v-neck-bodysuit-shapewear-tummy-control	0	0	1	0	0	0
537	320784	1	0	0	0	0	0
541	320783	1	0	0	0	0	0
542	180292	1	0	0	0	0	0
543	354553	1	0	0	0	0	0
544	354554	1	0	0	0	0	0
545	spanx-seamless-power-thong-bodysuit-soft-seamless-shapewear-for-women-adjustable-straps-with-snap-closure	1	1	0	0	0	0
539	320801	2	0	0	0	0	0
540	320776	2	0	0	0	0	0
546	322053	1	0	0	0	0	0
547	322570	1	0	0	0	0	0
548	110051	1	0	0	0	0	0
549	320792	1	0	0	0	0	0
550	327762	1	0	0	0	0	0
551	354563	1	0	0	0	0	0
538	320799	2	0	0	0	0	0
552	110052	1	0	0	0	0	0
553	321945	1	0	0	0	0	0
554	110104	1	0	0	0	0	0
555	110030	1	0	0	0	0	0
567	262723	1	0	0	0	0	0
568	265548	1	0	0	0	0	0
569	265460	1	0	0	0	0	0
570	262382	1	0	0	0	0	0
571	263702	1	0	0	0	0	0
572	322765	1	0	0	0	0	0
573	262150	1	0	0	0	0	0
574	263199	1	0	0	0	0	0
575	265691	1	0	0	0	0	0
576	265193	1	0	0	0	0	0
577	264901	1	0	0	0	0	0
578	265092	1	0	0	0	0	0
579	261953	1	0	0	0	0	0
580	263070	1	0	0	0	0	0
581	328826	1	0	0	0	0	0
582	262142	1	0	0	0	0	0
583	262613	1	0	0	0	0	0
584	324754	1	0	0	0	0	0
585	322281	1	0	0	0	0	0
586	262296	1	0	0	0	0	0
556	adrianna-papell-womens-bell-sleeve-tie-front-dress	1	1	1	0	0	0
587	265717	1	0	0	0	0	0
588	262419	1	0	0	0	0	0
589	264452	1	0	0	0	0	0
590	264153	1	0	0	0	0	0
591	263189	1	0	0	0	0	0
592	263375	1	0	0	0	0	0
593	262479	1	0	0	0	0	0
594	265316	1	0	0	0	0	0
595	265336	1	0	0	0	0	0
557	262043	2	0	0	0	0	0
558	264823	2	0	0	0	0	0
596	265525	1	0	0	0	0	0
597	265948	2	0	0	0	0	0
598	265022	2	0	0	0	0	0
599	265580	2	0	0	0	0	0
600	322152	2	0	0	0	0	0
601	262051	2	0	0	0	0	0
602	262579	2	0	0	0	0	0
603	264887	2	0	0	0	0	0
604	322341	2	0	0	0	0	0
605	263515	2	0	0	0	0	0
606	263259	2	0	0	0	0	0
559	328120	2	0	0	0	0	0
560	263170	2	0	0	0	0	0
561	325885	2	0	0	0	0	0
562	266185	2	0	0	0	0	0
563	262669	2	0	0	0	0	0
564	265326	2	0	0	0	0	0
565	265614	2	0	0	0	0	0
566	265323	2	0	0	0	0	0
607	petticoat-skirt-for-women-under-dress-elastic-waist-chiffon-petticoat-puffy-tutu-tulle-skirt	0	0	1	0	0	0
608	266753	1	0	0	0	0	0
609	266384	1	0	0	0	0	0
610	266683	1	0	0	0	0	0
611	202666	1	0	0	0	0	0
612	266938	1	0	0	0	0	0
613	266638	1	0	0	0	0	0
615	285687	1	0	0	0	0	0
616	285481	1	0	0	0	0	0
617	281064	1	0	0	0	0	0
618	282619	1	0	0	0	0	0
619	118490	1	0	0	0	0	0
620	285306	1	0	0	0	0	0
621	238664	1	0	0	0	0	0
622	281871	1	0	0	0	0	0
623	239379	1	0	0	0	0	0
624	239464	1	0	0	0	0	0
625	279501	1	0	0	0	0	0
626	239942	1	0	0	0	0	0
627	282224	1	0	0	0	0	0
628	280775	1	0	0	0	0	0
629	281353	1	0	0	0	0	0
630	286927	1	0	0	0	0	0
631	282459	1	0	0	0	0	0
632	79708	1	0	0	0	0	0
633	285689	1	0	0	0	0	0
634	285852	1	0	0	0	0	0
635	286086	1	0	0	0	0	0
636	286063	1	0	0	0	0	0
637	280784	1	0	0	0	0	0
638	239129	1	0	0	0	0	0
639	254789	1	0	0	0	0	0
640	281290	1	0	0	0	0	0
641	285808	1	0	0	0	0	0
642	280049	1	0	0	0	0	0
643	285662	1	0	0	0	0	0
644	285336	1	0	0	0	0	0
645	269757	1	0	0	0	0	0
646	285593	1	0	0	0	0	0
647	285458	1	0	0	0	0	0
648	285349	1	0	0	0	0	0
649	118505	1	0	0	0	0	0
650	285764	1	0	0	0	0	0
651	239160	1	0	0	0	0	0
652	282573	1	0	0	0	0	0
653	286266	1	0	0	0	0	0
654	281229	1	0	0	0	0	0
655	298594	1	0	0	0	0	0
656	285664	1	0	0	0	0	0
657	280893	1	0	0	0	0	0
658	239648	1	0	0	0	0	0
659	329810	1	0	0	0	0	0
660	280787	1	0	0	0	0	0
661	238908	1	0	0	0	0	0
662	285405	1	0	0	0	0	0
663	285085	1	0	0	0	0	0
664	239130	1	0	0	0	0	0
614	carhartt-mens-rugged-flex-relaxed-fit-flannel-fleece-lined-hooded-shirt-jac	1	1	1	0	0	0
665	279729	2	0	0	0	0	0
666	285387	2	0	0	0	0	0
667	285392	2	0	0	0	0	0
668	238832	2	0	0	0	0	0
669	238686	2	0	0	0	0	0
670	283557	2	0	0	0	0	0
671	285383	2	0	0	0	0	0
672	286269	2	0	0	0	0	0
673	285344	2	0	0	0	0	0
674	279452	2	0	0	0	0	0
675	282785	1	0	0	0	0	0
676	238691	1	0	0	0	0	0
677	283519	1	0	0	0	0	0
678	239989	1	0	0	0	0	0
679	284243	1	0	0	0	0	0
680	286555	1	0	0	0	0	0
681	284009	1	0	0	0	0	0
682	285618	1	0	0	0	0	0
683	285471	1	0	0	0	0	0
684	286615	1	0	0	0	0	0
685	lioness-womens-hamptons-skirt	0	0	1	0	0	0
696	297181	1	0	0	0	0	0
697	267297	1	0	0	0	0	0
698	268676	1	0	0	0	0	0
699	268220	1	0	0	0	0	0
700	250071	1	0	0	0	0	0
701	268371	1	0	0	0	0	0
702	354304	1	0	0	0	0	0
703	268107	1	0	0	0	0	0
704	267283	1	0	0	0	0	0
705	267378	1	0	0	0	0	0
706	267926	1	0	0	0	0	0
707	267273	1	0	0	0	0	0
708	267857	1	0	0	0	0	0
709	267121	1	0	0	0	0	0
710	268344	1	0	0	0	0	0
711	268067	1	0	0	0	0	0
712	267950	1	0	0	0	0	0
713	267832	1	0	0	0	0	0
714	268722	1	0	0	0	0	0
686	261742	2	0	0	0	0	0
687	297861	2	0	0	0	0	0
688	299555	2	0	0	0	0	0
689	296943	2	0	0	0	0	0
690	296650	2	0	0	0	0	0
691	266992	2	0	0	0	0	0
692	267726	2	0	0	0	0	0
693	267538	2	0	0	0	0	0
694	267157	2	0	0	0	0	0
695	250102	2	0	0	0	0	0
715	tanming-womens-high-waist-pleated-long-denim-skirt	0	0	1	0	0	0
716	202658	1	0	0	0	0	0
717	266715	1	0	0	0	0	0
718	262129	1	0	0	0	0	0
719	202877	1	0	0	0	0	0
720	267958	1	0	0	0	0	0
721	268720	1	0	0	0	0	0
722	268167	1	0	0	0	0	0
723	270903	1	0	0	0	0	0
724	266703	1	0	0	0	0	0
725	267135	1	0	0	0	0	0
726	324740	1	0	0	0	0	0
727	267075	1	0	0	0	0	0
728	202564	1	0	0	0	0	0
729	268088	1	0	0	0	0	0
730	267711	1	0	0	0	0	0
731	267827	1	0	0	0	0	0
732	268211	1	0	0	0	0	0
733	266653	1	0	0	0	0	0
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

SELECT pg_catalog.setval('public.events_id_seq', 1235, true);


--
-- Name: order_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.order_items_id_seq', 1, false);


--
-- Name: product_metrics_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.product_metrics_id_seq', 733, true);


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
    ADD CONSTRAINT product_metrics_pkey PRIMARY KEY (id);


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
-- Name: ix_product_metrics_product_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_product_metrics_product_id ON public.product_metrics USING btree (product_id);


--
-- PostgreSQL database dump complete
--

\unrestrict GkE4UtdsFPr5h1oSDxAvHQrvSm72R8kufaaDNfh5RA5YyXAt0T6H51WoiDSsFK3

