# `grape_backend` repository guide

This document records an implementation-level reading of the backend in
`grape_backend/`. It describes what the current code does, rather than what a
new Django project would normally be expected to do.

## 1. What the backend is

`grape_backend` is the server for a Chinese-language grape vineyard management
application ("葡萄通"/GrapeMaster). It combines:

- vineyard, user, crop-season, task, and field-record management;
- weather retrieval and spray-suitability calculation;
- grape phenology and disease-risk simulation;
- scheduled agronomic reminders, disease warnings, WebSocket events, and SMS;
- a community forum and feedback/document endpoints;
- image-based grape/leaf detection, classification, and segmentation.

The application is a Django 4.2 project using Django REST Framework. HTTP is
served through WSGI or ASGI; Django Channels supplies two WebSocket routes.
PostgreSQL is the configured database. Several ML models and a modified copy of
Ultralytics are stored directly in the repository.

The code is deployment-coupled: it expects an existing PostgreSQL schema,
external Agromodel services, model weights, specific filesystem layouts, and an
Alibaba Cloud SMS account. A clean clone is therefore **not currently a
one-command local deployment**.

## 2. Repository layout

```text
grape_backend/
├── README.md                    # Generic Codeup text; little project detail
├── config.py                    # Calls django.setup(); not the Django settings
├── model/
│   ├── phen/                    # Local GDD/BBCH phenology model and parameters
│   ├── spray/                   # Spray-suitability rules
│   ├── vit/                     # EfficientViT leaf classifier
│   ├── seg/                     # YOLO + MobileSAM + U-Net severity pipeline
│   ├── qingkephen/              # Barley phenology model used by api/
│   └── yolov8-main/             # Additional YOLO source/model material
└── grape/
    ├── manage.py
    ├── requirements.txt         # UTF-16 LE; incomplete for all imported modules
    ├── ACF-YOLO.onnx            # Berry detection model used by yolo/
    ├── grape/                   # settings, root URLs, ASGI/WSGI, WS routing
    ├── <Django apps>/           # Domain and API modules described below
    ├── ultralytics_2/           # Vendored/renamed Ultralytics implementation
    ├── static/                  # Uploads, generated assets, and APK
    ├── media/                   # Another APK location
    └── backup/                  # Historical disease request/response examples
```

The backend is itself a nested Git repository. Run Git commands with
`git -C grape_backend ...` if working from the paper repository root.

The `.gitignore` contains broad extension rules such as `*.txt`, `*.png`, and
`*.svg`. These can hide relevant files from tools that honor ignore rules.
Use `rg -uu` when inspecting the complete working tree.

## 3. Runtime architecture

### Request-serving layer

- `grape/grape/settings.py` configures Django, DRF, PostgreSQL, CORS, JWT,
  static files, APScheduler, and Channels.
- `grape/grape/urls.py` mounts all HTTP APIs.
- `grape/grape/asgi.py` combines Django HTTP handling with the WebSocket URL
  router.
- `grape/grape/routing.py` exposes notification and VIT/chat WebSockets.
- `grape/daphne.sh` is the deployment script. It activates
  `/mnt/grape_backend/myenv`, then starts Daphne on port `5001`.

### Core domain relationship

```text
Django User ──1:1── CustomUser (phone is the public/domain identifier)
                         │
                         ├── owns ──> Field ──> CropSeason
                         │             │             │
                         │             │             ├── weather/phenology/disease JSON
                         │             │             ├── field records and images
                         │             │             ├── protection/irrigation tasks
                         │             │             └── notifications
                         │             └── may be shared by phone number
                         │
                         ├── VIT leaf-classification history / messages
                         └── forum posts, comments, replies, and forum notices

Master data ──> varieties, cultivation methods, BBCH stages,
                fungicides, pesticides, reminders, and disease types
```

`CustomUser` is not Django's configured `AUTH_USER_MODEL`; it is a profile with
a one-to-one link to `django.contrib.auth.models.User`. Its primary key is the
phone number. Most domain APIs accept that phone number directly.

