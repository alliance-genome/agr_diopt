# Python script for checking Xenbase orthology data.

import json
import pprint
from signal import struct_siginfo
json_filename = 'processed_data/diopt_v9/orthology/with_xenbase/orthology_Xenbase_v9.json'

def process_json_file(json_filename):
    # Open json file.
    with open(json_filename) as json_file:
        data = json.load(json_file)

    gene1Species = set()
    gene2Species = set()
    moderateFilter = set()
    predictionMethodsMatched = set()
    predictionMethodsNotCalled = set()
    predictionMethodsNotMatched = set()
    strictFilter = set()

    # Print out the contents of the json file.
    for item in data['data']:
        print(item)
        quit()
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

    print('==============================================================')

def __main__():
    process_json_file(json_filename)

if __name__ == '__main__':
    __main__()