#!/usr/bin/env python

import strict_rfc3339
import os
import pickle
import datetime
import json
import csv
import requests        # For fetching the orthology.json schema from GitHub
from nested_dict import nested_dict
import argparse
import coloredlogs
import logging
from tqdm import tqdm
import sys

################################################################################
# Classes and Global Structures
################################################################################

class OrthologyPair(object):
    """
    Represents a single orthology relationship between two genes from two species.
    """
    instances = []
    ortholog_tuple_dict = {}

    def __init__(self):
        OrthologyPair.instances.append(self)

        self.isBestScore = None
        self.isBestRevScore = None
        self.species_specific_geneid1 = None
        self.gene1Species = None
        self.species_specific_geneid2 = None
        self.gene2Species = None
        self.gene1Provider = None
        self.gene2Provider = None
        self.predictionMethodsMatched = []
        self.predictionMethodsNotMatched = []
        self.predictionMethodsNotCalled = []
        self.confidence = None
        self.strictFilter = None
        self.moderateFilter = None
        self.data_source = None

    def get_data_source(self):
        return self.data_source

    @classmethod
    def add_to_ortholog_tuple_dict(cls, key_tuple, value):
        cls.ortholog_tuple_dict[key_tuple] = value

    @classmethod
    def get_ortholog_tuple_dict(cls, key_tuple):
        return cls.ortholog_tuple_dict.get(key_tuple)

    @classmethod
    def get_all_instances(cls):
        return cls.instances

################################################################################
# Global diagnostic sets (for reporting)
################################################################################

xenbase_diopt_ortholog_pair_conflict = []
diopt_missing_species_specific_geneid = []
diopt_missing_species_specific_geneid_and_symbol = []
diopt_found_in_pair_table_missing_from_gene_information_table = []
xenbase_duplicate_data = []  # Each item is ((g1, g2, sp1, sp2), best_info_dict)
xenbase_duplicate_data_by_species = nested_dict(2, set)
failed_gene_information_lookup = []

best_score_dictionary = {}   # (geneid1, geneid2, speciesid1, speciesid2) -> (best_score, best_score_rev, confidence)
from_species_rows = nested_dict(2, set)  # from_species_rows[sp1][sp2] = set of algorithms
total_possible_algorithms = set()

trop_to_human_unidirectional_ortholog_pairs = []
human_to_trop_unidirectional_ortholog_pairs = []

################################################################################
# For TSV expansions: species name + symbol reverse lookups
################################################################################

speciesid_to_name = {}       # e.g. {9606: "Homo sapiens", ...}
geneid_lookup_by_ssgid = {}  # ssgid -> ( numeric_geneid, speciesid, symbol )

def get_species_name(spid):
    """Return the species name if known, else e.g. 'species_8355'."""
    return speciesid_to_name.get(spid, f"species_{spid}")

def get_symbol_by_ssgid(ssgid):
    """
    Return (symbol, species_name) for a species_specific_geneid.
    If not found, return ("unknown_symbol","unknown_species").
    """
    info = geneid_lookup_by_ssgid.get(ssgid)
    if not info:
        return ("unknown_symbol","unknown_species")
    numeric_id, spid, symbol = info
    return (symbol, get_species_name(spid))

################################################################################
# Reading CSV Data
################################################################################

def read_species_csv(logger, input_dir):
    path = os.path.join(input_dir, "fixed_species.csv")
    rows = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["speciesid"] = int(row["speciesid"])
            rows.append(row)
    logger.info(f"Read {len(rows)} lines from {path}.")
    return rows

def read_gene_information_csv(logger, input_dir):
    path = os.path.join(input_dir, "fixed_gene_information.csv")
    rows = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["geneid"] = int(row["geneid"])
            row["speciesid"] = int(row["speciesid"])
            rows.append(row)
    logger.info(f"Read {len(rows)} lines from {path}.")
    return rows

def read_ortholog_pair_csv(logger, input_dir):
    path = os.path.join(input_dir, "fixed_ortholog_pair.csv")
    rows = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["ortholog_pairid"] = int(row["ortholog_pairid"])
            row["speciesid1"] = int(row["speciesid1"])
            row["geneid1"] = int(row["geneid1"])
            row["speciesid2"] = int(row["speciesid2"])
            row["geneid2"] = int(row["geneid2"])
            rows.append(row)
    logger.info(f"Read {len(rows)} lines from {path}.")
    return rows

