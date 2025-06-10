#!/usr/bin/env python

import sys
import csv
import argparse
import sqlparse
import re
import os

###############################################################################
# Utility Functions for Handling the Fixes File
###############################################################################

def load_column_fixes(fixes_file_path):
    """
    Load a 'column_fixes.tsv' file that records user-approved column mappings.
    Returns a dict with keys = (table_name, original_column) and values = new_column.
    """
    fixes_dict = {}
    if not os.path.exists(fixes_file_path):
        return fixes_dict  # empty if file doesn't exist

    with open(fixes_file_path, 'r', newline='') as fixes_file:
        reader = csv.reader(fixes_file, delimiter='\t')
        # Expecting lines: table_name \t old_col \t new_col
        for row in reader:
            if len(row) < 3:
                continue
            tbl, old_col, new_col = row
            fixes_dict[(tbl.lower(), old_col)] = new_col
    return fixes_dict


def save_column_fix(fixes_file_path, table_name, old_col, new_col):
    """
    Append a new fix line (table_name, old_col, new_col) to the 'column_fixes.tsv' file.
    """
    with open(fixes_file_path, 'a', newline='') as fixes_file:
        writer = csv.writer(fixes_file, delimiter='\t')
        writer.writerow([table_name.lower(), old_col, new_col])


###############################################################################
# DDL Parsing
###############################################################################

def split_ddl_individual_entry(ddl_entry, dict_of_ddl_contents):
    """
    For each CREATE TABLE statement, parse out the columns and whether they allow NULL.
    """
    parts = ddl_entry.split('CREATE TABLE ')
    if len(parts) < 2:
        return dict_of_ddl_contents

    string_lines = parts[1].split('\n')
    # Extract the table title from the first line
    table_title = "".join(re.findall("[a-zA-Z_]+", string_lines[0]))
    table_title_lower = table_title.lower()

    dict_of_ddl_contents[table_title_lower] = {}

    # The lines between parentheses hold columns
    for command_row in string_lines[1:-1]:
        cleaned_line = "".join(re.findall("[a-zA-Z0-9_ ]+", command_row)).strip()
        if not cleaned_line:
            continue

        cleaned_line_values = cleaned_line.split()
        if len(cleaned_line_values) < 1:
            continue

        column_name = cleaned_line_values[0].lower()
        column_type = cleaned_line_values[1] if len(cleaned_line_values) > 1 else None
        can_be_null = True
        if 'NOT NULL' in command_row:
            can_be_null = False

        dict_of_ddl_contents[table_title_lower][column_name] = (column_type, can_be_null)

    return dict_of_ddl_contents


def parse_ddl_contents(ddl_file_location):
    """
    Split the SQL file by statements, look for CREATE TABLE, parse each table's columns.
    """
    dict_of_ddl_contents = {}
    with open(ddl_file_location) as ddl_file:
        sql = ddl_file.read()
        ddls = sqlparse.split(sql)
        for ddl_entry in ddls:
            if 'CREATE TABLE' in ddl_entry:
                dict_of_ddl_contents = split_ddl_individual_entry(ddl_entry, dict_of_ddl_contents)
    return dict_of_ddl_contents


###############################################################################
# Processing the TSV -> CSV
###############################################################################

def process_tsv_files(ddl_contents, input_dir, output_dir, fixes_file_path):
    """
    For each table in ddl_contents:
      - Look for 'table_name.tsv' in input_dir.
      - If found, parse headers, apply known fixes or prompt for new ones, rewrite as 'fixed_table_name.csv'.
    Then show a list of any .tsv files in input_dir that were not processed.
    """
    set_of_print_statements = set()

    # Load existing user fixes so we don't keep prompting every time
    known_fixes = load_column_fixes(fixes_file_path)

    # Gather the DDL table names
    table_names_from_ddl = list(ddl_contents.keys())  # e.g. ['gene_information', 'ortholog_pair', ...]

    # Keep track of which .tsv files we actually processed
    processed_basenames = []

    # For each table name, see if there's a corresponding .tsv
    for table_name in table_names_from_ddl:
        file_location = os.path.join(input_dir, f"{table_name}.tsv")
        output_file = os.path.join(output_dir, f"fixed_{table_name}.csv")

        if not os.path.exists(file_location):
            # There's no .tsv file for this table, so skip
            continue

        processed_basenames.append(f"{table_name}.tsv")

        try:
            with open(file_location, 'r', newline='') as tsv_file:
                tsv_reader = csv.reader(tsv_file, delimiter='\t')

                # Read headers
                try:
                    headers = next(tsv_reader)
                except StopIteration:
                    print(f"ERROR: {file_location} is empty or unreadable.")
                    continue

                headers = [h.strip('"').strip() for h in headers]

                # Step 1: Figure out final header names (prompt the user if needed).
                final_headers = resolve_headers(table_name, headers, ddl_contents, known_fixes, fixes_file_path)

            # Re-process the file to write out the new CSV
            with open(file_location, 'r', newline='') as tsv_file, \
                 open(output_file, 'w', newline='') as out_csv:
                reader = csv.reader(tsv_file, delimiter='\t')
                writer = csv.writer(out_csv)

                # read the headers again
                original_headers = next(reader)
                original_headers = [h.strip('"').strip() for h in original_headers]

                # Write out the final headers
                writer.writerow(final_headers)

                row_count = 1
                for row in reader:
                    row_count += 1

                    # build a new row, applying dash->NULL checks if the column is recognized in the DDL
                    new_row = []
                    for idx, item in enumerate(row):
                        new_colname = final_headers[idx]  # the final name we ended up with
                        # if new_colname exists in DDL, do the check
                        if new_colname.lower() in ddl_contents[table_name]:
                            (item_type, can_be_null) = ddl_contents[table_name][new_colname.lower()]

                            if item == '-':
                                replacement_message = f'Replaced "-" with "" in {table_name}:{new_colname}.'
                                if replacement_message not in set_of_print_statements:
                                    print(replacement_message)
                                    set_of_print_statements.add(replacement_message)
                                item = ''
                                if not can_be_null:
                                    warning_message = (f'ERROR: DDL specifies {table_name}:{new_colname} '
                                                       f'should NOT be NULL, but NULL value found.')
                                    if warning_message not in set_of_print_statements:
                                        print(warning_message)
                                        set_of_print_statements.add(warning_message)

                        new_row.append(item)

                    writer.writerow(new_row)

                print(f"\nFinished writing '{output_file}'. Processed {row_count} rows (including header).")

        except FileNotFoundError:
            print(f"ERROR: File {file_location} not found.")
            continue

    # --------------- Print the unprocessed .tsv files ---------------
    print_unprocessed_files(input_dir, processed_basenames)


