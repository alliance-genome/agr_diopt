--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET escape_string_warning = off;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: datetime; Type: DOMAIN; Schema: public; Owner: postgres
--

CREATE DOMAIN datetime AS timestamp without time zone;


ALTER DOMAIN public.datetime OWNER TO postgres;

--
-- Name: yes_no; Type: TYPE; Schema: public; Owner: diopt
--

CREATE TYPE yes_no AS ENUM (
    'Yes',
    'No'
);


ALTER TYPE public.yes_no OWNER TO diopt;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: gene_information; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE gene_information (
    geneid integer NOT NULL,
    speciesid integer NOT NULL,
    symbol character varying(50) NOT NULL,
    description text,
    locus_tag character varying(50),
    species_specific_geneid character varying(50),
    species_specific_geneid_type character varying(50),
    chromosome character varying(50),
    map_location character varying(50),
    gene_type character varying(50) NOT NULL
);


ALTER TABLE public.gene_information OWNER TO diopt;

--
-- Name: ortholog_pair; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE ortholog_pair (
    ortholog_pairid integer NOT NULL,
    speciesid1 integer NOT NULL,
    geneid1 integer NOT NULL,
    speciesid2 integer NOT NULL,
    geneid2 integer NOT NULL,
    prediction_method character varying(50) NOT NULL,
    blast_score integer,
    orig_score character varying(50),
    orig_score_information character varying(50),
    orig_clusterid character varying(50),
    url character varying(100)
);


ALTER TABLE public.ortholog_pair OWNER TO diopt;

--
-- Name: ortholog_pair_best; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE ortholog_pair_best (
    speciesid1 integer NOT NULL,
    geneid1 integer NOT NULL,
    speciesid2 integer NOT NULL,
    geneid2 integer NOT NULL,
    score integer NOT NULL,
    best_score character varying(50) NOT NULL,
    best_score_rev character varying(50) NOT NULL,
    confidence character varying(10) NOT NULL
);


ALTER TABLE public.ortholog_pair_best OWNER TO diopt;

--
-- Name: protein; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE protein (
    proteinid integer NOT NULL,
    speciesid integer NOT NULL,
    protein_acc character varying(50) NOT NULL,
    protein_version character varying(50),
    protein_gi character varying(50),
    protein_length integer NOT NULL,
    protein_sequence text,
    source character varying(50),
    status character varying(50),
    geneid integer NOT NULL,
    protein_count integer NOT NULL
);


ALTER TABLE public.protein OWNER TO diopt;

--
-- Name: protein_feature; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE protein_feature (
    featureid integer NOT NULL,
    proteinid integer NOT NULL,
    feature_type character varying(50) NOT NULL,
    protein_version character varying(50),
    start character varying(50),
    stop character varying(50),
    name text,
    description text,
    external_id character varying(50)
);


ALTER TABLE public.protein_feature OWNER TO diopt;

--
-- Name: protein_pair; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE protein_pair (
    protein_pair_id integer NOT NULL,
    proteinid1 integer NOT NULL,
    geneid1 integer NOT NULL,
    status1 character varying(50),
    proteinid2 integer NOT NULL,
    geneid2 integer NOT NULL,
    status2 character varying(50),
    align_seq1 text,
    start_pos1 integer,
    end_pos1 integer,
    align_seq2 text,
    start_pos2 integer,
    end_pos2 integer,
    match_seq text,
    align_score numeric(10,1),
    align_identity numeric(12,6),
    align_length integer,
    align_similarity numeric(12,6),
    align_gaps numeric(12,5),
    align_identity_count integer,
    align_similarity_count integer,
    align_gaps_count integer,
    comment text
);


ALTER TABLE public.protein_pair OWNER TO diopt;

--
-- Name: species; Type: TABLE; Schema: public; Owner: diopt; Tablespace: 
--

CREATE TABLE species (
    speciesid integer NOT NULL,
    species_name character varying(50),
    short_species_name character varying(2),
    common_name character varying(20),
    species_specific_geneid_type character varying(20),
    species_specific_database_url text,
    species_specific_url_format text,
    display_order integer
);


ALTER TABLE public.species OWNER TO diopt;