def read_ortholog_pair_best_csv(logger, input_dir):
    path = os.path.join(input_dir, "fixed_ortholog_pair_best.csv")
    rows = []
    with open(path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["speciesid1"] = int(row["speciesid1"])
            row["geneid1"] = int(row["geneid1"])
            row["speciesid2"] = int(row["speciesid2"])
            row["geneid2"] = int(row["geneid2"])
            if row["Score"].isdigit():
                row["Score"] = int(row["Score"])
            rows.append(row)
    logger.info(f"Read {len(rows)} lines from {path}.")
    return rows

################################################################################
# Fetch Orthology Schema from GitHub
################################################################################

SCHEMA_URL = "https://raw.githubusercontent.com/alliance-genome/agr_schemas/refs/heads/master/ingest/orthology/orthology.json"

def fetch_orthology_schema(logger):
    """
    Grab the orthology JSON schema from GitHub.
    Return the parsed JSON object.
    """
    logger.info(f"Fetching orthology schema from {SCHEMA_URL}...")
    resp = requests.get(SCHEMA_URL)
    resp.raise_for_status()
    return resp.json()

################################################################################
# Reading Xenbase JSON Data
################################################################################

def load_xenbase_sourced_data(logger, input_dir):
    xenbase_filenames = [
        "XB_ORTHO_1.json",
        "XB_ORTHO_2.json",
        "XB_ORTHO_3.json",
        "XB_ORTHO_4.json"
    ]

    combined_list = []

    def remove_missing_genes(data_obj):
        result = []
        missing_count = 0
        for item in data_obj.get('data', []):
            g1 = item.get('gene1','')
            g2 = item.get('gene2','')
            if not any(c.isalnum() for c in g1) or not any(c.isalnum() for c in g2):
                missing_count += 1
            else:
                result.append(item)
        return result, missing_count

    def filter_xenbase_algo(lst):
        return [x for x in lst if 'Xenbase' in x.get('predictionMethodsMatched', [])]

    total_files_read = 0
    total_entries_combined = 0
    total_missing = 0
    total_after_algo = 0

    for fname in xenbase_filenames:
        fpath = os.path.join(input_dir, fname)
        if not os.path.exists(fpath):
            logger.warning("Xenbase file missing: %s, skipping...", fpath)
            continue
        total_files_read += 1
        with open(fpath, 'r') as fx:
            data = json.load(fx)

        cleaned, missing_count = remove_missing_genes(data)
        total_missing += missing_count

        after = filter_xenbase_algo(cleaned)
        total_after_algo += len(after)

        combined_list.extend(after)
        total_entries_combined += len(cleaned)

    logger.info("Loaded %d Xenbase JSON files from input_dir.", total_files_read)
    logger.info("Total entries (pre-filter) from these files: %d", total_entries_combined)
    logger.info("Total removed for missing gene1/gene2: %d", total_missing)
    logger.info("Total kept after requiring 'Xenbase' in methods: %d", total_after_algo)

    def count_entries(lst, sp1, sp2):
        return sum(1 for x in lst if x.get('gene1Species') == sp1 and x.get('gene2Species') == sp2)

    t2h = count_entries(combined_list, 8364, 9606)
    h2t = count_entries(combined_list, 9606, 8364)
    l2h = count_entries(combined_list, 8355, 9606)
    h2l = count_entries(combined_list, 9606, 8355)
    t2l = count_entries(combined_list, 8364, 8355)
    l2t = count_entries(combined_list, 8355, 8364)

    logger.info("Xenbase entries (Tropicalis->Human): %s", t2h)
    logger.info("Xenbase entries (Human->Tropicalis): %s", h2t)
    logger.info("Xenbase entries (Laevis->Human): %s", l2h)
    logger.info("Xenbase entries (Human->Laevis): %s", h2l)
    logger.info("Xenbase entries (Tropicalis->Laevis): %s", t2l)
    logger.info("Xenbase entries (Laevis->Tropicalis): %s", l2t)
    logger.info("Combined Xenbase entries: %s", total_after_algo)

    return combined_list

################################################################################
# Reading Test Genes TSV
################################################################################

def read_test_genes_file(logger, test_genes_file):
    test_genes = set()
    with open(test_genes_file, 'r', newline='') as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            gene = row['gene_id'].strip()
            if gene:
                test_genes.add(gene)
    logger.info("Loaded %d test genes from %s", len(test_genes), test_genes_file)
    return test_genes

################################################################################
# Utility / ID Fixes
################################################################################

def sets_to_lists(obj):
    """
    Recursively convert sets -> lists, so we can JSON-serialize them.
    """
    if isinstance(obj, dict):
        return {k: sets_to_lists(v) for k, v in obj.items()}
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, list):
        return [sets_to_lists(x) for x in obj]
    else:
        return obj

# Rewrites for method names that appear incorrectly
REWRITE_MAP = {
    "phylome": "PhylomeDB",
    "RGD": "HGNC"
    # Add more if you find other "bad" or lowercase names that must be corrected
}

def rewrite_method_if_needed(method_in_lower):
    return REWRITE_MAP.get(method_in_lower)

