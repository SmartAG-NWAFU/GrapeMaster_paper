# `diseasemodel` repository guide

## 1. What this repository is

`diseasemodel` is the analytical risk service used by GrapeMaster's backend. It exposes one FastAPI endpoint that accepts a complete crop-season simulation request and returns date-aligned disease infection categories, persistent disease-risk states, field-level risk, fungicide protection dates, and treatment recommendations.

Despite the repository name, this is not a trained machine-learning model or an image classifier. It is a stateful-in-memory execution of epidemiological equations, interpolation tables, rolling windows, and management rules. Each request supplies all weather, phenology, susceptibility, and fungicide-history data needed for a simulation; the service has no database and persists nothing itself.

The operationally relevant path is grapevine (`VITVI`) with:

- `PLASVI`: grapevine downy mildew, *Plasmopara viticola*;
- `UNCINE`: grapevine powdery mildew, *Erysiphe necator*.

Other crop and disease directories are mostly inherited or unfinished scaffolding and should not be interpreted as deployable support without repair and validation.

## 2. Position in GrapeMaster

The service sits between backend data preparation and backend business workflows:

```text
Weather service + phenology model + crop metadata + treatment history
                              │
                              ▼
                     grape_backend (Django)
              builds one crop-season request body
                              │
                   POST /disease/simulate
                              ▼
                    diseasemodel /simulate
         weather suitability → disease state → field risk
                 → protection and treatment windows
                              │
                              ▼
                     grape_backend persists
      RB request payloads, DiseaseData, notifications, and tasks
                              │
                              ▼
                     grape_frontend displays
        risk timelines, warnings, spraying windows, and tasks
```

The checked-in FastAPI route is `/simulate`. The Django backend calls `http://118.89.50.72/disease/simulate`, so the `/disease` prefix is supplied by deployment routing or a reverse proxy rather than by this application.

## 3. Runtime entry point

[`diseasemodel/main.py`](diseasemodel/main.py) creates a FastAPI application and registers `POST /simulate`.

The handler:

1. validates the JSON body as `CropSeasonInputs`;
2. converts the Pydantic object back to a dictionary;
3. constructs `CropSeason`;
4. calls `simulate_requested_features()`;
5. returns a dictionary of requested result arrays.

There is no authentication, authorization, health endpoint, job queue, persistence layer, or explicit exception mapping. Model exceptions therefore surface as request failures. When run directly, Uvicorn listens on `0.0.0.0:5002` with reload enabled.

## 4. Source layout

```text
diseasemodel/
├── main.py                         FastAPI entry point
├── crop_season/
│   ├── crop_season_input.py        Pydantic request schema
│   └── crop_season.py              Request orchestration and response formatting
├── crops/
│   ├── crop.py                     Abstract crop and field-risk aggregation rule
│   ├── disease.py                  Generic disease favorability calculations
│   ├── VITVI/                      Grapevine implementation and configuration
│   │   └── diseases/
│   │       ├── config.py           Disease parameters and category thresholds
│   │       ├── VITVI_disease.py    Onset, risk, and fungicide-aware grape logic
│   │       ├── PLASVI.py           Downy mildew adapter
│   │       └── UNCINE.py           Powdery mildew weather adapter
│   └── MABSD/                      Incomplete apple scaffolding
├── models/
│   ├── disease/magarey.py          Generic temperature/wetness equation
│   ├── disease/powdery_mildew.py   Powdery-mildew weather equation
│   ├── disease/primary_infection.py Incomplete primary-infection prototype
│   └── phenology/                  Thermal-calculation helpers
├── management/fungicide.py         Protection, recommendations, and windows
├── weather/                        Weather wrapper and download/conversion tool
├── utilities/                      Legacy maps and model-configuration tools
├── test/                           Requests, responses, scripts, and one unit test
├── requirements.txt                Pinned Python runtime packages
├── dockerfile                      Python 3.11 container definition
└── docker_build.sh / docker_init.sh Image build and start helpers
```

The repository contains about 8,000 lines of Python, but much of that total belongs to legacy mapping utilities and bounding-box data. The main execution path is concentrated in `crop_season.py`, the `VITVI` crop/disease classes, `magarey.py`, `powdery_mildew.py`, and `fungicide.py`.

## 5. Request contract

The schema is defined in [`diseasemodel/crop_season/crop_season_input.py`](diseasemodel/crop_season/crop_season_input.py).

### Required operational inputs