### Model-output storage

There are two representations for several model domains:

| Domain | Row-oriented/older app | Aggregate JSON app used by the main refresh flow |
|---|---|---|
| Weather | `weather` | `weatherdata.CropWeather` |
| Phenology | `phenmodel` | `phendata.PhenData` |
| Disease | `disease` | `diseasedata.DiseaseData` and `diseasedata.RB` |

The scheduled refresh and crop-creation path primarily populate the aggregate
JSON tables. The row-oriented endpoints remain exposed and should not be
assumed to contain the same data.

## 4. Main application flows

### A. User, field, and crop-season setup

1. `user/` creates a Django `User` plus a phone-keyed `CustomUser`.
2. `field/` accepts a GeoJSON boundary. `Field.save()`:
   - loads it with GeoPandas;
   - calculates area and centroid;
   - generates an SVG boundary icon;
   - reverse-geocodes the centroid through
     `weather.agromodel.cn/api/v1/geodecoder/`.
3. Field deletion is initially a soft delete (`delete_day = 0`). The midnight
   job increments the counter and removes the field after roughly 30 days.
4. A field can be shared by storing recipient phone numbers in a PostgreSQL
   `ArrayField`. Sharing first posts a notification; acceptance adds the phone
   to `share_user`.
5. Creating a `CropSeason` copies useful field/variety data into denormalized
   columns, then posts to `/weatherdata/list/` to start weather, phenology, and
   disease-data generation.

### B. Weather, phenology, disease, and notifications

`weather/views.py` starts a `BackgroundScheduler` as soon as the module is
imported:

- `00:10` (`job`): increments field recycle-bin age and marks old unread
  notifications as read after ten days.
- `06:00` (`job3`): refreshes all active crop seasons.

The 06:00 job does the following for each crop season:

1. Fetches historical and 16-day forecast weather from
   `weather.agromodel.cn`.
2. Produces hourly and daily JSON and applies local spray-suitability rules from
   `model/spray/spray.py`.
3. Sends mean daily temperature into `model/phen/phenm.py`, which converts
   temperature to GDD and maps cumulative GDD to BBCH stages using
   `model/phen/BBCHGDD.json`.
4. Builds an hourly disease-model request for downy mildew (`PLASVI`) and
   powdery mildew (`UNCINE`), then posts it to the hard-coded disease simulation
   endpoint.
5. Stores aggregate weather, phenology, disease response, and disease request
   body records.
6. Creates agronomic/disease notifications and may send Alibaba Cloud SMS.

The job uses a thread pool for weather fetches and contains a second retry pass
for crop seasons that fail the first pass. At the end it deletes all current
aggregate model rows and bulk-creates the newly accumulated rows.

### C. Crop tasks and the disease feedback loop

`task/` manages two task types:

- `CropProtection`, with nested fungicide and pesticide applications;
- `Irrigation`.

Task status is stored as Chinese text such as `未执行`, `已过期`, and `已完成`.
A protection task automatically becomes expired when saved after its execution
date while still unexecuted.

Fungicide applications are converted to disease-model effects using the master
fungicide's target disease, preventive efficacy, protection days, and curative
days. Creating or completing an applicable protection task updates the saved
disease request body and, in some branches, asynchronously re-runs disease
simulation. This is the primary management-to-model feedback loop.

### D. Image analysis

| API/app | Purpose | Implementation |
|---|---|---|
| `yolo/` | Berry state/count analysis | Saves multipart images, shells out to the `yolo` CLI using `ACF-YOLO.onnx`, parses CLI text, and returns annotated images plus aggregate counts/rates. |
| `vitgpt/` (`/vit/vit/`) | Leaf disease classification and advice | Loads an EfficientViT checkpoint at module import, predicts one of five leaf states, and returns hard-coded Chinese management advice. Despite the name, the live GPT model calls are commented out. |
| `seg/` | Leaf/downy-mildew severity segmentation | Runs a YOLO detector, MobileSAM, and U-Net pipeline and returns processed images plus severity text. |
| `unet/` | Stored/manual segmentation experiment data | Exposes text records and random source/manual/predicted image triplets from an unmanaged `image_paths` table. |

