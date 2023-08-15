# Python script for checking Xenbase orthology data.
# Tropicalis = 8364
# Laevis = 8355

import json
import pprint
import csv
from re import I
from signal import struct_siginfo
json_filename = 'source_data/diopt_v9/orthology/from_xenbase/10_18_2022/ORTHOLOGY_XB.json'
json_filename2 = 'source_data/diopt_v9/orthology/from_xenbase/10_18_2022/ORTHOLOGY_XBXT.json'

def process_json_file(json_filename):
    # Open json file.
    with open(json_filename) as json_file:
        data = json.load(json_file)

    missing_identifier_resolution_gene1 = 0
    missing_identifier_resolution_gene2 = 0

    gene1Species = set()
    gene2Species = set()
    moderateFilter = set()
    predictionMethodsMatched = set()
    predictionMethodsNotCalled = set()
    predictionMethodsNotMatched = set()
    strictFilter = set()

    # Print out the contents of the json file.
    for item in data['data']:
        gene1Species.add(item['gene1Species'])
        gene2Species.add(item['gene2Species'])
        moderateFilter.add(item['moderateFilter'])
        for method in item['predictionMethodsMatched']:
            predictionMethodsMatched.add(method)
        for method in item['predictionMethodsNotCalled']:
            predictionMethodsNotCalled.add(method)
        for method in item['predictionMethodsNotMatched']:
            predictionMethodsNotMatched.add(method)
        strictFilter.add(item['strictFilter'])

        # If gene1 doesn't contain numbers:
        if not any(char.isdigit() for char in item['gene1']):
            missing_identifier_resolution_gene1 += 1
        
        # # If gene1 doesn't contain letters or numbers:
        # if not any(char.isalpha() or char.isdigit() for char in item['gene1']):

        # If gene2 doesn't contain numbers:
        if not any(char.isdigit() for char in item['gene2']):
            missing_identifier_resolution_gene2 += 1

    # Pretty print set.
    print(json_filename)

    print('gene1Species:')
    pprint.pprint(gene1Species)

    print('gene2Species:')
    pprint.pprint(gene2Species)

    print('moderateFilter:')
    pprint.pprint(moderateFilter)

    print('predictionMethodsMatched:')
    pprint.pprint(predictionMethodsMatched)

    print('predictionMethodsNotCalled:')
    pprint.pprint(predictionMethodsNotCalled)

    print('predictionMethodsNotMatched:')
    pprint.pprint(predictionMethodsNotMatched)

    print('strictFilter:')
    pprint.pprint(strictFilter)

    print('missing_identifier_resolution_gene1:')
    print(missing_identifier_resolution_gene1)

    print('missing_identifier_resolution_gene2:')
    print(missing_identifier_resolution_gene2)

    print('==============================================================')

    return(data)

def investigate_gene(data1):
    # Gene of interest
    gene_of_interest = 'DRSC:HGNC:30344'
    
    # Print out the JSON item if the gene of interest is gene1 or gene2.
    for item in data1['data']:
        if item['gene1'] == gene_of_interest or item['gene2'] == gene_of_interest:
            pprint.pprint(item)

def __main__():
    data1 = process_json_file(json_filename)
    data2 = process_json_file(json_filename2)
    # investigate_gene(data1)

if __name__ == '__main__':
    __main__()