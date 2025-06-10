import pandas as pd
import os
import sys
from tqdm import tqdm

def get_num_lines(file_path):
    with open(file_path) as f:
        for i, l in enumerate(f):
            pass
    return i + 1

def convert_tsv_to_csv(file_path):
    # Get the new file path
    csv_file_path = os.path.splitext(file_path)[0] + '.csv'
    
    # Initialize a first chunk flag
    first_chunk = True
    
    # Read and convert the file in chunks
    chunksize = 10 ** 6  # adjust this value depending on your available memory
    total_chunks = get_num_lines(file_path) // chunksize + 1
    with tqdm(total=total_chunks) as pbar:
        for chunk in pd.read_csv(file_path, sep='\t', chunksize=chunksize):
            if first_chunk:
                # Save the first chunk to initialize the CSV
                chunk.to_csv(csv_file_path, index=False)
                first_chunk = False
            else:
                # Append subsequent chunks
                chunk.to_csv(csv_file_path, mode='a', header=False, index=False)
            pbar.update()

    print(f'CSV file saved as: {csv_file_path}')

# Usage:
# script_name.py input_file.tsv
if __name__ == "__main__":
    input_file = sys.argv[1]
    convert_tsv_to_csv(input_file)
