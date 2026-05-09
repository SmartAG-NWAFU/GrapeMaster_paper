# Bakir et al. (2026) - Structured Reference Note

## Bibliographic Information

This section keeps the citation metadata for later literature review and reference management.

- Title: A scalable, end-to-end IoT and remote sensing platform for precision rangeland and livestock management
- Authors: Mehmet E. Bakir, Andres R. Perea, Micah Funk, Sajidur Rahman, Maximiliano J. Spetter, Lara Macon, Andrew Cox, Richard E. Estell, Huiping Cao, Andres F. Cibils, Sheri A. Spiegal, Brandon T. Bestelmeyer, Santiago A. Utsumi
- Journal: Computers and Electronics in Agriculture
- Year: 2026
- Volume and article number: 247, 111615
- DOI: https://doi.org/10.1016/j.compag.2026.111615
- Keywords: Precision ranching; Internet of Things; LoRaWAN; Remote sensing; Livestock monitoring; Rangeland management; Artificial intelligence

## 1. Introduction

The introduction builds the problem context for precision ranching. It first explains that extensive rangelands are difficult to manage because they are large, remote, environmentally variable, and often poorly connected. These conditions make routine livestock monitoring labor-intensive and limit the direct transfer of precision agriculture technologies from cropland or confined livestock systems.

The authors then identify the technical research gap: previous studies have discussed precision ranching concepts, tested LoRaWAN communication, or demonstrated small prototypes, but few have provided a complete end-to-end platform that integrates IoT sensing, data ingestion, storage, analytics, remote sensing, and user-facing decision support at operational scale.

For writing reference, this section follows a useful logic: practical management challenge -> limitation of existing technologies -> gap in previous studies -> need for a scalable platform -> study objectives. This structure can be reused when introducing an agricultural IoT platform or smart farming system.

### Main Objectives

The study aims to design a scalable, modular, and vendor-agnostic precision ranching architecture; integrate distributed IoT sensors and satellite imagery; implement AI-driven analytics; and validate the platform through large-scale field deployment.

This objective framing is useful because it presents the paper as a system-development and validation study rather than only a sensor or algorithm paper.

## 2. System Architecture

This section is the conceptual and technical backbone of the paper. The authors describe a multi-tier architecture designed to handle connectivity constraints, power limitations, heterogeneous data, and large-scale deployment requirements in remote rangelands.

For writing reference, this section is especially useful because it separates the system into clear layers. This makes the architecture easy to explain and helps readers understand how raw field data move from sensors to management decisions.

### 2.1 Conceptual Architecture

The conceptual architecture presents the high-level data flow. It divides the platform into four major components: data acquisition, data ingestion and storage, data processing and analytics, and application and presentation.

The main function of this subsection is to explain what each layer does before introducing specific software or hardware. This is a useful writing strategy: first describe the system logic in abstract terms, then explain the implementation details later.

### 2.2 Logical Architecture

The logical architecture expands the conceptual model into concrete components and interactions. It explains how sensors, gateways, network servers, ingestion nodes, databases, task schedulers, analytics modules, APIs, and user interfaces work together.

For future writing, this subsection provides a good model for translating a conceptual framework into an implementable system. It also justifies why the platform is modular, scalable, and replaceable at the component level.

### Architecture Layers

The Data Acquisition Layer collects sensor data from animal collars, water-level sensors, rain gauges, and other IoT devices. LoRaWAN is used because it supports long-range, low-power transmission in remote agricultural environments.

The Data Ingestion and Storage Layer receives and validates raw data, then stores it in MongoDB. This layer is designed for high-frequency, heterogeneous IoT payloads and fault-tolerant data storage.

The Data Processing and Analytics Layer converts raw data into useful indicators through cleaning, transformation, feature extraction, and machine learning inference. Scheduled tasks prepare processed results before users request them.

The Application and Presentation Layer provides maps, dashboards, charts, alerts, and management interfaces. This layer turns processed data into user-facing decision-support information.

## 3. Implementation

The implementation section explains how the logical architecture is translated into a working platform. The authors emphasize open-source and free software tools to improve flexibility, reduce vendor lock-in, and support deployment across different server environments.

