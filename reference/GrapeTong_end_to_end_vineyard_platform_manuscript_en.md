# GrapeTong - Draft Manuscript Note for an End-to-End Vineyard Disease Warning and Precision Management Platform

## Bibliographic Information

- Provisional title: GrapeTong: An end-to-end mobile decision-support platform for vineyard disease warning and precision management
- System name: GrapeTong
- Target domain: Precision viticulture; vineyard disease warning; mobile field management
- Candidate journal style: Computers and Electronics in Agriculture platform paper
- Reference structure: Bakir et al. (2026), "A scalable, end-to-end IoT and remote sensing platform for precision rangeland and livestock management"
- Candidate keywords: Precision viticulture; Disease warning; Phenology model; Disease-risk model; Mobile decision support; Image recognition; Plant-protection task management; Flutter; Django; FastAPI
- Main technology stack:
  - Flutter mobile client
  - Django REST Framework backend
  - PostgreSQL database
  - Django Channels WebSocket services
  - Django APScheduler scheduled jobs
  - FastAPI disease-model service
  - YOLO, ViT/EfficientViT, UNet, and segmentation-related image-analysis modules

## 1. Introduction

Grapevine production is threatened by multiple diseases whose risk changes with weather, phenology, cultivar susceptibility, cultivation method, and fungicide history. In field practice, growers often need to decide whether to monitor, spray, delay operations, or create follow-up tasks within a narrow treatment window. These decisions are difficult when field boundaries, weather data, phenological status, disease-risk indicators, fungicide records, image observations, and task execution logs are distributed across separate tools.

Digital agriculture has made it possible to combine mobile applications, weather services, geospatial field data, crop models, disease models, image recognition, and notification systems. However, a useful vineyard disease-warning system must go beyond isolated model execution. It must support an operational workflow in which data are acquired, stored, processed, interpreted, displayed, and converted into management actions.

GrapeTong addresses this platform-level problem by organizing vineyard management around fields and crop seasons. The system integrates mobile field operations, weather retrieval, grape phenology simulation, weather-driven disease-risk modeling, fungicide protection tracking, image-based disease recognition, notifications, task management, and grower communication. In this sense, GrapeTong follows the same end-to-end platform logic emphasized by Bakir et al. (2026), but adapts it from rangeland livestock management to vineyard disease warning and precision crop management.

### Main Objectives

The main objectives of the GrapeTong platform are to:

- provide an end-to-end software architecture for vineyard disease warning and precision management;
- integrate field boundaries, crop-season metadata, cultivar susceptibility, weather data, phenology outputs, disease-risk models, and fungicide records;
- support mobile workflows for field creation, weather inspection, disease warning, image recognition, notes, plant-protection tasks, irrigation tasks, and forum communication;
- convert completed plant-protection tasks into fungicide-history inputs for subsequent disease-risk recalculation;
- connect model outputs to user-facing notifications and task execution records;
- establish a platform foundation that can later be validated with deployment statistics, field disease observations, image-label datasets, and performance metrics.

## 2. System Architecture

GrapeTong uses a layered architecture in which the mobile client, backend services, model services, and external data services are separated but connected through APIs and scheduled workflows.

### 2.1 Conceptual Architecture

Conceptually, GrapeTong is a crop-season-centered decision-support platform. The vineyard field provides the spatial unit, while the crop season provides the agronomic unit that links cultivar, cultivation method, vine age, weather, phenology, disease risk, fungicide tasks, irrigation tasks, notes, and notifications.

The conceptual workflow is:

1. A user creates a vineyard field and crop season in the mobile application.
2. The backend stores field geometry, crop metadata, cultivar susceptibility, and cultivation information.
3. Scheduled jobs retrieve historical and forecast weather for the field centroid.
4. Weather data are transformed into inputs for phenology, spraying suitability, and disease-risk models.
5. Phenology outputs are used to construct disease-model growth-stage inputs.
6. Historical plant-protection tasks are converted into fungicide-application records.
7. The disease-model service computes infection risks, disease risks, field risks, protection times, action recommendations, and treatment windows.
8. Results are stored in the backend and displayed through the mobile application.
9. Notifications guide users toward inspection, task creation, and field operations.
10. Completed tasks update fungicide history and trigger future risk recalculation.

### 2.2 Logical Architecture

The logical architecture consists of four major subsystems:

- **Mobile subsystem:** Flutter application for growers and field operators.
- **Business-data subsystem:** Django REST Framework backend with PostgreSQL storage.
- **Analytics subsystem:** phenology, spraying suitability, disease-risk, and image-analysis workflows.
- **External-service subsystem:** weather, geocoding, SMS, disease-model endpoint, and WebSocket-related services.

These subsystems communicate mainly through REST APIs, database records, scheduled tasks, and WebSocket messages.

### Architecture Layers