| Field | Purpose in the active grape path |
|---|---|
| `growth_stage` | One row per day with date, principal BBCH stage, GDD, cumulative GDD, and one-digit BBCH |
| `weather_hourly` | Hourly timestamp, air temperature, relative humidity, precipitation, dew point, and wind speed |
| `variety_susceptibility` | Disease-specific susceptibility group, normally keyed by `PLASVI` and `UNCINE` |
| `stress_eppo_codes` | Disease modules to instantiate dynamically |
| `applied_fungicides` | Target disease, application date, efficacy fields, and protection durations |
| `crop_establishment` | Calculation lower bound, normally January 1 of the crop year |
| `request_datetime` | Reference day used in protection-time output |
| `requested_features` | Output names and per-output date ranges |

### Context fields

The schema also accepts `crop_season_uuid`, `province`, `crop_eppo_code`, `cultivation_method`, `time_zone`, latitude, longitude, and optional daily weather.

In the current calculations:

- `crop_eppo_code` chooses the crop class;
- `province` chooses a configuration overlay;
- coordinates are stored on the weather wrapper but do not modify equations;
- `crop_season_uuid`, `cultivation_method`, and `time_zone` are not used;
- daily weather is not used by the two active grape disease modules.

The Django caller relies on the default `crop_season_uuid = "xx"` rather than passing the actual crop UUID. This does not change results because the service does not use or return that identifier.

### Weather and date assumptions

The weather wrapper parses timestamps without applying `time_zone`. The active model expects one growth-stage record for every simulated date and enough hourly data to cover the calculation period. Onset logic additionally asserts that hourly weather begins no later than January 1 of the establishment year.

`CropSeason` defines the usable season as the intersection of its inputs:

```text
season start = latest available start among growth stage and weather inputs
season end   = earliest available end among growth stage and weather inputs
```

Output is then sliced again by each requested feature's `start_date` and `end_date`.

## 6. Execution and dependency order

`CropSeason.simulate_requested_features()` always executes the first four stages in order:

```text
dailyInfectionRisks
  → shortTimeAggregatedRisks
  → stressRisks
  → fieldRisks
```

It runs those stages even when the caller requests only a later management output because the stages share dependent DataFrames. It then conditionally calculates:

```text
stressProtectionTimes
actionRecommendations
treatmentWindows
```

Only requested stages are included in the response. Methods and response-formatting branches exist for `vraLimitations` and `stressEnablings`, but the dispatcher never invokes or returns them. The effective public contract is seven features, not nine.

Crop and disease implementations are loaded dynamically from the request's EPPO codes. Results are accumulated in pandas DataFrames on the per-request `CropSeason` object.

## 7. Disease-risk calculation

### 7.1 Daily weather favorability

For downy mildew and the generic grape path, the service uses the Magarey temperature/wetness model:

1. calculate mean daily temperature from hourly values;
2. calculate a beta-shaped temperature favorability between disease-specific minimum, optimum, and maximum temperatures;
3. count hours above the relative-humidity threshold as wetness hours;
4. adjust required wetness duration according to temperature;
5. return favorability in `[0, 1]`, or zero when conditions are unsuitable.

For powdery mildew, a specialized function instead multiplies temperature favorability by a rainfall correction on rainy days or a mean-relative-humidity correction on dry days.

### 7.2 Phenology and variety corrections

Daily weather favorability is multiplied by interpolated modifiers:

```text
raw favorability
  = weather favorability
  × BBCH-stage favorability
  × variety-susceptibility factor
```

Variety groups 1, 5, and 9 map to factors 0.8, 1.0, and 1.2, with interpolation between them. Growth-stage factors are disease-specific lookup curves.

For the base/downy implementation, the fungicide factor is also multiplied into favorability. The powdery override calculates fungicide factors but does not multiply them into daily or rolling favorability; protection is applied later when deriving stress risk.

### 7.3 Daily and rolling categories

Continuous values are multiplied by 100 and mapped to symbolic categories. Both active diseases use these daily thresholds:

| Favorability | `infectionCode` |
|---|---|
| `[0, 20)` | `UNFAVORABLE` |
| `[20, 40)` | `FAVORABLE` |
| `[40, 300)` | `OPTIMAL` |

Short-term risk is a rolling mean with disease-specific windows:

| Disease | Window | Unfavorable | Favorable | Optimal |
|---|---:|---:|---:|---:|
| `PLASVI` | 7 days | `<20` | `20–<50` | `≥50` |
| `UNCINE` | 10 days | `<30` | `30–<70` | `≥70` |

