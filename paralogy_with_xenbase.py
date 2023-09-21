#!/usr/bin/env python
import psycopg2
import strict_rfc3339
import os
import pickle
import datetime
import json
import pprint
from tqdm import tqdm
import csv
from nested_dict import nested_dict
import configparser
import argparse
import coloredlogs
import logging

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

def fix_identifier(logger, identifier, speciesid):
    if speciesid == 7955:  # ZFIN
        identifier_output = 'DRSC:' + identifier
        return identifier_output
    elif speciesid == 6239:  # WB
        identifier_output = 'DRSC:' + identifier
        return identifier_output
    elif speciesid == 10090:  # MGI
        identifier_output = 'DRSC:MGI:' + identifier
        return identifier_output
    elif speciesid == 10116:  # RGD
        identifier_output = 'DRSC:RGD:' + identifier
        return identifier_output
    elif speciesid == 4932:  # SGD
        identifier_output = 'DRSC:' + identifier
        return identifier_output
    elif speciesid == 7227:  # FB
        identifier_output = 'DRSC:' + identifier
        return identifier_output
    elif speciesid == 9606:  # HGNC
        identifier_output = 'DRSC:HGNC:' + identifier
        return identifier_output
    elif speciesid == 8364:  # Xenbase
        identifier_output = 'DRSC:Xenbase:' + identifier
        return identifier_output
    else:
        logger.critical("Fatal error: cannot correct species specific gene id %s" % (identifier))
        quit()

def fix_missing_entry(logger, speciesid):
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
        'HGNC:897', 'HGNC:869', 'HGNC:10848', 'HGNC:10402', 'HGNC:11204', 'HGNC:12597', 'HGNC:811'
    }

    return test_set_of_genes


def calculate_score(entry, max_length, avg_length):
    # Extract necessary data, retaining None values
    length = entry.get("length")
    similarity = entry.get("similarity")
    identity = entry.get("identity")
    
    method_count_ratio = len(entry['matched_prediction_methods']) / (len(entry['possible_prediction_methods']) + 1e-5)
    
    # Calculate absolute similarity and identity, handling None values appropriately
    absolute_similarity = (length * (similarity / 100)) if (length is not None and similarity is not None) else None
    absolute_identity = (length * (identity / 100)) if (length is not None and identity is not None) else None
    
    # Calculate alignment length ratio, handling None values appropriately
    alignment_length_ratio = (length / max_length) if (length is not None and max_length != 0) else None
    
    # Calculate score using the new formula, handling None values appropriately
    score_components = [value for value in [(1.000 * absolute_similarity if absolute_similarity is not None else 0), 
                                            (1.000 * absolute_identity if absolute_identity is not None else 0), 
                                            1.500 * method_count_ratio, 
                                            (1.500 * alignment_length_ratio if alignment_length_ratio is not None else 0)] 
                        if value is not None]
    score = sum(score_components)
    return score

