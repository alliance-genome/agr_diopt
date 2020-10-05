[![Build Status](https://travis-ci.com/FlyBase/harvdev-diopt.svg?token=7Nvc5gEdzuNraK13EL3s&branch=master)](https://travis-ci.com/FlyBase/harvdev-diopt)

# harvdev-diopt

Scripts for updating DIOPT data at FlyBase.

## Instructions for updating DIOPT

### Creation of DIOPT working directories.

- All past DIOPT work is performed (files processed, scripts run) in directories located under `/data/ortholog/diopt`. 
- When working with a new version of DIOPT, first create a folder in `/data/ortholog/diopt/diopt_vX` where `X` is the current version (_e.g._ 9 or 10).
- Within this folder, create a filed called `implement_diopt_vX.README`. This file will contain notes about implementing this particular version of DIOPT.
- See previous DIOPT folders at `/data/ortholog/diopt` for examples of directory structure and this `README` file.

### GitHub repository

- This repository contains all necessary scripts for updating DIOPT. Please clone it into an appropriate folder for use.
    - This does not need to necessarily be cloned into a directory under `/data/ortholog/diopt`.
    - Anywhere Python scripts can be executed should be sufficient (_e.g._ your home directory, _etc._).

### Processing of DIOPT CSV files.

- Claire Hu (claire_hu@genetics.med.harvard.edu) provides a dump of DIOPT data in the form of CSV files, typically once per year. 
- These files must be inspected for possible formatting errors or issues before being used to load the DIOPT data.

#### Examining and modifying DIOPT CSV files.

- The script `ddl_tsv_to_csv.py` located in the `support_scripts` folder is used to process the DIOPT CSV files from Claire.
- Extract the CSV files from Claire into your DIOPT folder at `/data/ortolog/diopt/diopt_vX`.
- A DDL file from a previous version of DIOPT is required to process the CSV files.
    - The DDL file was originally extracted from the Postgres instance of the DIOPT data.
    - A Postgres instance of DIOPT data is no longer used in these scripts, but the DDL is still necessary to check the validity of the data.
    - An older version of the DDL file can be obtained by copy + pasting the DDL from a previous DIOPT upgrade folder (_e.g._ `/data/ortholog/diopt/diopt_v8`).
    - In the `diopt_v8` folder, the file is named `diopt_v8.ddl`.
- Create an additional folder in your `diopt_vX` folder called `fixed_csv`. This folder will contain the output from the script `ddl_tsv_to_csv.py`.
- Run the script `ddl_tsv_to_csv.py` script with the appropriate flags.
    - _e.g._ `python ddl_tsv_to_csv.py -i /data/ortolog/diopt/diopt_vX -o /data/ortolog/diopt/diopt_vX/fixed_csv -d /data/ortolog/diopt/diopt_vX/diopt_v9.ddl`
    - The `-i` flag is for the input directory (for CSVs from Claire).
    - The `-o` flag is for the output directory.
    - The `-d` flag is for the location of the DDL.
- If this script fails, it will stop and dump out an error. Common issues for failing are things like:
    - NULL values where NULL values are not expected.
    - Incorrect datatype such as `VARCHAR` where `BOOLEAN` is expected.
    - Weird characters.
    - Basically anything that's not expected by the DDL will crash it.
- You'll need to fix any errors that occur when this script fails. You have two choices:
    - Modify the DDL to accommodate the failures.
    - Modify the CSV data to accommodate the failures.
- There are pros and cons for each approach. 
    - If you change the DDL to accommodate the errors, then the main DIOPT loading script might fail because it is expecting data that is validated by the DDL.
    - If the DDL is changed, pay close attention to the output of the main processing script.
    - Look for errors or unexpected data.
    - Everything could still work correctly if the changes to the DDL are minor.
    - Modifying the CSV data by editing the data directly _or_ by adding a function in the `ddl_tsv_to_csv.py` script will typically ensure that the downstream scripts function as expected.
    - There's no real easy answer on "how" to fix bad or malformed data, you just need to try and poke around until it's working.
    
### Obtaining external data not included in the DIOPT CSV files.

- The DIOPT processing script requires data from NCBI in order to fully load the orthology.
- These data exist in the form of a downloadable bulk filed called: `All_Data.gene_info.gz`.
- This file can be downloaded from: `ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/All_Data.gene_info.gz`
- Download and extract the data from this file into the `/data/ortolog/diopt/diopt_vX` directory.
- Not all data in this file is needed -- only a subset.
    - To obtain the subset of data that overlaps with data in the DIOPT csv files, use the script `trim_all_data.py`.
    - Open the script file with an editor and edit the configuration fields under the `main()` function to account for the directories with DIOPT CSV information.
        - Command-line configurations are a TODO. Feel free to update this script and edit this README.md.
    - Run the script once the configuration variables are updated. It will create a new copy of the `All_Data` file with significantly less data for use in the main DIOPT script.
    
### Running the main DIOPT processing script `rework_diopt2chado.py`.

- This script should **always** be run against a **copy of production** (test database) before using production.
- This script uses a **tremendous** amount of memory and should be run on a FlyBase desktop machine. It will not run on most laptops or home computers.
- No Postgres database is required to run this script, everything is handled via CSV files and in-memory.
- Outstanding improvements and TODOs are listed as issues in this GitHub repo. 

#### Configuring `rework_diopt2chado.py`. 

- Verbose / Debug mode can be turned on by using the -v or --verbose flag when executing the script.
- All other configuration options can be found in `/data/credentials/diopt/config.cfg`.
- **PLEASE CHECK THE CONFIG FILE BEFORE RUNNING.**

#### Launching `rework_diopt2chado.py`.

- Install all requirements from the requirements.txt file.
- Execute the script with `python rework_diopt2chado.py`.
- Verbose mode can be enable with `python rework_diopt2chado.py -v`.

#### Loading bulk CSV data.

- The python script `rework_diopt2chado.py` will also generate 3 bulk CSV files in the DIOPT output directory.
- These files need to be manually loaded into Chado _after_ changes from `rework_diopt2chado.py` are committed.
- Be sure to test load everything in a test database first, including these files.
- It will take a few minutes (at least) to load each file.
- The commands to load these files are (must be run **in this order**):
    - `psql -h <flysql> -d <database> -c "\copy dbxref (db_id, accession, version, description, url) FROM 'dbxref_output_file.csv' CSV HEADER;"` 
    - `psql -h <flysql> -d <database> -c "\copy feature_dbxref (feature_id, dbxref_id, is_current) FROM 'feature_dbxref_output_file.csv' CSV HEADER;"` 
    - `psql -h <flysql> -d <database> -c "\copy dbxrefprop (dbxref_id, type_id, value, rank) FROM 'dbxrefprop_output_file.csv' CSV HEADER;"`
    - Replace <flysql> with the appropriate flysql server and <database> with your test database or production_chado.
    
#### Drop the previous DIOPT dataset.

- After all the data is tested, loaded, and confirmed, the old DIOPT dataset can be manually dropped.
- Use this command when logged into the appropriate database: 
    - `delete from db where name = 'diopt_v6_0';`
- Replace the name `diopt_v6_0` with the version of DIOPT you'd like to remove.

## Fin!