def fix_identifier(logger, identifier, speciesid):
    """
    Prepends the DRSC: prefix if missing, adds the species code for certain species,
    and checks if the final identifier matches the expected prefix for that species.
    Returns None if there's a mismatch.
    """
    if not identifier.startswith("DRSC:"):
        if speciesid == 7955:    # ZFIN
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 6239:  # WB
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 10090: # MGI
            identifier_output = 'DRSC:MGI:' + identifier
        elif speciesid == 10116: # RGD
            identifier_output = 'DRSC:RGD:' + identifier
        elif speciesid == 4932:  # SGD
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 7227:  # FB
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 9606:  # HGNC
            identifier_output = 'DRSC:HGNC:' + identifier
        elif speciesid in [8364, 8355]:  # Xenbase
            if identifier.startswith('Xenbase:'):
                identifier_output = 'DRSC:' + identifier
            else:
                identifier_output = 'DRSC:Xenbase:' + identifier
        else:
            logger.critical("Fatal error: cannot correct gene id for species %s, id=%s",
                            speciesid, identifier)
            sys.exit(1)
    else:
        identifier_output = identifier

    # Expected prefixes by species
    starts_with_identifier_dict_by_species = {
        7955: 'DRSC:ZDB',
        6239: 'DRSC:WBGene',
        10090: 'DRSC:MGI',
        10116: 'DRSC:RGD',
        4932: 'DRSC:S',
        7227: 'DRSC:FBgn',
        9606: 'DRSC:HGNC',
        8364: 'DRSC:Xenbase:XB-GENE',
        8355: 'DRSC:Xenbase:XB-GENE'
    }
    expected_prefix = starts_with_identifier_dict_by_species.get(speciesid)
    if expected_prefix is None:
        logger.critical("No expected prefix for species %s", speciesid)
        sys.exit(1)

    if not identifier_output.startswith(expected_prefix):
        # if mismatch, return None so caller can skip
        return None

    return identifier_output

def fix_species_specific_geneid_type(logger, field, speciesid):
    """
    Convert the species_specific_geneid_type to a known short ID or fallback based on speciesid.
    """
    # If the field is one of these known ones:
    if field == 'FLYBASE':
        return 'FB'
    elif field == 'WormBase':
        return 'WB'
    elif field == 'Xenbase':
        return 'Xenbase'

    # Otherwise deduce from speciesid
    if speciesid == 7955:
        return 'ZFIN'
    elif speciesid == 6239:
        return 'WB'
    elif speciesid == 10090:
        return 'MGI'
    elif speciesid == 10116:
        return 'RGD'
    elif speciesid == 4932:
        return 'SGD'
    elif speciesid == 7227:
        return 'FB'
    elif speciesid == 9606:
        return 'HGNC'
    elif speciesid in [8364, 8355]:
        return 'Xenbase'
    else:
        logger.critical("Fatal error: cannot correct species %s", speciesid)
        sys.exit(1)

def convert_algorithm_name(name_input):
    """
    Convert partial names to standardized ones, plus handle rewriting (e.g. "phylome" -> "PhylomeDB").
    """
    # 1) rewrite if needed
    candidate = rewrite_method_if_needed(name_input)
    if candidate:
        name_input = candidate

    # 2) old name_map
    name_map = {
        'Panther': 'PANTHER',
        'Phylome': 'PhylomeDB',
        'Compara': 'Ensembl Compara',
        'Inparanoid': 'InParanoid',
        'RoundUp': 'Roundup',
        'sonicParanoid': 'SonicParanoid'
    }
    return name_map.get(name_input, name_input)

################################################################################
# Main
################################################################################

