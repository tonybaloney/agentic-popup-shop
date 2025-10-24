--
-- PostgreSQL database dump
--

\restrict 34IWWrc0AAR99H6LwePQt38hRUZntJS37Qe3O0ur8xMuUEUV7xfLFJPrRPh8GoU

-- Dumped from database version 17.6 (Debian 17.6-1.pgdg13+1)
-- Dumped by pg_dump version 17.6 (Debian 17.6-2.pgdg12+1)

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

--
-- Name: retail; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA retail;


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: approvers; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.approvers (
    approver_id integer NOT NULL,
    employee_id text NOT NULL,
    full_name text NOT NULL,
    email text NOT NULL,
    department text NOT NULL,
    approval_limit numeric(10,2) DEFAULT 0.00,
    is_active boolean DEFAULT true
);


--
-- Name: approvers_approver_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.approvers_approver_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: approvers_approver_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.approvers_approver_id_seq OWNED BY retail.approvers.approver_id;


--
-- Name: categories; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.categories (
    category_id integer NOT NULL,
    category_name text NOT NULL
);


--
-- Name: categories_category_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.categories_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: categories_category_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.categories_category_id_seq OWNED BY retail.categories.category_id;


--
-- Name: company_policies; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.company_policies (
    policy_id integer NOT NULL,
    policy_name text NOT NULL,
    policy_type text NOT NULL,
    policy_content text NOT NULL,
    department text,
    minimum_order_threshold numeric(10,2),
    approval_required boolean DEFAULT false,
    is_active boolean DEFAULT true,
    CONSTRAINT company_policies_policy_type_check CHECK ((policy_type = ANY (ARRAY['procurement'::text, 'order_processing'::text, 'budget_authorization'::text, 'vendor_approval'::text])))
);


--
-- Name: company_policies_policy_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.company_policies_policy_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: company_policies_policy_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.company_policies_policy_id_seq OWNED BY retail.company_policies.policy_id;