`dailyInfectionRisks` is the raw daily category. `shortTimeAggregatedRisks` is the rolling category. Neither is the final persistent risk displayed by the platform.

### 7.4 First-infection/onset process

Before deriving `stressRisks`, both active disease objects run a process-based primary-inoculum calculation:

1. estimate overwintering inoculum from cold-day count;
2. accumulate wet-temperature conditions until maturation;
3. release a fraction of available inoculum on rain events;
4. combine inoculum with weather, variety, and growth-stage favorability;
5. define onset as the first day with a positive infection-event value.

Before onset, risk is forced to `UNFAVORABLE`. Outside the configured BBCH limits it is `NOT_SEASONAL`.

The same generic onset implementation is inherited by downy and powdery mildew here. In the manuscript, the independently evaluated first-infection component is specifically the downy-mildew FSIM-S configuration; that validation should not be generalized to powdery mildew.

### 7.5 Fungicide protection

Applications are filtered by target EPPO code. During preventive, curative, or eradicative duration, the implementation calculates an effect multiplier below 1. A non-seasonal day remains `NOT_SEASONAL`; otherwise an active effect changes final stress to `PROTECTED`.

Although the request requires `preventive_efficacy` and `curative_efficacy`, the effect calculation ignores row-specific values. It uses fixed defaults—0.95 preventive, 0.5 curative, and 0.5 eradicative—and uses records mainly for dates, target, and durations. The Pydantic input model does not expose eradicative fields; `CropSeason` injects a false/default value, so the eradicative branch cannot normally be activated through the validated API request.

`stressProtectionTimes` reports the latest end date obtained from curative or preventive durations for each disease. It returns an empty array when there are no applications.

### 7.6 Persistent long-range disease state

The rolling category, onset/season restrictions, and protection first produce daily `stress_risk`. `calculate_stress_risk_long_range()` then gives risk memory:

- escalation is accepted immediately;
- ordinary decreases are held at the previous higher state;
- `PROTECTED` may end without being held indefinitely;
- `NOT_SEASONAL` is never overwritten;
- after ten consecutive `OPTIMAL` days, a lower raw state may reset persistent risk if none of the preceding ten days contains a target-specific spray.

This ten-day reset is the repository's most recent focused change and is covered by the only assertion-based unit test.

## 8. Field risk and management recommendations

### Field risk

For each date, the crop aggregates disease states using:

```text
NOT_SEASONAL < UNFAVORABLE < FAVORABLE < OPTIMAL < PROTECTED
```

Protection is special: all diseases protected gives `PROTECTED`; protected plus a favorable/optimal unprotected disease uses the unprotected risk; protected plus only unfavorable/not-seasonal alternatives remains `PROTECTED`; otherwise the highest disease risk wins.

### Recommendations and windows

Only `OPTIMAL` field risk directly maps to:

```text
recommendationCode = RECOMMENDED
actionTypeCode      = TREAT
```

Other states initially map to `NOT_NEEDED` and `NO_ACTION`. Starting from the first optimal day, the algorithm creates:

| Window | Default interpretation |
|---|---|
| `FUTURE` | Four-day early warning before the optimal day |
| `CURRENT` | Five-day interval beginning on the optimal day |
| `MISSED` | The interval passed while persistent risk remains relevant |
| `NOT_PRESENT` | No active treatment window |

Missed days change to `recommendationCode = NECESSARY`. The algorithm can create later windows if another optimal period occurs. `actionRecommendations` and `treatmentWindows` are projections of the same field-level DataFrame and should align with `fieldRisks` by date.

## 9. Active parameter summary

| Parameter | Downy mildew `PLASVI` | Powdery mildew `UNCINE` |
|---|---:|---:|
| Min / optimum / max temperature | 1 / 20 / 30 °C | 10 / 26 / 35 °C |
| Humidity/wetness approach | RH >92%; 2–14 h requirement | RH correction when dry; rainfall suppression when wet |
| BBCH risk limits | 9–99 | 11–89 |
| Rolling period | 7 days | 10 days |
| Latent-duration parameter | 6 days | 6 days |
| Config development status | `in_progress` | `in_progress` |
| Config validation metadata | Guang Xi: `not_validated` | Global: `none` |

The `Guang Xi` downy-mildew configuration overrides metadata only, not numerical parameters in `config.py`. The manuscript's calibration data and reported validation metrics are not reproduced by tests or calibration scripts inside this nested repository.

## 10. Response contract