The ML endpoints are synchronous and compute-heavy. Some paths are relative to
the process working directory, while the YOLO endpoint contains the absolute
deployment path `/mnt/grape_backend/grape_backend`.

### E. WebSockets

Two Channels routes are mounted:

- `ws/notice/<group_name>/`: joins a group and receives server-side
  `push_message` notification events.
- `ws/vitgpt/<group_name>/`: currently echoes incoming text as `AI` output and
  reads the latest stored message history for the group/user.

The configured channel layer is `InMemoryChannelLayer`. Groups work only inside
one process; they do not span multiple Daphne/Gunicorn workers or hosts. A Redis
configuration exists only as commented code.

## 5. Django app map

| App | Responsibility |
|---|---|
| `user` | Phone-keyed user profiles linked to Django users. |
| `field` | GeoJSON vineyard fields, generated boundary icons, soft deletion, sharing, reverse geocoding. |
| `crop` | Crop seasons joining a field, grape variety, and cultivation method. |
| `master_data` | Varieties, BBCH stages, cultivation methods, fungicides, pesticides, reminders, disease types. |
| `note` | General, incidence, and growth-stage field records with images. |
| `task` | Protection and irrigation tasks; fungicide feedback into disease simulation. |
| `weather`, `weatherdata` | Weather APIs, scheduled refresh, spray suitability, normalized and JSON weather storage. |
| `phenmodel`, `phendata` | Normalized and aggregate phenology outputs. |
| `disease`, `diseasedata` | Normalized and aggregate disease outputs and saved simulation request bodies. |
| `warn` | User-reported disease discoveries, image evidence, location lookup, and nearby-user alerts. |
| `notice` | Persistent notification state and notification WebSocket fan-out. |
| `message` | Image, reply, role/text, and conversation-history records. |
| `forum` | Posts, comments, replies, images, and interaction notices. |
| `yolo` | ONNX/CLI-based berry analysis. |
| `vitgpt` | EfficientViT leaf classification, advice, and chat WebSocket stub. |
| `seg` | Uploaded-image disease segmentation/severity pipeline. |
| `unet` | Segmentation experiment/result browsing. |
| `api` | Separate barley phenology and sowing-condition model endpoints. |
| `grapepdf` | List/retrieve PDF metadata and download links. |
| `suggestions` | Simple user suggestion submission. |
| `location` | Address-to-coordinate proxy through the external weather service. |
| `updataapk` | Returns the APK URL and a message. |
| `grapeapp` | Root index and a test/echo API. |
| `download` | APK download view exists but is not mounted by the root URLconf. |

## 6. HTTP and WebSocket API surface

All paths below are relative to the server root. List/create and detail routes
generally use DRF's standard `GET`, `POST`, `PUT`, and `DELETE` semantics, but
several custom views intentionally overload `POST` or `DELETE` for state
transitions.

| Prefix | Important routes |
|---|---|
| `/api/jwt/` | `token/`, `refresh/`, `token/verify/` |
| `/user/` | `customusers`, `customusers/<phone>` |
| `/field/` | `list/`, `detail/<uuid>/`, user fields, recycle bin, recover, share, accept share |
| `/crop/` | `list/`, `list/<uuid>/`, `list/field/<field_uuid>` |
| `/master_data/` | CRUD for varieties, cultivation methods, growth stages, fungicides, pesticides, reminders, disease types |
| `/weather/` | normalized weather CRUD plus current/15-day weather proxies |
| `/weatherdata/` | aggregate weather list/detail/by-crop |
| `/phenmodel/`, `/phendata/` | normalized and aggregate phenology APIs |
| `/disease/`, `/diseasedata/` | normalized and aggregate disease/RB APIs |
| `/note/` | all records and typed note/incidence/growth-stage routes, including by-crop views |
| `/task/` | protection and irrigation CRUD; all tasks by crop or user |
| `/notice/` | notification CRUD, unread/read/important state, mark-all-read, and HTTP-to-WebSocket fan-out |
| `/warn/` | disease-discovery CRUD |
| `/forum/` | posts, comments, replies, per-user content, and forum notices |
| `/message/` | message CRUD and messages by user |
| `/yolo/detect/` | berry detection/list/detail |
| `/vit/vit/` | leaf classification/list/detail |
| `/seg/upload/` | multipart segmentation |
| `/unet/` | experiment images and text/result records |
| `/api/v1/` | `sowing_condition/`, `qing_ke_phenology/`, and root test endpoint |
| `/location/` | `get-location-info/` |
| `/suggestions/` | `submit/` |
| `/grapepdf/` | `pdfs/`, `pdfs/<uuid>/` |
| `/apk/` | `send-message/` |
| `/swagger_docs/`, `/redoc/` | generated API documentation |
| `/admin/` | Django admin |

