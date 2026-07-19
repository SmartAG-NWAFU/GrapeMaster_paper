# `grape_frontend` repository guide

## 1. What this repository is

`grape_frontend` is the Flutter client for **葡萄通 / GrapeMaster**, a grape-production decision-support application. It is primarily an Android-oriented mobile app, although standard Flutter scaffolding is checked in for iOS, web, Windows, macOS, and Linux.

The app joins five kinds of functionality in one client:

1. vineyard and crop-block management;
2. weather, phenology, and disease-risk monitoring;
3. irrigation and plant-protection task planning/execution;
4. field observations and image-based disease diagnosis;
5. community, notifications, documentation, and account functions.

This is a direct, widget-driven Flutter application rather than a layered client SDK. UI, HTTP calls, response parsing, local persistence, and domain calculations frequently live in the same feature files.

## 2. Product model

The central hierarchy is:

```text
User (identified by phone number)
└── Field / vineyard polygon
    └── Crop configuration
        ├── weather and forecast data
        ├── phenological stage
        ├── disease-risk data
        ├── observations / notes
        ├── irrigation tasks
        └── plant-protection tasks
```

A field is a geospatial polygon drawn on a map. A crop records grape variety, cultivation method, vine age, and planted area. Most monitoring and management data is attached to the crop UUID, while notifications and task lists are also aggregated for the current user.

## 3. Main user journey

The intended operating loop is:

```text
Sign in by phone
  → draw or accept a shared field
  → configure its crop
  → inspect weather, phenology, and disease risk
  → receive a warning or create a management task
  → select treatment products / irrigation details
  → execute and complete the task
  → record observations and feed results back into the system
```

Image diagnosis is a parallel path: the user photographs or selects a grape-leaf image, sends it to a classification service, asks follow-up questions over WebSocket, optionally evaluates disease severity, and can report the diagnosis against one of their fields.

## 4. Runtime entry points and navigation

The application starts in [`grape_frontend/lib/main.dart`](grape_frontend/lib/main.dart). `MyApp` creates a `MaterialApp` with Chinese and English localization delegates and opens `HomeView`.

`HomeView` creates another `MaterialApp` and an `IndexedStack` controlled by a four-item `CupertinoTabBar`:

| Tab | Screen | Purpose |
|---|---|---|
| 地块 | `FieldView` | Field list, weather summary, notifications, crop entry, and account access |
| 任务 | `TaskListView` | Irrigation and plant-protection tasks grouped by execution state |
| 识别 | `CommunitionView` | Leaf-image classification and AI-assisted advice |
| 论坛 | `Forum` | Posts, images, comments, replies, and forum notices |

The `IndexedStack` preserves each tab's widget state. The task tab is explicitly refreshed when selected.

There is no centralized named-route table. Most navigation uses `Navigator.push` with inline `MaterialPageRoute` objects. Some screens return string flags such as `refresh`, `backandback1`, or `backandback2` to tell their caller what to refresh or how far to pop. Consequently, navigation behavior must usually be traced from the calling widget.

An important current behavior is that the login initialization/check in `HomeView` is commented out. The app therefore opens the main tabs directly, even when no user is stored locally. Several downstream screens assume a saved phone number or UUID exists, so a clean installation can reach null-related failures before authentication.

## 5. Source layout

