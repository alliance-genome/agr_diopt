import pickle
import argparse
from tqdm import tqdm
from nested_dict import nested_dict
from shared_func import obtain_connection, obtain_data_from_database

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
pickle_help = '''
Use the local database dump pickle file and do not query the Postgres database.
This is useful for creating changes in the JSON without needing to re-query everything (slow).'
'''

args = parser.parse_args()

for_distinct_algorithms = ('SELECT distinct(prediction_method) FROM ortholog_pair')
conn_diopt = obtain_connection(args.host, args.database, args.username, args.password)

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

# Obtain the total possible algorithms.
returned_distinct_algorithms = obtain_data_from_database(conn_diopt, for_distinct_algorithms)

total_possible_algorithms = set()
for i in returned_distinct_algorithms:
    algorithm_name = convert_algorithm_name(i[0])
    total_possible_algorithms.add(algorithm_name)

# Obtain the possible algorithm configurations
for_species_possibilities = ('SELECT distinct(sp1.speciesid), sp2.speciesid, op.prediction_method '
                                'FROM species sp1, species sp2, ortholog_pair op '
                                'WHERE op.speciesid1 = sp1.speciesid '
                                'AND op.speciesid2 = sp2.speciesid ')
returned_possible_combinations = obtain_data_from_database(conn_diopt, for_species_possibilities)

# Create a nested dictionary with all the possible species1 x species2 algorithms.
# First level is species1, second level is species2, third level is a set with all the algorithms called.
algorithm_dictionary = nested_dict(2, set)

for i in returned_possible_combinations:
    algorithm_name = convert_algorithm_name(i[2])
    algorithm_dictionary[i[0]][i[1]].add(algorithm_name)

mini_database = pickle.load(open("mini_database.p", "rb"))

json_by_mod = {}
json_by_mod[9606] = []
json_by_mod[6239] = []
json_by_mod[10090] = []
json_by_mod[10116] = []
json_by_mod[4932] = []
json_by_mod[7955] = []
json_by_mod[7227] = []

for k, v in tqdm(mini_database.items()):
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

sonic_count_matched_together = {
    'PANTHER': 0,
    'InParanoid': 0,
    'OrthoInspector': 0,
    'Hieranoid': 0,
    'Ensembl Compara': 0,
    'PhylomeDB': 0,
    'HGNC': 0,
    'ZFIN': 0,
    'OrthoFinder': 0,
    'OMA': 0,
    'sonicParanoid': 0,
}

sonic_count_not_matched_together = {
    'PANTHER': 0,
    'InParanoid': 0,
    'OrthoInspector': 0,
    'Hieranoid': 0,
    'Ensembl Compara': 0,
    'PhylomeDB': 0,
    'HGNC': 0,
    'ZFIN': 0,
    'OrthoFinder': 0,
    'OMA': 0,
    'sonicParanoid': 0,
}

sonic_count_not_called_together = {
    'PANTHER': 0,
    'InParanoid': 0,
    'OrthoInspector': 0,
    'Hieranoid': 0,
    'Ensembl Compara': 0,
    'PhylomeDB': 0,
    'HGNC': 0,
    'ZFIN': 0,
    'OrthoFinder': 0,
    'OMA': 0,
    'sonicParanoid': 0,
}

for final_item in tqdm(json_by_mod):
    for inside_item in json_by_mod[final_item]:
        matched = inside_item['predictionMethodsMatched']
        if 'sonicParanoid' in matched:
            for item in matched:
                sonic_count_matched_together[item] += 1

        not_matched = inside_item['predictionMethodsNotMatched']
        if 'sonicParanoid' in not_matched:
            for item in not_matched:
                sonic_count_not_matched_together[item] += 1

        not_called = inside_item['predictionMethodsNotCalled']
        if 'sonicParanoid' in not_called:
            for item in not_called:
                sonic_count_not_called_together[item] += 1

print('Matched together:')
print(sonic_count_matched_together)
print('Not matched together:')
print(sonic_count_not_matched_together)
print('Not called together:')
print(sonic_count_not_called_together)

sonic_count = sonic_count_matched_together['sonicParanoid']
print('Matched together percentage:')
for matched_together in sonic_count_matched_together:
    print(matched_together, ':', round((sonic_count_matched_together[matched_together]/sonic_count*100)))

sonic_count = sonic_count_not_matched_together['sonicParanoid']
print('Not matched together percentage:')
for not_matched_together in sonic_count_not_matched_together:
    print(not_matched_together, ':', round((sonic_count_not_matched_together[not_matched_together]/sonic_count*100)))

# sonic_count = sonic_count_not_called_together['sonicParanoid']
# print('Not called together percentage:')
# for not_called_together in sonic_count_not_called_together:
#     print(not_called_together, ':', round((sonic_count_not_called_together[not_called_together]/sonic_count*100)))