def main():
    parser = argparse.ArgumentParser(description='Process DIOPT data for the Alliance of Genome Resources.')
    parser.add_argument('--input_dir', required=True,
                        help='Directory with CSV + Xenbase JSON files')
    parser.add_argument('--output_dir', default='.',
                        help='Directory where output logs and JSON files are written')
    parser.add_argument('--test_genes_file', required=True,
                        help='TSV file with column "gene_id"')
    parser.add_argument('--pickle', action='store_true', default=False,
                        help='If set, attempt to load/save gene info database as a pickle')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable debug logging')

    args = parser.parse_args()

    # Logging
    verbosity = logging.DEBUG if args.verbose else logging.INFO
    coloredlogs.install(level=verbosity,
        fmt='%(asctime)s %(levelname)s: %(name)s:%(lineno)d: %(message)s')
    logger = logging.getLogger(__name__)

    start_time = datetime.datetime.now()
    logger.info("Script start time: %s", start_time)

    # 0) Fetch orthology schema + get valid methods
    schema_json = fetch_orthology_schema(logger)
    valid_methods = schema_json["properties"]["predictionMethodsMatched"]["items"]["enum"]
    logger.info("According to the schema, valid methods are: %s", valid_methods)

    # 1) Read species CSV
    logger.info("Reading species CSV for species name lookups.")
    species_rows = read_species_csv(logger, args.input_dir)
    for row in species_rows:
        spid = row["speciesid"]
        species_name = row.get("species_name", f"species_{spid}")
        speciesid_to_name[spid] = species_name

    # 2) Load Xenbase data
    logger.info("Loading Xenbase data from input_dir: %s", args.input_dir)
    combined_xenbase_list = load_xenbase_sourced_data(logger, args.input_dir)

    # 3) Read test genes
    test_set_of_genes = read_test_genes_file(logger, args.test_genes_file)

    # Possibly load from pickle
    gene_info_pickle_path = os.path.join(args.output_dir, "gene_information_database.p")
    use_pickle = args.pickle

    if use_pickle and os.path.exists(gene_info_pickle_path):
        logger.info("Using existing pickle for gene_information_database: %s", gene_info_pickle_path)
        with open(gene_info_pickle_path, "rb") as pf:
            gene_information_database = pickle.load(pf)
        logger.info("Still reading CSV for best_score_dictionary, from_species_rows, etc.")
    else:
        logger.info("Reading from CSV in %s (not using or found pickle).", args.input_dir)
        gene_information_database = {}

    # 4) Read CSV
    gene_info_rows = read_gene_information_csv(logger, args.input_dir)
    ortholog_pair_rows = read_ortholog_pair_csv(logger, args.input_dir)
    ortholog_best_rows = read_ortholog_pair_best_csv(logger, args.input_dir)

    # 5) Build gene_information_database
    for row in gene_info_rows:
        gid = row["geneid"]
        spid = row["speciesid"]
        ssgid = row["species_specific_geneid"]
        ssgid_type = row["species_specific_geneid_type"]
        symbol = row["symbol"]

        if ssgid == '':
            if symbol == '':
                diopt_missing_species_specific_geneid_and_symbol.append((spid, gid))
                continue
            else:
                diopt_missing_species_specific_geneid.append((spid, gid))
                ssgid = symbol

        ssgid_fixed = fix_identifier(logger, ssgid, spid)
        if ssgid_fixed is None:
            # Means the prefix didn't match
            continue

        ssgid_type_fixed = fix_species_specific_geneid_type(logger, ssgid_type, spid)

        gene_information_database[gid] = {
            "species": spid,
            "symbol": symbol,
            "species_specific_geneid": ssgid_fixed,
            "mod_data_source": ssgid_type_fixed
        }

    # 6) Build best_score_dictionary
    for row in ortholog_best_rows:
        g1 = row["geneid1"]
        g2 = row["geneid2"]
        sp1 = row["speciesid1"]
        sp2 = row["speciesid2"]
        best_score = row["best_score"]
        best_score_rev = row["best_score_rev"]
        confidence = row["confidence"]
        best_score_dictionary[(g1, g2, sp1, sp2)] = (best_score, best_score_rev, confidence)

    # 7) Build total_possible_algorithms + from_species_rows
    for row in ortholog_pair_rows:
        algo = convert_algorithm_name(row["prediction_method"])
        total_possible_algorithms.add(algo)
        sp1 = row["speciesid1"]
        sp2 = row["speciesid2"]
        from_species_rows[sp1][sp2].add(algo)

    # 8) Merge in Xenbase data algorithms
    for item in combined_xenbase_list:
        for a in item.get('predictionMethodsMatched', []):
            total_possible_algorithms.add(convert_algorithm_name(a))
        for a in item.get('predictionMethodsNotCalled', []):
            total_possible_algorithms.add(convert_algorithm_name(a))
        for a in item.get('predictionMethodsNotMatched', []):
            total_possible_algorithms.add(convert_algorithm_name(a))
    logger.info("Total distinct algorithms after Xenbase merges: %s", len(total_possible_algorithms))

    # 9) Create OrthologyPairs from DIOPT data
    species_list = [7227, 7955, 6239, 10090, 10116, 4932, 9606, 8364]
    allowed_species2 = set(species_list)

    for sp in tqdm(species_list, desc="Processing DIOPT data by species"):
        sub_op = [r for r in ortholog_pair_rows if r["speciesid1"] == sp and r["speciesid2"] in allowed_species2]
        for row in sub_op:
            ortholog_pairid = row["ortholog_pairid"]
            sp1 = row["speciesid1"]
            g1 = row["geneid1"]
            sp2 = row["speciesid2"]
            g2 = row["geneid2"]
            pm = row["prediction_method"]

            if g1 not in gene_information_database:
                diopt_found_in_pair_table_missing_from_gene_information_table.append((sp1, ortholog_pairid))
                continue

            data_source = 'DIOPT'
            best_info_and_algorithms = {
                'predictionMethodsMatched': pm
            }

            create_new_ortholog_pair_object(
                logger,
                gene_information_database,
                best_score_dictionary,
                g1, g2, sp1, sp2,
                data_source,
                **best_info_and_algorithms
            )

    # Optionally dump pickle
    if use_pickle:
        logger.info("Dumping gene_information_database to pickle: %s", gene_info_pickle_path)
        with open(gene_info_pickle_path, "wb") as pf:
            pickle.dump(gene_information_database, pf)

    # 10) Incorporate Xenbase data
    add_XB_to_gene_information_database_and_create_ortholog_pair(logger, combined_xenbase_list, gene_information_database)

    # 11) Build reverse lookup for symbol/species
    geneid_lookup_by_ssgid.clear()
    for numeric_id, info in gene_information_database.items():
        ssgid = info["species_specific_geneid"]
        spid = info["species"]
        symbol = info["symbol"]
        geneid_lookup_by_ssgid[ssgid] = (numeric_id, spid, symbol)

    # 12) Update filters
    ops = OrthologyPair.get_all_instances()
    logger.info("Updating algorithms and filters on %d OrthologyPair objects", len(ops))

    for item in tqdm(ops, desc="Updating filters"):
        ds = item.data_source
        matched_methods = set(item.predictionMethodsMatched)

        if ds == 'Xenbase':
            item.predictionMethodsNotMatched = set(item.predictionMethodsNotMatched)
            item.predictionMethodsNotCalled = set(item.predictionMethodsNotCalled)
            item.predictionMethodsMatched = matched_methods
        else:
            sp1 = item.gene1Species
            sp2 = item.gene2Species
            possible = from_species_rows[sp1][sp2]
            possible = {convert_algorithm_name(a) for a in possible}

            item.predictionMethodsNotCalled = total_possible_algorithms - possible
            item.predictionMethodsNotMatched = possible - matched_methods

        # Filters logic
        strict_f = False
        moderate_f = False
        bs = item.isBestScore
        brs = item.isBestRevScore

        # Additional logic from original script
        if any(x in matched_methods for x in ['ZFIN', 'HGNC', 'Xenbase']):
            strict_f = True
            moderate_f = True

        if (len(matched_methods) > 2 and (bs in ['Yes','Yes_Adjusted'] or brs == 'Yes')) \
           or (len(matched_methods) == 2 and (bs in ['Yes','Yes_Adjusted'] and brs == 'Yes')):
            strict_f = True
        elif len(matched_methods) > 2 \
             or (len(matched_methods) == 2 and (bs in ['Yes','Yes_Adjusted'] and brs == 'Yes')):
            moderate_f = True

        item.strictFilter = strict_f
        item.moderateFilter = moderate_f

    # 12b) Validate methods
    logger.info("Verifying that all prediction methods match the official schema enum list.")
    mismatch_found = False
    for op in OrthologyPair.get_all_instances():
        for arrname in ["predictionMethodsMatched","predictionMethodsNotMatched","predictionMethodsNotCalled"]:
            arr = getattr(op, arrname)
            for method in arr:
                if method not in valid_methods:
                    logging.error(f"Method '{method}' in {arrname} is not recognized by the schema. Valid = {valid_methods}")
                    mismatch_found = True
    if mismatch_found:
        logger.error("At least one method is not in the official orthology schema list. Exiting with error.")
        sys.exit(1)

    # 13) Print stats
    logger.info("Total xenbase_diopt_ortholog_pair_conflict: %d", len(set(xenbase_diopt_ortholog_pair_conflict)))
    logger.info("Total duplicate Xenbase entries: %d", len(xenbase_duplicate_data))
    logger.info("Total diopt_missing_species_specific_geneid: %d", len(diopt_missing_species_specific_geneid))
    logger.info("Total diopt_missing_species_specific_geneid_and_symbol: %d", len(diopt_missing_species_specific_geneid_and_symbol))
    logger.info("Total diopt_found_in_pair_table_missing_from_gene_information_table: %d", len(diopt_found_in_pair_table_missing_from_gene_information_table))

    total_xenbase_skipped = 0
    for s1 in xenbase_duplicate_data_by_species:
        for s2 in xenbase_duplicate_data_by_species[s1]:
            c = len(xenbase_duplicate_data_by_species[s1][s2])
            total_xenbase_skipped += c
            logger.info("Duplicate Xenbase entries for %s and %s: %s", s1, s2, c)
    logger.info("Total duplicate Xenbase entries skipped: %d", total_xenbase_skipped)

    # 14) Unidirectional checks
    logger.info("Checking for unidirectional orthology issues.")
    t2h_check = {}
    h2t_check = {}

    for op in tqdm(ops, desc="Unidirectional checks"):
        if op.gene1Species == op.gene2Species:
            continue
        if op.gene1Species == 8355 and op.gene2Species == 9606:
            t2h_check[op.species_specific_geneid1] = op.species_specific_geneid2
        if op.gene1Species == 9606 and op.gene2Species == 8355:
            h2t_check[op.species_specific_geneid1] = op.species_specific_geneid2

    trop2human_uni = []
    human2trop_uni = []
    for k, val in t2h_check.items():
        if val not in h2t_check:
            trop2human_uni.append((k, val))
    for k, val in h2t_check.items():
        if val not in t2h_check:
            human2trop_uni.append((k, val))

    trop_to_human_unidirectional_ortholog_pairs[:] = trop2human_uni
    human_to_trop_unidirectional_ortholog_pairs[:] = human2trop_uni

    logger.info("Unidirectional (Tropicalis->Human): %d", len(trop2human_uni))
    logger.info("Unidirectional (Human->Tropicalis): %d", len(human2trop_uni))

    logger.info("Total failed gene info lookups: %d", len(failed_gene_information_lookup))

    # 15) Convert to JSON
    logger.info("Converting data into JSON structure.")
    ops = OrthologyPair.get_all_instances()
    logger.info("Number of ortholog pairs for export: %d", len(ops))

    taxon_to_mod = {
        10116: 'RGD',
        10090: 'MGI',
        7955: 'ZFIN',
        4932: 'SGD',
        6239: 'WormBase',
        7227: 'FlyBase',
        9606: 'Human',
        8364: 'XBXT',
        8355: 'XBXL'
    }
    json_by_mod = {
        'RGD': [],
        'MGI': [],
        'ZFIN': [],
        'SGD': [],
        'WormBase': [],
        'FlyBase': [],
        'Human': [],
        'XBXT': [],
        'XBXL': []
    }

    test_json_to_export = {
        'metaData': {
            'dataProvider': {
                'type': 'curated',
                'crossReference': {'id': 'DRSC', 'pages': ['homepage']}
            },
            'dateProduced': strict_rfc3339.now_to_rfc3339_localoffset(),
            'release': '9'
        },
        'data': []
    }

    for op in tqdm(ops, desc="Building final JSON"):
        if op.gene1Species == op.gene2Species:
            continue
        d = {
            'isBestScore': op.isBestScore,
            'isBestRevScore': op.isBestRevScore,
            'gene1': op.species_specific_geneid1,
            'gene1Species': op.gene1Species,
            'gene2': op.species_specific_geneid2,
            'gene2Species': op.gene2Species,
            'predictionMethodsMatched': list(op.predictionMethodsMatched),
            'predictionMethodsNotMatched': list(op.predictionMethodsNotMatched),
            'predictionMethodsNotCalled': list(op.predictionMethodsNotCalled),
            'confidence': op.confidence,
            'strictFilter': op.strictFilter,
            'moderateFilter': op.moderateFilter
        }
        mod_name = taxon_to_mod.get(op.gene1Species)
        if mod_name:
            json_by_mod[mod_name].append(d)

    now_time = strict_rfc3339.now_to_rfc3339_localoffset()
    dataProviderdict = {
        'type': 'curated',
        'crossReference': {'id': 'DRSC', 'pages': ['homepage']}
    }

    for mod in json_by_mod:
        out_dict = {
            'metaData': {
                'dataProvider': dataProviderdict,
                'dateProduced': now_time,
                'release': '9'
            },
            'data': json_by_mod[mod]
        }
        # Collect test data
        for entry in json_by_mod[mod]:
            trimmed = entry['gene1'][5:]
            if trimmed in test_set_of_genes:
                test_json_to_export['data'].append(entry)

        filename = f"orthology_{mod}_v9.json"
        out_path = os.path.join(args.output_dir, filename)
        logger.info("Saving %s with %d records", out_path, len(json_by_mod[mod]))
        with open(out_path, "w") as outfile:
            json.dump(out_dict, outfile, sort_keys=True, indent=2, separators=(',', ': '))
        os.system(f"gzip -f {out_path}")

    test_filename = "orthology_test_data_v9.json"
    test_path = os.path.join(args.output_dir, test_filename)
    logger.info("Saving %s with %d records", test_path, len(test_json_to_export['data']))
    with open(test_path, "w") as outfile:
        json.dump(test_json_to_export, outfile, sort_keys=True, indent=2, separators=(',', ': '))
    os.system(f"gzip -f {test_path}")

    end_time = datetime.datetime.now()
    logger.info("Script end time: %s", end_time)
    elapsed = end_time - start_time
    logger.info("Elapsed time: %s", elapsed)

    for mod in json_by_mod:
        logger.info("%s: %d", mod, len(json_by_mod[mod]))
    logger.info("Done! Please wait for the last gzip command to finish...")

    ###########################################################################
    # Write Diagnostic TSVs (expanded with symbol/speciesname columns)
    ###########################################################################
    logger.info("Writing diagnostic TSV files to %s", args.output_dir)

    # 1) xenbase_diopt_ortholog_pair_conflict.tsv
    if xenbase_diopt_ortholog_pair_conflict:
        conflict_tsv = os.path.join(args.output_dir, "xenbase_diopt_ortholog_pair_conflict.tsv")
        with open(conflict_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "gene1","gene1_symbol","gene1_speciesName",
                "gene2","gene2_symbol","gene2_speciesName",
                "speciesid1","speciesid2"
            ])
            for (g1,g2,sp1,sp2) in xenbase_diopt_ortholog_pair_conflict:
                sym1, spname1 = get_symbol_by_ssgid(g1)
                sym2, spname2 = get_symbol_by_ssgid(g2)
                row = [g1, sym1, spname1, g2, sym2, spname2, sp1, sp2]
                writer.writerow(row)

    # 2) xenbase_duplicate_data.tsv
    if xenbase_duplicate_data:
        xd_tsv = os.path.join(args.output_dir, "xenbase_duplicate_data.tsv")
        with open(xd_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "gene1","gene1_symbol","gene1_speciesName",
                "gene2","gene2_symbol","gene2_speciesName",
                "speciesid1","speciesid2","best_info_json"
            ])
            for (tracking_tuple, best_info) in xenbase_duplicate_data:
                (g1, g2, sp1, sp2) = tracking_tuple
                sym1, spname1 = get_symbol_by_ssgid(g1)
                sym2, spname2 = get_symbol_by_ssgid(g2)
                best_info_serializable = sets_to_lists(best_info)
                best_info_str = json.dumps(best_info_serializable, ensure_ascii=False)
                row = [g1, sym1, spname1, g2, sym2, spname2, sp1, sp2, best_info_str]
                writer.writerow(row)

    # 3) xenbase_duplicate_data_by_species.tsv
    xdb_tsv = os.path.join(args.output_dir, "xenbase_duplicate_data_by_species.tsv")
    with open(xdb_tsv, "w", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            "species1","species1_name","gene1","gene1_symbol","gene1_speciesName",
            "species2","species2_name","gene2","gene2_symbol","gene2_speciesName"
        ])
        for s1 in xenbase_duplicate_data_by_species:
            s1_name = get_species_name(s1)
            for s2 in xenbase_duplicate_data_by_species[s1]:
                s2_name = get_species_name(s2)
                for (g1, g2) in xenbase_duplicate_data_by_species[s1][s2]:
                    sym1, spname1 = get_symbol_by_ssgid(g1)
                    sym2, spname2 = get_symbol_by_ssgid(g2)
                    row = [s1, s1_name, g1, sym1, spname1, s2, s2_name, g2, sym2, spname2]
                    writer.writerow(row)

    # 4) diopt_missing_species_specific_geneid.tsv
    if diopt_missing_species_specific_geneid:
        missing_spgid_tsv = os.path.join(args.output_dir, "diopt_missing_species_specific_geneid.tsv")
        with open(missing_spgid_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["speciesid","species_name","geneid","symbol_if_known"])
            for (sp, gid) in diopt_missing_species_specific_geneid:
                sp_name = get_species_name(sp)
                info = gene_information_database.get(gid)
                symbol = info["symbol"] if info else "unknown_symbol"
                writer.writerow([sp, sp_name, gid, symbol])

    # 5) diopt_missing_species_specific_geneid_and_symbol.tsv
    if diopt_missing_species_specific_geneid_and_symbol:
        missing_both_tsv = os.path.join(args.output_dir, "diopt_missing_species_specific_geneid_and_symbol.tsv")
        with open(missing_both_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["speciesid","species_name","geneid"])
            for (sp, gid) in diopt_missing_species_specific_geneid_and_symbol:
                sp_name = get_species_name(sp)
                row = [sp, sp_name, gid]
                writer.writerow(row)

    # 6) diopt_found_in_pair_table_missing_from_gene_information_table.tsv
    if diopt_found_in_pair_table_missing_from_gene_information_table:
        missing_pair_tsv = os.path.join(args.output_dir, "diopt_found_in_pair_table_missing_from_gene_information_table.tsv")
        with open(missing_pair_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["speciesid1","species1_name","ortholog_pairid"])
            for (speciesid1, opid) in diopt_found_in_pair_table_missing_from_gene_information_table:
                sp1_name = get_species_name(speciesid1)
                writer.writerow([speciesid1, sp1_name, opid])

    # 7) failed_gene_information_lookup.tsv
    if failed_gene_information_lookup:
        fail_lookup_tsv = os.path.join(args.output_dir, "failed_gene_information_lookup.tsv")
        with open(fail_lookup_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["geneid","speciesid","species_name","symbol_if_known"])
            for (gid, spid) in failed_gene_information_lookup:
                sp_name = get_species_name(spid)
                info = gene_information_database.get(gid)
                symbol = info["symbol"] if info else "unknown_symbol"
                writer.writerow([gid, spid, sp_name, symbol])

    # 8) unidirectional_trop2human.tsv
    if trop_to_human_unidirectional_ortholog_pairs:
        t2h_tsv = os.path.join(args.output_dir, "unidirectional_trop2human.tsv")
        with open(t2h_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["gene1","gene1_symbol","gene1_species","gene2","gene2_symbol","gene2_species"])
            for (g1, g2) in trop_to_human_unidirectional_ortholog_pairs:
                sym1, spname1 = get_symbol_by_ssgid(g1)
                sym2, spname2 = get_symbol_by_ssgid(g2)
                writer.writerow([g1, sym1, spname1, g2, sym2, spname2])

    # 9) unidirectional_humantotrop.tsv
    if human_to_trop_unidirectional_ortholog_pairs:
        h2t_tsv = os.path.join(args.output_dir, "unidirectional_humantotrop.tsv")
        with open(h2t_tsv, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["gene1","gene1_symbol","gene1_species","gene2","gene2_symbol","gene2_species"])
            for (g1, g2) in human_to_trop_unidirectional_ortholog_pairs:
                sym1, spname1 = get_symbol_by_ssgid(g1)
                sym2, spname2 = get_symbol_by_ssgid(g2)
                writer.writerow([g1, sym1, spname1, g2, sym2, spname2])

    logger.info("All diagnostic TSVs written. Exiting.")