## 7. Configuration and external dependencies

### Environment variables read by the code

Create `grape_backend/grape/.env` or export these variables before Django loads:

```dotenv
GXG_DEBUG=True
GXG_DB_NAME=...
GXG_DB_USER=...
GXG_DB_PASSWORD=...
GXG_DB_HOST=127.0.0.1
GXG_DB_PORT=5432

# Needed when a scheduled job attempts to send SMS.
ALIBABA_CLOUD_ACCESS_KEY_ID=...
ALIBABA_CLOUD_ACCESS_KEY_SECRET=...
```

`python-decouple` searches the process environment and nearby `.env` files.
Do not commit the `.env` file.

### Required external systems

- PostgreSQL, including support for `django.contrib.postgres.fields.ArrayField`;
- Agromodel weather, geocoder, and reverse-geocoder HTTP services;
- the disease simulation endpoint currently hard-coded as
  `http://118.89.50.72/disease/simulate`;
- Alibaba Cloud SMS for scheduled SMS notices;
- local model checkpoints under `model/` and the `ACF-YOLO.onnx` file;
- the `yolo` command on `PATH` for `/yolo/detect/`.

Several internal callbacks and generated links are also hard-coded to
`118.89.50.72`. Changing the public host requires source changes, not only an
environment update.

## 8. Local setup: what works and what needs attention

The repository states Python 3.10. A reasonable starting point is:

```bash
cd grape_backend
python3.10 -m venv .venv
source .venv/bin/activate

# requirements.txt is UTF-16 LE, so create a temporary UTF-8 copy first.
iconv -f UTF-16 -t UTF-8 grape/requirements.txt > /tmp/grape-requirements.txt
python -m pip install -r /tmp/grape-requirements.txt

cd grape
export PYTHONPATH="$(pwd)/..:${PYTHONPATH}"
python manage.py check
python manage.py runserver --noreload
```

This is only a starting point:

- `requirements.txt` does not list every imported runtime dependency. The ML
  paths additionally need packages such as PyTorch, torchvision, Pillow,
  OpenCV, Transformers, segmentation-models-pytorch, and a compatible
  Ultralytics/YOLO CLI. Daphne is also used by the deployment script but is not
  listed.
- Most apps contain only `migrations/__init__.py`; only `user` and `grapepdf`
  have an initial migration in this checkout. `python manage.py migrate` alone
  will therefore not create most application tables. The deployment appears to
  rely on an existing database schema. Before generating migrations, reconcile
  the models against the authoritative production schema.
- Starting Django imports `weather.views`, which starts APScheduler. The normal
  development autoreloader can start it more than once, hence `--noreload` in
  the example. Management commands may also start it because URL checks import
  the module.
- Some model and upload paths depend on the current working directory. Starting
  from another directory may break imports or checkpoint resolution.
- Creating/updating fields and crops makes live external HTTP calls. Local
  development without those services needs mocks or configuration refactoring.

For the deployment-style ASGI process, after installing `daphne` and correcting
the virtual-environment path in `daphne.sh`:

```bash
cd grape_backend/grape
daphne --port 5001 --access-log daphne.log grape.asgi:application
```

## 9. Validation and test state

- All non-vendored application Python files compile successfully with
  `compileall` at the time this guide was written.
- Most `tests.py` files are empty placeholders.
- `api/tests.py` is a manually invoked integration script that expects missing
  local JSON fixtures and a live server; it is not a self-contained Django test.
- `notice/tests.py` sends a WebSocket event at module import and is not a normal
  isolated test.
- A full `manage.py check` was not possible in the inspected environment because
  runtime packages such as `python-decouple`, Channels, Django APScheduler, and
  the ML stack were not installed.

There is no dependable automated regression suite for the domain or scheduler
flows. High-value future tests would isolate weather/disease/SMS clients, verify
the crop initialization flow, exercise fungicide feedback, and ensure failed
scheduled refreshes do not discard valid prior data.

## 10. Important operational and security observations

These points are part of understanding the current system and should be
addressed before treating it as a hardened or horizontally scalable service:

1. **Authentication is effectively not enforced on domain APIs.** JWT endpoints
   exist, but global permission/authentication settings and view-level checks
   are commented out. Many endpoints trust a phone number supplied in the URL
   or body.
2. **A Django secret key is committed**, `DEBUG` is externally configurable,
   CORS allows all origins, and static content is served through a development
   view in the root URLconf.
3. **TLS verification is disabled** on many outbound requests. Other callbacks
   use plain HTTP and hard-coded IP addresses.
4. **Schedulers run inside the web process.** Multiple workers can each start a
   scheduler, despite the shared Django job store. Import-time startup also
   affects management commands and test discovery.
5. **The 06:00 refresh is replacement-oriented.** It deletes all aggregate
   weather/phenology/disease/RB rows before bulk-creating the newly accumulated
   results. Failures and process interruption can create incomplete or empty
   datasets; the operation is not wrapped in an explicit transaction.
6. **Background task updates use ad-hoc thread pools.** They are not durable and
   may be lost on process restart. Exceptions are frequently swallowed by broad
   `except` blocks.
7. **WebSockets use in-memory channels**, so events do not cross workers and are
   lost on restart.
8. **Upload handling has global side effects.** The YOLO path clears shared
   directories and deletes all `YOLO_M` database records after a request. It is
   unsafe for concurrent requests and assumes a Linux deployment path.
9. **Media configuration is inconsistent.** Models write under paths beginning
   `grape/static/...`; `MEDIA_ROOT`/`MEDIA_URL` are not explicitly configured,
   and some deletion code references `settings.MEDIA_ROOT`.
10. **Database evolution is not reproducible from the checkout** because most
    migrations are absent.
11. **The vendored `ultralytics_2` tree is large and locally renamed.** Treat it
    as third-party/model infrastructure unless deliberately changing the
    inference implementation.

## 11. Best entry points for future work

- Overall configuration and routing:
  `grape/grape/settings.py`, `grape/grape/urls.py`, `grape/grape/asgi.py`.
- Domain ownership and lifecycle:
  `user/models.py`, `field/models.py`, `field/views.py`, `crop/serializers.py`.
- Daily decision-support pipeline:
  `weather/views.py` and `weatherdata/serializers.py`.
- Phenology and spray rules:
  `model/phen/phenm.py`, `model/phen/GDD.py`, `model/spray/spray.py`.
- Management feedback into disease risk:
  `task/serializers.py`.
- Notification delivery:
  `notice/views.py`, `notice/consumers.py`, `grape/routing.py`.
- ML inference:
  `yolo/views.py`, `vitgpt/views.py`, `model/vit/vitgpt.py`, `seg/views.py`,
  `model/seg/LDSP.py`.

In short, the backend's distinguishing feature is not ordinary CRUD but the
closed loop connecting a geospatial crop season to weather, phenology,
disease-risk forecasts, management tasks, and farmer notifications. The current
implementation demonstrates that loop end-to-end, while remaining closely tied
to its original server, database, and external model services.
