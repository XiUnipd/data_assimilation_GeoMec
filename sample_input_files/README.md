# Sample input files

This directory contains a small, fully synthetic input set matching the file
formats expected by the ES-MDA workflow. It contains no real project data,
coordinates, observations, or private paths.

## Directory structure

```text
sample_input_files/
├── mesh.grid_zones
├── node_to_be_DA.xlsx
├── observations.xlsx
├── standard_deviations.xlsx
├── solbox/
│   ├── solbox001.csv
│   ├── solbox002.csv
│   └── solbox003.csv
└── cm_prior/
    ├── mat_001
    ├── mat_002
    ├── mat_003
    └── mat_mean
```

## Suggested configuration

Use these values in a local `data_assimilation/config.py` when experimenting
with the sample set:

```python
SAMPLE_DIR = PROJECT_ROOT / "sample_input_files"

INPUT_DIR = SAMPLE_DIR
MESH_GRID_FILE = SAMPLE_DIR / "mesh.grid_zones"
NODE_DIR = SAMPLE_DIR / "node_to_be_DA.xlsx"
OBS_FILE = SAMPLE_DIR / "observations.xlsx"
COVARIANCE_FILE = SAMPLE_DIR / "standard_deviations.xlsx"
POT_DIR = SAMPLE_DIR / "solbox"
MAT_DIR = SAMPLE_DIR / "cm_prior"

N_ENSEMBLE = 3
N_ASSIM = 2
YEAR_MIN = 1992
YEAR_MAX = 1994
```

The normal output and lithology-selection settings may remain unchanged.

# File descriptions

### `mesh.grid_zones`

- First line: `number_of_nodes number_of_elements`.
- Keep fixed the second line.
- The current reader calculates `skiprows = number_of_elements + 2`.
- The first numeric block contains: `element_id`, `node_1`, `node_2`, `node_3`, `node_4`, `lithology`, `zone`.
- The final numeric block has four columns: `node_id`, `X`, `Y`, `Z`.
- This sample contains four nodes with IDs 1–4 and fictitious coordinates.

### `node_to_be_DA.xlsx`

- Sheet: `Sheet1`.
- Required column: `Node`.
- Node IDs must exist in the mesh and match the node set present in every
  solbox CSV. This sample lists nodes 1–4.

### `observations.xlsx`

- One row per observation point.
- Required coordinate columns: `X_mean` and `Y_mean`. They mean the coordinates of the measurement point.
- Year columns contain a four-digit year, for example `Y1992_mean`.
- Values represent observed annual settlement in millimetres.
- Blank cells demonstrate supported missing observations.

### `standard_deviations.xlsx`

- Point rows and coordinates must match `observations.xlsx` exactly.
- Year columns contain standard deviations, for example `Y1992_stddev`.
- Standard deviations must be finite and strictly positive wherever the
  corresponding observation is present.
- The program squares these values to form the covariance vector.

### `solbox/solboxNNN.csv`

- They are the results given by the Geomechanical model (GEPS3D).
- First column: `node`.
- Remaining columns: calendar-year labels and cumulative settlement in metres.
- Node IDs must be unique and must match `node_to_be_DA.xlsx`.
- The program converts cumulative metres to adjacent-year millimetre
  differences with:

  ```python
  vals_annual = (vals[:, 1:] - vals[:, :-1]) * 1e3
  years_annual = years[1:]
  ```

- The 1991–1994 cumulative columns therefore produce annual values for
  1992–1994.

### `cm_prior/mat_NNN`

- They are the material prior generated according to your given type of distribution.
- Files are ordered by their trailing number.
- The reader skips the header and reads the second token from the next four
  rows as Gravel, Sand, Silty, and Clay Cm values.
- The remaining material rows are included to illustrate the original
  three-zone file layout but are not read by the current Cm reader.
- `mat_mean` demonstrates a non-ensemble summary file. It sorts after numbered
  files and is excluded when `N_ENSEMBLE = 3`.
