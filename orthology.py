#!/usr/bin/env python
# Written for Python3
import psycopg2
import strict_rfc3339
import os
import pickle
import datetime
import json
import csv
from nested_dict import nested_dict
import configparser
import argparse


def obtain_connection(connection_type):
    # Read in credentials for querying our database. Either "default" (reporting) or "diopt".
    config = configparser.ConfigParser()
    # config.read('location')
    dbhost = config[connection_type]['DatabaseHost']
    database = config[connection_type]['Database']
    username = config[connection_type]['Username']
    password = config[connection_type]['Password']

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


def process_fb_identifier(identifier, tracking_dict, conn_flybase):

    update_fb_identifier = ('SELECT DISTINCT f.uniquename as query '
                            'FROM feature f, feature_dbxref fdbx, dbxref dbx, db '
                            'WHERE dbx.accession = %s '
                            'AND f.feature_id = fdbx.feature_id '
                            'AND fdbx.dbxref_id = dbx.dbxref_id '
                            'AND db.name = \'FlyBase\' '
                            'AND dbx.db_id = db.db_id '
                            'AND f.organism_id = \'1\' '
                            'AND f.type_id = \'219\' '
                            'AND f.is_obsolete = \'f\' ')

    query_variable = (identifier,)
    returned_identifier = obtain_data_from_database_query_variable(conn_flybase, update_fb_identifier, query_variable)

    identifier_to_return = None
    try:
        identifier_to_return = returned_identifier[0][0]
    except IndexError:
        identifier_to_return = identifier

    tracking_dict[identifier] = identifier_to_return

    return (identifier_to_return, tracking_dict)


def fix_identifier(identifier, speciesid):
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
    else:
        print("Fatal error: cannot correct species specific gene id %s" % (identifier))
        quit()


def fix_missing_entry(speciesid):
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
    else:
        print("Fatal error: cannot correct species %s" % (speciesid))
        quit()


def convert_algorithm_name(name_input):
    name_conversion_dictionary = {
        'Panther': 'PANTHER',
        'Phylome': 'PhylomeDB',
        'Compara': 'Ensembl Compara',
        'Inparanoid': 'InParanoid',
        'RoundUp': 'Roundup'
    }

    # Try to get the new value by key, if the key is not found, send back the input value.
    return name_conversion_dictionary.get(name_input, name_input)


