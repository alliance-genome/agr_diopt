#!/usr/bin/env python3

import os
import argparse
import subprocess
import sys

def main():
    parser = argparse.ArgumentParser(
        description="Upload orthology files to FMS using a provided Bearer token."
    )
    parser.add_argument("--input_dir", required=True, help="Directory containing orthology_*.json.gz files")
    parser.add_argument("--version", required=True, help="Version string, e.g. 3.0.0")
    parser.add_argument("--bearer", required=True, help="Bearer token for authorization")

    args = parser.parse_args()

    # Mapping from the "filename mod" (the middle portion of "orthology_MOD_v9.json.gz")
    # to the FMS label:
    # - e.g. FlyBase -> FB, WormBase -> WB, Human -> HUMAN, etc.
    mod_map = {
        "FlyBase": "FB",
        "WormBase": "WB",
        "ZFIN": "ZFIN",
        "RGD": "RGD",
        "MGI": "MGI",
        "XBXL": "XBXL",
        "XBXT": "XBXT",
        "Human": "HUMAN",
        "SGD": "SGD"
    }

    # List all files in input_dir that match "orthology_*_v9.json.gz".
    # We skip "orthology_test_data_v9.json.gz".
    input_files = sorted([
        f for f in os.listdir(args.input_dir)
        if f.startswith("orthology_") and f.endswith(".json.gz")
        and "test_data" not in f
    ])

    if not input_files:
        print(f"No orthology_*.json.gz files found in {args.input_dir}, or only test files present.")
        sys.exit(0)

    print(f"Found {len(input_files)} orthology JSON.gz files to upload.")
    print("Beginning uploads...")

    for filename in input_files:
        # Example filename: orthology_FlyBase_v9.json.gz
        # We want to parse out "FlyBase" from "orthology_FlyBase_v9.json.gz".
        # This is a simplistic approach: splitting on '_' and ignoring the 'orthology' & 'v9.json.gz' parts.
        # If your naming convention changes, adapt accordingly.
        # "orthology_{mod}_v9.json.gz" => mod = splitted[1]
        splitted = filename.split("_")
        # splitted = ["orthology", "FlyBase", "v9.json.gz"] for example
        if len(splitted) < 3:
            print(f"Skipping {filename} - cannot parse mod from name.")
            continue
        mod_part = splitted[1]  # e.g. "FlyBase"

        # Convert "FlyBase" -> "FB", "WormBase" -> "WB", etc.
        if mod_part not in mod_map:
            print(f"Skipping {filename} - unknown mod '{mod_part}'.")
            continue

        mapped_mod = mod_map[mod_part]  # e.g. FB, WB, HUMAN, etc.

        # Build the final upload label like "3.0.0_ORTHO_FB"
        # if version=3.0.0, mapped_mod=FB => "3.0.0_ORTHO_FB"
        label = f"{args.version}_ORTHO_{mapped_mod}"

        # Full path to file
        full_path = os.path.join(args.input_dir, filename)

        # Construct the curl command
        # We can post the compressed file as-is; 
        # The FMS endpoint is typically fine with .gz if you specify the "@" notation.
        # E.g. curl -H "Authorization: Bearer xxxxx" -X POST 
        #      "https://fms.alliancegenome.org/api/data/submit" 
        #      -F "3.0.0_ORTHO_ZFIN=@orthology_ZFIN_v9.json.gz"
        curl_cmd = [
            "curl",
            "-H", f"Authorization: Bearer {args.bearer}",
            "-X", "POST",
            "https://fms.alliancegenome.org/api/data/submit",
            "-F", f"{label}=@{full_path}"
        ]

        print(f"Uploading {filename} as {label}...")
        try:
            # If you'd prefer just to print commands, comment out the run() and print curl_cmd instead
            subprocess.run(curl_cmd, check=True)
            print(f"Upload succeeded for {filename}")
        except subprocess.CalledProcessError as e:
            print(f"Upload failed for {filename}. Error: {e}")
            # Decide if you want to exit or continue to the next file
            # sys.exit(1)

    print("All uploads completed (or attempted).")

if __name__ == "__main__":
    main()