```text
grape_frontend/
├── lib/
│   ├── main.dart                 App entry point
│   ├── net_config.dart           Partial network configuration and SMS API client
│   ├── http_util.dart            Legacy/general Dio wrapper (apparently unused)
│   ├── api/                      Small standalone API helpers
│   ├── common/                   Shared widgets, constants, and product rules
│   ├── constants/                App constants, including the AMap key
│   ├── features/
│   │   ├── auth/                 Login, profile, feedback, help/about/update
│   │   ├── home/                 Four-tab application shell
│   │   ├── field/                Fields, crops, weather, risk, notifications, notes
│   │   ├── map/                  WebGIS field-polygon drawing bridge
│   │   ├── task/                 Irrigation and plant-protection workflows
│   │   ├── communition/          Image diagnosis, severity, history, reporting, chat
│   │   ├── note/                 General, incidence, and growth-stage observations
│   │   └── forum/                Posts, comments, replies, and forum notifications
│   ├── generated/                Generated localization code
│   ├── l10n/                     English and Chinese ARB localization sources
│   ├── res/                      Legacy/static data helpers
│   ├── services/                 APK update service
│   └── theme/                    Theme definitions
├── assets/
│   ├── templates/                Local Leaflet/WebGIS HTML used by the map screen
│   ├── css/, js/, lib/           Vendored WebGIS/Leaflet/Bootstrap dependencies
│   ├── images/ and image/        Raster and SVG application assets
│   └── fonts/                    Custom icon fonts
├── android/, ios/, web/, ...     Flutter platform projects
├── test/                         One stale template widget test
└── pubspec.yaml                  Flutter dependencies and asset declarations
```

The largest screens are several thousand lines long. `field_view.dart`, `crop_view.dart`, the weather views, and many task-execution variants combine UI and orchestration and are the most important files to understand before making cross-cutting changes.

## 6. State and persistence

The app does not use Provider, Bloc, Riverpod, Redux, or another application-wide state framework. State is held in:

- `StatefulWidget` fields;
- controller objects instantiated by screens;
- static/global values in a few helpers;
- `SharedPreferences`, which acts both as a session store and as the current domain context.

Important persisted values include:

| Context | Representative keys |
|---|---|
| User session | `username` (phone number), `token` (JWT) |
| Current field | `field_uuid`, `name`, `size`, `latitude`, `longitude` |
| Current crop | `uuid`, `field_uuid`, `variety_uuid`, `cultivation_uuid`, `tree_age`, `size` |
| Current mission | date and task type |
| Plant-protection flow | selected fungicides/pesticides, dates, capacities, quantities, and mixing mode |

Screen-to-screen domain data is often passed indirectly by saving it first and reloading it in the next screen. This makes keys part of the navigation contract. Generic keys such as `uuid`, `name`, and `size` can collide between features, and many getters use non-null assertions.

There are also concrete storage inconsistencies worth checking before relying on saved state: one mission helper returns its `type` member instead of the loaded name, the plant-protection helper writes `selectedItems` but reads `electedItems`, and one size key includes a leading space (`' size'`).

## 7. Feature walkthrough

### 7.1 Authentication and profile

Login is phone/SMS based:

1. the app requests a code from `https://cotton.agrodigits.cn/api/v1/stt_gxg/`;
2. it creates or updates `/user/customusers` on the main backend;
3. it fetches that user and compares the entered value with `validation_code` in the returned record;
4. it requests a JWT from `/api/jwt/token/`;
5. it saves the phone and token in `SharedPreferences`.

The profile area reads and edits the user name, logs in/out, controls a notification preference, submits suggestions, opens help/regulation PDFs and an introduction video, and checks for APK updates.

### 7.2 Fields and maps

`FieldView` is the application's operational hub. It loads fields owned by the saved phone number, shows remotely generated field SVGs, displays current weather, opens notifications and profile pages, and enters a crop workspace.

Creating a field opens `MapPage`, an `InAppWebView` backed by the local `assets/templates/WebGIS3857Draw.html` Leaflet page. Dart and JavaScript communicate through handlers for:

- obtaining the device position;
- obtaining the current user ID;
- posting a drawn GeoJSON polygon;
- returning from the map.

The native side uses Geolocator and AMap-related packages for permissions/location. Fields can be edited, soft-deleted to a recycle bin, restored, and shared. A recipient can accept a shared-field notification.

### 7.3 Crop workspace and decision support

Each field can have a crop configuration containing variety, cultivation method, tree age, and crop area. The crop screen combines:

- aggregate weather and forecast information;
- current/predicted phenological stage;
- disease-risk data;
- field and crop metadata;
- observation/note entry points;
- crop editing and sharing actions.

The data comes from separate backend resources (`weatherdata`, `phendata`, and `diseasedata`) keyed by crop UUID. The client is therefore primarily a presentation and workflow layer over backend model results; it does not run the forecasting models locally.

### 7.4 Notifications and warning-to-task conversion