For writing reference, this section is useful because it connects architectural design with specific technical choices. It shows how to report hardware, software, data processing, and user-interface implementation in a structured way.

### 3.1 Data Acquisition Layer Implementation

This subsection describes the deployed IoT devices and communication infrastructure. The platform uses animal collar trackers, water-level sensors, rain gauges, LoRaWAN gateways, and a LoRaWAN network server.

Animal collars provide GNSS locations and accelerometer-based activity data. Water-level sensors monitor troughs and tanks. Rain gauges provide localized precipitation data. Gateways are installed as solar-powered base stations or portable trailer/tripod systems.

For writing reference, this subsection shows the importance of reporting field hardware details, including transmission frequency, battery life, mounting strategy, power supply, and communication protocol.

### 3.2 Data Ingestion and Storage Implementation

This subsection explains how raw data are received and stored. Nginx is used as a load balancer, Flask servers act as ingestion nodes, and MongoDB stores raw IoT data with replication for redundancy.

The key writing value is that the authors justify the storage design based on the nature of IoT data: high volume, high velocity, semi-structured payloads, and device-level heterogeneity.

### 3.3 Data Processing and Analytics Implementation

This subsection describes the computational tasks that convert sensor streams into livestock and rangeland indicators. Python, Pandas, Scikit-learn, XGBoost, and Celery are used for data processing, model execution, and task scheduling.

The analytics include walking-distance calculation, activity-count calculation, behavior classification, and event detection. These modules are scheduled periodically, which reduces user-facing delays and keeps results ready for visualization.

For writing reference, this subsection is useful for presenting analytical modules with a consistent pattern: input data, method, output, and management meaning.

#### Walking Distance Calculation

Walking distance is calculated from consecutive GNSS points using the haversine formula. This converts raw location records into movement indicators that can support grazing analysis, anomaly detection, and calving detection.

#### Activity Count Calculation

Activity count is derived from cumulative accelerometer values by subtracting the previous value from the latest value. This converts raw motion payloads into interval-level activity indicators.

#### Behavior Classification

The behavior model classifies cattle behavior into grazing, resting, and walking. It is trained using video-labeled data and implemented with XGBoost, achieving more than 90% accuracy on a holdout test set.

#### Event Detection

The event detection module focuses on calving prediction. It uses location, activity, walking distance, and nearest-neighbor features. The model is promising but limited by the small number of confirmed calving events, making it a useful example of rare-event detection in agricultural AI.

### 3.4 Application and Presentation Implementation

This subsection explains the software stack used to deliver processed information to users. Django manages web application logic, PostgreSQL/PostGIS supports structured and geospatial queries, and Leaflet, Plotly.js, D3.js, DataTables, and Bootstrap support maps and visual analytics.

The platform also integrates the Rangeland Analysis Platform and Google Earth Engine to include satellite-derived vegetation and forage productivity information.

For writing reference, this subsection shows how to describe the transition from backend analytics to practical decision-support interfaces.

## 4. Deployment

The deployment section validates that the platform works beyond a small prototype. The system was deployed across 12 ranching operations in four US states, covering more than 500,000 acres of arid and semiarid rangelands.

The deployment included 27 LoRaWAN gateways, 931 cattle tracking collars, 19 water-level sensors, and 7 rain gauges. At the time of reporting, the platform had ingested approximately 130.4 million cattle-collar packets, 810 thousand rain-gauge readings, and 2.9 million water-level measurements.

For writing reference, this section is important because it shows how to report operational validation: geographic coverage, number of sites, number of devices, data volume, communication infrastructure, and power solutions.

### Deployment Scale by State

| State | Ranches | Gateways | Collar trackers | Rain gauges | Water-level sensors |
|---|---:|---:|---:|---:|---:|
| New Mexico | 6 | 13 | 729 | 3 | 10 |
| Utah | 1 | 5 | 35 | 1 | 2 |
| Arizona | 4 | 7 | 132 | 2 | 6 |
| California | 1 | 2 | 35 | 1 | 1 |
| Total | 12 | 27 | 931 | 7 | 19 |

## 5. Features and Functionalities

