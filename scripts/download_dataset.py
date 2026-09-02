#!/usr/bin/env python3
"""
OmniWatch dataset acquisition.

Dataset: "FIR DETAILS (KARNATAKA POLICE)"
Source:  https://www.kaggle.com/datasets/vanshangaria/fir-details-karnataka-police
License: as published by the uploader on Kaggle (see the dataset page for
         current license terms before any redistribution).

This dataset consists of 1,674,734 real First Information Report (FIR)
records recorded by Karnataka Police between 2016 and 2024, covering 41
districts. It includes District, Police Station (UnitName), crime
category (CrimeGroup_Name / CrimeHead_Name), date (FIR_YEAR/MONTH/Day),
victim/accused demographics, and Latitude/Longitude for a subset of records
(~30%; the remainder have real district/station location but no
coordinates - these are never fabricated).

This script does NOT download the dataset automatically, because:
  1. Kaggle requires authenticated API access (KAGGLE_USERNAME/KAGGLE_KEY),
     which is not configured in this environment.
  2. The dataset license on the Kaggle page should be reviewed by you
     before automated redistribution.

Manual steps
------------
1. Create a Kaggle account and API token (kaggle.com/settings -> API ->
   "Create New Token"), which downloads kaggle.json.
2. Set the credentials as environment variables (see .env.example):
     KAGGLE_USERNAME=<your-username>
     KAGGLE_KEY=<your-key>
3. Install the Kaggle CLI:  pip install kaggle
4. Run:
     kaggle datasets download -d vanshangaria/fir-details-karnataka-police -p data/raw --unzip
5. Rename the extracted CSV to match what the pipeline expects:
     mv data/raw/FIR_Details_Data.csv data/raw/karnataka_fir_2016_2024.csv

Alternatively (used in this project): download the dataset zip manually
from the Kaggle page in your browser, then run this script with --from-zip
to extract and place it correctly.
"""
import argparse
import os
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
TARGET_FILENAME = "karnataka_fir_2016_2024.csv"
EXPECTED_SOURCE_FILENAME = "FIR_Details_Data.csv"


def try_kaggle_api_download():
    username = os.environ.get("KAGGLE_USERNAME")
    key = os.environ.get("KAGGLE_KEY")
    if not username or not key:
        print("KAGGLE_USERNAME / KAGGLE_KEY not set in environment (.env). "
              "See the docstring in this file for manual download instructions.")
        return False
    try:
        import kaggle  # noqa
    except ImportError:
        print("The 'kaggle' package is not installed. Run: pip install kaggle")
        return False

    os.system(
        f"kaggle datasets download -d vanshangaria/fir-details-karnataka-police "
        f"-p {RAW_DIR} --unzip"
    )
    extracted = RAW_DIR / EXPECTED_SOURCE_FILENAME
    if extracted.exists():
        extracted.rename(RAW_DIR / TARGET_FILENAME)
        print(f"Downloaded and placed dataset at {RAW_DIR / TARGET_FILENAME}")
        return True
    print("Kaggle download did not produce the expected file. Check manually.")
    return False


def extract_from_zip(zip_path: str):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        csv_candidates = [n for n in names if n.lower().endswith(".csv")]
        if not csv_candidates:
            raise SystemExit(f"No CSV found inside {zip_path}")
        member = csv_candidates[0]
        z.extract(member, RAW_DIR)
        extracted_path = RAW_DIR / member
        target_path = RAW_DIR / TARGET_FILENAME
        shutil.move(str(extracted_path), str(target_path))
        print(f"Extracted {member} -> {target_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-zip", help="Path to a manually downloaded Kaggle dataset zip")
    args = parser.parse_args()

    if args.from_zip:
        extract_from_zip(args.from_zip)
        return

    target = RAW_DIR / TARGET_FILENAME
    if target.exists():
        print(f"Dataset already present at {target} ({target.stat().st_size / 1e6:.1f} MB). Nothing to do.")
        return

    ok = try_kaggle_api_download()
    if not ok:
        raise SystemExit(
            "Could not download dataset automatically. Please follow the manual "
            "steps in this file's docstring, or run:\n"
            f"  python {__file__} --from-zip /path/to/downloaded/archive.zip"
        )


if __name__ == "__main__":
    main()
