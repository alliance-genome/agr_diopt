#!/usr/bin/env python

import sys
import csv
import argparse
import sqlparse


def parse_ddl_contents(ddl_file_location):
    dict_of_ddl_contents = dict()  # Create a dictionary to store all of our DDL information.
    with open(ddl_file_location) as ddl_file:
        sql = ddl_file.read()
        ddls = sqlparse.split(sql)  # Splits the file into SQL statements.
        for ddl in ddls:
            if 'CREATE TABLE' in ddl:
                # The following section could / should be updated with some cool regex.
                # Using splits and strips works fine, but it's less efficient and less readable.
                split_string = ddl.split('CREATE TABLE ')[1]  # Extract the CREATE TABLE commands.
                string_lines = split_string.split('\n')  # Break them into a list separated by \n.
                table_title = string_lines[0].split(' ')[0]  # Extract the table title from the first item in the list.
                dict_of_ddl_contents[table_title] = dict()  # Create an empty dictionary to store the table information.
                for command_row in string_lines[1:-1]:  # Loop between 2nd and n-1 entry (to ignore title and ); characters).
                    cleaned_line = command_row.strip(' ')  # Remove whitespace from beginning and end of string.
                    column_name_and_type = cleaned_line.split(' ', 2)  # Split off the column name and type.
                    column_name = column_name_and_type[0]  # Save the column name.
                    column_type = column_name_and_type[1].split('(')[0]  # Remove parenthesis from column type.
                    column_type = column_type.replace(',', '')  # Remove commas from column type.
                    can_be_null = True
                    if 'NOT NULL' in cleaned_line:  # Check for NOT NULL declaration.
                        can_be_null = False
                    dict_of_ddl_contents[table_title][column_name] = (column_type, can_be_null)  # Populate the table dictionary.
    return(dict_of_ddl_contents)


def process_tsv_files(ddl_contents, input_dir, output_dir):
    set_of_print_statements = set()  # Used to track error messages and avoid duplicate print statments.
    for filename in ddl_contents:
        file_location = input_dir + '/' + filename + '.tsv'
        output_file = output_dir + '/' + 'fixed_' + filename + '.csv'
        try:
            with open(file_location) as tsv_file, open(output_file, 'w') as output_csv:
                print("Reading from file %s and writing to file %s" % (file_location, output_file))
                tsvin = csv.reader(tsv_file, delimiter='\t')
                csvout = csv.writer(output_csv)
                headers = next(tsvin)  # Extract the headers from the TSV file and move the loop one step forward.
                headers_to_print = [str(x.strip('"')) for x in headers]
                csvout.writerow(headers_to_print)
                row_count = 1
                for row in tsvin:
                    row_count += 1
                    row_print_array = []
                    for idx, item in enumerate(row):  
                        # Loop with both the array item itself and the index number (idx) of the item.
                        # Lookup the item type and whether it can be NULL from our ddl_contents dictionary.
                        # This will fail (which is desirable) if the DDL is missing a column header from a TSV.
                        # We're also looping through the headers array using the index number of the row via "enumerate".
                        # This is a cool trick which allows us to step through the header as we step through the row items.
                        # The goal is to include the name of the "column" alongside the row item itself.
                        try:
                            (item_type, can_be_null) = ddl_contents[filename][headers[idx].lower()]
                        except KeyError:
                            print("ERROR: The column %s from %s.tsv is missing from the DDL. Please fix before proceeding." % (headers[idx], filename))
                            sys.exit(-1)
                        # Fix the undesired NULL characters and replace it with an actual NULL.
                        if item == '-':
                            item_orig = item
                            item = ''
                            replacement_message = 'Replaced \"%s\" with %s in %s:%s.' % (item_orig, item, filename, headers[idx])
                            if replacement_message not in set_of_print_statements:  # Store the messages and print them only once.
                                print(replacement_message)
                                set_of_print_statements.add(replacement_message)
                            if can_be_null is False:
                                warning_message = 'ERROR: DDL specifies %s:%s should not be NULL, but NULL value found.' % (filename, headers[idx])
                                if warning_message not in set_of_print_statements:
                                    print(warning_message)
                                    set_of_print_statements.add(warning_message)

                        # Append values to our row list.
                        row_print_array.append(item)

                    # Construct output statements.
                    csvout.writerow(row_print_array)
                    del row_print_array[:]  # Dump the array to save memory.

        except FileNotFoundError:
            print("ERROR: File %s not found." % file_location)
            row_count = 0

        # Print row counts.
        print('Processed %s rows in %s.tsv (including headers).' % (row_count, filename))


def main():
    parser = argparse.ArgumentParser(description='Convert DDL + TSV files into CSV.')
    parser.add_argument('-i', '--input_dir', help='Input directory with DDL + TSV files.', required=True)
    parser.add_argument('-o', '--output_dir', help='Output directory.', required=True)
    parser.add_argument('-d', '--ddl_file', help='DDL file to process.', required=True)
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    ddl_file = args.ddl_file

    ddl_contents = parse_ddl_contents(ddl_file)

    print('Verifying the following DDL information:')
    for table_title in ddl_contents:
        print('TABLE: %s' % (table_title))
        print('')
        for column in ddl_contents[table_title]:
            print('COLUMN: %s\tTYPE: %s\tNOTNULL: %s' % (column, ddl_contents[table_title][column][0], ddl_contents[table_title][column][1]))
        print('------------------')

    process_tsv_files(ddl_contents, input_dir, output_dir)

    print('Finished.')


if __name__ == '__main__':
    main()