| Feature | Row shape | Meaning |
|---|---|---|
| `dailyInfectionRisks` | `referenceDate`, `stressId`, `infectionCode` | Daily environmental/host infection suitability |
| `shortTimeAggregatedRisks` | `referenceDate`, `stressId`, `infectionCode` | Disease-specific rolling suitability |
| `stressRisks` | `referenceDate`, `stressId`, `riskCode` | Onset-, season-, protection-, and memory-adjusted disease risk |
| `fieldRisks` | `referenceDate`, `riskCode` | Combined state across requested diseases |
| `stressProtectionTimes` | `referenceDate`, `stressId`, `protectionEndDate` | Latest duration-based protection end |
| `actionRecommendations` | `referenceDate`, `recommendationCode`, `actionTypeCode` | Field-level treatment decision |
| `treatmentWindows` | `referenceDate`, `treatmentWindowCode`, `treatmentStartDate`, `treatmentEndDate` | Future/current/missed timing |

Disease-level outputs are concatenated disease by disease, not interleaved by date. With `stress_eppo_codes = ["PLASVI", "UNCINE"]`, all downy rows precede all powdery rows. The Django integration depends on that order and assumes both diseases return the same number of dates.

The model returns symbolic states rather than probabilities. `OPTIMAL` means modelled conditions and state rules are optimal for disease risk; it is not a calibrated probability of observed disease or a guarantee that infection will occur.

## 11. Backend and frontend integration

The Django backend builds requests from:

- hourly weather retrieved and transformed for field coordinates;
- daily phenology results converted into `startGrowthStage` rows;
- variety-specific downy- and powdery-mildew susceptibility scores;
- completed plant-protection products converted to dates and durations;
- a horizon from January 1 through about 15 days beyond the current date.

It normally requests daily infection risk, stress risk, field risk, protection time, recommendations, and treatment windows. It saves request and response bodies in crop-linked `RB` and `DiseaseData` records. Scheduled and task-related paths rerun the service after treatment history changes.

The backend creates Chinese alerts and reminders from treatment windows and current `PLASVI`/`UNCINE` states. Flutter retrieves the persisted summaries through `/diseasedata/list/crop/<crop_uuid>` and related weather/task APIs; it does not call `diseasemodel` directly.

This separation matters for traceability: `diseasemodel` calculates rows but does not retain crop identity, requests, results, notifications, tasks, or feedback links. Those are backend/database responsibilities.

## 12. Running the service

### Local Python

The pinned stack includes FastAPI 0.100, Pydantic 2.1, pandas 2.0, and NumPy 1.25.

```bash
cd diseasemodel
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Then submit the full example:

```bash
curl -X POST http://127.0.0.1:5002/simulate \
  -H 'Content-Type: application/json' \
  --data-binary @test/grape_rb.json