def resolve_headers(table_name, headers, ddl_contents, known_fixes, fixes_file_path):
    """
    Determine the final headers for a given TSV by:
      - Matching columns to DDL if they exist
      - Using known fixes from column_fixes.tsv
      - Prompting the user if there's a mismatch
    Returns a list of final header names.
    """

    final_headers = []
    mismatch_cols = []
    matched_columns_info = []

    for h in headers:
        h_lower = h.lower()

        # 1) Check if direct DDL match
        if h_lower in ddl_contents[table_name]:
            final_headers.append(h)
            matched_columns_info.append(f"  {h} (direct match in DDL)")

        # 2) Check if known fix in column_fixes.tsv
        elif (table_name, h) in known_fixes:
            fix_col = known_fixes[(table_name, h)]
            final_headers.append(fix_col)

            # More explicit message
            print(f"Using previously saved fix from column_fixes.tsv for table '{table_name}': '{h}' -> '{fix_col}'")
            matched_columns_info.append(f"  {h} -> {fix_col} (known fix)")

        # 3) Otherwise it's a mismatch
        else:
            final_headers.append(h)
            mismatch_cols.append(h)
            matched_columns_info.append(f"  {h} (NO MATCH in DDL)")

    # Print a summary for user
    print(f"\nColumns for table '{table_name}' were evaluated. Here is the matching report:")
    for info_line in matched_columns_info:
        print(info_line)

    if not mismatch_cols:
        print(f"No new mismatches for table '{table_name}'.")
        return final_headers

    # We have some mismatches. Let's prompt for each mismatch.
    # (We won't sample rows here unless you want that feature again.)
    for mismatch_col in mismatch_cols:
        valid_columns = list(ddl_contents[table_name].keys())
        print("\n==================================================")
        print(f"MISMATCH COLUMN: '{mismatch_col}' in table '{table_name}' is not in the DDL.")
        print("\nPossible columns in the DDL for table:", table_name)
        for c in valid_columns:
            print(f" - {c}")
        print("If you'd like to rename, type the EXACT new column name. Otherwise type 'skip' or press Enter.")
        user_input = input(f"Enter new column name for '{mismatch_col}': ").strip()

        if user_input.lower() in ['no', 'skip', '']:
            print(f"No rename performed for '{mismatch_col}'. (Leaving as '{mismatch_col}')")
        else:
            # rename in final_headers
            idx_in_final = final_headers.index(mismatch_col)
            final_headers[idx_in_final] = user_input
            save_column_fix(fixes_file_path, table_name, mismatch_col, user_input)
            known_fixes[(table_name, mismatch_col)] = user_input
            print(f"Renamed '{mismatch_col}' to '{user_input}' for table '{table_name}'.")
        print("==================================================\n")

    return final_headers


def print_unprocessed_files(input_dir, processed_basenames):
    """
    Look at all .tsv files in input_dir, compare to 'processed_basenames'.
    If any are unprocessed, print them out at the end.
    """
    all_tsv_in_input = []
    for f in os.listdir(input_dir):
        if f.endswith('.tsv'):
            all_tsv_in_input.append(f)

    unprocessed = [f for f in all_tsv_in_input if f not in processed_basenames]
    if unprocessed:
        print("\nThe following TSV files were NOT processed (no matching table in DDL or otherwise skipped):")
        for f in unprocessed:
            print(f"  {f}")
    else:
        print("\nAll TSV files in the input directory were processed (or matched no DDL).")


###############################################################################
# Main
###############################################################################

def main():
    parser = argparse.ArgumentParser(description='Convert DDL + TSV files into CSV.')
    parser.add_argument('-i', '--input_dir', help='Input directory with DDL + TSV files.', required=True)
    parser.add_argument('-o', '--output_dir', help='Output directory.', required=True)
    parser.add_argument('-d', '--ddl_file', help='DDL file to process.', required=True)
    parser.add_argument('-f', '--fixes_file', help='TSV file storing approved column fixes.')
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir
    ddl_file = args.ddl_file

    # If user didn't specify fixes_file, put it in output_dir
    if args.fixes_file:
        fixes_file_path = args.fixes_file
    else:
        fixes_file_path = os.path.join(output_dir, "column_fixes.tsv")

    # Parse DDL
    ddl_contents = parse_ddl_contents(ddl_file)

    print('\nDDL Information:')
    for table_title in ddl_contents:
        print(f'\nTABLE: {table_title}')
        for col, (col_type, can_be_null) in ddl_contents[table_title].items():
            not_null_str = 'NOT NULL' if not can_be_null else 'NULL OK'
            print(f"  {col} -> {col_type}, {not_null_str}")

    # Process
    process_tsv_files(ddl_contents, input_dir, output_dir, fixes_file_path)

    print('\nAll done.\n')


if __name__ == '__main__':
    main()