def main():    # noqa C901

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

    pickle_help = """
        Use the local database dump pickle file and do not query the Postgres database.
        This is useful for creating changes in the JSON without needing to re-query everything (slow).'
        """
    parser = argparse.ArgumentParser(description='Generate DIOPT orthology JSON for use at the Alliance.')
    parser.add_argument('-p', '--pickle', help=pickle_help, dest='pickle', action='store_true')
    parser.set_defaults(pickle=False)

    args = parser.parse_args()
    picklefile = args.pickle

    print('')
    if picklefile is True:
        print('Note: Pickle file use is enabled. This script will attempt to use the existing pickle file and not query Postgres.')
    elif picklefile is False:
        print('Pickle use not requested. \nScript will query Postgres and create new pickle file as well as generate JSON. \nPlease use --help for more info.')
    print('')

    # 7955 = Danio rerio, 6239 = Caenorhabditis elegans, 10090 = Mus musculus, 10116 = Rattus norvegicus
    # 4932 = Saccharomyces cerevisiae S288c, 7227 = Drosophila melanogaster, 9606 = Homo sapiens

    ts = datetime.datetime.now()
    print(ts)

    # Attempt to get database connections
    conn_diopt = obtain_connection('diopt')
    conn_flybase = obtain_connection('default')

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
                    'OR op.speciesid2 = \'9606\') ')

    for_opb_table = ('SELECT opb.geneid1, opb.geneid2, opb.speciesid1, opb.speciesid2, opb.score, opb.best_score, opb.best_score_rev, opb.confidence '
                     'FROM ortholog_pair_best opb '
                     'WHERE opb.speciesid1 = %s '
                     'AND (opb.speciesid2 = \'7955\' '
                     'OR opb.speciesid2 = \'6239\' '
                     'OR opb.speciesid2 = \'10090\' '
                     'OR opb.speciesid2 = \'10116\' '
                     'OR opb.speciesid2 = \'4932\' '
                     'OR opb.speciesid2 = \'7227\' '
                     'OR opb.speciesid2 = \'9606\') ')

    for_species_possibilities = ('SELECT distinct(sp1.speciesid), sp2.speciesid, op.prediction_method '
                                 'FROM species sp1, species sp2, ortholog_pair op '
                                 'WHERE op.speciesid1 = sp1.speciesid '
                                 'AND op.speciesid2 = sp2.speciesid ')

    for_distinct_algorithms = ('SELECT distinct(prediction_method) FROM ortholog_pair')

    # 7955 = Danio rerio, 6239 = Caenorhabditis elegans, 10090 = Mus musculus, 10116 = Rattus norvegicus
    # 4932 = Saccharomyces cerevisiae S288c, 7227 = Drosophila melanogaster, 9606 = Homo sapiens

    # Short species list for testing purposes.
    # species_list = [7955]
    species_list = [7227, 7955, 6239, 10090, 10116, 4932, 9606]

    taxon_to_mod = {
        10116: 'RGD',
        10090: 'MGI',
        7955: 'ZFIN',
        4932: 'SGD',
        6239: 'WormBase',
        7227: 'FlyBase',
        9606: 'Human'
    }

    # taxon_to_species_name = {
    # 10116: 'R. norvegicus',
    # 10090: 'M. musculus',
    # 7955: 'D. rerio',
    # 4932: 'S. cerevisiae',
    # 6239: 'C. elegans',
    # 7227: 'D. melanogaster',
    # 9606: 'H. sapiens'
    # }

    # Obtain the total possible algorithms.
    returned_distinct_algorithms = obtain_data_from_database(conn_diopt, for_distinct_algorithms)

    total_possible_algorithms = set()
    for i in returned_distinct_algorithms:
        algorithm_name = convert_algorithm_name(i[0])
        total_possible_algorithms.add(algorithm_name)

    # Obtain the possible algorithm configurations
    returned_possible_combinations = obtain_data_from_database(conn_diopt, for_species_possibilities)

    # Create a nested dictionary with all the possible species1 x species2 algorithms.
    # First level is species1, second level is species2, third level is a set with all the algorithms called.
    algorithm_dictionary = nested_dict(2, set)

    for i in returned_possible_combinations:
        algorithm_name = convert_algorithm_name(i[2])
        algorithm_dictionary[i[0]][i[1]].add(algorithm_name)

    mini_database = {}
    tracking_dict = {}

    if picklefile is False:
        for i in species_list:

            print("Obtaining gene_information for species %s" % (i))
            query_variable = (i,)
            returned_geneid = obtain_data_from_database_query_variable(conn_diopt, for_geneid, query_variable)

            # geneid, speciesid, species_specific_geneid, species_specific_geneid_type, symbol
            for j in returned_geneid:
                species = j[1]
                geneid = j[0]
                raw_species_specific_geneid = j[2]

                if raw_species_specific_geneid is None:
                    continue

                checked_for_fb = None

                # Update FB identifiers
                if raw_species_specific_geneid.startswith('FBgn'):
                    if raw_species_specific_geneid in tracking_dict:
                        checked_for_fb = tracking_dict[raw_species_specific_geneid]
                    else:
                        checked_for_fb, tracking_dict = process_fb_identifier(raw_species_specific_geneid, tracking_dict, conn_flybase)
                else:
                    checked_for_fb = raw_species_specific_geneid

                fixed_species_specific_geneid = fix_identifier(checked_for_fb, species)

                mini_database[geneid] = {}

                if j[3] == '-' or j[3] is None:  # Weird hyphen character or None found in some fields.
                    mini_database[geneid]['species_specific_geneid_type'] = fix_missing_entry(species)
                elif j[3] == 'FLYBASE':
                    mini_database[geneid]['species_specific_geneid_type'] = 'FB'
                elif j[3] == 'WormBase':
                    mini_database[geneid]['species_specific_geneid_type'] = 'WB'
                else:
                    mini_database[geneid]['species_specific_geneid_type'] = j[3]

                mini_database[geneid]['species'] = species

                mini_database[geneid]['symbol'] = j[4]

                mini_database[geneid]['species_specific_geneid'] = fixed_species_specific_geneid

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

        print("Dumping pickle file.")
        pickle.dump(mini_database, open("mini_database.p", "wb"))

    elif picklefile is True:
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

