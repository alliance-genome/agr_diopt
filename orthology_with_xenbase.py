#!/usr/bin/env python
import psycopg2
import strict_rfc3339
import os
import pickle
import datetime
import json
import csv
from nested_dict import nested_dict
import argparse
import coloredlogs
import logging
from tqdm import tqdm

class OrthologyPair(object):
    # Class attribute to keep track of instances.
    instances = []

    # Class attribute to keep track of ortholog_pairid
    ortholog_pairid_list = []

    # A dictionary to keep track of parid and its instance.
    ortholog_tuple_dict = {}

    # A dictionary to keep track of parid and its instance without the second gene
    ortholog_tuple_dict_no_geneid2 = {}

    # A set to track a "unique" interaction between two genes from two species.
    # It contains tuples of (gene1, gene2, species1, species2).
    # We check this tracking tuple before we make a new OrthologPair object.
    # If it exists in the tracking tuple, we use the ortholog_pairid to update the existing OrthologPair object.
    # unique_tracking_tuple = set()

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
    
    # Class method to add to the unique tracking tuple.
    @classmethod
    def add_to_ortholog_tuple_dict(cls, tuple, value):
        cls.ortholog_tuple_dict[tuple] = value

    # Class method to search the unique tracking tuple.
    @classmethod
    def get_ortholog_tuple_dict(cls, value):
        try: 
            return cls.ortholog_tuple_dict[value]
        except KeyError:
            return None

    # Class method to add to the unique tracking tuple without second gene id.
    @classmethod
    def add_to_ortholog_tuple_dict_no_geneid2(cls, tuple, value):
        cls.ortholog_tuple_dict_no_geneid2[tuple] = value

    # Class method to search the unique tracking tuple without second gene id.
    @classmethod
    def get_ortholog_tuple_dict_no_geneid2(cls, value):
        try: 
            return cls.ortholog_tuple_dict_no_geneid2[value]
        except KeyError:
            return None

    # Class method to return a list of all instances.
    @classmethod
    def get_all_instances(cls):
        return cls.instances

def obtain_connection(dbhost, database, username, password):
    # Define our connection.
    conn_string = "host=%s dbname=%s user=%s password='%s'" % (dbhost, database, username, password)
    # Attempt to get a connection
    conn = psycopg2.connect(conn_string)
    return conn

def obtain_data_from_database(connection, query):
    cursor = connection.cursor('my_cursor')
    # Execute the query.
    cursor.execute(query)
    # Grab the results.
    database_data = cursor.fetchall()
    # Close the cursor.
    cursor.close()
    return database_data

def obtain_data_from_database_query_variable(connection, query, query_variable):
    cursor = connection.cursor('my_cursor')
    # Execute the query.
    cursor.execute(query, query_variable)
    # Grab the results.
    database_data = cursor.fetchall()
    # Close the cursor.
    cursor.close()
    return database_data

def load_xenbase_sourced_data(logger):
    # Some of the orthology data is sourced directly from Xenbase in the form of JSON files.
    # We need to load these data separately and then merge them with the data from the other sources.
    xenbase_json_filename = 'source_data/diopt_v9/orthology/from_xenbase/10_18_2022/ORTHOLOGY_XB.json'
    xenbase_json_filename2 = 'source_data/diopt_v9/orthology/from_xenbase/10_18_2022/ORTHOLOGY_XBXT.json'

    def keep_only_xenbase_algorithms(algorithm_list):
        processed_list = []
        for entry in algorithm_list:
            if 'Xenbase' in entry['predictionMethodsMatched']:
                processed_list.append(entry)
        return processed_list

    def remove_entries_missing_genes(json_data_structure):
        # Cycle through the JSON data structure and warn/remove missing gene1/gene2 entries.
        # Also convert the structure into a list of JSON dictionaries.
        processed_json_list = []
        total_missing_entries = 0
        search_list = ['gene1', 'gene2']
        for key in json_data_structure['data']:
            found_missing_entry = False
            for search_item in search_list:
                if not any(char.isalpha() or char.isdigit() for char in key[search_item]):
                    total_missing_entries += 1
                    found_missing_entry = True
            # Add key to processed list.
            if not found_missing_entry:
                processed_json_list.append(key)
        
        if total_missing_entries > 0:
            logger.warning('Xenbase data warning:')
            logger.warning("%s entries were removed from the JSON data structure due to missing gene1/gene2 entries." % (total_missing_entries))

        return(processed_json_list)

    with open(xenbase_json_filename) as json_file:
        xenbase_to_human = json.load(json_file)

    with open(xenbase_json_filename2) as json_file:
        tropicalis_to_laevis = json.load(json_file)

    xenbase_to_human_list = remove_entries_missing_genes(xenbase_to_human)
    tropicalis_to_laevis_list = remove_entries_missing_genes(tropicalis_to_laevis)

    xenbase_to_human_list = keep_only_xenbase_algorithms(xenbase_to_human_list)
    tropicalis_to_laevis_list = keep_only_xenbase_algorithms(tropicalis_to_laevis_list)

    logger.info('Loading Xenbase data and checking number of entries.')
    # Loop through the JSON data and determine the number of entries.
    tropicalis_to_human_entries = 0
    for key in xenbase_to_human_list:
        if key['gene1Species'] == 8364 and key['gene2Species'] == 9606:
                tropicalis_to_human_entries += 1

    laevis_to_human_entries = 0
    for key in xenbase_to_human_list:
        if key['gene1Species'] == 8355 and key['gene2Species'] == 9606:
                laevis_to_human_entries += 1

    human_to_tropicalis_entries = 0
    for key in xenbase_to_human_list:
        if key['gene1Species'] == 9606 and key['gene2Species'] == 8364:
                human_to_tropicalis_entries += 1

    human_to_laevis_entries = 0
    for key in xenbase_to_human_list:
        if key['gene1Species'] == 9606 and key['gene2Species'] == 8355:
                human_to_laevis_entries += 1

    tropicalis_to_laevis_entries = 0
    for key in tropicalis_to_laevis_list:
        if key['gene1Species'] == 8364 and key['gene2Species'] == 8355:
            tropicalis_to_laevis_entries += 1

    laevis_to_tropicalis_entries = 0
    for key in tropicalis_to_laevis_list:
        if key['gene1Species'] == 8355 and key['gene2Species'] == 8364:
            laevis_to_tropicalis_entries += 1

    logger.info('Total Xenbase entries (Tropicalis to Human): %s' % (tropicalis_to_human_entries))
    logger.info('Total Xenbase entries (Human to Tropicalis): %s' % (human_to_tropicalis_entries))
    logger.info('Total Xenbase entries (Laevis to Human): %s' % (laevis_to_human_entries))
    logger.info('Total Xenbase entries (Human to Laevis): %s' % (human_to_laevis_entries))
    logger.info('Total Xenbase entries (Tropicalis to Laevis): %s' % (tropicalis_to_laevis_entries))
    logger.info('Total Xenbase entries (Laevis to Tropicalis): %s' % (laevis_to_tropicalis_entries))
    logger.info('Combined Xenbase entries: %s' % (tropicalis_to_human_entries + laevis_to_human_entries + tropicalis_to_laevis_entries))

    return (xenbase_to_human_list, tropicalis_to_laevis_list)

