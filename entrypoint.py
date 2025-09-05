#! /usr/bin/env python3

from argparse import ArgumentParser
from ptflib import PTFLib
from pathlib import Path
from typing import (
    List,
)
import logging
import sys
import csv

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)


################################################################################
def ingest_libraries(libroot) -> List[PTFLib]:
    available_libs = []
    for ptf_path in Path(libroot).rglob(f"*pt.{'ptf'}"):
        ptf_lib = PTFLib(ptf_path)
        available_libs.append(ptf_lib)
    return available_libs


################################################################################
if __name__ == "__main__":
    # Initialize argument parser
    parser = ArgumentParser()
    parser.add_argument("bom_file", help="Path to the input BOM file")
    parser.add_argument("--library_path", required=True, help="Path to library")
    parser.add_argument("--output_path", required=True, help="Path for the output BOM file")
    parser.add_argument(
        "--part_number_column_name",
        required=True,
        help="Name of the column in the input BOM that contains part numbers that need to be mapped to an external library",
    )
    parser.add_argument(
        "--part_type_column_name",
        required=True,
        help="Name of the column in the input BOM that contains part types, e.g. RES-SMD",
    )
    parser.add_argument(
        "--search_ptf_column_name",
        required=True,
        help="Name of the column to search for in the PTF file, e.g. AML",
    )
    parser.add_argument(
        "--include_ptf_columns",
        required=True,
        help="A comma separated value list of the column names in the PTF file to match for inclusion in the output BOM.",
    )
    parser.add_argument(
        "--add_bom_columns",
        required=True,
        help="A comma separated value list of the column names to add to the output BOM. The order must match the corresponding sequence provided with the --include_ptf_columns argument",
    )

    args = parser.parse_args()
    library_path = args.library_path
    output_path = args.output_path
    part_number_column_name = args.part_number_column_name
    part_type_column_name = args.part_type_column_name
    search_ptf_column_name = args.search_ptf_column_name
    use_ptf_cols = args.include_ptf_columns.split(",")
    new_bom_cols = args.add_bom_columns.split(",")

    logger.setLevel("DEBUG")
    logger.info("Running generate-bom-with-hdl-library action.")
    logger.debug("Arguments: %s", vars(args))

    # Ingest all available libraries
    available_libs = ingest_libraries(library_path)
    # Get a list of all ingested part types' indices
    lib_part_type_idxs = [ptflib.lib.part_type for ptflib in available_libs]

    # Ingest input BOM
    with open(args.bom_file, newline="") as bomfile:
        bomreader = csv.reader(bomfile, delimiter=",", quotechar='"')
        bom_line_items = list(bomreader)
        part_num_idx = (bom_line_items[0]).index(part_number_column_name)
        part_type_idx = (bom_line_items[0]).index(part_type_column_name)
        title_row_columns = bom_line_items[0]
        del bom_line_items[0]

    for bom_col in new_bom_cols:
        title_row_columns.append(bom_col)

    # Loop through the BOM
    for item in bom_line_items:
        # Get which library to reference
        lib_idx = lib_part_type_idxs.index(item[part_type_idx])
        try:
            # Find matching parts in the library
            lib = available_libs[lib_idx]
            parts_found = lib.find_part(search_ptf_column_name, item[part_num_idx])
            # Update BOM for all parts found
            for part in parts_found:
                for col_name in use_ptf_cols:
                    item.append(part[col_name])
        except Exception:
            continue

    # Update BOM with title rows and output to file
    if args.output_path is not None:
        with open(args.output_path, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(title_row_columns)
            writer.writerows(bom_line_items)