This section describes the platform from the user's perspective. After explaining architecture, implementation, and deployment, the authors show what users can actually do with the system.

For writing reference, this is a useful order: first describe the technical system, then explain user-facing functions and decision-support value.

### 5.1 Monitoring

The monitoring interface provides an interactive map for viewing animals, pasture boundaries, grazing areas, water sources, rain gauges, and device status. Users can create, edit, import, and export spatial features.

This function demonstrates how WebGIS can serve as the central interface for agricultural IoT platforms.

### RAP Map and Remote Sensing Visualization

The platform integrates RAP maps to visualize vegetation cover and aboveground biomass productivity. Users can compare time periods, vegetation classes, and productivity changes using customizable expressions.

This function shows how remote sensing can be connected with ground IoT data to support grazing and resource allocation decisions.

### Movement Timeline and Heatmaps

The movement timeline allows users to replay cattle movement over selected time periods. Heatmaps summarize high-use areas and can be filtered by behavior such as grazing, walking, or resting.

This function is useful for explaining spatiotemporal behavior visualization and pasture-use analysis.

### 5.2 Cow Events

The cow events page displays machine-learning predictions of events such as calving. It provides feature tables and time-series plots so users can interpret why an event was predicted.

This function shows how AI outputs can be made more interpretable by linking predictions to supporting behavioral and spatial features.

### 5.3 Cow Analytics

The cow analytics page provides individual and herd-level analysis of activity, walking distance, and behavior budgets. It helps identify animals that deviate from normal herd patterns.

This function is useful for writing about animal-level monitoring, anomaly detection, and herd management dashboards.

### 5.4 Water-Level Sensors

The water-level interface displays 10-minute water tank or trough reports and allows users to set low-water and overflow thresholds. This supports timely water-resource management in remote pastures.

This function demonstrates how static environmental sensors can reduce field inspection labor and improve operational response.

### 5.5 Rain Gauges

The rain-gauge interface displays interval-specific and cumulative precipitation. These data help users interpret forage production and vegetation dynamics.

This function shows how localized weather data can complement satellite-derived vegetation information and animal movement data.

## 6. Discussion

The discussion explains the scientific and practical significance of the platform. The authors argue that the study advances precision ranching by moving beyond conceptual proposals and network feasibility tests toward a complete operational system.

For writing reference, the discussion is organized around three major points: how the work addresses previous research gaps, what its main strengths and innovations are, and what limitations remain.

### 6.1 Advancing Solutions to Established Research Gaps

This subsection compares the study with previous work. Earlier studies often focused on LoRaWAN connectivity, small-scale prototypes, or conceptual frameworks. In contrast, this platform integrates sensing, storage, analytics, remote sensing, and decision support at a much larger operational scale.

This is useful for writing a discussion because it explicitly connects the results back to the research gap introduced earlier.

### 6.2 Proposed Strengths and Innovations

The authors highlight several strengths: vendor-agnostic design, containerized deployment, hybrid database architecture, modular analytics, integration of satellite and ground data, and practical field adaptations such as solar-powered portable gateways.

This subsection is useful as a reference for discussing innovation in system papers, where novelty often lies in integration, scalability, deployment robustness, and operational usability rather than a single new algorithm.

### 6.3 Limitations and Future Directions

The limitations include hardware and deployment costs, dependence on internet backhaul, limited training data for calving detection, uncertain model transferability across breeds or regions, and processing latency from scheduled tasks.

Future directions include lower-cost infrastructure, shared gateway models, edge-cloud or hybrid architectures, larger datasets, iterative model retraining, and broader validation across environments.

## 7. Conclusion

The conclusion restates the paper's main contribution: a scalable, modular, open-source-oriented precision ranching platform that integrates IoT sensors, LoRaWAN communication, satellite imagery, AI analytics, and user-facing decision support.

The authors emphasize that successful deployment across multiple ranches and approximately 1,000 sensors validates the platform's operational feasibility. The conclusion also frames the platform as an architectural blueprint for future data-driven, sustainable, and resilient rangeland livestock management systems.

For writing reference, this conclusion is effective because it returns to the original problem, summarizes the system-level solution, mentions validation scale, and points toward broader future use.

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