1. Mobile Application Layer
   - Provides field, task, recognition, forum, weather, notification, and note interfaces.
   - Uses HTTP APIs for backend communication.
   - Uses WebSocket channels for notifications and intelligent-recognition sessions.
   - Integrates mapping, location, image upload, local storage, charts, PDF viewing, and video playback.

2. Backend Business and Storage Layer
   - Uses Django 4.2 and Django REST Framework.
   - Uses PostgreSQL for users, fields, crop seasons, master data, weather, phenology, disease data, tasks, notes, messages, and forum content.
   - Uses Django Channels for WebSocket routing.
   - Uses Django APScheduler for periodic jobs.

3. Data Processing and Analytics Layer
   - Runs grape phenology simulation.
   - Calculates spraying suitability.
   - Constructs disease-model request bodies.
   - Calls the independent FastAPI `/simulate` disease-model service.
   - Processes model outputs into mobile-facing disease-risk datasets.
   - Supports image detection, classification, segmentation, and severity-related outputs.

4. External Data and Service Layer
   - Retrieves weather-history and weather-forecast data.
   - Uses reverse geocoding to identify field regions.
   - Uses SMS verification for authentication.
   - Calls deployed disease-model and intelligent-recognition endpoints.
   - Requires configuration management and fault-tolerant service handling for production use.

## 3. Implementation

### 3.1 Data Acquisition Layer Implementation

Unlike the Bakir et al. platform, which acquires data from physical IoT sensors and remote-sensing products, GrapeTong primarily acquires data from mobile user input, external weather services, model services, and uploaded images.

Key acquisition channels include:

- Mobile field boundary input as GeoJSON.
- Crop-season metadata entered by users.
- Grape cultivar, fungicide, pesticide, growth-stage, and cultivation-method master data.
- Historical and forecast weather requested from external weather APIs.
- Field notes, growth-stage observations, disease observations, and task records entered in the mobile app.
- Disease images uploaded through recognition or reporting modules.
- WebSocket messages for notifications and intelligent-recognition workflows.

Field boundaries are stored with centroid latitude and longitude, which become the spatial anchor for weather retrieval and model workflows.

### 3.2 Data Ingestion and Storage Implementation

The backend uses PostgreSQL as the main structured database. Major stored entities include:

- users and phone-based account records;
- vineyard fields with GeoJSON boundaries, centroids, area, SVG preview, region, sharing status, and deletion status;
- crop seasons linked to fields, cultivars, cultivation methods, vine age, and field coordinates;
- grape cultivar susceptibility data;
- fungicide and pesticide master data;
- hourly and daily weather datasets;
- phenology results;
- disease-model request bodies;
- disease-risk outputs;
- plant-protection and irrigation tasks;
- notifications;
- field notes, disease notes, images, messages, and forum records.

The Django backend exposes REST endpoints for mobile access and uses scheduled jobs to update derived weather, phenology, disease, and notification data. The current implementation stores processed analytical outputs directly in relational structures and JSON fields, making them easy for the mobile application to query.

### 3.3 Data Processing and Analytics Implementation

#### Weather Processing

For each active crop season, the backend retrieves weather data using field latitude and longitude. The weather variables include hourly temperature, relative humidity, dew point, precipitation, wind speed, wind gusts, and daily temperature and precipitation summaries. Historical weather and short-term forecast data are combined to create a continuous sequence for phenology and disease modeling.

Missing values are handled with simple continuity rules. Hourly weather is converted into the disease-model schema containing datetime, dew point, precipitation, relative humidity, air temperature, and wind speed.

#### Phenology Simulation

The grape phenology workflow uses daily mean temperature and crop-season attributes to simulate:

- daily growing degree days;
- accumulated growing degree days;
- BBCH principal stage;
- one-digit BBCH class;
- growth-stage descriptions from master data.

The phenology output is stored for mobile display and transformed into the `growth_stage` input required by the disease-risk model.

#### Disease-Risk Simulation

The disease-model service is implemented as a FastAPI application with a `/simulate` endpoint. The backend constructs a crop-season-level request body with:

- crop-season identifier;
- region and crop EPPO code;
- latitude and longitude;
- request date;
- hourly weather;
- growth-stage sequence;
- historical fungicide applications;
- target disease codes;
- cultivar susceptibility values;
- requested output features and date ranges.

The main requested features are:

- `dailyInfectionRisks`;
- `stressRisks`;
- `fieldRisks`;
- `stressProtectionTimes`;
- `actionRecommendations`;
- `treatmentWindows`.

For grape, the disease-model service includes disease structures for:

- `PLASVI`: grapevine downy mildew;
- `UNCINE`: grapevine powdery mildew;
- `BOTRCI`: Botrytis bunch rot;
- `ELSIAM`: anthracnose or related grape disease representation;
- `GUIGBI`: grape black rot.

