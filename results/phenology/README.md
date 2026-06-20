# Phenology module calibration and validation outputs

This folder contains the conservative calibration and validation outputs for the
GrapeMaster phenology support module.

## Purpose

The phenology module is evaluated as a platform-supporting crop-stage component,
not as a standalone phenology-model contribution. Its role in the manuscript is
to support crop-season state interpretation and disease-risk timing.

## Data and preprocessing

- Source data: `model_moudle/grape_bbch/standalone_phenology/data/growth_stage_data.xlsx`
- Raw rows: 561
- Valid phenology observations: 151
- Independent site-year units: 6
- First-observed BBCH events after removing repeated same-stage records: 67
- Supported BBCH transition events present in the platform threshold table: 47
- Management-stage events after excluding early-season initial states: 14

Variety mapping used by the script:

- `wk` -> `温克`, maturation `晚`
- `JF` -> `巨峰`, maturation `中`
- `MPT` -> `毛葡萄野酿2号`, maturation `晚`

## Validation design

The script keeps the platform thermal response parameters fixed
(`Tbase=10`, `Topt=30`, `Tcei=42`) and recalibrates only Guangxi BBCH-GDD
thresholds under monotonic constraints. Thresholds are updated only for stages
with at least two training observations.

Validation uses leave-one-site-year-out cross-validation. Reported metrics are
MAE, RMSE, bias, and the proportion of matched events within seven days.

## Interpretation

The all-data conservative calibration reduces resubstitution error, but strict
leave-one-site-year-out validation does not show stable transfer improvement.
These outputs support transparent regional checking and boundary definition for
the platform phenology module. They should not be presented as strong
cross-site generalization evidence.