# Temporary code to fix 'Yes_Adjusted' values for version 7.
# From Claire's email:
# We just realize that we did not do this adjustment for human2fish with DIOPT vs7 and will get it updated soon.
# Chris, you might find the 2nd best score (>=2) for any human to zebrafish 1tomany relationships and
# adjust the "best_score" annotation for AGR mapping.
# We will release DIOPT vs8 this summer and will keep in mind to do this adjustment with any new release in the future.

    print('Fixing \'Yes_Adjusted\' values for DIOPT v7 release.')

    human2fish_lookup_set = set()

    adjusted_counter = 0

    print('Loading human2fish.txt filter file.')
    with open('human2fish.txt') as tsvfile:
        reader = csv.reader(tsvfile, delimiter='\t')
        next(reader, None)
        for row in reader:
            human2fish_lookup_set.add((int(row[1]), int(row[3])))

    for k, v in mini_database.items():
        geneid1 = k
        gene1_species = mini_database[geneid1]['species']
        if gene1_species == 9606:
            best_score = (0, None)
            second_best_score = (0, None)
            if isinstance(v, dict):
                for j, q in v.items():
                    if isinstance(q, dict):
                        geneid2 = j
                        if geneid2 not in mini_database:
                            continue
                        gene2_species = mini_database[geneid2]['species']
                        if gene2_species == 7955:
                            score = len(q['prediction_method'])

                            tracking_tuple = (score, geneid2)

                            if score >= best_score[0] and score >= 2:
                                second_best_score = best_score
                                best_score = tracking_tuple
                            elif score >= second_best_score[0] and score >= 2:
                                second_best_score = tracking_tuple

                if second_best_score[1] is not None:
                    tuple_lookup = (geneid1, second_best_score[1])
                    if tuple_lookup in human2fish_lookup_set:
                        if mini_database[geneid1][tuple_lookup[1]]['best_score'] != 'Yes':
                            mini_database[geneid1][tuple_lookup[1]]['best_score'] = 'Yes_Adjusted'
                            adjusted_counter += 1

    print('Adjusted the score for {} entries.'.format(adjusted_counter))