def fix_identifier(logger, identifier, speciesid):
    if identifier[:5] != 'DRSC:':

        if speciesid == 7955:  # ZFIN
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 6239:  # WB
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 10090:  # MGI
            identifier_output = 'DRSC:MGI:' + identifier
        elif speciesid == 10116:  # RGD
            identifier_output = 'DRSC:RGD:' + identifier
        elif speciesid == 4932:  # SGD
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 7227:  # FB
            identifier_output = 'DRSC:' + identifier
        elif speciesid == 9606:  # HGNC
            identifier_output = 'DRSC:HGNC:' + identifier
        elif speciesid == 8364:  # Xenbase
            # If this is coming from DIOPT, it will be missing the Xenbase: prefix as well.
            # We need to add it.
            # If this is coming from Xenbase, it will already have this prefix
            # Check for the prefix Xenbase and if it is not present, add it.
            if identifier.startswith('Xenbase:'):
                identifier_output = 'DRSC:' + identifier
            else:
                identifier_output = 'DRSC:Xenbase:' + identifier
        elif speciesid == 8355:  # Xenbase
            # If this is coming from DIOPT, it will be missing the Xenbase: prefix as well.
            # We need to add it.
            # If this is coming from Xenbase, it will already have this prefix
            # Check for the prefix Xenbase and if it is not present, add it.
            if identifier.startswith('Xenbase:'):
                identifier_output = 'DRSC:' + identifier
            else:
                identifier_output = 'DRSC:Xenbase:' + identifier
        else:
            logger.critical("Fatal error: cannot correct species specific gene id %s" % (identifier))
            quit()

    else:
        identifier_output = identifier

    starts_with_identifier_dict_by_species = {
            7955: 'DRSC:ZDB',
            6239: 'DRSC:WBGene',
            10090: 'DRSC:MGI',
            10116: 'DRSC:RGD',
            4932: 'DRSC:S', # This looks wrong but it's actually correct.
            7227: 'DRSC:FBgn',
            9606: 'DRSC:HGNC',
            8364: 'DRSC:Xenbase:XB-GENE',
            8355: 'DRSC:Xenbase:XB-GENE'
        }

    # Check whether the identifier starts with the correct prefix.

    if not identifier_output.startswith(starts_with_identifier_dict_by_species[speciesid]):
        return None
    else:
        return identifier_output

def fix_species_specific_geneid_type(logger, field, speciesid):

    # First we check the field type.
    # If it contains FLYBASE, WormBase, or Xenbase, we can update the field and return immediately.

    if field == 'FLYBASE':
       return 'FB'
    elif field == 'WormBase':
        return 'WB'
    elif field == 'Xenbase':
        return field

    # If we don't find FLYBASE, WormBase, or Xenbase as a field value, then we check the species ID.

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
    elif speciesid == 8364:
        return 'Xenbase'
    elif speciesid == 8355:
        return 'Xenbase'
    else:
        logger.critical("Fatal error: cannot correct species %s" % (speciesid))
        quit()

def convert_algorithm_name(name_input):
    name_conversion_dictionary = {
        'Panther': 'PANTHER',
        'Phylome': 'PhylomeDB',
        'Compara': 'Ensembl Compara',
        'Inparanoid': 'InParanoid',
        'RoundUp': 'Roundup',
        'sonicParanoid': 'SonicParanoid'
    }

    # Try to get the new value by key, if the key is not found, send back the input value.
    return name_conversion_dictionary.get(name_input, name_input)

