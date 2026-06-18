# ES-MDA Subsidence Data Assimilation

## Attention!!!
This workflow is only suitable for those who are using GEPS3D developed by dICEA-Unipd

## Description
A modular Python workflow for assimilating observed land-subsidence data into
an ensemble of geomechanical simulations with the Ensemble Smoother with
Multiple Data Assimilation (ES-MDA).

The repository contains both the original single-file implementation and a
behavior-preserving modular refactor. A dedicated comparison runner verifies
the observation vector, simulated responses, covariance, prior parameters,
every ES-MDA update, posterior files, and rendered figures between both
implementations.

## Features

- Reads observation and uncertainty tables from CSV or Excel.
- Maps observation coordinates to mesh nodes with `scipy.spatial.cKDTree`.
- Reads ensembles of `solboxNNN.csv` settlement simulations.
- Converts cumulative settlement in metres to adjacent-year differences in
  millimetres.
- Reads Gravel, Sand, Silty, and Clay prior `Cm` parameters.
- Runs deterministic multi-round ES-MDA with a fixed seed.
- Exports posterior parameter ensembles and diagnostic figures.
- Provides strict original-versus-refactored consistency testing.

## Repository structure

```text
.
├── ESMDA_assimilate_solbox_covariance.py  # Original single-file workflow
├── data_assimilation/
│   ├── main.py                 # Refactored entry point
│   ├── config.example.py       # Configuration template
│   ├── io_utils.py             # CSV/Excel and path helpers
│   ├── observation.py          # Observation ordering and Y_model assembly
│   ├── mesh_mapping.py         # Mesh loading and nearest-node matching
│   ├── simulation_reader.py    # Solbox CSV/POT readers
│   ├── parameter_reader.py     # Prior Cm matrix reader
│   ├── covariance.py           # Observation covariance construction
│   ├── transforms.py           # Normal-score and ECDF helpers
│   ├── forward_model.py        # Forward-model boundary
│   ├── assimilation.py         # ES-MDA loop
│   ├── plotting.py             # Figures and posterior export
│   └── comparison.py           # Debug/comparison checkpoint storage

```

## Requirements

- Python 3.10+
- NumPy
- pandas
- SciPy
- Matplotlib
- openpyxl
- `iterative_ensemble_smoother`

## Input data

### Observation table

CSV, XLS, or XLSX with one row per observation point. Required coordinate
columns are `X_mean` and `Y_mean` by default. Observation columns must contain
a four-digit year, for example `Y2018_mean`. Missing values may be `NaN`.

### Standard-deviation table

CSV, XLS, or XLSX with the same point order, coordinates, and years as the
observation table. Values are interpreted as standard deviations and converted
to variances with:

```python
covariance_vec = std_vec ** 2
```

### Mesh grid

The first line must contain the value used by the original reader to calculate:

```python
skiprows = int(second_header_token) + 2
```

The resulting numeric table must contain node ID, X, Y, and Z columns.

### Node workbook

An Excel file containing a `Node` column with candidate 1-based mesh node tags.

### Solbox ensemble

Files must be named numerically:

```text
solbox001.csv
solbox002.csv
...
solbox100.csv
```

The first column contains unique mesh node IDs. Remaining columns contain
calendar-year labels such as `1991.0` and cumulative settlement values in
metres. The active conversion is intentionally preserved:

```python
vals_annual = (vals[:, 1:] - vals[:, :-1]) * 1e3
years_annual = years[1:]
```

### Prior material files

Prior files are numerically sorted (`mat_001`, ..., `mat_100`). The reader skips
the header and reads the second token from the next four rows as:

1. Gravel
2. Sand
3. Silty
4. Clay

The final material matrix has shape `(4, n_ensemble)`: parameter types are rows
and ensemble members are columns. Files without trailing digits, such as
`mat_mean`, are sorted last and are not included in the default 100-member run.

## Configuration

Create your local configuration after cloning the repository:

```bash
cp data_assimilation/config.example.py data_assimilation/config.py
```

`data_assimilation/config.py` is intentionally ignored by Git because it may
contain machine-specific or private paths. The public `config.example.py`
contains the complete supported configuration interface and portable example
defaults.

All paths and global settings are centralized in the local `config.py`. Edit
that file or override paths with environment variables:

```bash
export ESMDA_MESH_GRID_FILE=/path/to/mesh.grid_zones
export ESMDA_NODE_FILE=/path/to/node_to_be_DA.xlsx
export ESMDA_OBS_FILE=/path/to/observations.xlsx
export ESMDA_COVARIANCE_FILE=/path/to/standard_deviations.xlsx
export ESMDA_POT_DIR=/path/to/solbox_directory
export ESMDA_MAT_DIR=/path/to/cm_prior_directory
export ESMDA_RESULTS_DIR=/path/to/results
export ESMDA_FIGURES_DIR=/path/to/results/Figures
```

Optional numerical settings:

```bash
export ESMDA_N_ENSEMBLE=100
export ESMDA_ROUNDS=3
export ESMDA_YEAR_MIN=1900
export ESMDA_YEAR_MAX=2099
```

The current ES-MDA seed is `1688` and the inversion method is `subspace`.

## Run the workflow

From the repository root:

```bash
python -m data_assimilation.main
```

Equivalent direct entry:

```bash
python data_assimilation/main.py
```

From inside `data_assimilation/`:

```bash
python main.py
```

## Algorithm ordering

Observation values are expanded in source point-row order and then ascending
year order within each point. `NaN` records and years absent from the simulation
axis are skipped.

`Y_model` follows exactly the same point/year plan, with one column per ensemble
member. The covariance vector is extracted with the identical ordering. These
ordering rules are critical and covered by automated tests.

The current update remains in the physical parameter matrix:

```python
X_curr_log = smoother.assimilate(X_curr_log, Y=Y_curr)
X_curr = X_curr_log
```

## Outputs

The workflow generates:

- `ESMDA_K_posterior_lineara2.csv`
- `ESMDA_K_posterior_z.csv`
- Per-round parameter scatter plots
- Per-round empirical CDF plots
- Final prior/posterior comparison figures
- Printed shape and variance diagnostics for each assimilation round

## Current limitations

- Normal-score transforms are calculated for diagnostics and figures, but
  `Z_curr` is not the actual assimilation space.
- No explicit positivity constraint, clipping, bounds, or positive transform is
  active, despite wording in the original script header.
- The material reader uses fixed file-line positions and does not validate the
  trailing material labels.
