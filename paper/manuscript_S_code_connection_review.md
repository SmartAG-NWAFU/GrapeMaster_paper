# GrapeMaster manuscript-to-implementation connection review

## Sources reviewed

- `paper/manuscript_S.pdf` and `paper/manuscript_S.tex`
- `CEA_scrope.md`
- `grape_backend_readme.md`
- `grape_frontend_readme.md`
- `diseasemodel_readme.md` and `diseasemodel/README.md`
- Selected backend models, serializers, scheduled workflows, and advisory code

The generic `README.md` files inside `grape_backend/` and `grape_frontend/` are
repository-host boilerplate. The root-level backend and frontend guides are the
useful implementation descriptions.

## Main conclusion

The implementation supports a stronger and more concrete paper than a generic
"integrated application" description. Its most defensible contribution is a
model-aware operational workflow in which one crop UUID links field context,
weather and phenology payloads, disease-model requests and responses,
notifications, tasks, and treatment products. Plant-protection records are
translated into fungicide-effect parameters and can trigger disease-model
recalculation.

However, the checked-in implementation does not support every current
manuscript claim. In particular, the code does not encode an explicit crop year
or season interval in `CropSeason`; notifications and tasks share a crop UUID
but do not have a direct event-to-task foreign key; advisory messages are linked
primarily to users rather than crop seasons; and the adjacent backend does not
run the claimed ChatGLM3 advisory model. These distinctions should be made
explicit before submission.

## End-to-end implementation chain

| Workflow step | Backend implementation | Frontend implementation | Manuscript connection | Support level |
|---|---|---|---|---|
| User and field context | `CustomUser` owns `Field`; field boundaries are stored as GeoJSON and used to calculate area and centroid | Users draw a vineyard polygon in an embedded WebGIS/Leaflet view or accept a shared field | Field configuration and persistent field context | Strong |
| Crop context creation | `CropSeason` links field, cultivar, cultivation method, vine age, coordinates, and area; creation posts the new UUID to the model-data initialization endpoint | A field-level crop form creates or selects the crop workspace | Crop-centered organizational anchor | Strong as a relational anchor; partial as an annual season |
| Environmental update | A scheduled Django workflow retrieves historical and forecast weather, produces hourly/daily payloads, and calculates spray suitability | Weather and spray-suitability screens request backend payloads by crop UUID | Weather state and operational suitability | Strong |
| Phenology update | Daily mean temperature is passed to the local GDD/BBCH workflow and stored in `PhenData` under the crop UUID | The crop workspace displays current and predicted phenology | Phenological state within the crop context | Strong |
| Disease-risk calculation | The backend constructs a disease-service request containing weather, growth stage, cultivar susceptibility, target diseases, and fungicide history; the stateless FastAPI service returns infection risk, field risk, recommendations, protection time, and treatment windows | The crop workspace displays disease and field risk timelines | Disease-risk interpretation | Strong as an interface; the deployed parameter version must be reconciled with the offline FSIM-S evaluation |
| Event delivery | Risk and management events are stored as `Notification` records with a crop foreign key and can be pushed through Django Channels and SMS | REST and WebSocket clients display alerts and the notification archive | Risk/event delivery | Strong |
| Warning to task | The client can open task creation from supported warning types; protection and irrigation tasks store the same crop UUID | The task workflow collects date, status, products, equipment capacity, water volume, and mixing details | Executable field operation | Functionally supported, but the database does not retain a direct notification-to-task provenance key |
| Treatment feedback | Fungicide rows link directly to a protection task; task serializers translate product metadata into applied-fungicide effects | Product and mixing screens submit products and task completion state | Treatment feedback | Strong |
| Risk recalculation | For applicable creation/update/completion branches, the backend updates the saved disease request and asynchronously calls the disease service again | Updated risk/protection states can be displayed on the crop screen | Management-to-model feedback | Strong in code; the operational audit should show timestamps or pre/post payloads to demonstrate it in deployment |
| Field observations | Notes, incidence records, and growth-stage records have crop foreign keys | Users can submit crop notes, incidence observations, growth stages, and images | Manual observation and review branch | Strong |
| Image diagnosis | The adjacent backend contains a five-state EfficientViT classifier; the frontend also calls separately hosted classification and severity services | Users upload images, receive a classification, ask follow-up questions, and can report a disease to a field | Symptom-recognition branch | Partially supported; service identity and evaluated model version must be reconciled |
| Advisory records | The adjacent backend stores message history by user; its local WebSocket currently echoes input and its ChatGLM3 loading/inference code is commented out | The frontend calls a separately hosted advisory WebSocket | LLM-assisted advisory branch | Not established by the adjacent backend; requires documentation and code/version evidence for the external service |