The main field page and notification widgets connect to `ws://118.89.50.72/ws/notice/<phone>/` and also query notification REST endpoints. Notifications can be read, marked important, batch-read, or interpreted as field/crop warnings.

For supported warning types, the UI can turn the alert into an irrigation or plant-protection task. Shared-field invitations are also handled through the notification experience. The code includes reconnection timers and duplicate notification logic in both `FieldView` and notification-specific widgets.

### 7.5 Tasks

The task tab fetches `/task/user/<phone>` and distinguishes irrigation from crop-protection work. It routes each task to different detail/execution screens according to status, including not executed, completed, and expired variants.

The irrigation path records timing, amount, completion state, and related crop details.

The plant-protection path can:

- inspect weather/spraying suitability;
- choose an execution date;
- choose fungicides and pesticides from master data;
- enter sprayer, mixer, and water capacities;
- calculate product quantities and mixing batches;
- save or update the task and its execution state.

`lib/common/map.dart` contains client-side product-group rules intended to prevent inappropriate repeat use and manage resistance for a small hard-coded set of products. These rules are domain logic and should be reviewed whenever master product data changes.

The many similarly named task screens (`already*`, `sterill*`, `sterillexe*`) are separate, largely duplicated status/workflow variants rather than aliases for one reusable component.

### 7.6 Observations and notes

The app supports three observation families:

- general crop notes (`/note/note/`);
- disease-incidence notes (`/note/incidence/`);
- growth-stage notes (`/note/growthstage/`).

They support text, dates, crop association, and image upload. List and detail screens construct media URLs from the main backend host. These observations are the main manual feedback mechanism for crop conditions and model validation.

### 7.7 Image diagnosis and advisory chat

`CommunitionView` lets the user capture or select an image. It crops/compresses the image to a square, keeps it below the upload threshold, and sends multipart data to `http://106.75.19.191:3389/vit/vit/`.

The result screen displays classification text and offers predefined follow-up questions. Answers stream from `ws://106.75.19.191:3389/ws/vitgpt/<phone>/` until an `/end` marker is received.

Related flows include:

- diagnosis history through the main backend's `/message/list/...` resources;
- disease-severity estimation through `http://106.75.19.191/predict`;
- reporting a detected disease to `/warn/discovering/diseases/` after choosing a field;
- a manual disease-report screen.

The report flow extracts a disease name from Chinese classification prose using a regular expression, so changes to the inference service's wording can break reporting even when classification itself succeeds.

### 7.8 Forum and supporting content

The forum implements post listing/creation, multiple images, post details, comments, nested replies, user-owned posts, and sent/received reply notices under `/forum/...`.

The account/support area also exposes static PDFs, a product video, user feedback, copyright/about information, and an Android APK updater.

## 8. Backend and external-service integration

Network access is distributed across controllers and widgets; `NetConfig.baseUrl` is not consistently used. The active service map is:

| Service | Hard-coded origin | Use |
|---|---|---|
| Main application backend | `http://118.89.50.72/` | Users, JWT, fields, crops, weather/model outputs, tasks, notes, notifications, forum, files, messages, APK metadata |
| Main notification WebSocket | `ws://118.89.50.72/ws/notice/<phone>/` | Live user notifications |
| Image classification/advice | `http://106.75.19.191:3389/` and `ws://106.75.19.191:3389/` | Leaf classification and streamed follow-up advice |
| Severity inference | `http://106.75.19.191/predict` | Disease-area/severity estimation |
| SMS provider | `https://cotton.agrodigits.cn/api/v1/stt_gxg/` | Verification-code request |
| IP geolocation | `https://ipapi.co/json/` | Approximate location fallback/context |
| AMap | Key stored in app/platform files | Native location/map support |

Representative main-backend resources are:

| Area | Endpoints used by the app |
|---|---|
| Authentication | `/user/customusers`, `/api/jwt/token/` |
| Fields | `/field/list/`, `/field/detail/...`, `/field/bin/user/...`, `/field/recover/...`, `/field/share/...`, `/field/accept/share/...` |
| Crops | `/crop/list/`, `/crop/list/field/...` |
| Model data | `/weatherdata/list/crop/...`, `/phendata/list/crop/...`, `/diseasedata/list/crop/...` |
| Master data | `/master_data/variety/`, `/cultivation/method/`, `/growth/stage/`, `/fungicide/`, `/pesticide/`, `/disease/type/` |
| Tasks | `/task/user/...`, `/task/irrigation/...`, `/task/crop/protection/...` |
| Notes | `/note/list/...`, `/note/note/`, `/note/incidence/`, `/note/growthstage/` |
| Notifications | `/notice/list/...` plus field/user read variants |
| Diagnosis reports/history | `/warn/discovering/diseases/`, `/message/list/...` |
| Forum | `/forum/forums/...`, `/forum/comments/...`, `/forum/notice/...` |
| Support/update | `/suggestions/submit/`, `/apk/send-message/`, `/static/...` |

The separate classification and severity servers are not represented by a configurable interface in this repository. Their response shapes are parsed directly by the screens. They must be running with the expected contracts for the diagnosis features to work.

## 9. Localization and assets

Flutter localization is configured for Chinese and English through ARB files and generated `intl` code. In practice, many labels, statuses, alert types, regular expressions, and navigation decisions are hard-coded in Chinese, so English localization is partial.

The app bundles a large WebGIS asset tree: Leaflet, Bootstrap, jQuery, Highcharts, CSS, plugins, images, and HTML templates. These assets are declared explicitly in `pubspec.yaml`; moving or pruning them without checking the embedded map page can cause runtime WebView failures.

## 10. Platform and build configuration

### Declared toolchain

- package version: `1.0.16`;
- Dart constraint: `>=2.19.6 <3.0.0`;
- Android application ID: `com.example.grape_frontend`;
- Android minimum SDK: 21;
- Android manifest label: `葡萄通`;
- the application permits cleartext HTTP traffic because all main APIs use `http://`/`ws://`.

The repository contains standard Flutter platform directories, but the implementation is strongly mobile-specific: it imports mobile plugins, uses `dart:io`, assumes camera/gallery/location permissions, embeds a WebView, and downloads/opens Android APKs. Android is the best-supported target. Before treating iOS as production-ready, add and verify all required camera, photo-library, and location usage descriptions and validate the WebView/AMap setup. Web and desktop targets will need conditional implementations or dependency changes.

### Typical local commands

From `grape_frontend/`:

```bash
flutter pub get
flutter analyze
flutter test
flutter run
```

These commands are the intended workflow, but dependency resolution must first be repaired for a current Flutter installation.

### Current verification result

On 2026-07-19, with Flutter 3.29.3 / Dart 3.7.2, `flutter analyze` stopped during dependency resolution:

```text
flutter_localizations requires intl 0.19.0
grape_frontend requires intl ^0.18.0
version solving failed
```

The package also declares a pre-Dart-3 SDK constraint. Upgrade the SDK constraint and dependent packages together, then run analysis and tests; changing only `intl` may expose further obsolete-plugin or API issues.

The sole test, `test/widget_test.dart`, is Flutter's original counter-app template. It expects a counter and add button that do not exist in this application, so it is not a valid smoke test for the present UI.

## 11. Configuration and deployment assumptions

There is no environment/flavor configuration for development, staging, and production. Changing a backend currently requires finding multiple literal URLs throughout `lib/`, including media-URL concatenation and WebSocket construction.

The Android project contains a committed keystore and signing values in its Gradle configuration, and the AMap API key is committed in Dart and Android configuration. Both should be treated as exposed credentials: rotate them, move signing material outside the repository, and inject environment-specific secrets during builds.

APK update logic fetches `/apk/send-message/`, compares the response with a hard-coded `currentVersionCode = 16`, and opens the returned APK URL. Version information is inconsistent across `pubspec.yaml`, Android defaults, and this service; it should come from package metadata or build configuration.

## 12. Important technical risks

The following are the main issues to account for when maintaining or deploying this client:

1. **Transport security:** primary REST and WebSocket traffic is unencrypted. JWTs, phone numbers, field data, and agronomic records can travel in clear text.
2. **Authentication design:** SMS codes are returned to the client, stored/read through the user API, and compared in the app. Startup authentication is bypassed, and JWT attachment is inconsistent. Verification and authorization should be enforced server-side.
3. **Exposed credentials:** the map key, Android keystore, alias, and signing passwords are in the repository.
4. **Hard-coded infrastructure:** hosts and media prefixes are duplicated across many widgets/controllers, preventing safe environment switching.
5. **Fragile local context:** generic `SharedPreferences` keys, typos, and non-null assertions can select stale objects or crash a fresh session.
6. **Mixed responsibilities:** very large stateful screens perform rendering, networking, parsing, navigation, persistence, and calculations, making changes hard to isolate and test.
7. **Duplicated workflows:** notification handling and numerous task-status screens implement similar logic independently and can drift.
8. **Weak error handling:** many calls use broad catches, console prints, or direct response indexing, with inconsistent timeouts and authentication headers.
9. **Contract brittleness:** some history responses are repaired by replacing single quotes, media URLs are built by string splitting, and disease reporting depends on exact Chinese prose.
10. **Legacy HTTP helper:** `lib/http_util.dart` has duplicate `method == 'get'` branches, so its intended POST branch is unreachable. It should not be adopted without repair.
11. **Platform gaps:** Android permissions are broad, while iOS permission/configuration coverage appears incomplete; web/desktop compatibility is not established.
12. **No meaningful automated tests:** domain calculations, response parsing, navigation outcomes, and core screens are currently unprotected.

## 13. Relationship to `grape_backend` and the manuscript

The frontend consumes the REST and notification interfaces implemented by the adjacent `grape_backend` project for users, fields, crops, agronomic master data, model outputs, notes, warnings, tasks, and community features. The checked-in frontend additionally depends on separately hosted classification/advisory and severity services, so the adjacent backend alone is not sufficient to run every feature end to end.

Conceptually, the implementation matches the manuscript's decision-support loop:

- digitized vineyard boundaries and crop profiles establish context;
- weather, phenology, and disease-model outputs form the monitoring layer;
- notifications surface actionable risks;
- irrigation and protection workflows convert advice into management actions;
- field notes and disease reports provide observations and feedback;
- vision inference offers an additional diagnostic entry point.

When comparing paper claims with code behavior, distinguish server-computed intelligence from client behavior. The Flutter client mostly obtains and presents model outputs, orchestrates user actions, and records feedback. Forecasting, disease-risk computation, SVG generation, and most recommendation data originate outside this repository.

The manuscript's mobile screenshots correspond closely to the checked-in screens: login and polygon editing, weather/phenology/risk summaries, warning dialogs and archives, task/product/mixing pages, and image-recognition/advisory pages are all identifiable in this codebase. However, the manuscript's central term **crop season** maps to a frontend class and API resource named simply `Crop`. The frontend's crop creation/edit payload contains tree age, variety, cultivation method, and field UUID but no explicit crop year or season-renewal field. Annual separation and the stronger record-linkage/traceability claims therefore depend on backend models, timestamps, jobs, and exported database records; they cannot be established from this client alone.

## 14. Recommended reading order

For a new maintainer, the fastest path through the code is:

1. `lib/main.dart` and `lib/features/home/view/home_view.dart` for startup and tabs;
2. `lib/features/field/view/field_view.dart` for the main application hub;
3. field/crop/weather/growth controllers under `lib/features/field/controller/`;
4. `lib/features/field/view/crop_view.dart` for the monitoring workspace;
5. `lib/features/task/view/tasklist_view.dart`, then the irrigation and `sterill*` screens;
6. `lib/features/map/view/map_view.dart` and `assets/templates/WebGIS3857Draw.html` for field creation;
7. `lib/features/communition/` for diagnosis, chat, severity, and disease reporting;
8. `lib/features/note/` and `lib/features/forum/` for observations and community behavior;
9. `lib/net_config.dart`, all URL literals, and platform configuration before changing deployment environments.

That order follows the same path as the product: application shell → field context → crop intelligence → management actions → supporting feedback and community features.