--
-- Name: gene_information_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY gene_information
    ADD CONSTRAINT gene_information_pkey PRIMARY KEY (geneid);


--
-- Name: ortholog_pair_best_unique; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY ortholog_pair_best
    ADD CONSTRAINT ortholog_pair_best_unique UNIQUE (geneid1, geneid2);


--
-- Name: ortholog_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY ortholog_pair
    ADD CONSTRAINT ortholog_pair_pkey PRIMARY KEY (ortholog_pairid);


--
-- Name: p1_p2_unique; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY protein_pair
    ADD CONSTRAINT p1_p2_unique UNIQUE (proteinid1, proteinid2);

--
-- Name: protein_pair_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY protein_pair
    ADD CONSTRAINT protein_pair_pkey UNIQUE (protein_pair_id);

--
-- Name: protein_feature_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY protein_feature
    ADD CONSTRAINT protein_feature_pkey PRIMARY KEY (featureid);


--
-- Name: protein_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY protein
    ADD CONSTRAINT protein_pkey PRIMARY KEY (proteinid);


--
-- Name: species_pkey; Type: CONSTRAINT; Schema: public; Owner: diopt; Tablespace: 
--

ALTER TABLE ONLY species
    ADD CONSTRAINT species_pkey PRIMARY KEY (speciesid);


--
-- Name: ortholog_pair__best_geneid1_geneid2_key; Type: INDEX; Schema: public; Owner: diopt; Tablespace: 
--

CREATE INDEX ortholog_pair__best_geneid1_geneid2_key ON ortholog_pair_best USING btree (geneid1, geneid2);


--
-- Name: ortholog_pair_geneid1_geneid2_prediction_method_key; Type: INDEX; Schema: public; Owner: diopt; Tablespace: 
--

CREATE INDEX ortholog_pair_geneid1_geneid2_prediction_method_key ON ortholog_pair USING btree (geneid1, geneid2, prediction_method);

--
-- Name: protein_pair_geneid1_geneid2_key; Type: INDEX; Schema: public; Owner: diopt; Tablespace: 
--

CREATE INDEX protein_pair_geneid1_geneid2_key ON protein_pair USING btree (geneid1, geneid2);

--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- Name: gene_information; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE gene_information FROM PUBLIC;
REVOKE ALL ON TABLE gene_information FROM diopt;
GRANT ALL ON TABLE gene_information TO diopt;
GRANT ALL ON TABLE gene_information TO PUBLIC;


--
-- Name: ortholog_pair; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE ortholog_pair FROM PUBLIC;
REVOKE ALL ON TABLE ortholog_pair FROM diopt;
GRANT ALL ON TABLE ortholog_pair TO diopt;
GRANT ALL ON TABLE ortholog_pair TO PUBLIC;


--
-- Name: ortholog_pair_best; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE ortholog_pair_best FROM PUBLIC;
REVOKE ALL ON TABLE ortholog_pair_best FROM diopt;
GRANT ALL ON TABLE ortholog_pair_best TO diopt;
GRANT ALL ON TABLE ortholog_pair_best TO PUBLIC;


--
-- Name: protein; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE protein FROM PUBLIC;
REVOKE ALL ON TABLE protein FROM diopt;
GRANT ALL ON TABLE protein TO diopt;
GRANT ALL ON TABLE protein TO PUBLIC;


--
-- Name: protein_feature; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE protein_feature FROM PUBLIC;
REVOKE ALL ON TABLE protein_feature FROM diopt;
GRANT ALL ON TABLE protein_feature TO diopt;
GRANT ALL ON TABLE protein_feature TO PUBLIC;


--
-- Name: protein_pair; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE protein_pair FROM PUBLIC;
REVOKE ALL ON TABLE protein_pair FROM diopt;
GRANT ALL ON TABLE protein_pair TO diopt;
GRANT ALL ON TABLE protein_pair TO PUBLIC;


--
-- Name: species; Type: ACL; Schema: public; Owner: diopt
--

REVOKE ALL ON TABLE species FROM PUBLIC;
REVOKE ALL ON TABLE species FROM diopt;
GRANT ALL ON TABLE species TO diopt;
GRANT ALL ON TABLE species TO PUBLIC;


--
-- PostgreSQL database dump complete
--