def load_test_set_of_genes():

    # TODO Create a submodule of agr_loader in this repository and use it to access the test object file.
    # Given the frequency of updates for the orthology (~once per year) this isn't a pressing issue.
    test_set_of_genes = {
        'MGI:5437116', 'MGI:1915135', 'MGI:109337', 'MGI:108202', 'MGI:2676586', 'MGI:88180', 'MGI:88467',
        'MGI:109583', 'MGI:96765', 'MGI:1099804', 'MGI:1916172', 'MGI:96680', 'MGI:2175810', 'MGI:5437110', 'MGI:5437073', 'MGI:88525',
        'MGI:1923696', 'MGI:1929597', 'MGI:87853', 'MGI:2179405', 'MGI:1337006', 'MGI:1929470', 'MGI:1929288', 'MGI:1929209',
        'MGI:1915127', 'MGI:1915121', 'MGI:1915122', 'MGI:1915123', 'MGI:3643831', 'MGI:1929183', 'MGI:2443198', 'MGI:1861441',
        'MGI:1928478', 'MGI:1928761', 'MGI:1914047', 'MGI:88053', 'MGI:88054', 'MGI:1855948', 'MGI:88056', 'MGI:88456', 'MGI:88447',
        'MGI:88587', 'MGI:1338803', 'MGI:94864', 'MGI:1915101', 'MGI:1915112', 'MGI:1355324', 'MGI:3029164', 'MGI:1856330',
        'MGI:1915181', 'MGI:1915162', 'MGI:1915164', 'MGI:1929699', 'MGI:94909', 'MGI:1856331', 'MGI:97490', 'MGI:108092', 'MGI:2156738',
        'MGI:2148260', 'MGI:1856328', 'MGI:2678393', 'MGI:2429942', 'MGI:1856332', 'MGI:5569634', 'MGI:3531484', 'MGI:3531484',
        'MGI:2148259', 'MGI:3531483', 'MGI:1856329', 'MGI:3531484', 'MGI:5781149', 'MGI:2148259', 'MGI:104735', 'MGI:98834',
        'MGI:88123', 'MGI:2148259', 'MGI:98297', 'MGI:5011818', 'MGI:98371', 'MGI:1919338',

        'WB:WBGene00044305', 'WB:WBGene00169423', 'WB:WBGene00000987', 'WB:WBGene00021789',
        'WB:WBGene00006750', 'WB:WBGene00000540', 'WB:WBGene00017866', 'WB:WBGene00001131',
        'WB:WBGene00015146', 'WB:WBGene00015599', 'WB:WBGene00001133', 'WB:WBGene00001115',
        'WB:WBGene00018468', 'WB:WBGene00019001', 'WB:WBGene00007438', 'WB:WBGene00001136',
        'WB:WBGene00006742', 'WB:WBGene00003883',
        'WB:WBGene00004264', 'WB:WBGene00004488',

        'SGD:S000003256', 'SGD:S000003513', 'SGD:S000000119', 'SGD:S000001015',

        'ZFIN:ZDB-GENE-990415-72', 'ZFIN:ZDB-GENE-030131-3445', 'ZFIN:ZDB-GENE-980526-388',
        'ZFIN:ZDB-GENE-010525-1', 'ZFIN:ZDB-GENE-010525-1', 'ZFIN:ZDB-GENE-060117-5',
        'ZFIN:ZDB-GENE-050302-80', 'ZFIN:ZDB-GENE-060503-876',
        'ZFIN:ZDB-GENE-050302-82', 'ZFIN:ZDB-GENE-030131-4430', 'ZFIN:ZDB-GENE-060503-872',
        'ZFIN:ZDB-GENE-060503-873', 'ZFIN:ZDB-GENE-010525-1', 'ZFIN:ZDB-GENE-990415-72',
        'ZFIN:ZDB-GENE-060503-867', 'ZFIN:ZDB-GENE-010323-11', 'ZFIN:ZDB-GENE-010525-1',
        'ZFIN:ZDB-GENE-010320-1', 'ZFIN:ZDB-GENE-010525-1', 'ZFIN:ZDB-GENE-051127-5',
        'ZFIN:ZDB-GENE-990415-270', 'ZFIN:ZDB-LINCRNAG-160518-1',
        'ZFIN:ZDB-GENE-040426-1716', 'ZFIN:ZDB-ALT-980203-985', 'ZFIN:ZDB-ALT-060608-195',
        'ZFIN:ZDB-ALT-050428-6', 'ZFIN:ZDB-ALT-151012-9',
        'ZFIN:ZDB-GENE-131121-260', 'ZFIN:ZDB-GENE-980526-368', 'ZFIN:ZDB-GENE-051101-2', 'ZFIN:ZDB-GENE-090311-1',
        'ZFIN:ZDB-GENE-040426-2889', 'ZFIN:ZDB-GENE-140619-1', 'ZFIN:ZDB-GENE-990714-29',
        'ZFIN:ZDB-GENE-030131-7696', 'ZFIN:ZDB-GENE-060312-41',

        'FB:FBgn0083973', 'FB:FBgn0037960', 'FB:FBgn0027296', 'FB:FBgn0032006', 'FB:FBgn0001319',
        'FB:FBgn0002369', 'FB:FBgn0033885', 'FB:FBgn0024320', 'FB:FBgn0283499', 'FB:FBgn0032465',
        'FB:FBgn0285944', 'FB:FBgn0032728', 'FB:FBgn0000014', 'FB:FBgn0032729', 'FB:FBgn0065610',
        'FB:FBgn0032730', 'FB:FBgn0032732', 'FB:FBgn0260987', 'FB:FBgn0032781', 'FB:FBgn0032782',
        'FB:FBgn0032740', 'FB:FBgn0032741', 'FB:FBgn0032744', 'FB:FBgn0036309', 'FB:FBgn0003470',
        'FB:FBal0161187', 'FB:FBal0000003', 'FB:FBal0000004', 'FB:FBgn0039156',
        'FB:FBgn0004644', 'FB:FBgn0039129', 'FB:FBgn0010412', 'FB:FBgn0263006',

        'RGD:70891', 'RGD:1306349', 'RGD:708528', 'RGD:620796', 'RGD:61995', 'RGD:1309165',
        'RGD:1581495', 'RGD:2322065', 'RGD:1309063', 'RGD:2845', 'RGD:628748', 'RGD:1581476',
        'RGD:1309312', 'RGD:7627512', 'RGD:1309105', 'RGD:1309109', 'RGD:7627503', 'RGD:1578801',
        'RGD:68936', 'RGD:3886', 'RGD:3673', 'RGD:6498788', 'RGD:1303329',

        'HGNC:17889', 'HGNC:25818', 'HGNC:3686', 'HGNC:7881', 'HGNC:6709', 'HGNC:6526', 'HGNC:6553',
        'HGNC:7218', 'HGNC:6560', 'HGNC:6551', 'HGNC:6700',
        'HGNC:897', 'HGNC:869', 'HGNC:10848', 'HGNC:10402', 'HGNC:11204', 'HGNC:12597', 'HGNC:811',

        'Xenbase:XB-GENE-494002', 'Xenbase:XB-GENE-967980', 'Xenbase:XB-GENE-5729710', 'Xenbase:XB-GENE-5942644',
        'Xenbase:XB-GENE-5942644', 'Xenbase:XB-GENE-1013749', 'Xenbase:XB-GENE-949827', 'Xenbase:XB-GENE-959557'
    }

    return test_set_of_genes

#### Diagnostic variables used throughout the program. ####
xenbase_diopt_ortholog_pair_conflict = []
diopt_missing_species_specific_geneid = []
diopt_missing_species_specific_geneid_and_symbol = []
diopt_found_in_pair_table_missing_from_gene_information_table = []
xenbase_duplicate_data = []
xenbase_duplicate_data_by_species = nested_dict(2, set)
failed_gene_information_lookup = []

