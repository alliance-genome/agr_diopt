# Combine DIOPT 8 + DIOPT 9 data for Alliance orthology.
# A temporary fix until the DIOPT 9 pipeline is fixed.

import csv
from tqdm import tqdm

pair_best_csv_9 = '/home/ctabone/programming/agr_diopt/source_data/diopt_v9/orthology/fixed/fixed_ortholog_pair_best.csv'
pair_csv_9 = '/home/ctabone/programming/agr_diopt/source_data/diopt_v9/orthology/fixed/fixed_ortholog_pair.csv'

pair_best_tsv_8 = '/home/ctabone/programming/agr_diopt/source_data/diopt_v8/Ortholog_Pair_Best_v8-2/Ortholog_Pair_Best_v2.tsv'
pair_tsv_8 = '/home/ctabone/programming/agr_diopt/source_data/diopt_v8/Ortholog_Pair_vs8/Ortholog_Pair.tsv'


# Load the pair_best_csv_9 into a set of tuples using the first four columns.
pair_best_set_9 = set()
with open(pair_best_csv_9, 'r') as pair_best_csv_9_file:
    pair_best_csv_9_reader = csv.reader(pair_best_csv_9_file)
    for row in pair_best_csv_9_reader:
        pair_best_set_9.add((row[0], row[1], row[2], row[3]))

# Load the pair_csv_9 into a set of tuples using columns 2 through 5.
# The first column is the orthology id, which is not needed.
pair_set_9 = set()
with open(pair_csv_9, 'r') as pair_csv_9_file:
    pair_csv_9_reader = csv.reader(pair_csv_9_file)
    for row in pair_csv_9_reader:
        pair_set_9.add((row[1], row[2], row[3], row[4]))       

# List of algorithms to use.
algorithm_list = ['Panther', 'Phylome', 'Compara', 'Inparanoid', 'HGNC', 'OMA', 'OrthoFinder', 'OrthoInspector', 'ZFIN', 'Hieranoid']

# Open the output file for pair.
pair_output_file = open('pair_combined.csv', 'w')

# Open the output file for pair_best.
pair_best_output_file = open('pair_best_combined.csv', 'w')

# Track the number of ortholog pairs are added to the output file.
pair_count = 0

# The highest ortology id in the DIOPT 9 pair file is 7735710 so we have to start from there + 1.
next_orthology_id = 7735711

# Open the pair_tsv_8 file.
with open(pair_tsv_8, 'r') as pair_tsv_8_file:
    # Skip the header.
    next(pair_tsv_8_file)
    # Read the file.
    pair_tsv_8_reader = csv.reader(pair_tsv_8_file, delimiter='\t')
    for row in tqdm(pair_tsv_8_reader):
        # Remove the quotes around every column.
        row = [column.replace('"', '') for column in row]
        # If column 2 or 4 contains 8364 and column 6 is in the algorithm list:
        if (row[1] == '8364' or row[3] == '8364') and row[5] in algorithm_list:
            # If the row is not in pair_set_9:
            if (row[1], row[2], row[3], row[4]) not in pair_set_9:
                # Replace row[0] with the next orthology id.
                row[0] = str(next_orthology_id)
                # Increment the next orthology id.
                next_orthology_id += 1
                # Write the row to the output file.
                pair_output_file.write(','.join(row) + '')
                # Write a newline to the output file.
                pair_output_file.write('\n')
                # Increment the pair_count.
                pair_count += 1

print('pair_count:', pair_count)

# Track the number of ortholog pairs are added to the output file.
pair_best_count = 0

# Open the pair_best_tsv_8 file.
with open(pair_best_tsv_8, 'r') as pair_best_tsv_8_file:
    # Skip the header.
    next(pair_best_tsv_8_file)
    # Read the file.
    pair_best_tsv_8_reader = csv.reader(pair_best_tsv_8_file, delimiter='\t')
    for row in tqdm(pair_best_tsv_8_reader):
        # Remove the quotes around every column.
        row = [column.replace('"', '') for column in row]
        # If column 2 or 4 contains 8364:
        if row[1] == '8364' or row[3] == '8364':
            # If the row is not in pair_best_set_9:
            if (row[1], row[2], row[3], row[4]) not in pair_best_set_9:
                # Remove row[0] from the row.
                row.pop(0)
                # Write the row to the output file.
                pair_best_output_file.write(','.join(row) + '')
                # Write a newline to the output file.
                pair_best_output_file.write('\n')
                # Increment the pair_best_count.
                pair_best_count += 1

print('pair_best_count:', pair_best_count)