The current backend workflow appears to operationally emphasize downy mildew and powdery mildew, while the model service contains broader grape disease capacity.

#### Fungicide Protection and Task Feedback

Completed plant-protection tasks are converted into disease-model `applied_fungicides` records. The backend derives application date, target disease, preventive protection days, curative protection days, preventive efficacy, and curative efficacy from fungicide master data.

When a task is deleted or changed, the backend updates the fungicide-history input and recalculates disease risk. This creates a feedback mechanism between field operations and risk modeling.

#### Spraying Suitability

Spraying suitability is calculated from temperature, precipitation, wind speed, relative humidity, near-future precipitation, cultivation method, sunrise time, and sunset time. The result supports short-term decisions about whether field application conditions are suitable.

#### Image Recognition and Segmentation

The backend includes image-analysis modules based on YOLO, ViT/EfficientViT, UNet, and segmentation-related components. Uploaded field images can be processed to return recognition text, processed images, and severity-related outputs.

For formal publication, this part requires dataset documentation, disease-class definitions, expert labels, model metrics, and inference-time reporting.

### 3.4 Application and Presentation Implementation

The Flutter mobile application is organized into feature modules:

- `auth`: login, user profile, copyright page, and feedback.
- `field`: fields, crops, varieties, growth stages, weather, notifications, sharing, and recycle bin.
- `task`: plant-protection and irrigation task workflows.
- `communition`: disease recognition, reporting, history messages, and intelligent communication.
- `forum`: posts, replies, comments, and forum notices.
- `map`: map-based field interaction.
- `note`: field notes, growth-stage notes, and disease notes.

The main mobile interface uses four bottom navigation tabs:

- Fields
- Tasks
- Recognition
- Forum

The backend provides API endpoints for these modules and WebSocket routes for notifications and intelligent-recognition sessions.

## 4. Deployment

The current codebase shows a complete software system, but deployment information must be collected from operational records before the manuscript can be considered publication-ready.

Required deployment information includes:

- demonstration vineyard locations;
- deployment period;
- number of registered and active users;
- number of vineyard fields;
- total vineyard area;
- number of crop seasons;
- grape cultivars represented;
- weather records ingested;
- phenology simulations completed;
- disease simulations completed;
- notifications generated;
- plant-protection and irrigation tasks recorded;
- disease images uploaded;
- forum posts, comments, and messages.

### Deployment Scale by Region

The following table should replace placeholders once deployment data are available.

| Region | Vineyards | Fields | Area | Crop seasons | Users | Disease images | Disease simulations |
|---|---:|---:|---:|---:|---:|---:|---:|
| Region 1 | To be added | To be added | To be added | To be added | To be added | To be added | To be added |
| Region 2 | To be added | To be added | To be added | To be added | To be added | To be added | To be added |
| Total | To be added | To be added | To be added | To be added | To be added | To be added | To be added |

## 5. Features and Functionalities

### 5.1 Monitoring

The monitoring component is centered on vineyard fields and crop seasons. Users can view field lists, field boundary previews, field details, crop-season information, weather data, notifications, and disease-risk status.

Field monitoring includes:

- field name, area, centroid, and boundary preview;
- crop-season cultivar and cultivation method;
- weather summaries and hourly weather;
- phenology stage;
- disease-risk indicators;
- notification status.

### Weather, Phenology, and Disease-Risk Visualization

GrapeTong displays weather and model-derived indicators for crop seasons. The disease-risk visualization should include, or can be extended to include:

- downy mildew infection risk;
- powdery mildew infection risk;
- disease-specific stress risk;
- field-level risk;
- treatment-window code;
- treatment start and end dates;
- action recommendation code;
- fungicide protection information.

### Field Notes and Observation Timeline

The note modules allow users to record general notes, growth-stage notes, and disease notes. These observations can provide a timeline of field events and potential validation evidence for phenology and disease-risk models.

### 5.2 Disease Events

The disease-event equivalent in GrapeTong consists of field disease warnings, disease notes, image-based reports, and treatment-window recommendations.

A future manuscript should define event categories such as:

- high infection-risk day;
- high field-level risk day;
- recommended treatment window;
- missed treatment window;
- visible disease symptom report;
- image-recognition disease detection.

These events can be analyzed against field observations and plant-protection task execution.

### 5.3 Vineyard Analytics

The vineyard analytics component can summarize weather, phenology, disease risk, treatment windows, task completion, and disease observations at crop-season or field level.

Potential analytics include:

- daily disease-risk curves;
- phenology progression curves;
- weather-risk relationship plots;
- task execution timeline;
- fungicide protection-period visualization;
- comparison among fields or crop seasons;
- disease-image count and recognition result summaries.

### 5.4 Plant-Protection and Irrigation Tasks