################################################################################
# create_new_ortholog_pair_object
################################################################################

def create_new_ortholog_pair_object(logger,
                                    gene_information_database,
                                    best_score_dictionary,
                                    diopt_geneid1,
                                    diopt_geneid2,
                                    speciesid1,
                                    speciesid2,
                                    data_source,
                                    **best_info_and_algorithms):
    try:
        species_specific_geneid1 = gene_information_database[diopt_geneid1]['species_specific_geneid']
    except KeyError:
        failed_gene_information_lookup.append((diopt_geneid1, speciesid1))
        return
    try:
        species_specific_geneid2 = gene_information_database[diopt_geneid2]['species_specific_geneid']
    except KeyError:
        failed_gene_information_lookup.append((diopt_geneid2, speciesid2))
        return

    tracking_tuple = (species_specific_geneid1, species_specific_geneid2, speciesid1, speciesid2)
    existing_op = OrthologyPair.get_ortholog_tuple_dict(tracking_tuple)
    if existing_op is not None:
        # If there's already an OrthologyPair for this exact tuple
        existing_source = existing_op.get_data_source()
        if existing_source == data_source:
            # If it's DIOPT, we just add the new method
            if data_source == 'DIOPT':
                pm = convert_algorithm_name(best_info_and_algorithms['predictionMethodsMatched'])
                existing_op.predictionMethodsMatched.append(pm)
            else:
                # If it's Xenbase duplicate
                xenbase_duplicate_data.append((tracking_tuple, best_info_and_algorithms))
                xenbase_duplicate_data_by_species[speciesid1][speciesid2].add((species_specific_geneid1, species_specific_geneid2))
            return
        else:
            # Different data source => conflict
            xenbase_diopt_ortholog_pair_conflict.append((species_specific_geneid1, species_specific_geneid2, speciesid1, speciesid2))
            return
    else:
        # Create a new OrthologyPair
        op = OrthologyPair()
        OrthologyPair.add_to_ortholog_tuple_dict(tracking_tuple, op)

    op = OrthologyPair.get_ortholog_tuple_dict(tracking_tuple)
    op.species_specific_geneid1 = species_specific_geneid1
    op.species_specific_geneid2 = species_specific_geneid2
    op.gene1Species = gene_information_database[diopt_geneid1]['species']
    op.gene2Species = gene_information_database[diopt_geneid2]['species']
    op.gene1Provider = gene_information_database[diopt_geneid1]['mod_data_source']
    op.gene2Provider = gene_information_database[diopt_geneid2]['mod_data_source']
    op.data_source = data_source

    if data_source == 'Xenbase':
        op.isBestScore = best_info_and_algorithms.get('isBestScore')
        op.isBestRevScore = best_info_and_algorithms.get('isBestRevScore')
        op.confidence = best_info_and_algorithms.get('confidence')

        pm_matched = [convert_algorithm_name(x) for x in best_info_and_algorithms.get('predictionMethodsMatched', [])]
        pm_not_matched = [convert_algorithm_name(x) for x in best_info_and_algorithms.get('predictionMethodsNotMatched', [])]
        pm_not_called = [convert_algorithm_name(x) for x in best_info_and_algorithms.get('predictionMethodsNotCalled', [])]

        op.predictionMethodsMatched = pm_matched
        op.predictionMethodsNotMatched = pm_not_matched
        op.predictionMethodsNotCalled = pm_not_called
    else:
        # data_source = DIOPT
        key = (diopt_geneid1, diopt_geneid2, speciesid1, speciesid2)
        if key in best_score_dictionary:
            (bs, bsr, conf) = best_score_dictionary[key]
            op.isBestScore = bs
            op.isBestRevScore = bsr
            op.confidence = conf
        pm = convert_algorithm_name(best_info_and_algorithms['predictionMethodsMatched'])
        op.predictionMethodsMatched.append(pm)

    return