## What the manuscript can claim confidently

1. A deployed Flutter-Django-PostgreSQL platform connects vineyard geometry,
   crop configuration, model payloads, notifications, tasks, products, and
   observations through stable identifiers.
2. Crop creation initializes the analytical data flow, and a scheduled workflow
   refreshes weather, phenology, disease risk, and notifications.
3. Disease-service requests are management-aware: fungicide applications are
   included in each stateless request and affect protection and risk outputs.
4. The mobile client converts model and management information into executable
   irrigation and plant-protection workflows.
5. The exported database can be audited for record coverage and contextual
   linkage.

These claims align with *Computers and Electronics in Agriculture* when the
novelty is framed as an investigator-developed, model-aware orchestration and
feedback mechanism rather than the first use of existing mobile, weather, or AI
technology in grapes.

## Claims that need correction or additional evidence

### 1. Crop season is not explicitly represented as an annual interval

The manuscript describes "annually renewed crop-season management units" and
lists crop year as crop-season metadata. The checked-in `CropSeason` model has a
UUID, field, variety, cultivation method, vine age, denormalized field
attributes, and creation/update timestamps, but no `season_year`, `start_date`,
`end_date`, or lifecycle status. The frontend calls this object `Crop` and also
has no explicit season-year field.

Before retaining the paper's central annual-season claim, provide one of the
following:

- production-schema evidence that a year/season field exists but is absent from
  this checkout;
- a documented operational rule that a new crop UUID is created for each field
  and production year, verified in the exported records; or
- a manuscript revision that calls it a "crop management context" or "crop
  instance" rather than an explicitly annual crop season.

### 2. Weather-provider statement is inconsistent

The manuscript states that weather is retrieved from Open-Meteo. The backend
code and implementation guide use the Agromodel weather service. The supplement
also lists Open-Meteo client packages. Identify the provider used during the
reported 2023-2026 deployment and make the manuscript, supplement, and data
provenance consistent.

### 3. LLM advisory claims are not supported by the adjacent backend

The manuscript identifies a fine-tuned ChatGLM3 advisory model and states that
advisory responses are generated and stored by the backend. In the checked-in
backend:

- ChatGLM3 tokenizer/model loading is commented out;
- the local recognition endpoint returns one of five classes plus hard-coded
  Chinese advice;
- the advisory WebSocket echoes the user's message;
- message records are keyed to the user, not directly to a crop UUID.

The frontend calls a different, separately hosted classification/advisory
service. If that external service is the evaluated CDIP-ChatGLM3 system, the
paper needs its repository or archived version, endpoint contract, model
checkpoint/version, deployment dates, and the exact identifier path used to
associate messages with field or crop context. Otherwise, remove or narrow the
LLM-specific claims.

### 4. Image-recognition implementation and evaluation are not yet reconciled

The adjacent backend implements five output states, while the manuscript reports
seven disease categories and class-wise F1 scores. This may be explained by the
separate service used by the frontend, but the paper must state which deployed
service and checkpoint produced the seven-class results. The evaluated model,
the deployed model, and the service shown in the architecture must be the same
version or be clearly distinguished.

### 5. Contextual linkage is not the same as causal provenance

Notifications and tasks both carry a crop UUID, but tasks do not store a
`source_notification_uuid`. Therefore, the audit can show that events and tasks
co-occurred within one crop context, not that a particular warning caused a
particular task. Similarly, task-to-product linkage is direct and much stronger
than notification-to-task linkage.

Use three explicit linkage levels in the paper:

- **direct relational linkage:** field-to-crop, crop-to-payload,
  crop-to-notification, crop-to-task, task-to-product, crop-to-note;
- **contextual linkage:** notification and task share a crop UUID and compatible
  timestamps;
- **functional code path:** the mobile warning screen can open task creation,
  and task completion can update/rerun the disease request.

Do not call the operational replay a proven event-causal chain unless the
export contains event provenance or an audit log demonstrating the transition.

### 6. Modularity and scalability should be bounded

The services are separated conceptually, but the checked-in deployment is
tightly coupled to fixed hosts, an existing database schema, local model paths,
in-process scheduling, in-memory WebSocket channels, and ad hoc thread pools.
There is no load, failover, or horizontal-scaling evaluation. "Modular service
composition" is defensible; "scalable platform" is not currently demonstrated.

### 7. The evaluated FSIM-S configuration is not reproducible from the runtime service checkout

The root disease-service guide reports that the active downy- and
powdery-mildew configurations are labelled `in_progress`, the Guangxi downy
configuration contains validation metadata but no numerical parameter override,
and the offline calibration/validation scripts that produced the reported 6.3
day MAE are outside the nested service repository. The service also supports
downy and powdery mildew operationally, while the manuscript validation supports
only the downy-mildew first-infection component.