The task module supports plant-protection and irrigation operations. Users can create, update, complete, and delete tasks. Overdue tasks are marked based on execution date and status.

Plant-protection tasks are analytically important because completed fungicide applications are converted into model inputs and affect future disease-risk calculations.

### 5.5 Image-Based Disease Assistance and Forum

The recognition module supports disease-image upload, automated recognition or segmentation, disease reporting, and historical message review. The forum module supports posts, comments, replies, and grower communication.

Together, these functions add user-generated evidence and social knowledge exchange to the weather-driven disease-warning workflow.

## 6. Discussion

### 6.1 Advancing Solutions to Established Research Gaps

Many agricultural decision-support tools focus on isolated functions such as weather display, disease modeling, image recognition, or field recording. GrapeTong addresses a broader gap by integrating these functions into a crop-season-centered platform. Its workflow connects field geometry, cultivar susceptibility, weather, phenology, disease risk, fungicide records, notifications, and task execution.

This integration is important because disease-risk model outputs become operationally useful only when growers can translate them into field actions. GrapeTong links analytical outputs to mobile notifications and plant-protection tasks, then feeds completed tasks back into disease-risk recalculation.

### 6.2 Proposed Strengths and Innovations

The main strengths of GrapeTong include:

- an end-to-end architecture from mobile field input to model output and task feedback;
- integration of phenology simulation with weather-driven disease-risk modeling;
- use of cultivar susceptibility and fungicide history as dynamic model inputs;
- mobile-first support for field operations;
- inclusion of image recognition and segmentation as complementary disease evidence;
- support for notifications, notes, and forum communication within the same platform;
- modular separation between the Django business backend and FastAPI disease-model service.

Compared with a standalone disease model, GrapeTong provides a management loop. Compared with a standalone mobile record app, it incorporates model-driven risk interpretation. Compared with standalone image recognition, it combines symptom-level visual evidence with weather-driven risk indicators.

### 6.3 Limitations and Future Directions

Current limitations include:

- deployment scale and user statistics are not yet documented;
- disease-model validation against field observations is still required;
- image-recognition dataset size, label protocol, and performance metrics must be reported;
- hard-coded API endpoints and service URLs exist in the frontend and backend;
- scheduled weather, phenology, disease, and notification workflows are tightly coupled in some backend modules;
- the current WebSocket channel layer uses an in-memory backend, which is not suitable for multi-process production deployment;
- external weather, geocoding, SMS, disease-model, and recognition services introduce availability risks;
- some model paths and server paths are environment-specific.

Future work should:

- collect field deployment and usage statistics;
- validate disease warnings with field disease observations;
- benchmark image-recognition models with expert-labeled datasets;
- quantify API latency, scheduled-job runtime, and model-service response time;
- refactor configuration and service boundaries for reproducible deployment;
- evaluate user adoption and management impact through logs, interviews, or surveys.

## 7. Conclusion

GrapeTong is an end-to-end mobile decision-support platform for vineyard disease warning and precision management. The system integrates Flutter mobile interfaces, Django backend services, PostgreSQL storage, scheduled weather and model workflows, grape phenology simulation, a FastAPI disease-risk model, fungicide task feedback, image-analysis modules, notifications, field notes, and grower communication.

The platform demonstrates how vineyard disease-warning models can be embedded into a practical field-management workflow. Its central design principle is the crop season, which links spatial field data, cultivar susceptibility, weather, phenology, disease risk, management tasks, and observations. To convert this system description into a journal-ready manuscript, the next step is to add deployment-scale statistics, disease-model validation, image-model validation, system-performance metrics, and user-workflow evidence.

## Suggested Citation

Bakir, M. E., Perea, A. R., Funk, M., Rahman, S., Spetter, M. J., Macon, L., Cox, A., Estell, R. E., Cao, H., Cibils, A. F., Spiegal, S. A., Bestelmeyer, B. T., & Utsumi, S. A. (2026). A scalable, end-to-end IoT and remote sensing platform for precision rangeland and livestock management. *Computers and Electronics in Agriculture, 247*, 111615. https://doi.org/10.1016/j.compag.2026.111615

## BibTeX

```bibtex
@article{Bakir2026PrecisionRanchingPlatform,
  title = {A scalable, end-to-end IoT and remote sensing platform for precision rangeland and livestock management},
  author = {Bakir, Mehmet E. and Perea, Andres R. and Funk, Micah and Rahman, Sajidur and Spetter, Maximiliano J. and Macon, Lara and Cox, Andrew and Estell, Richard E. and Cao, Huiping and Cibils, Andres F. and Spiegal, Sheri A. and Bestelmeyer, Brandon T. and Utsumi, Santiago A.},
  journal = {Computers and Electronics in Agriculture},
  volume = {247},
  pages = {111615},
  year = {2026},
  doi = {10.1016/j.compag.2026.111615}
}
```
