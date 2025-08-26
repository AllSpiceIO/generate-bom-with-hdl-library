from argparse import ArgumentParser
from ptflib import PTFLib
from pathlib import Path
from typing import (
    List,
)
import csv


################################################################################
def ingest_libraries(libroot) -> List[PTFLib]:
    available_libs = []
    for ptf_path in Path(libroot).rglob(f'*.{"ptf"}'):
        ptf_lib = PTFLib(ptf_path)
        available_libs.append(ptf_lib)
    return available_libs


################################################################################
if __name__ == "__main__":
    # Initialize argument parser
    parser = ArgumentParser()
    parser.add_argument("bom_file", help="Path to the input BOM file")
    parser.add_argument("--library_path", help="Path to library")
    parser.add_argument("--output_path", help="Path for the output BOM file")
    parser.add_argument(
        "--part_number_column_name",
        help="Name of the column which contains the part number",
    )
    parser.add_argument(
        "--part_type_column_name",
        help="Name of the column which contains the part type, e.g. RES-SMD",
    )
    parser.add_argument(
        "--search_ptf_column_name", help="Name of the column in the PTF file to search for"
    )
    parser.add_argument("--add_column", action="extend", nargs="+")
    args = parser.parse_args()

    # Ingest all available libraries
    available_libs = ingest_libraries(args.library_path)
    # Get a list of all ingested part types' indices
    lib_part_type_idxs = [ptflib.lib.part_type for ptflib in available_libs]

    # Ingest input BOM
    with open(args.bom_file, newline="") as bomfile:
        bomreader = csv.reader(bomfile, delimiter=",", quotechar='"')
        bom_line_items = list(bomreader)
        part_num_idx = (bom_line_items[0]).index(args.part_number_column_name)
        part_type_idx = (bom_line_items[0]).index(args.part_type_column_name)
        title_row_columns = bom_line_items[0]
        del bom_line_items[0]

    ptf_file_col_names = []
    for column in args.add_column:
        column_args = column.split(",")
        ptf_col_name, bom_col_name = column_args[0], column_args[1]
        title_row_columns.append(bom_col_name)
        ptf_file_col_names.append(ptf_col_name)

    # Loop through the BOM
    for item in bom_line_items:
        # Get which library to reference
        lib_idx = lib_part_type_idxs.index(item[part_type_idx])
        try:
            # Find matching parts in the library
            lib = available_libs[lib_idx]
            parts_found = lib.find_part(args.search_ptf_column_name, item[part_num_idx])
            # Update BOM for all parts found
            for part in parts_found:
                for col_name in ptf_file_col_names:
                    item.append(part[col_name])
        except Exception:
            continue

    # Update BOM with title rows and output to file
    if args.output_path is not None:
        with open(args.output_path, "w") as fp:
            writer = csv.writer(fp)
            writer.writerow(title_row_columns)
            writer.writerows(bom_line_items)
