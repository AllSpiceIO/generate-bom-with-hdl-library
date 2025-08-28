# Generate Complete BOM with External DeHDL / System Capture Library

*Note: this repo is temporary and will be merged with https://hub.allspice.io/Actions/generate-bom/src/branch/main/README.md* 

Generate an enriched ("complete") Bill of Materials for a System Capture project by
augmenting a base BOM (produced with `py-allspice` / the standard `generate-bom` action)
with additional part metadata sourced from one or more external Cadence DeHDL / System
Capture library `.ptf` files stored in a separate repository (or subdirectory).

The action:
- Parses every `*.ptf` file under the provided `library_path`.
- Selects the appropriate library to search per BOM row based on that row's part type.
- Locates matching parts by searching a chosen PTF column (e.g. `AML`, `PART_NUMBER`).
- Copies selected PTF columns into newly appended columns in the output BOM.

Result: a CSV BOM (`complete_bom.csv` by default) with extra, library-quality
attributes (approved manufacturer list, status, links, etc.) attached to each line item.

## When to Use This Action
Use this action when your design repo does **not** contain all authoritative part data,
and you maintain a curated System Capture / DeHDL library repository with PTF tables (for
example containing AML, manufacturer, lifecycle status, ERP/PLM links). The base BOM
coming from schematic extraction only has limited columns; this action joins in the rich
library data without needing to manually merge spreadsheets.

## Inputs
| Input | Required | Description |
|-------|----------|-------------|
| `bom_file` | yes | Path to an existing BOM CSV generated earlier in the workflow (e.g. via `generate-bom`). |
| `library_path` | yes | Directory containing one or more `*.ptf` files (recursively scanned). You usually checkout a separate library repo here. |
| `part_number_column_name` | yes | Column header in the input BOM whose value you want to look up inside the PTF files (e.g. `Part Number`). |
| `part_type_column_name` | yes | Column header in the input BOM identifying the PART type (maps to the `PART 'XXXX'` line in the PTF). Used to select which PTF to search. |
| `search_ptf_column_name` | yes | Column name (from the PTF title row) to match against `part_number_column_name` values (e.g. `AML`, `PART_NUMBER`, `VALUE`). |
| `include_ptf_columns` | yes | Comma-separated list of PTF column names whose values should be copied into the BOM. Order must align with `add_bom_columns`. |
| `add_bom_columns` | yes | Comma-separated list of new column headers to append to the output BOM receiving the mapped values (same length & order as `include_ptf_columns`). |
| `output_path` | yes | Output path (inside the workspace) for the enriched BOM. Default: `complete_bom.csv`. |

## Output
A CSV file at `output_path` with original BOM columns plus the new columns named in
`add_bom_columns`. Each new column contains the corresponding value from the matched
PTF row (or is left blank if no match). The file is not automatically uploaded—add an
artifact/upload step if desired.

## PTF Parsing Overview
Each `.ptf` file is loosely parsed with these assumptions:
- Canonical ordering: `FILE_TYPE`, `PART`, `CLASS`, title row, one or more data rows.
- Comment lines starting with `{` and any `END` lines are ignored.
- Title row tokens become column names (symbols stripped of decoration).
- Data rows are split on `|` and `=` while preserving HTTP URLs intact.

A match occurs when:
1. The BOM row's part type equals the PTF's `PART` token (after parsing).
2. The value in the BOM row's `part_number_column_name` equals the value in the
	 PTF row under `search_ptf_column_name`.

If multiple PTF rows match, all selected columns are appended in sequence (currently the
script appends values for each matching row; typically there is one). If no match, the
new columns remain empty for that row.

## Example Workflow
Assume you already generate a base BOM for a System Capture design and you have a
separate library repository `Company/SystemCapture-Library` containing PTF files.

