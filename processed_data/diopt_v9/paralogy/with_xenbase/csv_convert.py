import json
import csv
import gzip

# Load and decompress the gzipped JSON data
with gzip.open("/home/ctabone/programming/agr_diopt/processed_data/diopt_v9/paralogy/with_xenbase/paralogy_ZFIN_v9_test_with_xenbase.json.gz", 'r') as file:
    json_content = json.loads(file.read().decode('utf-8'))

# Open the output CSV file
with open("ZFIN.csv", 'w', newline='') as file:
    writer = csv.writer(file)

    # Write the header
    header = ['gene1', 'gene2', 'isBestScore', 'isBestRevScore', 'predictionMethodsMatched']
    writer.writerow(header)

    # Iterate over the data
    for item in json_content['data']:
        # Extract the fields
        gene1 = item['gene1']
        gene2 = item['gene2']
        is_best_score = item['isBestScore']
        is_best_rev_score = item['isBestRevScore']
        prediction_methods_matched = ';'.join(item['predictionMethodsMatched'])

        # Write the row
        row = [gene1, gene2, is_best_score, is_best_rev_score, prediction_methods_matched]
        writer.writerow(row)