--
-- Name: customers; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.customers (
    customer_id integer NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL,
    phone text,
    primary_store_id integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: customers_customer_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.customers_customer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: customers_customer_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.customers_customer_id_seq OWNED BY retail.customers.customer_id;


--
-- Name: inventory; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.inventory (
    store_id integer NOT NULL,
    product_id integer NOT NULL,
    stock_level integer NOT NULL
);


--
-- Name: notifications; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.notifications (
    notification_id integer NOT NULL,
    request_id integer,
    notification_type text NOT NULL,
    recipient_email text NOT NULL,
    subject text NOT NULL,
    message text NOT NULL,
    sent_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    read_at timestamp without time zone,
    CONSTRAINT notifications_notification_type_check CHECK ((notification_type = ANY (ARRAY['approval_request'::text, 'status_update'::text, 'completion'::text])))
);


--
-- Name: notifications_notification_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.notifications_notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notifications_notification_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.notifications_notification_id_seq OWNED BY retail.notifications.notification_id;


--
-- Name: order_items; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.order_items (
    order_item_id integer NOT NULL,
    order_id integer NOT NULL,
    store_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    unit_price numeric(10,2) NOT NULL,
    discount_percent integer DEFAULT 0,
    discount_amount numeric(10,2) DEFAULT 0,
    total_amount numeric(10,2) NOT NULL
);


--
-- Name: order_items_order_item_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.order_items_order_item_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: order_items_order_item_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.order_items_order_item_id_seq OWNED BY retail.order_items.order_item_id;


--
-- Name: orders; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.orders (
    order_id integer NOT NULL,
    customer_id integer NOT NULL,
    store_id integer NOT NULL,
    order_date date NOT NULL
);


--
-- Name: orders_order_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.orders_order_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: orders_order_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.orders_order_id_seq OWNED BY retail.orders.order_id;


--
-- Name: procurement_requests; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.procurement_requests (
    request_id integer NOT NULL,
    request_number text NOT NULL,
    requester_name text NOT NULL,
    requester_email text NOT NULL,
    department text NOT NULL,
    product_id integer NOT NULL,
    supplier_id integer NOT NULL,
    quantity_requested integer NOT NULL,
    unit_cost numeric(10,2) NOT NULL,
    total_cost numeric(10,2) NOT NULL,
    justification text,
    urgency_level text DEFAULT 'Normal'::text,
    approval_status text DEFAULT 'Pending'::text,
    approved_by text,
    approved_at timestamp without time zone,
    request_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    required_by_date date,
    vendor_restrictions text,
    esg_requirements boolean DEFAULT false,
    bulk_discount_eligible boolean DEFAULT false,
    CONSTRAINT procurement_requests_approval_status_check CHECK ((approval_status = ANY (ARRAY['Pending'::text, 'Approved'::text, 'Rejected'::text, 'On Hold'::text]))),
    CONSTRAINT procurement_requests_urgency_level_check CHECK ((urgency_level = ANY (ARRAY['Low'::text, 'Normal'::text, 'High'::text, 'Critical'::text])))
);


--
-- Name: procurement_requests_request_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.procurement_requests_request_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: procurement_requests_request_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.procurement_requests_request_id_seq OWNED BY retail.procurement_requests.request_id;


--
-- Name: product_description_embeddings; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.product_description_embeddings (
    product_id integer NOT NULL,
    description_embedding public.vector(1536),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: product_image_embeddings; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.product_image_embeddings (
    product_id integer NOT NULL,
    image_url text NOT NULL,
    image_embedding public.vector(512),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: product_types; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.product_types (
    type_id integer NOT NULL,
    category_id integer NOT NULL,
    type_name text NOT NULL
);


--
-- Name: product_types_type_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.product_types_type_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: product_types_type_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.product_types_type_id_seq OWNED BY retail.product_types.type_id;


--
-- Name: products; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.products (
    product_id integer NOT NULL,
    sku text NOT NULL,
    product_name text NOT NULL,
    category_id integer NOT NULL,
    type_id integer NOT NULL,
    supplier_id integer NOT NULL,
    cost numeric(10,2) NOT NULL,
    base_price numeric(10,2) NOT NULL,
    gross_margin_percent numeric(5,2) DEFAULT 33.00,
    product_description text NOT NULL,
    procurement_lead_time_days integer DEFAULT 14,
    minimum_order_quantity integer DEFAULT 1,
    discontinued boolean DEFAULT false
);


--
-- Name: products_product_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.products_product_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_product_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.products_product_id_seq OWNED BY retail.products.product_id;


--
-- Name: stores; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.stores (
    store_id integer NOT NULL,
    store_name text NOT NULL,
    rls_user_id uuid NOT NULL,
    is_online boolean DEFAULT false NOT NULL
);


--
-- Name: stores_store_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.stores_store_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: stores_store_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.stores_store_id_seq OWNED BY retail.stores.store_id;


--
-- Name: supplier_contracts; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.supplier_contracts (
    contract_id integer NOT NULL,
    supplier_id integer NOT NULL,
    contract_number text NOT NULL,
    contract_status text DEFAULT 'active'::text,
    start_date date NOT NULL,
    end_date date,
    contract_value numeric(12,2),
    payment_terms text NOT NULL,
    auto_renew boolean DEFAULT false,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT supplier_contracts_contract_status_check CHECK ((contract_status = ANY (ARRAY['active'::text, 'expired'::text, 'terminated'::text])))
);


--
-- Name: supplier_contracts_contract_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.supplier_contracts_contract_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supplier_contracts_contract_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.supplier_contracts_contract_id_seq OWNED BY retail.supplier_contracts.contract_id;


--
-- Name: supplier_performance; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.supplier_performance (
    performance_id integer NOT NULL,
    supplier_id integer NOT NULL,
    evaluation_date date NOT NULL,
    cost_score numeric(3,2) DEFAULT 3.00,
    quality_score numeric(3,2) DEFAULT 3.00,
    delivery_score numeric(3,2) DEFAULT 3.00,
    compliance_score numeric(3,2) DEFAULT 3.00,
    overall_score numeric(3,2) DEFAULT 3.00,
    notes text,
    CONSTRAINT supplier_performance_compliance_score_check CHECK (((compliance_score >= (0)::numeric) AND (compliance_score <= (5)::numeric))),
    CONSTRAINT supplier_performance_cost_score_check CHECK (((cost_score >= (0)::numeric) AND (cost_score <= (5)::numeric))),
    CONSTRAINT supplier_performance_delivery_score_check CHECK (((delivery_score >= (0)::numeric) AND (delivery_score <= (5)::numeric))),
    CONSTRAINT supplier_performance_overall_score_check CHECK (((overall_score >= (0)::numeric) AND (overall_score <= (5)::numeric))),
    CONSTRAINT supplier_performance_quality_score_check CHECK (((quality_score >= (0)::numeric) AND (quality_score <= (5)::numeric)))
);


--
-- Name: supplier_performance_performance_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.supplier_performance_performance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: supplier_performance_performance_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.supplier_performance_performance_id_seq OWNED BY retail.supplier_performance.performance_id;


--
-- Name: suppliers; Type: TABLE; Schema: retail; Owner: -
--

CREATE TABLE retail.suppliers (
    supplier_id integer NOT NULL,
    supplier_name text NOT NULL,
    supplier_code text NOT NULL,
    contact_email text,
    contact_phone text,
    address_line1 text,
    address_line2 text,
    city text,
    state_province text,
    postal_code text,
    country text DEFAULT 'USA'::text,
    payment_terms text DEFAULT 'Net 30'::text,
    lead_time_days integer DEFAULT 14,
    minimum_order_amount numeric(10,2) DEFAULT 0.00,
    bulk_discount_threshold numeric(10,2) DEFAULT 10000.00,
    bulk_discount_percent numeric(5,2) DEFAULT 5.00,
    supplier_rating numeric(3,2) DEFAULT 3.00,
    esg_compliant boolean DEFAULT true,
    approved_vendor boolean DEFAULT true,
    preferred_vendor boolean DEFAULT false,
    active_status boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    last_updated timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT suppliers_supplier_rating_check CHECK (((supplier_rating >= (0)::numeric) AND (supplier_rating <= (5)::numeric)))
);


--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE; Schema: retail; Owner: -
--

CREATE SEQUENCE retail.suppliers_supplier_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: suppliers_supplier_id_seq; Type: SEQUENCE OWNED BY; Schema: retail; Owner: -
--

ALTER SEQUENCE retail.suppliers_supplier_id_seq OWNED BY retail.suppliers.supplier_id;


--
-- Name: vw_company_supplier_policies; Type: VIEW; Schema: retail; Owner: -
--

CREATE VIEW retail.vw_company_supplier_policies AS
 SELECT policy_id,
    policy_name,
    policy_type,
    policy_content,
    department,
    minimum_order_threshold,
    approval_required,
    is_active,
        CASE
            WHEN (policy_type = 'procurement'::text) THEN 'Covers supplier selection and procurement processes'::text
            WHEN (policy_type = 'vendor_approval'::text) THEN 'Defines vendor approval and onboarding requirements'::text
            WHEN (policy_type = 'budget_authorization'::text) THEN 'Specifies budget limits and authorization levels'::text
            WHEN (policy_type = 'order_processing'::text) THEN 'Outlines order processing and fulfillment procedures'::text
            ELSE 'General company policy'::text
        END AS policy_description,
    length(policy_content) AS content_length
   FROM retail.company_policies
  WHERE (is_active = true);


--
-- Name: vw_supplier_contract_details; Type: VIEW; Schema: retail; Owner: -
--

CREATE VIEW retail.vw_supplier_contract_details AS
 SELECT s.supplier_id,
    s.supplier_name,
    s.supplier_code,
    s.contact_email,
    s.contact_phone,
    sc.contract_id,
    sc.contract_number,
    sc.contract_status,
    sc.start_date,
    sc.end_date,
    sc.contract_value,
    sc.payment_terms,
    sc.auto_renew,
    sc.created_at AS contract_created,
        CASE
            WHEN (sc.end_date IS NOT NULL) THEN (sc.end_date - CURRENT_DATE)
            ELSE NULL::integer
        END AS days_until_expiry,
        CASE
            WHEN ((sc.end_date IS NOT NULL) AND (sc.end_date <= (CURRENT_DATE + '90 days'::interval))) THEN true
            ELSE false
        END AS renewal_due_soon
   FROM (retail.suppliers s
     LEFT JOIN retail.supplier_contracts sc ON ((s.supplier_id = sc.supplier_id)))
  WHERE ((sc.contract_status = 'active'::text) OR (sc.contract_status IS NULL));


--
-- Name: vw_supplier_history_performance; Type: VIEW; Schema: retail; Owner: -
--

CREATE VIEW retail.vw_supplier_history_performance AS
 SELECT s.supplier_id,
    s.supplier_name,
    s.supplier_code,
    s.supplier_rating,
    s.esg_compliant,
    s.preferred_vendor,
    s.lead_time_days,
    s.created_at AS supplier_since,
    sp.evaluation_date,
    sp.cost_score,
    sp.quality_score,
    sp.delivery_score,
    sp.compliance_score,
    sp.overall_score,
    sp.notes AS performance_notes,
    count(pr.request_id) OVER (PARTITION BY s.supplier_id) AS total_requests,
    sum(pr.total_cost) OVER (PARTITION BY s.supplier_id) AS total_value
   FROM ((retail.suppliers s
     LEFT JOIN retail.supplier_performance sp ON ((s.supplier_id = sp.supplier_id)))
     LEFT JOIN retail.procurement_requests pr ON ((s.supplier_id = pr.supplier_id)));


--
-- Name: vw_suppliers_for_request; Type: VIEW; Schema: retail; Owner: -
--

CREATE VIEW retail.vw_suppliers_for_request AS
 SELECT DISTINCT s.supplier_id,
    s.supplier_name,
    s.supplier_code,
    s.contact_email,
    s.contact_phone,
    s.supplier_rating,
    s.esg_compliant,
    s.preferred_vendor,
    s.approved_vendor,
    s.lead_time_days,
    s.minimum_order_amount,
    s.bulk_discount_threshold,
    s.bulk_discount_percent,
    s.payment_terms,
    count(p.product_id) AS available_products,
    COALESCE(avg(sp.overall_score), s.supplier_rating) AS avg_performance_score,
    sc.contract_status,
    sc.contract_number,
    c.category_name
   FROM ((((retail.suppliers s
     LEFT JOIN retail.products p ON ((s.supplier_id = p.supplier_id)))
     LEFT JOIN retail.categories c ON ((p.category_id = c.category_id)))
     LEFT JOIN retail.supplier_performance sp ON (((s.supplier_id = sp.supplier_id) AND (sp.evaluation_date >= (CURRENT_DATE - '6 mons'::interval)))))
     LEFT JOIN retail.supplier_contracts sc ON (((s.supplier_id = sc.supplier_id) AND (sc.contract_status = 'active'::text))))
  WHERE ((s.active_status = true) AND (s.approved_vendor = true))
  GROUP BY s.supplier_id, s.supplier_name, s.supplier_code, s.contact_email, s.contact_phone, s.supplier_rating, s.esg_compliant, s.preferred_vendor, s.approved_vendor, s.lead_time_days, s.minimum_order_amount, s.bulk_discount_threshold, s.bulk_discount_percent, s.payment_terms, sc.contract_status, sc.contract_number, c.category_name;


--
-- Name: approvers approver_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.approvers ALTER COLUMN approver_id SET DEFAULT nextval('retail.approvers_approver_id_seq'::regclass);


--
-- Name: categories category_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.categories ALTER COLUMN category_id SET DEFAULT nextval('retail.categories_category_id_seq'::regclass);


--
-- Name: company_policies policy_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.company_policies ALTER COLUMN policy_id SET DEFAULT nextval('retail.company_policies_policy_id_seq'::regclass);


--
-- Name: customers customer_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.customers ALTER COLUMN customer_id SET DEFAULT nextval('retail.customers_customer_id_seq'::regclass);


--
-- Name: notifications notification_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.notifications ALTER COLUMN notification_id SET DEFAULT nextval('retail.notifications_notification_id_seq'::regclass);


--
-- Name: order_items order_item_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.order_items ALTER COLUMN order_item_id SET DEFAULT nextval('retail.order_items_order_item_id_seq'::regclass);


--
-- Name: orders order_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.orders ALTER COLUMN order_id SET DEFAULT nextval('retail.orders_order_id_seq'::regclass);


--
-- Name: procurement_requests request_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.procurement_requests ALTER COLUMN request_id SET DEFAULT nextval('retail.procurement_requests_request_id_seq'::regclass);


--
-- Name: product_types type_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_types ALTER COLUMN type_id SET DEFAULT nextval('retail.product_types_type_id_seq'::regclass);


--
-- Name: products product_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products ALTER COLUMN product_id SET DEFAULT nextval('retail.products_product_id_seq'::regclass);


--
-- Name: stores store_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.stores ALTER COLUMN store_id SET DEFAULT nextval('retail.stores_store_id_seq'::regclass);


--
-- Name: supplier_contracts contract_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_contracts ALTER COLUMN contract_id SET DEFAULT nextval('retail.supplier_contracts_contract_id_seq'::regclass);


--
-- Name: supplier_performance performance_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_performance ALTER COLUMN performance_id SET DEFAULT nextval('retail.supplier_performance_performance_id_seq'::regclass);


--
-- Name: suppliers supplier_id; Type: DEFAULT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.suppliers ALTER COLUMN supplier_id SET DEFAULT nextval('retail.suppliers_supplier_id_seq'::regclass);


--
-- Name: approvers approvers_employee_id_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.approvers
    ADD CONSTRAINT approvers_employee_id_key UNIQUE (employee_id);


--
-- Name: approvers approvers_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.approvers
    ADD CONSTRAINT approvers_pkey PRIMARY KEY (approver_id);


--
-- Name: categories categories_category_name_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.categories
    ADD CONSTRAINT categories_category_name_key UNIQUE (category_name);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (category_id);


--
-- Name: company_policies company_policies_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.company_policies
    ADD CONSTRAINT company_policies_pkey PRIMARY KEY (policy_id);


--
-- Name: customers customers_email_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.customers
    ADD CONSTRAINT customers_email_key UNIQUE (email);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (customer_id);


--
-- Name: inventory inventory_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.inventory
    ADD CONSTRAINT inventory_pkey PRIMARY KEY (store_id, product_id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (notification_id);


--
-- Name: order_items order_items_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.order_items
    ADD CONSTRAINT order_items_pkey PRIMARY KEY (order_item_id);


--
-- Name: orders orders_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.orders
    ADD CONSTRAINT orders_pkey PRIMARY KEY (order_id);


--
-- Name: procurement_requests procurement_requests_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.procurement_requests
    ADD CONSTRAINT procurement_requests_pkey PRIMARY KEY (request_id);


--
-- Name: procurement_requests procurement_requests_request_number_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.procurement_requests
    ADD CONSTRAINT procurement_requests_request_number_key UNIQUE (request_number);


--
-- Name: product_description_embeddings product_description_embeddings_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_description_embeddings
    ADD CONSTRAINT product_description_embeddings_pkey PRIMARY KEY (product_id);


--
-- Name: product_image_embeddings product_image_embeddings_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_image_embeddings
    ADD CONSTRAINT product_image_embeddings_pkey PRIMARY KEY (product_id);


--
-- Name: product_types product_types_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_types
    ADD CONSTRAINT product_types_pkey PRIMARY KEY (type_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: products products_sku_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products
    ADD CONSTRAINT products_sku_key UNIQUE (sku);


--
-- Name: stores stores_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.stores
    ADD CONSTRAINT stores_pkey PRIMARY KEY (store_id);


--
-- Name: stores stores_store_name_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.stores
    ADD CONSTRAINT stores_store_name_key UNIQUE (store_name);


--
-- Name: supplier_contracts supplier_contracts_contract_number_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_contracts
    ADD CONSTRAINT supplier_contracts_contract_number_key UNIQUE (contract_number);


--
-- Name: supplier_contracts supplier_contracts_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_contracts
    ADD CONSTRAINT supplier_contracts_pkey PRIMARY KEY (contract_id);


--
-- Name: supplier_performance supplier_performance_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_performance
    ADD CONSTRAINT supplier_performance_pkey PRIMARY KEY (performance_id);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (supplier_id);


--
-- Name: suppliers suppliers_supplier_code_key; Type: CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.suppliers
    ADD CONSTRAINT suppliers_supplier_code_key UNIQUE (supplier_code);


--
-- Name: idx_approvers_department; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_approvers_department ON retail.approvers USING btree (department);


--
-- Name: idx_approvers_limit; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_approvers_limit ON retail.approvers USING btree (approval_limit);


--
-- Name: idx_categories_name; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_categories_name ON retail.categories USING btree (category_name);


--
-- Name: idx_company_policies_threshold; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_company_policies_threshold ON retail.company_policies USING btree (minimum_order_threshold);


--
-- Name: idx_company_policies_type; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_company_policies_type ON retail.company_policies USING btree (policy_type);


--
-- Name: idx_customers_email; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_customers_email ON retail.customers USING btree (email);


--
-- Name: idx_customers_primary_store; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_customers_primary_store ON retail.customers USING btree (primary_store_id);


--
-- Name: idx_inventory_product; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_inventory_product ON retail.inventory USING btree (product_id);


--
-- Name: idx_inventory_store; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_inventory_store ON retail.inventory USING btree (store_id);


--
-- Name: idx_inventory_store_product; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_inventory_store_product ON retail.inventory USING btree (store_id, product_id);


--
-- Name: idx_notifications_request; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_notifications_request ON retail.notifications USING btree (request_id);


--
-- Name: idx_notifications_type; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_notifications_type ON retail.notifications USING btree (notification_type);


--
-- Name: idx_order_items_covering; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_order_items_covering ON retail.order_items USING btree (order_id, store_id, product_id, total_amount, quantity);


--
-- Name: idx_order_items_order; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_order_items_order ON retail.order_items USING btree (order_id);


--
-- Name: idx_order_items_product; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_order_items_product ON retail.order_items USING btree (product_id);


--
-- Name: idx_order_items_store; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_order_items_store ON retail.order_items USING btree (store_id);


--
-- Name: idx_order_items_total; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_order_items_total ON retail.order_items USING btree (total_amount);


--
-- Name: idx_orders_customer; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_orders_customer ON retail.orders USING btree (customer_id);


--
-- Name: idx_orders_customer_date; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_orders_customer_date ON retail.orders USING btree (customer_id, order_date);


--
-- Name: idx_orders_date; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_orders_date ON retail.orders USING btree (order_date);


--
-- Name: idx_orders_store; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_orders_store ON retail.orders USING btree (store_id);


--
-- Name: idx_orders_store_date; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_orders_store_date ON retail.orders USING btree (store_id, order_date);


--
-- Name: idx_procurement_requests_date; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_date ON retail.procurement_requests USING btree (request_date);


--
-- Name: idx_procurement_requests_department; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_department ON retail.procurement_requests USING btree (department);


--
-- Name: idx_procurement_requests_number; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_number ON retail.procurement_requests USING btree (request_number);


--
-- Name: idx_procurement_requests_product; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_product ON retail.procurement_requests USING btree (product_id);


--
-- Name: idx_procurement_requests_requester; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_requester ON retail.procurement_requests USING btree (requester_email);


--
-- Name: idx_procurement_requests_status; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_status ON retail.procurement_requests USING btree (approval_status);


--
-- Name: idx_procurement_requests_supplier; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_supplier ON retail.procurement_requests USING btree (supplier_id);


--
-- Name: idx_procurement_requests_urgency; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_procurement_requests_urgency ON retail.procurement_requests USING btree (urgency_level);


--
-- Name: idx_product_description_embeddings_vector; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_description_embeddings_vector ON retail.product_description_embeddings USING ivfflat (description_embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_product_image_embeddings_product; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_image_embeddings_product ON retail.product_image_embeddings USING btree (product_id);


--
-- Name: idx_product_image_embeddings_url; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_image_embeddings_url ON retail.product_image_embeddings USING btree (image_url);


--
-- Name: idx_product_image_embeddings_vector; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_image_embeddings_vector ON retail.product_image_embeddings USING ivfflat (image_embedding public.vector_cosine_ops) WITH (lists='100');


--
-- Name: idx_product_types_category; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_types_category ON retail.product_types USING btree (category_id);


--
-- Name: idx_product_types_name; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_product_types_name ON retail.product_types USING btree (type_name);


--
-- Name: idx_products_category; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_category ON retail.products USING btree (category_id);


--
-- Name: idx_products_cost; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_cost ON retail.products USING btree (cost);


--
-- Name: idx_products_covering; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_covering ON retail.products USING btree (category_id, type_id, product_id, sku, cost, base_price);


--
-- Name: idx_products_discontinued; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_discontinued ON retail.products USING btree (discontinued);


--
-- Name: idx_products_lead_time; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_lead_time ON retail.products USING btree (procurement_lead_time_days);


--
-- Name: idx_products_margin; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_margin ON retail.products USING btree (gross_margin_percent);


--
-- Name: idx_products_price; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_price ON retail.products USING btree (base_price);


--
-- Name: idx_products_sku; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_sku ON retail.products USING btree (sku);


--
-- Name: idx_products_sku_covering; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_sku_covering ON retail.products USING btree (sku, product_id, product_name, cost, base_price);


--
-- Name: idx_products_supplier; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_supplier ON retail.products USING btree (supplier_id);


--
-- Name: idx_products_type; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_products_type ON retail.products USING btree (type_id);


--
-- Name: idx_stores_name; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_stores_name ON retail.stores USING btree (store_name);


--
-- Name: idx_supplier_contracts_status; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_supplier_contracts_status ON retail.supplier_contracts USING btree (contract_status);


--
-- Name: idx_supplier_contracts_supplier; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_supplier_contracts_supplier ON retail.supplier_contracts USING btree (supplier_id);


--
-- Name: idx_supplier_performance_date; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_supplier_performance_date ON retail.supplier_performance USING btree (evaluation_date);


--
-- Name: idx_supplier_performance_overall; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_supplier_performance_overall ON retail.supplier_performance USING btree (overall_score);


--
-- Name: idx_supplier_performance_supplier; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_supplier_performance_supplier ON retail.supplier_performance USING btree (supplier_id);


--
-- Name: idx_suppliers_active; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_active ON retail.suppliers USING btree (active_status);


--
-- Name: idx_suppliers_approved; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_approved ON retail.suppliers USING btree (approved_vendor);


--
-- Name: idx_suppliers_code; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_code ON retail.suppliers USING btree (supplier_code);


--
-- Name: idx_suppliers_esg; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_esg ON retail.suppliers USING btree (esg_compliant);


--
-- Name: idx_suppliers_name; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_name ON retail.suppliers USING btree (supplier_name);


--
-- Name: idx_suppliers_preferred; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_preferred ON retail.suppliers USING btree (preferred_vendor);


--
-- Name: idx_suppliers_rating; Type: INDEX; Schema: retail; Owner: -
--

CREATE INDEX idx_suppliers_rating ON retail.suppliers USING btree (supplier_rating);


--
-- Name: customers customers_primary_store_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.customers
    ADD CONSTRAINT customers_primary_store_id_fkey FOREIGN KEY (primary_store_id) REFERENCES retail.stores(store_id);


--
-- Name: inventory inventory_product_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.inventory
    ADD CONSTRAINT inventory_product_id_fkey FOREIGN KEY (product_id) REFERENCES retail.products(product_id);


--
-- Name: inventory inventory_store_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.inventory
    ADD CONSTRAINT inventory_store_id_fkey FOREIGN KEY (store_id) REFERENCES retail.stores(store_id);


--
-- Name: notifications notifications_request_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.notifications
    ADD CONSTRAINT notifications_request_id_fkey FOREIGN KEY (request_id) REFERENCES retail.procurement_requests(request_id);


--
-- Name: order_items order_items_order_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.order_items
    ADD CONSTRAINT order_items_order_id_fkey FOREIGN KEY (order_id) REFERENCES retail.orders(order_id);


--
-- Name: order_items order_items_product_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.order_items
    ADD CONSTRAINT order_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES retail.products(product_id);


--
-- Name: order_items order_items_store_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.order_items
    ADD CONSTRAINT order_items_store_id_fkey FOREIGN KEY (store_id) REFERENCES retail.stores(store_id);


--
-- Name: orders orders_customer_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.orders
    ADD CONSTRAINT orders_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES retail.customers(customer_id);


--
-- Name: orders orders_store_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.orders
    ADD CONSTRAINT orders_store_id_fkey FOREIGN KEY (store_id) REFERENCES retail.stores(store_id);


--
-- Name: procurement_requests procurement_requests_product_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.procurement_requests
    ADD CONSTRAINT procurement_requests_product_id_fkey FOREIGN KEY (product_id) REFERENCES retail.products(product_id);


--
-- Name: procurement_requests procurement_requests_supplier_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.procurement_requests
    ADD CONSTRAINT procurement_requests_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES retail.suppliers(supplier_id);


--
-- Name: product_description_embeddings product_description_embeddings_product_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_description_embeddings
    ADD CONSTRAINT product_description_embeddings_product_id_fkey FOREIGN KEY (product_id) REFERENCES retail.products(product_id);


--
-- Name: product_image_embeddings product_image_embeddings_product_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_image_embeddings
    ADD CONSTRAINT product_image_embeddings_product_id_fkey FOREIGN KEY (product_id) REFERENCES retail.products(product_id);


--
-- Name: product_types product_types_category_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.product_types
    ADD CONSTRAINT product_types_category_id_fkey FOREIGN KEY (category_id) REFERENCES retail.categories(category_id);


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES retail.categories(category_id);


--
-- Name: products products_supplier_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products
    ADD CONSTRAINT products_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES retail.suppliers(supplier_id);


--
-- Name: products products_type_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.products
    ADD CONSTRAINT products_type_id_fkey FOREIGN KEY (type_id) REFERENCES retail.product_types(type_id);


--
-- Name: supplier_contracts supplier_contracts_supplier_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_contracts
    ADD CONSTRAINT supplier_contracts_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES retail.suppliers(supplier_id);


--
-- Name: supplier_performance supplier_performance_supplier_id_fkey; Type: FK CONSTRAINT; Schema: retail; Owner: -
--

ALTER TABLE ONLY retail.supplier_performance
    ADD CONSTRAINT supplier_performance_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES retail.suppliers(supplier_id);


--
-- Name: categories all_users_categories; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_categories ON retail.categories USING (true);


--
-- Name: procurement_requests all_users_procurement_requests; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_procurement_requests ON retail.procurement_requests USING (true);


--
-- Name: product_description_embeddings all_users_product_description_embeddings; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_product_description_embeddings ON retail.product_description_embeddings USING (true);


--
-- Name: product_image_embeddings all_users_product_image_embeddings; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_product_image_embeddings ON retail.product_image_embeddings USING (true);


--
-- Name: product_types all_users_product_types; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_product_types ON retail.product_types USING (true);


--
-- Name: products all_users_products; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_products ON retail.products USING (true);


--
-- Name: stores all_users_stores; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_stores ON retail.stores USING (true);


--
-- Name: supplier_performance all_users_supplier_performance; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_supplier_performance ON retail.supplier_performance USING (true);


--
-- Name: suppliers all_users_suppliers; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY all_users_suppliers ON retail.suppliers USING (true);


--
-- Name: categories; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.categories ENABLE ROW LEVEL SECURITY;

--
-- Name: customers; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.customers ENABLE ROW LEVEL SECURITY;

--
-- Name: inventory; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.inventory ENABLE ROW LEVEL SECURITY;

--
-- Name: order_items; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.order_items ENABLE ROW LEVEL SECURITY;

--
-- Name: orders; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.orders ENABLE ROW LEVEL SECURITY;

--
-- Name: procurement_requests; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.procurement_requests ENABLE ROW LEVEL SECURITY;

--
-- Name: product_description_embeddings; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.product_description_embeddings ENABLE ROW LEVEL SECURITY;

--
-- Name: product_image_embeddings; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.product_image_embeddings ENABLE ROW LEVEL SECURITY;

--
-- Name: product_types; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.product_types ENABLE ROW LEVEL SECURITY;

--
-- Name: products; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.products ENABLE ROW LEVEL SECURITY;

--
-- Name: customers store_manager_customers; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY store_manager_customers ON retail.customers USING (((current_setting('app.current_rls_user_id'::text, true) = '00000000-0000-0000-0000-000000000000'::text) OR (EXISTS ( SELECT 1
   FROM retail.stores s
  WHERE ((s.store_id = customers.primary_store_id) AND ((s.rls_user_id)::text = current_setting('app.current_rls_user_id'::text, true))))) OR (EXISTS ( SELECT 1
   FROM (retail.orders o
     JOIN retail.stores s ON ((o.store_id = s.store_id)))
  WHERE ((o.customer_id = customers.customer_id) AND ((s.rls_user_id)::text = current_setting('app.current_rls_user_id'::text, true)))))));


--
-- Name: inventory store_manager_inventory; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY store_manager_inventory ON retail.inventory USING (((current_setting('app.current_rls_user_id'::text, true) = '00000000-0000-0000-0000-000000000000'::text) OR (EXISTS ( SELECT 1
   FROM retail.stores s
  WHERE ((s.store_id = inventory.store_id) AND ((s.rls_user_id)::text = current_setting('app.current_rls_user_id'::text, true)))))));


--
-- Name: order_items store_manager_order_items; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY store_manager_order_items ON retail.order_items USING (((current_setting('app.current_rls_user_id'::text, true) = '00000000-0000-0000-0000-000000000000'::text) OR (EXISTS ( SELECT 1
   FROM retail.stores s
  WHERE ((s.store_id = order_items.store_id) AND ((s.rls_user_id)::text = current_setting('app.current_rls_user_id'::text, true)))))));


--
-- Name: orders store_manager_orders; Type: POLICY; Schema: retail; Owner: -
--

CREATE POLICY store_manager_orders ON retail.orders USING (((current_setting('app.current_rls_user_id'::text, true) = '00000000-0000-0000-0000-000000000000'::text) OR (EXISTS ( SELECT 1
   FROM retail.stores s
  WHERE ((s.store_id = orders.store_id) AND ((s.rls_user_id)::text = current_setting('app.current_rls_user_id'::text, true)))))));


--
-- Name: stores; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.stores ENABLE ROW LEVEL SECURITY;

--
-- Name: supplier_performance; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.supplier_performance ENABLE ROW LEVEL SECURITY;

--
-- Name: suppliers; Type: ROW SECURITY; Schema: retail; Owner: -
--

ALTER TABLE retail.suppliers ENABLE ROW LEVEL SECURITY;

--
-- PostgreSQL database dump complete
--

\unrestrict 34IWWrc0AAR99H6LwePQt38hRUZntJS37Qe3O0ur8xMuUEUV7xfLFJPrRPh8GoU