```yaml
name: Generate Complete BOM
on:
  push:
  issues:
    types: [opened, closed, reopened]
jobs:
  Generate_Full_BOM:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout design repo
        uses: actions/checkout@v4
      - name: Checkout library repo
        uses: actions/checkout@v4
        with:
          repository: Organization/DeHDL-Library
          token: ${{ secrets.PAT }}
          path: local_lib
      - name: Generate BOM
        uses: https://hub.allspice.io/Actions/generate-bom@v0.8
        with:
          # The path to the project file in your repo (.PrjPcb for Altium, .DSN for OrCad).
          source_path: allspice_bom_gen_test.sdax
          # [optional] A path to a YML file mapping columns to the component attributes
          # they are from. This file must be provided.
          # Default: 'columns.json'
          columns: .allspice/columns.yml
          # [optional] The path to the output file that will be generated.
          # Default: 'bom.csv'
          output_file_name: bom.csv
          # [optional] A comma-separated list of columns to group the BOM by. If empty
          # or not present, the BOM will be flat.
          # Default: ''
          group_by: "Internal PN"
          # [optional] The variant of the project to generate the BOM for. If empty
          # or not present, the BOM will be generated for the default variant.
          # Default: ''
          variant: ""
      # Print bom.csv to terminal
      - name: Show BOM
        run: cat bom.csv
      # Upload original BOM as artifact
      - name: Upload file as artifact
        uses: actions/upload-artifact@v3
        with:
          name: BOM.csv
          path: bom.csv
      # Generate Complete BOM
      - name: Generate Complete BOM
        uses: https://github.com/AllSpiceIO/generate-bom-with-hdl-library@4746bc315337b2fec113c08efc1e2403743759de
        with:
          bom_file: bom.csv
          library_path: local_lib
          output_path: complete_bom.csv
          part_number_column_name: "Internal PN"
          part_type_column_name: "Library Name"
          search_ptf_column_name: "PART_NUMBER"
          include_ptf_columns: "AML,MANUFACTURER,DESCRIPTION"
          add_bom_columns: "Manufacturer Part Number,Manufacturer,Description"
      # Print complete_bom.csv to terminal
      - name: Show complete BOM
        run: cat complete_bom.csv
      # Upload complete BOM as artifact
      - name: Upload file as artifact
        uses: actions/upload-artifact@v3
        with:
          name: COMPLETE_BOM.csv
          path: complete_bom.csv
```

## Selecting Column Names
Inspect a representative PTF file in your library. The title row (after colons / pipes
and before data rows) yields the available column headers. Typical examples:
- `VALUE`, `TOL`, `PWR`, `PACK_TYPE`, `PART_NUMBER`, `JEDEC_TYPE`, `DESCRIPTION`, `AML`, `STATUS`, `ORACLE_LINK`, `MANUFACTURER`

Decide which of these you want to surface in your BOM (`include_ptf_columns`), then pick
clear user-facing names for the BOM columns (`add_bom_columns`). Ensure both lists have
identical length and ordering.

## Troubleshooting
| Symptom | Likely Cause | Action |
|---------|--------------|--------|
| New columns are blank | No matching part type or part number, or column typo | Confirm `part_type_column_name` values match PTF PART tokens; verify spelling & case of `search_ptf_column_name`. |
| Runtime error: "No matching column name found" | `search_ptf_column_name` not present in PTF title row | Adjust input to an existing column. |
| Some rows enriched, others not | Legitimate library gaps | Add missing parts to library or accept blanks. |
| Duplicate values appended | Multiple rows in PTF match the BOM part number | Deduplicate library entries or post-process BOM. |

## Limitations & Future Ideas
- Multiple matches append repeated groups; could be enhanced to choose first or aggregate.
- No direct support yet for fuzzy matching or case-insensitive search.
- Assumes unique mapping of part type to exactly one PTF file; collisions may cause first-hit behavior.

## Local Debug
You can run the container locally to test parsing:
```
python entrypoint.py \
	base_bom.csv \
	--library_path ./library \
	--output_path complete_bom.csv \
	--part_number_column_name "Part Number" \
	--part_type_column_name "Part Type" \
	--search_ptf_column_name AML \
	--include_ptf_columns AML,MANUFACTURER,STATUS \
	--add_bom_columns AML,Manufacturer,Status
```

## License
See `LICENSE.txt`.

## Related
- Standard BOM generator: https://hub.allspice.io/Actions/generate-bom
- AllSpice Actions Docs: https://learn.allspice.io/docs/actions-cicd