def main():    # noqa C901

    parser = argparse.ArgumentParser(
        description='Process DIOPT data for the Alliance of Genome Resources.', add_help=False)
    parser.add_argument('-h',
                        '--host', 
                        help='Specify the host used for the database connection.',
                        default='localhost')
    parser.add_argument('-d',
                        '--database',
                        help='Specify the name of the database containing the DIOPT data.')
    parser.add_argument('-u',
                        '--username',
                        help='Specify the username for connecting to the DIOPT database.')
    parser.add_argument('-p',
                        '--password',
                        help='Specify the password for connecting to the DIOPT database.')    
    parser.add_argument('-v',
                        '--verbose',
                        help='Enable DEBUG mode for logging.',
                        action='store_true')
    pickle_help = '''
    Use the local database dump pickle file and do not query the Postgres database.
    This is useful for creating changes in the JSON without needing to re-query everything (slow).'
    '''
    parser.add_argument('-pi', 
                        '--pickle', 
                        help=pickle_help, 
                        dest='pickle', 
                        action='store_true')
    parser.set_defaults(pickle=False)

    args = parser.parse_args()

    verbosity = logging.DEBUG if args.verbose else logging.INFO

    coloredlogs.install(level=verbosity,
                        fmt='%(asctime)s %(levelname)s: %(name)s:%(lineno)d: %(message)s',
                        field_styles={
                            'asctime': {'color': 'green'},
                            'hostname': {'color': 'magenta'},
                            'levelname': {'color': 'white', 'bold': True},
                            'name': {'color': 'blue'},
                            'programname': {'color': 'cyan'}
                        })

    logger = logging.getLogger(__name__)

    logger.debug('Connection details:')
    logger.debug('Host: %s', args.host)
    logger.debug('Database: %s', args.database)
    logger.debug('Username: %s', args.username)
    
    if args.pickle:
        logger.info('Note: Pickle file use is enabled. This script will attempt to use the existing pickle file and not query Postgres.')
    else:
        logger.info('Pickle use not requested.') 
        logger.info('Script will query Postgres and create new pickle file as well as generate JSON.')
        logger.info('Please use --help for more info.')

    test_set_of_genes = load_test_set_of_genes()

    ts = datetime.datetime.now()
    logger.info(ts)

    # Load the data sourced from Xenbase.
    xenbase_to_human, tropicalis_to_laevis = load_xenbase_sourced_data(logger)

    # Attempt to get a database connection.
    conn_diopt = obtain_connection(args.host, args.database, args.username, args.password)

    for_geneid = ('SELECT gi.geneid, gi.speciesid, gi.species_specific_geneid, gi.species_specific_geneid_type, gi.symbol '
                  'FROM gene_information gi '
                  'WHERE gi.speciesid = %s ')

    for_op_table = ('SELECT op.ortholog_pairid, op.speciesid1, op.geneid1, op.speciesid2, op.geneid2, op.prediction_method '
                    'FROM ortholog_pair op '
                    'WHERE op.speciesid1 = %s '
                    'AND (op.speciesid2 = \'7955\' '
                    'OR op.speciesid2 = \'6239\' '
                    'OR op.speciesid2 = \'10090\' '
                    'OR op.speciesid2 = \'10116\' '
                    'OR op.speciesid2 = \'4932\' '
                    'OR op.speciesid2 = \'7227\' '
                    'OR op.speciesid2 = \'9606\' '
                    'OR op.speciesid2 = \'8364\') ')

    for_opb_table = ('SELECT opb.geneid1, opb.geneid2, opb.speciesid1, opb.speciesid2, opb.score, opb.best_score, opb.best_score_rev, opb.confidence '
                     'FROM ortholog_pair_best opb '
                     'WHERE opb.speciesid1 = %s '
                     'AND (opb.speciesid2 = \'7955\' '
                     'OR opb.speciesid2 = \'6239\' '
                     'OR opb.speciesid2 = \'10090\' '
                     'OR opb.speciesid2 = \'10116\' '
                     'OR opb.speciesid2 = \'4932\' '
                     'OR opb.speciesid2 = \'7227\' '
                     'OR opb.speciesid2 = \'9606\' '
                     'OR opb.speciesid2 = \'8364\') ')

    for_species_possibilities = ('SELECT distinct(sp1.speciesid), sp2.speciesid, op.prediction_method '
                                 'FROM species sp1, species sp2, ortholog_pair op '
                                 'WHERE op.speciesid1 = sp1.speciesid '
                                 'AND op.speciesid2 = sp2.speciesid ')

    for_distinct_algorithms = ('SELECT distinct(prediction_method) FROM ortholog_pair')

    # Taxon IDs and species for reference.
    # 7955 = Danio rerio 
    # 6239 = Caenorhabditis elegans 
    # 10090 = Mus musculus
    # 10116 = Rattus norvegicus
    # 4932 = Saccharomyces cerevisiae S288c
    # 7227 = Drosophila melanogaster
    # 9606 = Homo sapiens
    # 8364 = Xenopus tropicalis
    # 8355 = Xenopus laevis

    # Short species list for testing purposes.
    species_list = [7227, 7955, 6239, 10090, 10116, 4932, 9606, 8364]

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

    # Obtain the total possible algorithms.
    returned_distinct_algorithms = obtain_data_from_database(conn_diopt, for_distinct_algorithms)

    total_possible_algorithms = set()
    for i in returned_distinct_algorithms:
        algorithm_name = convert_algorithm_name(i[0])
        total_possible_algorithms.add(algorithm_name)

    # Add the manual Xenbase data algorithms:
    def add_xenbase_data_algorithms(total_possible_algorithms, xenbase_data, tropicalis_to_laevis):
        list_to_add = [xenbase_data, tropicalis_to_laevis]

        for entry in list_to_add:
            for item in entry:
                for algorithm in item['predictionMethodsMatched']:
                    algorithm = convert_algorithm_name(algorithm)
                    total_possible_algorithms.add(algorithm)
                for algorithm in item['predictionMethodsNotCalled']:
                    algorithm = convert_algorithm_name(algorithm)
                    total_possible_algorithms.add(algorithm)
                for algorithm in item['predictionMethodsNotMatched']:
                    algorithm = convert_algorithm_name(algorithm)
                    total_possible_algorithms.add(algorithm)

        return total_possible_algorithms

    total_possible_algorithms = add_xenbase_data_algorithms(total_possible_algorithms, xenbase_to_human, tropicalis_to_laevis)

    # Print each of the possible algorithms on a newline.
    logger.info('Algorithm List:')
    for i in total_possible_algorithms:
        logger.info(i)

    # Obtain the possible algorithm configurations
    returned_possible_combinations = obtain_data_from_database(conn_diopt, for_species_possibilities)

    # Create a nested dictionary with all the possible species1 x species2 algorithms.
    # First level is species1, second level is species2, third level is a set with all the algorithms called.
    algorithm_dictionary = nested_dict(2, set)

    for i in returned_possible_combinations:
        algorithm_name = convert_algorithm_name(i[2])
        algorithm_dictionary[i[0]][i[1]].add(algorithm_name)

    # Manually add Xenbase combinations.
    def add_xenbase_combinations(algorithm_dictionary, xenbase_to_human, tropicalis_to_laevis):
        list_to_add = [xenbase_to_human, tropicalis_to_laevis]
        categories_to_search = ['predictionMethodsMatched', 'predictionMethodsNotCalled', 'predictionMethodsNotMatched']
        
        # I dislike this level of nesting, but it saves code.
        for item in list_to_add:
            for entry in item:
                for algorithm_type in categories_to_search:
                    for algorithm in entry[algorithm_type]:
                        try:
                            algorithm_dictionary[entry['gene1Species']][entry['gene2Species']].add(algorithm)
                        except KeyError:
                            algorithm_dictionary[entry['gene1Species']][entry['gene2Species']] = set()
                            algorithm_dictionary[entry['gene1Species']][entry['gene2Species']].add(algorithm)
    
        return algorithm_dictionary

    algorithm_dictionary = add_xenbase_combinations(algorithm_dictionary, xenbase_to_human, tropicalis_to_laevis)

    # Print out a three level nested dictionary.
    logger.debug('Algorithm Dictionary:')
    for i in algorithm_dictionary:
        for j in algorithm_dictionary[i]:
            for k in algorithm_dictionary[i][j]:
                logger.debug('%s %s %s', i, j, k)

    # A dictionary to store all the gene information, keyed by the DIOPT database entry ID.
    gene_information_database = {}

    # A dictionary to track best_score, best_score_rev, and confidence data.
    # It's keyed by (gene1, gene2, species1, species2).
    # We use this to update the OrthologPair object.
    best_score_dictionary = {}

    def add_information_to_gene_information_database(gene_information_database, species, diopt_geneid, species_specific_geneid, species_specific_geneid_type, symbol):

        # Update identifiers
        # TODO Load BGI files from FMS and update gene identifiers.
        
        # If the data is from Xenbase, then we won't have a geneid.
        # We need to get the largest number from the gene_information_database keys and make our own.
        # It's not referenced in any way, so the number itself doesn't matter.
        # The geneid is only used for lookups with DIOPT data.
        if diopt_geneid is None:
            diopt_geneid = max(gene_information_database.keys()) + 1

        # Data wrangling.
        # This updates the species_specific_geneid field with the 'DRSC:' prefix.
        # Only if the species_specific_geneid doesn't already start with 'DRSC:'.
        species_specific_geneid = fix_identifier(logger, species_specific_geneid, species)

        # If fixing the identifier returned a None value.
        if species_specific_geneid is None:
            return gene_information_database, diopt_geneid  

        # This updates the species_specific_geneid_type field with the proper MOD name (e.g. FB, WB, ZFIN).
        mod_data_source = fix_species_specific_geneid_type(logger, species_specific_geneid_type, species)

        # Create a new blank dictionary for the gene information.
        gene_information_database[diopt_geneid] = {}

        gene_information_database[diopt_geneid]['species'] = species
        gene_information_database[diopt_geneid]['symbol'] = symbol
        gene_information_database[diopt_geneid]['species_specific_geneid'] = species_specific_geneid
        gene_information_database[diopt_geneid]['mod_data_source'] = mod_data_source

        return gene_information_database, diopt_geneid # Need to return the diopt_geneid for Xenbase to use later.

    def create_new_ortholog_pair_object(gene_information_database, diopt_geneid1, diopt_geneid2, speciesid1, speciesid2, data_source, **best_info_and_algorithms):

        # First, lookup the species_specific_geneid for each gene.
        try:
            species_specific_geneid1 = gene_information_database[diopt_geneid1]['species_specific_geneid']
        except KeyError:
            # Add to failed list.
            failed_gene_information_lookup.append((diopt_geneid1, speciesid1))
            return
        try:
            species_specific_geneid2 = gene_information_database[diopt_geneid2]['species_specific_geneid']
        except KeyError:
            # Add to failed list.
            failed_gene_information_lookup.append((diopt_geneid2, speciesid2))
            return

        # if diopt_geneid1 == 548903 or diopt_geneid2 == 548903:
        #     logger.info('{} {} {} {} {}'.format(diopt_geneid1, diopt_geneid2, speciesid1, speciesid2, data_source))
        #     logger.info('{} {}'.format(species_specific_geneid1, species_specific_geneid2))

        # Second, check if we're already storing this ortholog pair via the tracking tuple set.
        # Third, we need to check the data source. We don't want to store duplicate data from DIOPT and Xenbase.
        tracking_tuple = (species_specific_geneid1, species_specific_geneid2, speciesid1, speciesid2)

        ortholog_pair = OrthologyPair.get_ortholog_tuple_dict(tracking_tuple)
        if ortholog_pair is not None:
            # We have an existing ortholog pair object.
            # Check the data source and compare it to the existing data source.
            existing_data_source = ortholog_pair.get_data_source()
            # If it's the same data source, then we add to it.
            # if species_specific_geneid1 == 'DRSC:Xenbase:XB-GENE-5843537':
            #     logger.info('{} {} {} {}'.format(species_specific_geneid1, species_specific_geneid2, speciesid1, speciesid2))
            if existing_data_source == data_source:
                # We should only be adding to existing DIOPT data. Xenbase is finished after the first pass.
                if data_source == 'DIOPT': 
                    # Methods will be individually added to the ortholog pair object.
                    prediction_method = convert_algorithm_name(best_info_and_algorithms['predictionMethodsMatched'])
                    ortholog_pair.predictionMethodsMatched.append(prediction_method)
                    return
                else:
                    xenbase_duplicate_data.append((tracking_tuple, best_info_and_algorithms))
                    xenbase_duplicate_data_by_species[speciesid1][speciesid2].add((species_specific_geneid1, species_specific_geneid2))
                    return
            # If there's a different data source, then we skip it and don't create duplicate data.
            # This would be the case where DIOPT (processed first) has already created an entry for an ortholog pair.
            else:
                xenbase_diopt_ortholog_pair_conflict.append((species_specific_geneid1, species_specific_geneid2, speciesid1, speciesid2))
                return 
        else:
            # If we haven't seen this orthology pair (species_specific_geneid1, species_specific_geneid2, species1, species2) before.
            # Create a new ortholog pair object.
            
            ortholog_pair = OrthologyPair()
            OrthologyPair.add_to_ortholog_tuple_dict(tracking_tuple, ortholog_pair)

        # Set the genes.
        ortholog_pair.species_specific_geneid1 = gene_information_database[diopt_geneid1]['species_specific_geneid']
        ortholog_pair.species_specific_geneid2 = gene_information_database[diopt_geneid2]['species_specific_geneid']

        # Set the species.
        gene1_species = gene_information_database[diopt_geneid1]['species']
        ortholog_pair.gene1Species = gene1_species

        gene2_species = gene_information_database[diopt_geneid2]['species']
        ortholog_pair.gene2Species = gene2_species

        # Add the provider.
        ortholog_pair.gene1Provider = gene_information_database[diopt_geneid1]['mod_data_source']
        ortholog_pair.gene2Provider = gene_information_database[diopt_geneid2]['mod_data_source']

        # Add the best and confidence information.
        # Check whether we've passed these parameters via best_info.
        # This is required when sourcing from Xenbase data.
        if data_source == 'Xenbase':
            # Data wrangling.
            prediction_methods_matched = []
            prediction_methods_not_called = []
            prediction_methods_not_matched = []

            ortholog_pair.isBestScore = best_info_and_algorithms['isBestScore']
            ortholog_pair.isBestRevScore = best_info_and_algorithms['isBestRevScore']
            ortholog_pair.confidence = best_info_and_algorithms['confidence']
        # For Xenbase, we'll have all the algorithm info on the first pass.
        # For DIOPT, this will be calculated later.
            for item in best_info_and_algorithms['predictionMethodsNotCalled']:
                prediction_methods_not_called.append(convert_algorithm_name(item))
            for item in best_info_and_algorithms['predictionMethodsNotMatched']:
                prediction_methods_not_matched.append(convert_algorithm_name(item))
            for item in best_info_and_algorithms['predictionMethodsMatched']:
                prediction_methods_matched.append(convert_algorithm_name(item))
            
            ortholog_pair.predictionMethodsMatched = prediction_methods_matched
            ortholog_pair.predictionMethodsNotMatched = prediction_methods_not_matched
            ortholog_pair.predictionMethodsNotCalled = prediction_methods_not_called

        # If not, we get the info from the best_score_dictionary.
        # This will be the case for DIOPT info.
        if data_source == 'DIOPT':
            best_score, best_score_rev, confidence = best_score_dictionary[(diopt_geneid1, diopt_geneid2, speciesid1, speciesid2)]
            ortholog_pair.isBestScore = best_score
            ortholog_pair.isBestRevScore = best_score_rev
            ortholog_pair.confidence = confidence

            # We also add the methods to the list of prediction methods matched.
            prediction_method = convert_algorithm_name(best_info_and_algorithms['predictionMethodsMatched'])
            ortholog_pair.predictionMethodsMatched.append(prediction_method)

        # Add the data source in both cases.
        ortholog_pair.data_source = data_source

        return

    logger.info('Processing DIOPT database information.')
    for i in tqdm(species_list):

        logger.info("Obtaining gene_information for species %s" % (i))
        query_variable = (i,)
        returned_geneid = obtain_data_from_database_query_variable(conn_diopt, for_geneid, query_variable)

        # Populate the gene_information_database dictionary.
        # This tracks loads of information for a specific geneid.
        for j in returned_geneid:

            species = j[1]
            diopt_geneid = j[0]
            species_specific_geneid = j[2]
            species_specific_geneid_type = j[3]
            symbol = j[4]

            if species_specific_geneid is None:
                diopt_missing_species_specific_geneid.append((species,diopt_geneid))
                if symbol is None:
                    diopt_missing_species_specific_geneid_and_symbol.append((species,diopt_geneid))
                    continue
                else:
                    species_specific_geneid = symbol

            gene_information_database, _ = add_information_to_gene_information_database(gene_information_database, species, diopt_geneid, species_specific_geneid, species_specific_geneid_type, symbol)

    for i in species_list:
        query_variable = (i,)
        logger.info("Obtaining ortholog_pair_best info for species %s" % (i))
        returned_opb_table = obtain_data_from_database_query_variable(conn_diopt, for_opb_table, query_variable)

        # Query results order for reference.
        # b[0] = geneid1
        # b[1] = geneid2
        # b[2] = speciesid1
        # b[3] = speciesid2
        # b[4] = score # Not used.
        # b[5] = best_score
        # b[6] = best_score_rev
        # b[7] = confidence

        for b in returned_opb_table:
            diopt_geneid1 = b[0]
            diopt_geneid2 = b[1]
            speciesid1 = b[2]
            speciesid2 = b[3]
            best_score = b[5]
            best_score_rev = b[6]
            confidence = b[7]

            best_score_dictionary[(diopt_geneid1, diopt_geneid2, speciesid1, speciesid2)] = (best_score, best_score_rev, confidence)

        logger.info("Obtaining ortholog_pair info for species %s" % (i))
        returned_op_table = obtain_data_from_database_query_variable(conn_diopt, for_op_table, query_variable)

        # These results are single gene-to-gene comparison for a single successful algorithm.
        # Query results order for reference.
        # k[0] = ortholog_pairid
        # k[1] = speciesid1
        # k[2] = geneid1
        # k[3] = speciesid2
        # k[4] = geneid2
        # k[5] = prediction_method

        for k in returned_op_table:
            ortholog_pairid = k[0]
            speciesid1 = k[1]
            diopt_geneid1 = k[2]
            speciesid2 = k[3]
            diopt_geneid2 = k[4]
            prediction_method = k[5]

            # if speciesid1 == 8364:
            #     logger.info('{}'.format(k))

            # if diopt_geneid1 == 548903:
            #     logger.info('{}'.format(k))

            # if diopt_geneid2 == 548903:
            #     logger.info('{}'.format(k))

            # TODO: Investigate further
            if diopt_geneid1 not in gene_information_database:
                diopt_found_in_pair_table_missing_from_gene_information_table.append((speciesid1, ortholog_pairid))
                continue

            data_source = 'DIOPT'

            best_info_and_algorithms = {
                'predictionMethodsMatched': prediction_method # This will be a single method.
            }

            _ = create_new_ortholog_pair_object(gene_information_database, diopt_geneid1, diopt_geneid2, speciesid1, speciesid2, data_source, **best_info_and_algorithms)

    logger.info("Dumping pickle file.")
    pickle.dump(gene_information_database, open("gene_information_database.p", "wb"))


    def add_XB_to_gene_information_database_and_create_ortholog_pair(source_dict, gene_information_database):

        # Loop through the Xenbase data and add it to the gene_information_database.
        logger.info('Adding Xenbase data to gene_information_database.')

        diopt_geneid = None # Starts as None.

        for item in tqdm(source_dict):
            gene1_species = item['gene1Species']
            gene2_species = item['gene2Species']

            gene1_species_specific_geneid = item['gene1']
            gene2_species_specific_geneid = item['gene2']

            species_specific_geneid_type = 'Xenbase'

            confidence = item['confidence']
            isBestRevScore  = item['isBestRevScore']
            isBestScore = item['isBestScore']

            best_info_and_algorithms = {
                'predictionMethodsMatched': set(item['predictionMethodsMatched']),
                'predictionMethodsNotMatched': set(item['predictionMethodsNotMatched']),
                'predictionMethodsNotCalled': set(item['predictionMethodsNotCalled']),
                'confidence': confidence,
                'isBestRevScore': isBestRevScore,
                'isBestScore': isBestScore,
            }

            gene_information_database, diopt_geneid1 = add_information_to_gene_information_database(gene_information_database, gene1_species, diopt_geneid, gene1_species_specific_geneid, species_specific_geneid_type, symbol)
            diopt_geneid2 = diopt_geneid1 + 1 # Increment manually for the next function.
            gene_information_database, diopt_geneid2 = add_information_to_gene_information_database(gene_information_database, gene2_species, diopt_geneid2, gene2_species_specific_geneid, species_specific_geneid_type, symbol)

            # Increment this one more time for the next diopt_geneid loop.
            diopt_geneid = diopt_geneid2 + 1

            data_source = 'Xenbase'

            create_new_ortholog_pair_object(gene_information_database, diopt_geneid1, diopt_geneid2, gene1_species, gene2_species, data_source, **best_info_and_algorithms)

        return gene_information_database
    
    gene_information_database = add_XB_to_gene_information_database_and_create_ortholog_pair(xenbase_to_human, gene_information_database)
    gene_information_database = add_XB_to_gene_information_database_and_create_ortholog_pair(tropicalis_to_laevis, gene_information_database)

    # Loop through our objects and update the algorithms.
    ortholog_pair_objects_list = OrthologyPair.get_all_instances()

    logger.info('Updating algorithms and filters.')
    for item in tqdm(ortholog_pair_objects_list):
        data_source = item.data_source

        # Needed for DIOPT and Xenbase calculations.
        matched_prediction_methods = set(item.predictionMethodsMatched)

        if data_source == 'Xenbase':
            item.predictionMethodsNotMatched = set(item.predictionMethodsNotMatched)
            item.predictionMethodsNotCalled = set(item.predictionMethodsNotCalled)
            item.predictionMethodsMatched = set(item.predictionMethodsMatched)     
        else:
            gene1_species = item.gene1Species
            gene2_species = item.gene2Species
            gene1 = item.species_specific_geneid1
            gene2 = item.species_specific_geneid2
            matched_prediction_methods = set(item.predictionMethodsMatched)
            possible_prediction_methods = set(algorithm_dictionary[gene1_species][gene2_species])
            not_called_prediction_methods = total_possible_algorithms - possible_prediction_methods  # subtracting sets
            not_matched_prediction_methods = possible_prediction_methods - matched_prediction_methods  # subtracting sets

            item.predictionMethodsNotMatched = not_matched_prediction_methods
            item.predictionMethodsNotCalled = not_called_prediction_methods

        # Determine the stringency filter to add.
        strict_filter = False
        moderate_filter = False

        if 'ZFIN' in matched_prediction_methods or 'HGNC' in matched_prediction_methods or 'Xenbase' in matched_prediction_methods:
            strict_filter = True
            moderate_filter = True

        best_score = item.isBestScore
        best_rev_score = item.isBestRevScore

        if (len(matched_prediction_methods) > 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') or best_rev_score == 'Yes')) \
                or (len(matched_prediction_methods) == 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') and best_rev_score == 'Yes')):
            strict_filter = True

        elif len(matched_prediction_methods) > 2 \
                or (len(matched_prediction_methods) == 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') and best_rev_score == 'Yes')):
            moderate_filter = True

        item.moderateFilter = moderate_filter
        item.strictFilter = strict_filter

    # Printing out some stats.

    # Transform xenbase_diopt_ortholog_pair_conflict from a list to a set.
    xenbase_diopt_ortholog_pair_conflict_set = set(xenbase_diopt_ortholog_pair_conflict)

    logger.info('Total number of xenbase_diopt_ortholog_pair_conflict: %s' % (len(xenbase_diopt_ortholog_pair_conflict_set)))
    logger.info('Total number of duplicate Xenbase entries: %s' % (len(xenbase_duplicate_data)))
    logger.info('Total number of diopt_missing_species_specific_geneid: %s' % (len(diopt_missing_species_specific_geneid)))
    logger.info('Total number of diopt_missing_species_specific_geneid_and_symbol: %s' % (len(diopt_missing_species_specific_geneid_and_symbol)))
    logger.info('Total number of diopt_found_in_pair_table_missing_from_gene_information_table: %s' % (len(diopt_found_in_pair_table_missing_from_gene_information_table)))

    # Print counts from the more complicated nested dict xenbase_duplicate_data_by_species.
    total_xenbase_skipped = 0

    for species1 in xenbase_duplicate_data_by_species:
        for species2 in xenbase_duplicate_data_by_species[species1]:
            total_xenbase_skipped += len(xenbase_duplicate_data_by_species[species1][species2])
            logger.info('Total number of duplicate Xenbase entries for %s and %s: %s' % (species1, species2, len(xenbase_duplicate_data_by_species[species1][species2])))

    logger.info('Total number of duplicate Xenbase entries skipped: %s' % (total_xenbase_skipped))

    # Open a log file to save this information.
    log_file = open('log_file.txt', 'w')

    for item in xenbase_duplicate_data:
        log_file.write('{}\n'.format(item))

    # Checking for unidirectional orthology issues.
    logger.info('Checking for unidirectional orthology issues.')

    tropicalis_to_human_uni_check = {}
    human_to_tropicalis_uni_check = {}

    for item in tqdm(ortholog_pair_objects_list):

        isBestScore = item.isBestScore
        isBestRevScore = item.isBestRevScore
        gene1 = item.species_specific_geneid1
        gene2 = item.species_specific_geneid2
        gene1Species = item.gene1Species
        gene2Species = item.gene2Species
        predictionMethodsMatched = item.predictionMethodsMatched
        predictionMethodsNotMatched = item.predictionMethodsNotMatched
        predictionMethodsNotCalled = item.predictionMethodsNotCalled
        confidence = item.confidence
        strictFilter = item.strictFilter
        moderateFilter = item.moderateFilter

        # Skipping paralogs
        if gene1Species == gene2Species:
            continue

        if gene1Species == 8355 and gene2Species == 9606:
            tropicalis_to_human_uni_check[gene1] = gene2

        if gene1Species == 9606 and gene2Species == 8355:
            human_to_tropicalis_uni_check[gene1] = gene2

    # Check if the key and value from one dictionary exist as a reversed key and value in the other dictionary.
    # If so, then the ortholog pair is unidirectional.
    trop_to_human_unidirectional_ortholog_pairs = []
    human_to_trop_unidirectional_ortholog_pairs = []

    for item in tropicalis_to_human_uni_check:
        item_to_check = tropicalis_to_human_uni_check[item]
        if not item_to_check in human_to_tropicalis_uni_check.keys():
            trop_to_human_unidirectional_ortholog_pairs.append((item, item_to_check))

    for item in human_to_tropicalis_uni_check:
        item_to_check = human_to_tropicalis_uni_check[item]
        if not item_to_check in tropicalis_to_human_uni_check.keys():
            human_to_trop_unidirectional_ortholog_pairs.append((item, item_to_check))

    logger.info('Total number of unidirectional ortholog pairs from tropicalis to human: %s' % (len(trop_to_human_unidirectional_ortholog_pairs)))
    logger.info('Total number of unidirectional ortholog pairs from human to tropicalis: %s' % (len(human_to_trop_unidirectional_ortholog_pairs)))
    
    logger.info('Total number of failed gene information lookups: %s' % (len(failed_gene_information_lookup)))

    # Loop though our nested dictionaries and form the JSON for export.  

    logger.info("Converting data into JSON structure.")

    json_by_mod = {}
    json_by_mod['RGD'] = []
    json_by_mod['MGI'] = []
    json_by_mod['ZFIN'] = []
    json_by_mod['SGD'] = []
    json_by_mod['WormBase'] = []
    json_by_mod['FlyBase'] = []
    json_by_mod['Human'] = []
    json_by_mod['XBXT'] = []
    json_by_mod['XBXL'] = []

    # Get total list of OrthologPair objects.
    ortholog_pair_objects_list = OrthologyPair.get_all_instances()

    # Print out the number of ortholog pairs.
    logger.info('Number of ortholog pairs for export: {}'.format(len(ortholog_pair_objects_list)))

    logger.info('Creating JSON.')
    for item in tqdm(ortholog_pair_objects_list):

        isBestScore = item.isBestScore
        isBestRevScore = item.isBestRevScore
        gene1 = item.species_specific_geneid1
        gene2 = item.species_specific_geneid2
        gene1Species = item.gene1Species
        gene2Species = item.gene2Species
        predictionMethodsMatched = item.predictionMethodsMatched
        predictionMethodsNotMatched = item.predictionMethodsNotMatched
        predictionMethodsNotCalled = item.predictionMethodsNotCalled
        confidence = item.confidence
        strictFilter = item.strictFilter
        moderateFilter = item.moderateFilter

        # if gene1 == 'DRSC:XB-GENE-5843537' or gene2 == 'DRSC:XB-GENE-5843537':
        #     logger.info('{} {} {} {}'.format(gene1, gene2, gene1Species, gene2Species))

        # Skipping paralogs
        if gene1Species == gene2Species:
            continue

        # Add the data to the JSON.
        dict_to_add = {}

        dict_to_add['isBestScore'] = isBestScore
        dict_to_add['isBestRevScore'] = isBestRevScore
        dict_to_add['gene1'] = gene1
        dict_to_add['gene1Species'] = gene1Species
        dict_to_add['gene2'] = gene2
        dict_to_add['gene2Species'] = gene2Species
        dict_to_add['predictionMethodsMatched'] = list(predictionMethodsMatched)
        dict_to_add['predictionMethodsNotMatched'] = list(predictionMethodsNotMatched)
        dict_to_add['predictionMethodsNotCalled'] = list(predictionMethodsNotCalled)
        dict_to_add['confidence'] = confidence
        dict_to_add['strictFilter'] = strictFilter
        dict_to_add['moderateFilter'] = moderateFilter

        mod_to_add = taxon_to_mod[gene1Species]
        json_by_mod[mod_to_add].append(dict_to_add)

    the_time = strict_rfc3339.now_to_rfc3339_localoffset()

    # Dictionary for producing a test set of data.
    dataProviderdict = {}
    dataProviderdict['type'] = 'curated'
    dataProviderdict['crossReference'] = {}
    dataProviderdict['crossReference']['id'] = 'DRSC'
    dataProviderdict['crossReference']['pages'] = ['homepage']

    test_json_to_export = {}
    test_json_to_export['metaData'] = {}
    test_json_to_export['metaData']['dataProvider'] = dataProviderdict
    test_json_to_export['metaData']['dateProduced'] = the_time
    test_json_to_export['metaData']['release'] = '9'
    test_json_to_export['data'] = []

    logger.info("Exporting JSON by MOD.")
    for mod in json_by_mod:
        to_export_as_json = {}
        to_export_as_json['metaData'] = {}
        to_export_as_json['metaData']['dataProvider'] = dataProviderdict
        to_export_as_json['metaData']['dateProduced'] = the_time
        to_export_as_json['metaData']['release'] = '9'
        to_export_as_json['data'] = json_by_mod[mod]

        for entry in json_by_mod[mod]:
            trimmed_entry = entry['gene1'][5:]
            if trimmed_entry in test_set_of_genes:
                test_json_to_export['data'].append(entry)

        filename = 'orthology_%s_v9.json' % (mod)
        logger.info("Saving %s" % (filename))
        with open(filename, 'w') as outfile:
            json.dump(to_export_as_json, outfile, sort_keys=True, indent=2, separators=(',', ': '))
            outfile.close()
        os.system("gzip -f orthology_" + str(mod) + "_v9.json")

    logger.info("Saving test JSON dataset.")
    test_filename = 'orthology_test_data_v9.json'
    logger.info("Saving %s" % (test_filename))
    with open(test_filename, 'w') as outfile:
        json.dump(test_json_to_export, outfile, sort_keys=True, indent=2, separators=(',', ': '))
        outfile.close()

    os.system("gzip -f orthology_test_data_v9.json")
    # Close the database connection.
    conn_diopt.close()

    tf = datetime.datetime.now()
    logger.info(tf)

    te = tf - ts

    logger.info('Total orthology comparisons by MOD:')
    for mod in json_by_mod:
        logger.info('%s: %s' % (mod, len(json_by_mod[mod])))

    logger.info("Done!")
    logger.info("Elapsed time: %s" % (te))
    logger.info("Please wait for the last gzip command to finish...")


if __name__ == "__main__":
    main()
