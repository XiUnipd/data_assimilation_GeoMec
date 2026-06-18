# ES-MDA data assimilation

This package is a modular refactor of
`ESMDA_assimilate_solbox_covariance.py`. It preserves the original numerical
ordering, units, ES-MDA update call, diagnostics, figures, and posterior CSV
layout.

## Modules

- `main.py`: single entry point and workflow orchestration.
- `config.py`: paths, ensemble count, year range, ES-MDA settings, and outputs.
- `io_utils.py`: common CSV/Excel loading and path validation.
- `observation.py`: year-column detection and ordered observation/`Y_model` assembly.
- `mesh_mapping.py`: mesh loading and `cKDTree` nearest-node matching.
- `simulation_reader.py`: solbox CSV/POT reading, node alignment, and annual differences.
- `parameter_reader.py`: Gravel, Sand, Silty, and Clay prior Cm loading.
- `covariance.py`: observation-aligned standard-deviation/variance vector construction.
- `transforms.py`: flattening, normal-score transforms, and empirical CDF helpers.
- `forward_model.py`: current fixed forward-model wrapper.
- `assimilation.py`: shape checks and iterative ES-MDA updates.
- `plotting.py`: round/final figures and posterior CSV export.
- `comparison.py`: opt-in checkpoint persistence for consistency tests.

## Configure paths

Create a local configuration from the public template:

```bash
cp config.example.py config.py
```

The local `config.py` is Git-ignored because it may contain private paths.
Paths are defined using `pathlib.Path`; edit the local file or override them
with environment variables such as:

```bash
export ESMDA_MESH_GRID_FILE=/path/to/mesh.grid_zones
export ESMDA_NODE_FILE=/path/to/node_to_be_DA.xlsx
export ESMDA_OBS_FILE=/path/to/observations.xlsx
export ESMDA_COVARIANCE_FILE=/path/to/std.xlsx
export ESMDA_POT_DIR=/path/to/solbox_csv_directory
export ESMDA_MAT_DIR=/path/to/cm_prior_directory
export ESMDA_RESULTS_DIR=/path/to/results
export ESMDA_FIGURES_DIR=/path/to/results/Figures
export ESMDA_ROUNDS=5
```

## Run

From inside this directory:

```bash
python main.py
```

From the repository root, the equivalent commands are:

```bash
python data_assimilation/main.py
python -m data_assimilation.main
```

## Input files

- **Observation Excel/CSV**: rows are observation points; columns include
  `X_mean`, `Y_mean`, and headers containing four-digit years. Missing yearly
  records may be `NaN`. If a year appears more than once, the first matching
  column is used.
- **Covariance/std Excel/CSV**: same point rows, coordinates, and year coverage
  as the observation table. Year columns contain standard deviations, not
  variances.
- **Mesh grid**: the second token on the first line defines the original
  `skiprows = int(token) + 2` calculation. The loaded numeric rows must contain
  node ID, X, Y, and Z columns.
- **Node Excel**: contains a `Node` column listing the candidate 1-based mesh
  node tags used for nearest-neighbour matching.
- **Solbox CSV**: named `solbox001.csv`, `solbox002.csv`, etc. The first column
  contains unique node IDs; remaining columns contain calendar-year labels such
  as `1991.0` and cumulative settlement values in metres. CSV node IDs must
  match the node workbook and belong to the mesh.
- **Cm prior files**: numerically suffixed files such as `mat_001` through
  `mat_100`. After one header line, the second token of the next four lines is
  read as Gravel, Sand, Silty, and Clay Cm respectively.

## Current algorithm

Observation records are expanded in source point-row order and, within each
point, ascending year order. `NaN` records and years absent from the simulation
axis are skipped.

Solbox rows are aligned to mesh-node order. Cumulative settlement is converted
from metres to millimetre differences without changing the original formula:

```python
vals_annual = (vals[:, 1:] - vals[:, :-1]) * 1e3
years_annual = years[1:]
```

`Y_model` uses the same point/year plan as the observation vector and stores one
column per ensemble member. The covariance vector follows that identical plan;
input standard deviations are converted to variances with `std_vec ** 2`.

ES-MDA uses the configured number of rounds, seed `168`, and `subspace`
inversion. Each round retains the original physical-space update:

```python
X_curr_log = smoother.assimilate(X_curr_log, Y=Y_curr)
X_curr = X_curr_log
```

## Current limitations

- The forward model does not rerun the external numerical simulator after Cm
  updates. Every ES-MDA round currently reuses the precomputed prior `Y_model`.
- Normal-score transforms are calculated for diagnostics and figures, but
  `Z_curr` is not the actual assimilation space.
- Despite the source title mentioning a positive limitation, the active
  algorithm contains no clipping, bounds, transform, or other positive-value
  constraint. This refactor does not invent one.

## Original/refactored consistency check

The comparison runner executes the original script and refactored entry in
separate processes with identical inputs, ensemble count, ES-MDA rounds, seed,
inversion, and Matplotlib backend. It compares preprocessing arrays, every
round posterior, final CSV values, diagnostics, and rendered PNG pixels.

```bash
python tests/compare_original_vs_refactor.py \
  --output-dir comparison_outputs/production_100 \
  --n-ensemble 100 \
  --n-assim 5 \
  --memmap
```

`--memmap` changes only comparison-mode storage: the unchanged dense simulation
ensemble is held in a temporary disk-backed NumPy array to avoid a roughly
11 GB RAM allocation. Normal runs do not use this mode. Comparison checkpoints
are enabled only through `ESMDA_COMPARISON_MODE=1` and are written beneath the
configured `ESMDA_COMPARISON_OUTPUT_DIR`.

All three debug switches are parsed centrally in the clearly marked
`DEBUG / COMPARISON MODE` section of `config.py`. Comparison mode defaults to
off:

```bash
export ESMDA_COMPARISON_MODE=1
export ESMDA_COMPARISON_OUTPUT_DIR=/path/to/comparison_outputs
export ESMDA_COMPARISON_MEMMAP=1
```
