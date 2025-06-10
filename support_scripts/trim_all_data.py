import logging
import coloredlogs
import argparse
import os
import csv
import tqdm

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', help='Enable verbose mode.', action='store_true')
args = parser.parse_args()

if args.verbose or ("DEBUG" in os.environ and os.environ['DEBUG'] == "True"):
    debug_level = logging.DEBUG
else:
    debug_level = logging.INFO

coloredlogs.install(level=debug_level,
                    fmt='%(asctime)s %(levelname)s: %(name)s:%(lineno)d: %(message)s',
                    field_styles={
                        'asctime': {'color': 'green'},
                        'hostname': {'color': 'magenta'},
                        'levelname': {'color': 'white', 'bold': True},
                        'name': {'color': 'blue'},
                        'programname': {'color': 'cyan'}
                    })

log = logging.getLogger(__name__)


def main():
    diopt_directory = '/data/ortholog/diopt/diopt_v8/fixed_csv/'
    ortholog_pair = diopt_directory + 'fixed_gene_information.csv'
    gene_info_location = diopt_directory + 'All_Data.gene_info'
    output_all_data = diopt_directory + 'All_Data.gene_info_filtered'

    log.info('Extracting information from DIOPT gene_information source file.')
    with open(ortholog_pair) as source_file:
        temp_reader = csv.DictReader(source_file)
        ortholog_pair_list = list(temp_reader)

    # The gene information file contains many entries which are *not* in the ortholog pairs file.
    # In other words, these genes are not used for DIOPT in any way.
    # We use this set to filter out any irrelevant entries when iterating through gene information later.
    log.info('Building a filter set of gene ids from ortholog_pairs.')
    gene_id_filter_set = set()
    for entry in ortholog_pair_list:
        gene_id_filter_set.add(entry['geneid'])

    log.info('Creating a filtered version of All_Data based on DIOPT gene ids.')
    with open(gene_info_location) as source_file:
        gene_info_reader = csv.DictReader(source_file, delimiter='\t')
        with open(output_all_data, 'w') as output_file:
            writer = csv.DictWriter(output_file, delimiter='\t', fieldnames=gene_info_reader.fieldnames)
            writer.writeheader()
            for row in tqdm(gene_info_reader):
                if row['GeneID'] in gene_id_filter_set:
                    writer.writerow(row)


if __name__ == "__main__":
    main()