Archive the exact deployed service commit, configuration file, calibrated
parameter file, and model checksum used during the reported audit. State clearly
whether the offline FSIM-S configuration was actually deployed or was evaluated
only as a platform-compatible module.

### 8. Fungicide effects are simpler than the prose currently implies

The request requires application-specific efficacy values, but the inspected
disease service uses fixed default preventive and curative multipliers and uses
each product record mainly for target disease, date, and duration. The paper
should not imply that product-specific efficacy is dynamically modelled unless
the deployed version differs. Describe the implemented feedback as
date-, target-, and protection-duration-aware, and document any production
version that additionally uses product-specific efficacy.

### 9. Traceability is added by Django, not by the stateless disease service

The disease-service schema accepts a crop-season UUID, but the Django caller
does not pass the actual UUID and the service does not use or return it. The
backend supplies traceability by storing the request and response in crop-linked
`RB` and `DiseaseData` rows. This is a useful architectural distinction and
should be explicit in the paper.

### 10. Authentication and privacy language needs care

JWT endpoints exist, but access control is not consistently enforced in the
checked-in backend, and many endpoints accept a phone number directly. The
frontend uses cleartext HTTP/WebSocket endpoints and stores session/context data
locally. The paper should not claim secure access control without evidence from
the deployed configuration. The ethics/privacy section should state the lawful
basis or consent process, de-identification procedure, access restrictions, and
whether location/image/message data were reviewed by an institutional body.

## Recommended manuscript changes

### Reframe the technical contribution

Recommended contribution statement:

> GrapeMaster contributes a crop-context orchestration mechanism that binds
> environmental and phenological state, disease-model inputs and outputs,
> warning delivery, field tasks, and product-level treatment feedback through
> relational identifiers and management-aware model recalculation.

This is more specific and defensible than saying the contribution is simply an
integrated collection of digital tools.

### Replace the generic implementation description with the real service chain

The implementation section should state that:

1. the Flutter client captures field geometry, selects the crop context,
   displays model state, and submits tasks and observations;
2. Django REST Framework manages relational business objects and JSON model
   payloads in PostgreSQL;
3. crop creation initializes model-data generation;
4. a scheduled backend workflow retrieves weather, runs the local phenology and
   spray-suitability logic, constructs disease-service requests, stores model
   inputs/outputs, and creates notifications;
5. the FastAPI disease service computes infection, field-risk, protection,
   recommendation, and treatment-window outputs; and
6. protection-task products are converted to fungicide-effect parameters and
   can trigger disease-risk recalculation.

### Add a linkage-strength table

A manuscript or supplementary table should list each record pair, the actual
database key, relationship type, and supported inference. This will make the
traceability argument auditable and prevent contextual joins from being
presented as direct causal links.

### Strengthen the operational replay

For the representative crop, report a timestamped sequence containing:

- risk request and response timestamp;
- notification UUID and timestamp;
- task UUID, creation source if available, planned date, and completion time;
- fungicide product rows linked to the task;
- the pre-feedback and post-feedback disease-request payloads; and
- the resulting change in protection or risk state.

If notification provenance is unavailable, label the replay a
"crop-context record reconstruction" rather than a complete event-causal replay.

### Separate the core paper from auxiliary AI claims

The defensible core is the risk-to-action-to-feedback workflow. Image diagnosis
and advisory functions should be a clearly separated auxiliary branch. Until
the external advisory service is versioned and independently evaluated, do not
make it part of the main novelty claim.

## High-priority line-level targets in `manuscript_S.tex`

- Lines 118 and 154: verify or narrow the annual season/year semantics.
- Lines 122, 224, 256-257, and 289-293: reconcile the deployed recognition and
  advisory services with the checked-in code and external service.
- Lines 143, 179-182, 317-319, 363, and 456: distinguish direct, contextual, and
  functional linkage.
- Line 209: avoid implying enforced access control unless the deployed settings
  differ from the checkout.
- Line 279 and Supplementary Table S5: correct the weather provider and
  libraries.
- Lines 283-287: add the concrete fungicide-to-request conversion and
  recalculation behavior; this is one of the paper's strongest software
  contributions.

## Recommended next revision order

1. Resolve the crop-season/year, weather-provider, and external advisory-service
   facts with the authors/developers.
2. Rewrite the architecture and implementation sections using the verified
   service and identifier chain.
3. Rebuild the operational replay with linkage strengths and pre/post feedback
   evidence.
4. Narrow the abstract, discussion, and conclusion to claims supported by those
   records.
5. Add reproducibility, software-version, security/privacy, and deployment
   limitations.
6. Only then perform language polishing and final journal formatting.
