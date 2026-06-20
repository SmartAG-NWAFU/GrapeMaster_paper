# Phenology full-stage calibration v2

This analysis treats the GrapeMaster phenology module as a standalone
temperature-driven BBCH-stage predictor. It is separate from the conservative
platform-support analysis in `results/phenology/`.

## Method

- Source data: `model_moudle/grape_bbch/standalone_phenology/data/growth_stage_data.xlsx`
- Effective events: first-observed BBCH stages by site-year-variety, excluding BBCH 00.
- Observed stages used: 01, 05, 07, 14, 15, 17, 18, 53, 55, 57, 60, 61, 62, 63, 68, 71, 73, 75, 76, 77, 79, 81, 83, 85, 89, 99.
- Thermal framework: Wang-Engel response, with calibrated `Tbase`, `Topt`, and `Tcei`.
- Threshold framework: full observed BBCH-stage thresholds, initialized from platform thresholds plus interpolation and constrained to be monotonic.
- Model variants:
  - `baseline_interpolated`: platform thermal parameters and interpolated thresholds for observed stages.
  - `pooled_calibrated`: shared thermal parameters and shared full-stage thresholds.
  - `cultivar_offset_calibrated`: pooled model plus cultivar-level GDD threshold offsets.
- Validation: grouped 3-fold cross-validation by site-year, with resubstitution reported only as fitting diagnostics.

## Main results

The current conservative run is:

- `results/phenology_v2_3fold/`: offset limit +/-150 GDD, grouped 3-fold validation.

Older sensitivity outputs using leave-one-site-year-out validation remain in
`results/phenology_v2/` and `results/phenology_v2_offset150/`. They are retained
as historical runs, but the 3-fold output is the preferred result because it is
faster and less dominated by very small single-site-year test folds.

3-fold exact-BBCH MAE:

- Baseline: 29.1 days.
- Pooled calibrated: 26.7 days.
- Cultivar-offset calibrated: 23.9 days.

3-fold major-stage first-date MAE:

- Baseline: 23.6 days.
- Pooled calibrated: 25.9 days.
- Cultivar-offset calibrated: 26.0 days.

3-fold major-stage state agreement on observed dates:

- Baseline: 27.9%.
- Pooled calibrated: 33.3%.
- Cultivar-offset calibrated: 36.7%.

## Interpretation

The v2 calibration reduces exact BBCH timing error relative to the baseline, and
the cultivar-level offsets provide additional improvement over the pooled shared
model. However, the broader major-stage first-date metric does not improve in
3-fold validation, and major-stage agreement remains moderate. The result is
therefore best interpreted as a transparent, data-limited platform-support
calibration rather than as a standalone regional phenology model claim.