def add_XB_to_gene_information_database_and_create_ortholog_pair(logger, source_list, gene_information_db):
    """
    For Xenbase data, we generate new numeric IDs for the geneid, fix IDs, and build OrthologyPair objects.
    """
    if gene_information_db:
        max_id = max(gene_information_db.keys())
    else:
        max_id = 0

    for item in tqdm(source_list, desc="Adding Xenbase data"):
        g1_species = item['gene1Species']
        g2_species = item['gene2Species']
        g1 = item['gene1']
        g2 = item['gene2']

        conf = item.get('confidence', None)
        isBestRevScore = item.get('isBestRevScore', None)
        isBestScore = item.get('isBestScore', None)

        best_info = {
            'predictionMethodsMatched': set(item.get('predictionMethodsMatched', [])),
            'predictionMethodsNotMatched': set(item.get('predictionMethodsNotMatched', [])),
            'predictionMethodsNotCalled': set(item.get('predictionMethodsNotCalled', [])),
            'confidence': conf,
            'isBestRevScore': isBestRevScore,
            'isBestScore': isBestScore
        }

        # For gene1
        max_id += 1
        new_id_1 = max_id
        ssgid1_fixed = fix_identifier(logger, g1, g1_species)
        if ssgid1_fixed is None:
            continue
        ssgid1_type = fix_species_specific_geneid_type(logger, 'Xenbase', g1_species)
        gene_information_db[new_id_1] = {
            "species": g1_species,
            "symbol": "",
            "species_specific_geneid": ssgid1_fixed,
            "mod_data_source": ssgid1_type
        }

        # For gene2
        max_id += 1
        new_id_2 = max_id
        ssgid2_fixed = fix_identifier(logger, g2, g2_species)
        if ssgid2_fixed is None:
            continue
        ssgid2_type = fix_species_specific_geneid_type(logger, 'Xenbase', g2_species)
        gene_information_db[new_id_2] = {
            "species": g2_species,
            "symbol": "",
            "species_specific_geneid": ssgid2_fixed,
            "mod_data_source": ssgid2_type
        }

        create_new_ortholog_pair_object(
            logger,
            gene_information_db,
            best_score_dictionary,
            new_id_1,
            new_id_2,
            g1_species,
            g2_species,
            "Xenbase",
            **best_info
        )
    return gene_information_db

if __name__ == "__main__":
    main()
