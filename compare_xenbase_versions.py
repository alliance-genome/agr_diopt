# Compare Xenopus genes between Alliance release 5.3.0 and 5.4.0.
# Version 5.3.0 database
import psycopg2

db_5_3_0 = 'agr_diopt_v9_ortholog_2'
db_5_4_0 = 'agr_diopt_v9_ortholog_nov'

username = 'diopt'
host = 'localhost'

# Prompt for password.
password = input('Password: ')

# Connect to the database.
conn_5_3_0 = psycopg2.connect(database=db_5_3_0, user=username, host=host, password=password)
conn_5_4_0 = psycopg2.connect(database=db_5_4_0, user=username, host=host, password=password)

# Create a cursor.
cur_5_3_0 = conn_5_3_0.cursor()
cur_5_4_0 = conn_5_4_0.cursor()

# Query the ortholog_pair table from both 5_3_0 and 5_4_0 and return geneid1 if speciesid1 is '8364' or '8355' and return geneid2 if speciesid2 is '8364' or '8355'.
cur_5_3_0.execute('SELECT DISTINCT geneid1 FROM ortholog_pair WHERE speciesid1 = \'8364\' OR speciesid1 = \'8355\'')
cur_5_3_0.execute('SELECT DISTINCT geneid2 FROM ortholog_pair WHERE speciesid2 = \'8364\' OR speciesid2 = \'8355\'')
cur_5_4_0.execute('SELECT DISTINCT geneid1 FROM ortholog_pair WHERE speciesid1 = \'8364\' OR speciesid1 = \'8355\'')
cur_5_4_0.execute('SELECT DISTINCT geneid2 FROM ortholog_pair WHERE speciesid2 = \'8364\' OR speciesid2 = \'8355\'')

# Fetch the results.
rows_5_3_0 = cur_5_3_0.fetchall()
rows_5_4_0 = cur_5_4_0.fetchall()

# Look up the symbol and species_specific_geneid for each geneid in the gene_information table. Save the results in a list.
gene_info_5_3_0 = []
for row in rows_5_3_0:
    cur_5_3_0.execute('SELECT symbol, species_specific_geneid FROM gene_information WHERE geneid = %s', row)
    gene_info_5_3_0.append(cur_5_3_0.fetchone())

gene_info_5_4_0 = []
for row in rows_5_4_0:
    cur_5_4_0.execute('SELECT symbol, species_specific_geneid FROM gene_information WHERE geneid = %s', row)
    gene_info_5_4_0.append(cur_5_4_0.fetchone())

# Remove duplicates from each list.
gene_info_5_3_0 = list(set(gene_info_5_3_0))
gene_info_5_4_0 = list(set(gene_info_5_4_0))

# Remove empty tuples from each list.
gene_info_5_3_0 = [x for x in gene_info_5_3_0 if x]
gene_info_5_4_0 = [x for x in gene_info_5_4_0 if x]

# Print the genes that are missing from 5.4.0 to a text file.
number_of_missing_genes = 0
with open('missing_genes.txt', 'w') as f:
    f.write('Missing genes from Xenbase release 5.4.0 (compared to 5.3.0):' + '\n' + '\n')
    f.write('Gene ID' + '\t' + 'Symbol' + '\n')
    for gene in gene_info_5_3_0:
        if gene not in gene_info_5_4_0:
            number_of_missing_genes += 1
            if gene[1] is not None:
                f.write(gene[0] + '\t' + gene[1] + '\n')
            else:
                f.write(gene[0] + '\t' + 'None' + '\n')

# Print the number of missing genes.
print('Number of missing genes: ' + str(number_of_missing_genes))