```

That request contains 5,856 hourly weather rows and 273 growth-stage rows.

### Docker

```bash
./docker_build.sh
./docker_init.sh
```

The image uses Python 3.11, installs from the Aliyun PyPI mirror, copies the repository to `/diseasemodel`, and starts `python main.py`. The run script publishes port 5002.

For production, remove reload mode, add a worker/process strategy, and put request limits, authentication, TLS, and health checks at the service or gateway layer.

## 13. Tests and reproducibility

The test tree mixes several artifact types:

- `test/test_stress_risk_reset.py`: five assertion-based tests for ten-day reset and downstream field/recommendation effects;
- `test/test_grape.py`: a live HTTP caller requiring a running service;
- `test/GXG-233/test_grape.py`: live callers that overwrite recorded responses;
- `test/mingyang/src/test_grape.py`: direct simulation and figure generation;
- `test/duan/` and `test/yangling/`: exploratory scripts and spreadsheets;
- checked-in request/response JSON: useful fixtures, but not automatically compared.

`pytest` is absent from `requirements.txt`. In the inspected environment, Python 3.13.3 had none of the service packages or `pytest`, so runtime tests could not be executed. A read-only syntax pass parsed 63 UTF-8 Python files; the apple configuration could not be decoded as UTF-8.

A reproducible setup should pin a supported Python version, add test dependencies, convert manual scripts into assertions, and compare API output against approved golden files without rewriting them during normal tests.

## 14. Incomplete and inactive areas

The file tree advertises more capability than the standalone service provides:

- grape diseases `BOTRCI`, `ELSIAM`, and `GUIGBI` import the absent old `ompd.*` package namespace;
- their configs omit onset/protection keys required by `VITVIDisease.__init__`;
- apple disease classes also use `ompd.*` imports;
- `crops/MABSD/diseases/config.py` contains non-UTF-8 bytes without an encoding declaration;
- `MABSD` lacks stress-risk, field-risk, and management methods expected by the dispatcher;
- insect support searches a path from the original larger project;
- irrigation and fertilizer modules are empty;
- the generic primary-infection class has unfinished methods;
- mapping/database utilities require undeclared packages and the historical namespace.

Operational support should therefore be stated as `VITVI` + `PLASVI`/`UNCINE`, with the manuscript's validated claim limited further to downy-mildew first infection.

## 15. Important technical and scientific risks

1. **Input-controlled dynamic imports:** crop and disease codes are interpolated into module paths without an allowlist; the endpoint also accepts arbitrarily large arrays.
2. **No service safeguards:** there are no request limits, rate limits, timeouts, authentication checks, or structured domain errors.
3. **Async route with synchronous work:** pandas-heavy simulation runs directly inside an `async` handler and can block the event loop.
4. **Implicit ordering contract:** Django uses array offsets rather than joining by disease and date. Missing rows or target reordering can silently misassign results.
5. **Fragile dates:** timezone is ignored, growth-stage lookup expects exactly one matching row per day, and calculations assume consecutive data.
6. **Efficacy mismatch:** application-specific efficacy values are required by the API but ignored by the effect calculation.
7. **Disease inconsistency:** downy favorability includes fungicide multiplication; powdery favorability does not, although both later use `PROTECTED`.
8. **Shared onset mechanism:** both active diseases inherit one primary-inoculum process, while manuscript validation supports downy mildew only.
9. **Parameter provenance:** config labels models `in_progress`/not validated, and Guangxi has no numerical overrides here. Calibration evidence is external.
10. **Mutable configuration:** province overrides update the selected global dictionary in place, allowing future numeric overrides to leak between instances.
11. **Repository residue:** old namespaces, path injection, generated bytecode, `.DS_Store`, datasets, figures, and binary workbooks are committed.
12. **Committed credentials:** tracked `utilities/.env` contains database connection values. Treat them as exposed, rotate them, and inject secrets instead.
13. **Weak coverage:** weather equations, onset logic, thresholds, fungicide effects, filtering, API validation, and full output lack regression tests.

## 16. Relationship to the manuscript

The repository implements the analytical service boundary described in `paper/manuscript_S.pdf`:

- backend-supplied weather, phenology, susceptibility, and treatment history form one crop-season request;
- the service returns date-aligned risk, protection, and treatment-window states;
- completed fungicide records alter later `PROTECTED` states;
- backend consumers convert results into warnings, tasks, and stored records.

The manuscript reports a validation MAE of 6.3 days and RMSE of 6.5 days for the Guangxi FSIM-S downy-mildew first-infection configuration. Those are offline validation results, not runtime API output, and their derivation scripts/data are not in the nested `diseasemodel` repository. Notification delivery, task execution, linkage, and crop-season traceability are likewise platform/backend properties rather than functions of this stateless service.

| Manuscript concept | Repository implementation |
|---|---|
| Crop-season analytical interface | `CropSeasonInputs` and `CropSeason` |
| Hourly weather input | `Weather` plus backend-prepared rows |
| Infection suitability | Magarey and powdery-mildew equations |
| FSIM-S first-infection warning | Inoculum maturation/release/onset path, principally `PLASVI` |
| Phenology/susceptibility context | Daily BBCH and interpolation modifiers |
| Protection feedback | `FungicideEffects` and `PROTECTED` state |
| Treatment windows | `Fungicide.fungicide_spray_recommendation()` |
| Workflow traceability | Django records and identifiers, not this repository |

## 17. Recommended reading order

1. `main.py` for the service surface;
2. `crop_season/crop_season_input.py` for the request;
3. `crop_season/crop_season.py` for orchestration and response shapes;
4. `crops/VITVI/VITVI.py` and `crops/crop.py` for dispatch and field risk;
5. `crops/VITVI/diseases/config.py` for parameters and thresholds;
6. `crops/VITVI/diseases/VITVI_disease.py` for onset, protection, and persistent risk;
7. `crops/VITVI/diseases/UNCINE.py` for powdery-mildew differences;
8. `models/disease/magarey.py` and `powdery_mildew.py` for weather equations;
9. `management/fungicide.py` for recommendations and windows;
10. `test/test_stress_risk_reset.py` and recorded request/response files;
11. Django `weatherdata` and `task` callers for production integration.

This follows the real data path: API contract → crop-season orchestration → disease equations → management state → platform consumption.