def assign_ranks(database):
    skipped_count = 0
    
    # Calculate the maximum and average alignment lengths across all entries
    all_lengths = [entry.get("length") for gene1, gene2_data in database.items() for entry in gene2_data.values() if isinstance(entry, dict)]
    filtered_lengths = [x for x in all_lengths if x is not None]
    max_length = max(filtered_lengths) if filtered_lengths else 0
    avg_length = sum(filtered_lengths) / len(filtered_lengths) if filtered_lengths else 0

    for gene1, gene2_data in tqdm(database.items()):
        gene2_dicts = {key: value for key, value in gene2_data.items() if isinstance(value, dict)}
        
        # Filter out gene2 entries missing 'matched_prediction_methods'
        valid_gene2_keys = [key for key in gene2_dicts if 'matched_prediction_methods' in gene2_dicts[key]]
        
        # Update the skipped count
        skipped_count += len(gene2_dicts) - len(valid_gene2_keys)
        
        prediction_scores = [calculate_score(gene2_dicts[key], max_length, avg_length) for key in valid_gene2_keys]

        sorted_gene2_keys = sorted(valid_gene2_keys, key=lambda x: -prediction_scores[valid_gene2_keys.index(x)])
        
        # Assigning ranks with shared ranks for identical entries
        previous_score = None
        previous_rank = 0
        for gene2 in sorted_gene2_keys:
            current_score = prediction_scores[valid_gene2_keys.index(gene2)]
            if current_score == previous_score:
                database[gene1][gene2]["rank"] = previous_rank
            else:
                previous_rank += 1
                database[gene1][gene2]["rank"] = previous_rank
                previous_score = current_score

    print(f"Skipped {skipped_count} entries due to missing 'matched_prediction_methods'.")

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

    # Attempt to get a database connection.
    conn_diopt = obtain_connection(args.host, args.database, args.username, args.password)

    for_geneid = ('SELECT gi.geneid, gi.speciesid, gi.species_specific_geneid, gi.species_specific_geneid_type, gi.symbol '
                  'FROM gene_information gi '
                  'WHERE gi.speciesid = %s ')

    for_op_table = ('SELECT op.paralog_pairid, op.speciesid1, op.geneid1, op.speciesid2, op.geneid2, op.prediction_method '
                    'FROM paralog_pair op '
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
                     'FROM paralog_pair_best opb '
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
                                 'FROM species sp1, species sp2, paralog_pair op '
                                 'WHERE op.speciesid1 = sp1.speciesid '
                                 'AND op.speciesid2 = sp2.speciesid ')

    for_distinct_algorithms = ('SELECT distinct(prediction_method) FROM paralog_pair')

    for_alignment = ('SELECT b.geneid1, b.geneid2, align_length, align_score, align_identity, align_similarity from protein_data '
                     'as a, paralog_pair_best as b where a.geneid1=b.geneid1 and a.geneid2=b.geneid2')

    # Taxon IDs and species for reference.
    # 7955 = Danio rerio 
    # 6239 = Caenorhabditis elegans 
    # 10090 = Mus musculus
    # 10116 = Rattus norvegicus
    # 4932 = Saccharomyces cerevisiae S288c
    # 7227 = Drosophila melanogaster
    # 9606 = Homo sapiens
    # 8364 = Xenopus tropicalis

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
        8364: 'Xenbase'
    }

    logger.info('Obtaining algorithm list.')
    # Obtain the total possible algorithms.
    returned_distinct_algorithms = obtain_data_from_database(conn_diopt, for_distinct_algorithms)

    total_possible_algorithms = set()
    for i in returned_distinct_algorithms:
        algorithm_name = convert_algorithm_name(i[0])
        total_possible_algorithms.add(algorithm_name)

    # Print each of the possible algorithms on a newline.
    logger.info('Algorithm List:')
    for i in total_possible_algorithms:
        logger.info(i)

    # Obtain the possible algorithm configurations
    returned_possible_combinations = obtain_data_from_database(conn_diopt, for_species_possibilities)

    # Create a nested dictionary with all the possible species1 x species2 algorithms.
    # First level is species1, second level is species2, third level is a set with all the algorithms called.
    algorithm_dictionary = nested_dict(2, set)

    logger.info('Creating algorithm dictionary.')
    for i in tqdm(returned_possible_combinations):
        algorithm_name = convert_algorithm_name(i[2])
        algorithm_dictionary[i[0]][i[1]].add(algorithm_name)

    mini_database = {}

    if not args.pickle:
        # Obtain all the protein pair records containing similarity, identity, etc.
        logger.info('Obtaining protein pair information.')
        return_protein_pair = obtain_data_from_database(conn_diopt, for_alignment)    

        # Print out the number of records returned.
        logger.info('Returned {} records'.format(len(return_protein_pair)))

        # (293085, 300605, 315.0, 541.0, 0.393651, 0.574603)
        logger.info('Converting returned list to a dictionary.')
        protein_pair_dict = {}
        for item in tqdm(return_protein_pair):
            if item[0] not in protein_pair_dict:
                protein_pair_dict[item[0]] = {}
            if item[1] not in protein_pair_dict[item[0]]:
                protein_pair_dict[item[0]][item[1]] = {}
            protein_pair_dict[item[0]][item[1]]['length'] = item[2]
            protein_pair_dict[item[0]][item[1]]['score'] = item[3]
            protein_pair_dict[item[0]][item[1]]['identity'] = item[4]
            protein_pair_dict[item[0]][item[1]]['similarity'] = item[5]

        for i in species_list:

            missing_species_specific_geneid = set()

            print("Obtaining gene_information for species %s" % (i))
            query_variable = (i,)
            returned_geneid = obtain_data_from_database_query_variable(conn_diopt, for_geneid, query_variable)

            # Query results order for reference.
            # geneid, speciesid, species_specific_geneid, species_specific_geneid_type, symbol
            for j in returned_geneid:
                species = j[1]
                geneid = j[0]
                species_specific_geneid = j[2]

                if species_specific_geneid is None:
                    missing_species_specific_geneid.add(geneid)
                    continue

                # Update identifiers
                # TODO Load BGI files from FMS and update gene identifiers.

                fixed_species_specific_geneid = fix_identifier(logger, species_specific_geneid, species)

                mini_database[geneid] = {}

                if j[3] == '-' or j[3] is None:  # Weird hyphen character or None found in some fields.
                    mini_database[geneid]['species_specific_geneid_type'] = fix_missing_entry(logger, species)
                elif j[3] == 'FLYBASE':
                    mini_database[geneid]['species_specific_geneid_type'] = 'FB'
                elif j[3] == 'WormBase':
                    mini_database[geneid]['species_specific_geneid_type'] = 'WB'
                else:
                    mini_database[geneid]['species_specific_geneid_type'] = j[3]

                mini_database[geneid]['species'] = species

                mini_database[geneid]['symbol'] = j[4]

                mini_database[geneid]['species_specific_geneid'] = fixed_species_specific_geneid

            if missing_species_specific_geneid:
                logger.warning('Missing {} species-specific gene identifiers for species {}'.format(len(missing_species_specific_geneid), i))

            print("Obtaining ortholog_pair info for species %s" % (i))
            returned_op_table = obtain_data_from_database_query_variable(conn_diopt, for_op_table, query_variable)

            # op.ortholog_pairid, op.speciesid1, op.geneid1, op.speciesid2, op.geneid2, op.prediction_method
            for k in returned_op_table:
                geneid = k[2]
                geneid2 = k[4]

                prediction_method = convert_algorithm_name(k[5])

                # TODO: Investigate further
                if geneid not in mini_database:
                    continue

                if geneid2 not in mini_database[geneid]:
                    mini_database[geneid][geneid2] = {}

                # Lookup the species specific gene id's from the first query.
                if 'prediction_method' in mini_database[geneid][geneid2]:
                    mini_database[geneid][geneid2]['prediction_method'].add(prediction_method)
                else:
                    mini_database[geneid][geneid2]['prediction_method'] = set()
                    mini_database[geneid][geneid2]['prediction_method'].add(prediction_method)

            print("Obtaining ortholog_pair_best info for species %s" % (i))
            returned_opb_table = obtain_data_from_database_query_variable(conn_diopt, for_opb_table, query_variable)

            # opb.geneid1, opb.geneid2, opb.speciesid1, opb.speciesid2, opb.score, opb.best_score, opb.best_score_rev, opb.confidence
            for b in returned_opb_table:
                geneid = b[0]
                geneid2 = b[1]

                # print "geneid: %s, geneid2: %s" % (geneid, geneid2)
                # TODO: Investigate further
                if geneid not in mini_database:
                    continue

                mini_database[geneid][geneid2]['best_score'] = b[5]
                mini_database[geneid][geneid2]['best_score_rev'] = b[6]
                mini_database[geneid][geneid2]['confidence'] = b[7]

        # Adding the prediction methods and alignment data to each pair.
        print("Sorting prediction methods and alignment stats for each possible paralog combination.")
        geneid2_missing_mini_database = 0
        successful = 0
        length_missing = 0
        identity_missing = 0
        similarity_missing = 0
        score_missing = 0
        geneid1_missing = 0
        geneid2_missing = 0
        list_of_ids_to_check = []
        for k, v in tqdm(mini_database.items()):
            geneid1 = k
            if isinstance(v, dict):
                for j, q in v.items():
                    if isinstance(q, dict):
                        geneid2 = j

                        # TODO: Investigate futher.
                        if geneid2 not in mini_database:
                            geneid2_missing_mini_database += 1
                            continue

                        gene1_species = mini_database[geneid1]['species']
                        gene2_species = mini_database[geneid2]['species']

                        possible_prediction_methods = algorithm_dictionary[gene1_species][gene2_species]
                        matched_prediction_methods = q['prediction_method']
                        not_called_prediction_methods = total_possible_algorithms - possible_prediction_methods  # subtracting sets
                        not_matched_prediction_methods = possible_prediction_methods - matched_prediction_methods  # subtracting sets
        
                        # Add the methods to the geneid2 dictionary.
                        mini_database[geneid1][geneid2]['not_called_prediction_methods'] = not_called_prediction_methods
                        mini_database[geneid1][geneid2]['not_matched_prediction_methods'] = not_matched_prediction_methods
                        mini_database[geneid1][geneid2]['matched_prediction_methods'] = matched_prediction_methods
                        mini_database[geneid1][geneid2]['possible_prediction_methods'] = possible_prediction_methods

                        
                        # Add the alignment data to the geneid2 dictionary.
                        # Try to lookup each key and assign it. If the key is missing, make it none.
                        try:
                            mini_database[geneid1][geneid2]['length'] = protein_pair_dict[geneid1][geneid2].get('length', None)
                            mini_database[geneid1][geneid2]['score'] = protein_pair_dict[geneid1][geneid2].get('score', None)
                            mini_database[geneid1][geneid2]['identity'] = protein_pair_dict[geneid1][geneid2].get('identity', None)
                            mini_database[geneid1][geneid2]['similarity'] = protein_pair_dict[geneid1][geneid2].get('similarity', None)
                            successful += 1
                        except KeyError:
                            # Figure out whether we're missing [geneid1] or [geneid2] or both in protein_pair_dict.
                            # Increment the tracking variable and still assign all the values as None.
                            if geneid1 not in protein_pair_dict:
                                geneid1_missing += 1
                                # list_of_ids_to_check.append(geneid1)
                                # if list_of_ids_to_check.count(geneid1) > 9:
                                #     for i in list_of_ids_to_check:
                                #         print('geneid1: {}'.format(i))
                                #     quit()
                            elif geneid2 not in protein_pair_dict[geneid1]:
                                geneid2_missing += 1
                            mini_database[geneid1][geneid2]['length'] = None
                            mini_database[geneid1][geneid2]['score'] = None
                            mini_database[geneid1][geneid2]['identity'] = None
                            mini_database[geneid1][geneid2]['similarity'] = None

                        if mini_database[geneid1][geneid2]['length'] is None:
                            length_missing += 1
                        if mini_database[geneid1][geneid2]['identity'] is None:
                            identity_missing += 1
                        if mini_database[geneid1][geneid2]['similarity'] is None:
                            similarity_missing += 1
                        if mini_database[geneid1][geneid2]['score'] is None:
                            score_missing += 1
                            
        print('Successful: {}'.format(successful))
        print('geneid2 missing mini database: {}'.format(geneid2_missing_mini_database))
        print('geneid1 missing alignment data: {}'.format(geneid1_missing))
        print('geneid2 missing alignment data: {}'.format(geneid2_missing))
        print('length missing: {}'.format(length_missing))
        print('identity missing: {}'.format(identity_missing))
        print('similarity missing: {}'.format(similarity_missing))
        print('score missing: {}'.format(score_missing))

        print('Filtering matches for yeast to include only SGD method matches.')
        print('Removing any yeast entry that does not have at least an SGD method match.')

        for gene1, gene2_data in tqdm(mini_database.items()):
            # Check if gene1 is yeast.
            if mini_database[gene1]['species'] != 4932:
                continue

            # Create a list to store keys that do not have an SGD match
            keys_to_remove = []

            # Check each gene2 entry for SGD method match
            for gene2, data in gene2_data.items():
                # Ensure it's a dictionary and check for SGD method match
                if isinstance(data, dict) and 'matched_prediction_methods' in data:
                    if 'SGD' not in data['matched_prediction_methods']:
                        keys_to_remove.append(gene2)

            # Remove entries without an SGD match
            for key in keys_to_remove:
                del mini_database[gene1][key]

        print('Filtering matches to include only those with two or more matches in matched_prediction_methods.')
        print('Removing any entry (except yeast) that does not meet this criterion.')

        for gene1, gene2_data in tqdm(mini_database.items()):
            # Check if gene1 is yeast and skip if true.
            if mini_database[gene1]['species'] == 4932:
                continue
            
            # Create a list to store keys that do not have at least two matches
            keys_to_remove = []

            # Check each gene2 entry for the number of matches in matched_prediction_methods
            for gene2, data in gene2_data.items():
                # Ensure it's a dictionary and check for the number of matches
                if isinstance(data, dict) and 'matched_prediction_methods' in data:
                    if len(data['matched_prediction_methods']) < 2:
                        keys_to_remove.append(gene2)

            # Remove entries with less than two matches
            for key in keys_to_remove:
                del mini_database[gene1][key]

        print('Assigning ranks to each paralog pair.')
        assign_ranks(mini_database)

        # Look for test gene with species specific geneid WBGene00001964
        # temp_analysis_dict = {}
        # for gene1 in tqdm(mini_database):
        #     if mini_database[gene1]['species_specific_geneid'] == 'DRSC:WBGene00001964':
        #         print('Found WBGene00001964')
        #         # Pretty print the dictionary.
        #         pp = pprint.PrettyPrinter(indent=4)
        #         pp.pprint(mini_database[gene1])
        #         for j, q in mini_database[gene1].items():
        #             if isinstance(q, dict):
        #                 geneid2 = j
        #                 temp_analysis_dict[geneid2] = {}
        #                 temp_analysis_dict[geneid2]['symbol'] = {mini_database[geneid2]['symbol']}
        #                 temp_analysis_dict[geneid2]['rank'] = {q['rank']}
        # pp.pprint(temp_analysis_dict)

        print("Dumping pickle file.")
        pickle.dump(mini_database, open("mini_database.p", "wb"))

    elif args.pickle:
        print("Loading pickle file.")
        mini_database = pickle.load(open("mini_database.p", "rb"))

    # Loop though our nested dictionaries and form the JSON for export.

    print("Converting data into JSON structure.")

    json_by_mod = {}
    json_by_mod[9606] = []
    json_by_mod[6239] = []
    json_by_mod[10090] = []
    json_by_mod[10116] = []
    json_by_mod[4932] = []
    json_by_mod[7955] = []
    json_by_mod[7227] = []
    json_by_mod[8364] = []

    for k, v in mini_database.items():
        geneid1 = k
        if isinstance(v, dict):
            for j, q in v.items():
                if isinstance(q, dict):
                    geneid2 = j
                    confidence = q['confidence']

                    # TODO: Investigate futher.
                    if geneid2 not in mini_database:
                        continue

                    # Translate the geneids to actual geneids from MODs.
                    # Sometimes we might be missing the species_specific_geneid and need to substitute a symbol.
                    if 'species_specific_geneid' in mini_database[geneid1]:
                        geneid1_id = mini_database[geneid1]['species_specific_geneid']
                    else:
                        geneid1_id = mini_database[geneid1]['symbol']
                    if 'species_specific_geneid' in mini_database[geneid2]:
                        geneid2_id = mini_database[geneid2]['species_specific_geneid']
                    else:
                        geneid2_id = mini_database[geneid2]['symbol']
                    gene1_species = mini_database[geneid1]['species']
                    gene2_species = mini_database[geneid2]['species']
                    gene1_provider = mini_database[geneid1]['species_specific_geneid_type']
                    gene2_provider = mini_database[geneid2]['species_specific_geneid_type']

                    # Alignment attributes
                    try:
                        # Only round to two places if the values is not empty.
                        # Drop the decimal point and anything afterwards.
                        if q["length"] is not None:
                            length = round(q['length'], 2)
                            # Drop the decimal point and anything afterwards.
                            length = int(length)
                        else:
                            length = None                        
                        
                        if q["identity"] is not None:
                            identity = round(q['identity'], 2)
                            # Times by 100 to make a percentage.
                            identity = identity * 100
                            identity = int(identity)
                        else:
                            identity = None

                        if q["similarity"] is not None:
                            similarity = round(q['similarity'], 2)
                            # Times by 100 to make a percentage.
                            similarity = similarity * 100
                            similarity = int(similarity)
                        else:
                            similarity = None

                    except KeyError:
                        # print the exception.
                        print("geneid1: %s" % (geneid1))
                        print("geneid2: %s" % (geneid2))
                        # print the geneid1_id and geneid2_id.
                        print("geneid1_id: %s" % (geneid1_id))
                        print("geneid2_id: %s" % (geneid2_id))
                        # Print the KeyError Exception:
                        print("KeyError: %s" % (KeyError))
                        pprint.pprint(q)
                        quit(-1)

                    # Rank
                    rank = q['rank']

                    if gene1_provider is None or gene2_provider is None:
                        logger.critical('Fatal error in gene1DataProvider/gene2DataProvider.')
                        logger.critical('geneid1 %s' % (geneid1))
                        logger.critical('geneid2 %s' % (geneid2))
                        logger.critical('geneid1_id %s' % (geneid1_id))
                        logger.critical('geneid2_id %s' % (geneid2_id))
                        logger.critical('species1 %s' % (gene1_species))
                        logger.critical('species2 %s' % (gene2_species))
                        logger.critical('gene1DataProvider %s' % (gene1_provider))
                        logger.critical('gene2DataProvider %s' % (gene2_provider))
                        quit(-1)

                    if gene1_species != gene2_species:
                        logger.critical('Fatal error in gene1_species/gene2_species.')
                        logger.critical('Species do not match.')
                        quit(-1)

                    # The final JSON output is in dict_to_add below.

                    dict_to_add = {}

                    dict_to_add['gene1'] = geneid1_id
                    dict_to_add['species'] = gene1_species
                    dict_to_add['gene2'] = geneid2_id
                    dict_to_add['predictionMethodsMatched'] = list(q['matched_prediction_methods'])
                    dict_to_add['predictionMethodsNotMatched'] = list(q['not_matched_prediction_methods'])
                    dict_to_add['predictionMethodsNotCalled'] = list(q['not_called_prediction_methods'])
                    dict_to_add['confidence'] = confidence
                    dict_to_add['length'] = length
                    dict_to_add['identity'] = identity
                    dict_to_add['similarity'] = similarity
                    dict_to_add['rank'] = rank

                    json_by_mod[gene1_species].append(dict_to_add)

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
    test_json_to_export['metaData']['release'] = '9.0'
    test_json_to_export['data'] = []

    print("Exporting JSON by MOD.")
    for mod_species in json_by_mod:
        to_export_as_json = {}
        to_export_as_json['metaData'] = {}
        to_export_as_json['metaData']['dataProvider'] = dataProviderdict
        to_export_as_json['metaData']['dateProduced'] = the_time
        to_export_as_json['metaData']['release'] = '9.0'
        to_export_as_json['data'] = json_by_mod[mod_species]

        for entry in json_by_mod[mod_species]:
            trimmed_entry = entry['gene1'][5:]
            if trimmed_entry in test_set_of_genes:
                test_json_to_export['data'].append(entry)

        mod = taxon_to_mod[mod_species]
        filename = 'paralogy_%s_v9_test_with_xenbase.json' % (mod)
        print("Saving %s" % (filename))
        with open(filename, 'w') as outfile:
            json.dump(to_export_as_json, outfile, sort_keys=True, indent=2, separators=(',', ': '))
            outfile.close()
        os.system("gzip paralogy_" + str(mod) + "_v9_test_with_xenbase.json")

    print("Saving test JSON dataset.")
    test_filename = 'paralogy_test_data_v9_test_with_xenbase.json'
    print("Saving %s" % (test_filename))
    with open(test_filename, 'w') as outfile:
        json.dump(test_json_to_export, outfile, sort_keys=True, indent=2, separators=(',', ': '))
        outfile.close()

    os.system("gzip paralogy_test_data_v9_test_with_xenbase.json")
    # Close the database connection.
    conn_diopt.close()

    tf = datetime.datetime.now()
    print(tf)

    te = tf - ts

    print("Done!")
    print("Elapsed time: %s" % (te))


if __name__ == "__main__":
    main()
