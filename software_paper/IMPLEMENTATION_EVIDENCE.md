# GrapeMaster claim-to-implementation evidence

This matrix records the evidence used to adapt the manuscript into a software paper. “Direct” means an implemented foreign key, stored resource, or explicit network call. “Contextual” means that records can be retrieved under a shared user, field, crop, image, or message context but do not have direct causal provenance.

| Manuscript claim | Implementation evidence | Linkage/evidence strength | Manuscript treatment |
|---|---|---|---|
| Persistent vineyard field identity | Backend field model stores ownership and geometry; Flutter provides field list and boundary editing | Direct | Presented as persistent geospatial and ownership context |
| Field-linked crop-management context | Backend `CropSeason` has UUID and field, variety, cultivation, vine-age, coordinate, and timestamp attributes; frontend `Crop` resources are keyed by UUID | Direct, with lifecycle limitation | Called crop-season context; annual start/end/year are not claimed as schema fields |
| Weather integration | Backend retrieves historical and forecast data from `weather.agromodel.cn`, transforms it, and stores crop-linked weather resources | Direct external service and backend resource | Agromodel is named; Open-Meteo is removed from the revised manuscript |
| Scheduled crop refresh | APScheduler starts backend jobs and refreshes active crop records with retry handling | Direct runtime behavior | Presented as scheduled backend orchestration; reliability is not claimed as evaluated |
| Phenology integration | Backend generates crop-linked phenology payloads and a daily stage sequence from weather and crop metadata | Direct backend processing | Presented as both mobile state and disease-service input |
| Disease-service separation | FastAPI/Pydantic service receives complete request context and retains no database state | Direct service interface | Presented as a stateless analytical service called by Django |
| Disease request and response retention | Backend stores disease request and response objects under the crop resource | Direct backend persistence | Traceability is assigned to the backend, not to the disease service |
| Disease service uses actual crop UUID | Django caller relies on the service default rather than passing the actual crop UUID; the service does not use that field | Unsupported | Explicitly excluded; crop association is described as backend-owned |
| Downy and powdery mildew pathways | Inspected disease-service source contains active `PLASVI` and `UNCINE` processing | Direct source evidence | Both are described as implemented service pathways |
| FSIM-S Guangxi performance represents every deployment response | Offline result exists, but the inspected source/configuration is not linked to historical records by an immutable version | Supporting but not version-linked | Reported as platform-compatible component evidence, not universal deployment proof |
| Disease result to notification and task workflow | Backend produces notification resources; frontend shows alerts and task entry; notification/task share context | Contextual/functional | Presented as risk-to-action workflow, not a direct causal database link |
| Notification directly creates a traceable task | Task lacks a `source_notification_uuid` foreign key | Unsupported as direct provenance | Revised paper states the limitation |
| Task-to-product feedback | Fungicide/pesticide products have direct task relationships | Direct | Presented as direct product-level treatment feedback |
| Treatment-aware recalculation | Task serializers translate disease target, date, and protection durations into `applied_fungicides`, update stored request, and invoke disease calculation in supported paths | Direct runtime behavior | Presented as the strongest analytical/management integration |
| Product-specific efficacy simulation | Service accepts efficacy fields but the active implementation does not fully use them | Partial | Described as treatment-aware protection-state recalculation, not individualized efficacy simulation |
| Image-recognition integration | Flutter submits images to a separately hosted HTTP service and parses returned classification text; backend has image-related records | Direct client contract; hosted implementation external | Presented as an integrated post-symptomatic service with an artifact-availability limitation |
| LLM-assisted advisory integration | Flutter sends questions to a hosted WebSocket and streams text until an end marker; advisory/message records exist | Direct client contract; hosted model external | Presented as an LLM-assisted interface, not as a fully archived model artifact |
| Fine-tuned ChatGLM3 model is verified in the inspected deployment source | Adjacent backend's local ChatGLM inference is commented out; hosted checkpoint, prompt, and fine-tuning data are absent | Not verified | The revised manuscript cites the framework concept and states the evidence boundary |
| Advisory quality is validated | No independent advisory-quality evaluation is available | Unsupported | Explicitly excluded from claims |
| Complete crop-keyed advisory history | Advisory messages are primarily user/message keyed; reports and notes use varying field/crop relationships | Contextual and heterogeneous | Functional integration is claimed; universal crop foreign-key linkage is not |
| Operational software use | Export contains 47 retained operational accounts, 139 fields, 128 crop records, analytical payloads, notifications, tasks, products, images, and messages | Descriptive deployment evidence | Used as implementation demonstration, not as efficacy or adoption evaluation |
| Agronomic efficacy, pesticide reduction, economic benefit, usability, or adoption | No controlled outcome comparison in the reviewed evidence | Unsupported | Explicitly outside scope |
| Broad scalability and plug-and-play extensibility | Service boundaries exist, but fixed endpoints, in-memory WebSocket state, deployment coupling, and limited automated tests remain | Design intent with implementation constraints | Discussed as future work; not claimed as measured performance |

## Highest-priority archival evidence before submission

1. A tagged frontend release with configurable endpoint documentation.
2. A tagged backend release with environment template, migrations, scheduler guidance, and dependency lock.
3. A tagged disease-service release with exact deployed configuration and regression fixtures.
4. The image classifier source, checkpoint, class mapping, preprocessing, and endpoint schema.
5. The LLM checkpoint or provider/version, prompt or retrieval configuration, fine-tuning description, safety constraints, and endpoint schema.
6. A mapping from operational-record timestamps to deployed software and model versions.
7. A reproducible, de-identified derived dataset for the deployment demonstration.