# End of temporary code to fix 'Yes_Adjusted' data.

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

                    # gene1_symbol = None
                    # if 'symbol' in mini_database[geneid1]:
                    #     gene1_symbol = mini_database[geneid1]['symbol']

                    # gene2_symbol = None
                    # if 'symbol' in mini_database[geneid2]:
                    #     gene2_symbol = mini_database[geneid2]['symbol']

                    if gene1_provider == gene2_provider:  # skipping paralogs for now.
                        continue

                    # Possible algorithm matches and associated calculations.
                    possible_prediction_methods = algorithm_dictionary[gene1_species][gene2_species]
                    matched_prediction_methods = q['prediction_method']
                    not_called_prediction_methods = total_possible_algorithms - possible_prediction_methods  # subtracting sets
                    not_matched_prediction_methods = possible_prediction_methods - matched_prediction_methods  # subtracting sets

                    # Determine the stringency filter to add.
                    strict_filter = False
                    moderate_filter = False

                    if 'ZFIN' in matched_prediction_methods or 'HGNC' in matched_prediction_methods:
                        strict_filter = True
                        moderate_filter = True

                    best_score = q['best_score']
                    best_score_rev = q['best_score_rev']

                    if (len(matched_prediction_methods) > 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') or best_score_rev == 'Yes')) \
                            or (len(matched_prediction_methods) == 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') and best_score_rev == 'Yes')):
                        strict_filter = True

                    elif len(matched_prediction_methods) > 2 \
                            or (len(matched_prediction_methods) == 2 and ((best_score == 'Yes' or best_score == 'Yes_Adjusted') and best_score_rev == 'Yes')):
                        moderate_filter = True

                    if gene1_provider is None or gene2_provider is None:
                        print('Fatal error in gene1DataProvider/gene2DataProvider.')
                        print('geneid1 %s' % (geneid1))
                        print('geneid2 %s' % (geneid2))
                        print('geneid1_id %s' % (geneid1_id))
                        print('geneid2_id %s' % (geneid2_id))
                        print('species1 %s' % (gene1_species))
                        print('species2 %s' % (gene2_species))
                        print('gene1DataProvider %s' % (gene1_provider))
                        print('gene2DataProvider %s' % (gene2_provider))
                        quit()

                    # The final JSON output is in dict_to_add below.

                    dict_to_add = {}

                    dict_to_add['isBestScore'] = q['best_score']
                    dict_to_add['isBestRevScore'] = q['best_score_rev']
                    dict_to_add['gene1'] = geneid1_id
                    dict_to_add['gene1Species'] = gene1_species
                    dict_to_add['gene2'] = geneid2_id
                    dict_to_add['gene2Species'] = gene2_species
                    dict_to_add['predictionMethodsMatched'] = list(matched_prediction_methods)
                    dict_to_add['predictionMethodsNotMatched'] = list(not_matched_prediction_methods)
                    dict_to_add['predictionMethodsNotCalled'] = list(not_called_prediction_methods)
                    dict_to_add['confidence'] = confidence
                    dict_to_add['strictFilter'] = strict_filter
                    dict_to_add['moderateFilter'] = moderate_filter

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
    test_json_to_export['metaData']['release'] = '7.0.5'
    test_json_to_export['data'] = []

    print("Exporting JSON by MOD.")
    for mod_species in json_by_mod:
        to_export_as_json = {}
        to_export_as_json['metaData'] = {}
        to_export_as_json['metaData']['dataProvider'] = dataProviderdict
        to_export_as_json['metaData']['dateProduced'] = the_time
        to_export_as_json['metaData']['release'] = '7.0.5'
        to_export_as_json['data'] = json_by_mod[mod_species]

        for entry in json_by_mod[mod_species]:
            trimmed_entry = entry['gene1'][5:]
            if trimmed_entry in test_set_of_genes:
                test_json_to_export['data'].append(entry)

        mod = taxon_to_mod[mod_species]
        filename = 'orthology_%s_1.0.0.7_5.json' % (mod)
        print("Saving %s" % (filename))
        with open(filename, 'w') as outfile:
            json.dump(to_export_as_json, outfile, sort_keys=True, indent=2, separators=(',', ': '))
            outfile.close()
        os.system("tar -czvf orthology_" + str(mod) + "_1.0.0.7_5.json.tar.gz orthology_" + str(mod) + "_1.0.0.7_5.json")

    print("Saving test JSON dataset.")
    test_filename = 'orthology_test_data_1.0.0.7_5.json'
    print("Saving %s" % (test_filename))
    with open(test_filename, 'w') as outfile:
        json.dump(test_json_to_export, outfile, sort_keys=True, indent=2, separators=(',', ': '))
        outfile.close()

    os.system("tar -czvf orthology_test_data_1.0.0.7_5.json.tar.gz orthology_test_data_1.0.0.7_5.json")
    # Close the database connection.
    conn_diopt.close()
    conn_flybase.close()

    tf = datetime.datetime.now()
    print(tf)

    te = tf - ts

    print("Done!")
    print("Elapsed time: %s" % (te))


if __name__ == "__main__":
    main()
