# GrapeMaster Software-Paper Revision Plan

## 1. Revision objective

This plan replaces the previous architecture-led outline. The revised manuscript will not inherit the current sequence of “conceptual architecture,” “logical architecture,” “service architecture,” and “analytical services.” Those labels make the design appear abstract and repetitive and do not provide a natural scientific narrative.

The paper will instead use a conventional structure suitable for a full-length research article in *Computers and Electronics in Agriculture* (CEA):

1. Introduction
2. Materials and methods
3. Results
4. Discussion
5. Conclusion

Within that structure, GrapeMaster will be presented as an investigator-developed agricultural software system. Its novelty is the software mechanism that integrates heterogeneous disease-management intelligence with field operations—not the use of a crop-season object and not the simple inclusion of several existing models.

This positioning is important because the [CEA aims and scope](https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture) emphasize innovation that advances agricultural computing and state that applying existing technology to a crop is not sufficient by itself.

### Implementation status (2026-07-19)

- [x] Repositioned the central contribution around model-to-management software orchestration.
- [x] Replaced the conceptual/logical architecture hierarchy with a conventional Materials and methods section.
- [x] Rewrote the Introduction with an explicit integration gap and four software contributions.
- [x] Reorganized Methods around system objectives, overall architecture, data coordination, disease-model integration, treatment feedback, image/LLM integration, and implementation evidence.
- [x] Reorganized Results around the implemented application, proactive workflow, post-symptomatic workflow, deployment demonstration, and supporting component performance.
- [x] Rewrote Discussion and Conclusion so they answer the Introduction in the same contribution order.
- [x] Revised the title, abstract, keywords, captions, tables, and supplementary terminology.
- [x] Added `SOFTWARE_CLAIM_EVIDENCE_MATRIX.md` to track support and remaining submission evidence.
- [x] Compiled and visually inspected the 31-page manuscript and 9-page supplement.
- [ ] Obtain and archive the exact deployed weather, disease-model, image-model, and LLM versions/configurations.
- [ ] Complete author information, CRediT statement, acknowledgements, and final software/data availability statements.

## 2. Essential contribution of the paper

### 2.1 Core problem

Vineyard disease-management information is fragmented across environmental monitoring, phenology estimation, disease forecasting, symptom recognition, advisory interaction, notifications, field tasks, and treatment records. The primary software problem is not the absence of any one model. It is the difficulty of making these heterogeneous components exchange information and support a coherent operational process.

### 2.2 Central thesis

GrapeMaster provides a management-oriented software orchestration mechanism that integrates environmental and crop-state information, disease forecasting, image-based diagnosis, LLM-assisted advisory, notifications, field operations, and treatment feedback into an end-to-end vineyard disease-management workflow.

### 2.3 Main innovation

The main innovation is the connection between three layers:

1. **Agricultural intelligence**
   - Weather and phenology state
   - Disease-risk modeling
   - Image-based symptom recognition
   - LLM-assisted interpretation and advisory interaction

2. **Software orchestration**
   - Model-service interfaces
   - Request construction and response handling
   - Scheduled and user-triggered execution
   - Shared identifiers and record persistence
   - Transformation of model outputs into application events

3. **Field management**
   - Warning delivery
   - Task creation and execution
   - Product and treatment recording
   - Management feedback to later disease-risk calculation
   - Historical review

The paper should demonstrate that the value of GrapeMaster arises from the interactions among these layers.

### 2.4 Contribution statements

The manuscript should consistently present the following contributions:

1. **An integrated disease-management computing framework** that combines predictive, diagnostic, advisory, and operational functions within one implemented vineyard application.

2. **A model-to-application integration mechanism** through which the backend constructs model inputs, invokes heterogeneous analytical services, stores their outputs, and translates results into user-facing management information.

3. **A management-feedback mechanism** that converts recorded field treatments into inputs for subsequent disease-risk interpretation, connecting analytical output with later software state.

4. **A deployed mobile and backend implementation** that demonstrates the complete workflow and provides supporting evidence from operational records and analytical-module results.

### 2.5 Subordinate role of crop season

Crop season is not the conceptual center or principal novelty of the revised paper. It is one implementation mechanism used to partition time-dependent records and associate them with a vineyard field.

It should appear mainly in:

- the database/entity description;
- the explanation of identifiers and record retrieval;
- the field and crop setup function; and
- the limitations if annual lifecycle semantics are not explicit in the schema.

It should not dominate the title, Introduction, contribution list, Discussion, or Conclusion.

## 3. Narrative spine: how the whole paper will echo itself

The manuscript should follow one argument from beginning to end.

| Part of paper | Question answered | Core message |
|---|---|---|
| Introduction | What important computing problem remains? | Disease-management intelligence remains fragmented and poorly connected with action and feedback. |
| Materials and methods | How was the problem addressed? | GrapeMaster uses a layered application architecture and explicit service-integration workflows. |
| Results | What was actually implemented and demonstrated? | The mobile/backend system executes proactive risk management and post-symptomatic diagnostic/advisory workflows. |
| Discussion | Why does this software design matter? | Integration changes isolated outputs into persistent, actionable, and updateable management information. |
| Conclusion | What is the lasting contribution? | A reusable method for connecting agricultural analytical services with operational disease management. |

Every major concept introduced in the Introduction should reappear as a method, an implemented result, and a discussion point. No major feature should appear late in the paper without being motivated earlier.

## 4. Target manuscript structure

### 1. Introduction

#### Paragraph 1 — Agricultural and decision context

- Explain the difficulty of managing grapevine disease under changing weather, host development, and field conditions.
- Emphasize that disease management involves repeated decisions before and after visible symptoms.
- Motivate the need to combine current state, predicted risk, diagnosis, advice, and recorded interventions.

#### Paragraph 2 — Existing analytical capabilities

- Introduce weather services, phenology models, disease models, image recognition, and LLM advisory.
- Organize them by decision role rather than presenting a flat technology list:
  - environmental and crop-state characterization;
  - pre-symptomatic risk forecasting;
  - post-symptomatic diagnosis; and
  - interpretation and interaction.
- State that strong individual models do not automatically form usable management software.

#### Paragraph 3 — Existing DSS and software platforms

- Review vineyard DSS and relevant agricultural platforms.
- Describe what they demonstrate: model delivery, monitoring, communication, or production management.
- Avoid claiming that integrated systems do not exist.
- Identify the more precise remaining problem: transparent software orchestration across heterogeneous analytical services, management operations, and feedback.

#### Paragraph 4 — Software requirements and research gap

- Derive the required capabilities:
  - common management context;
  - defined model-service interfaces;
  - persistence of model inputs and outputs;
  - conversion of outputs into warnings and operations;
  - treatment-aware updating;
  - support for both proactive and post-symptomatic workflows; and
  - presentation in a field-usable application.
- Define this as a computing and software-integration problem.

#### Paragraph 5 — GrapeMaster and contributions

- Introduce the Flutter frontend, Django backend, relational persistence, scheduled processing, and analytical services.
- State the four contributions explicitly.
- Say that deployment records and component results are used to demonstrate the implemented system, not to claim agronomic or economic effectiveness.

#### Introduction completion test

- The gap is software orchestration, not “lack of a crop-season unit.”
- The disease model and LLM both have clear but different roles.
- The contribution list predicts the organization of Sections 2–4.
- No evaluation result is presented as the paper’s reason for existence.

### 2. Materials and methods

This section should explain how GrapeMaster was designed and implemented. It should replace the current abstract sequence of conceptual and logical architectures.

#### 2.1 System objectives and usage scenarios

Purpose:

- Define the intended users and agricultural context.
- Explain the management problems the software is designed to support.

Content:

- Proactive workflow: environmental state → disease risk → notification → task → treatment → updated review.
- Post-symptomatic workflow: field image or question → recognition/context → LLM advisory → user interpretation or action.
- Key functional and information requirements derived from these workflows.
- Scope boundaries: decision support rather than autonomous pesticide prescription.

Suggested table:

| Management need | Software requirement | Implemented mechanism |
|---|---|---|
| Anticipate infection risk | Combine weather, phenology, susceptibility, and management state | Disease-model service request |
| Deliver timely information | Convert results to visible events | Notification and warning services |
| Record responses | Represent operations and products | Task and product records |
| Reflect previous treatment | Feed management records back into analysis | Treatment-to-model transformation |
| Interpret symptoms | Connect images with diagnostic output | Image-recognition service |
| Support interaction | Provide contextual natural-language advice | LLM advisory service |

#### 2.2 Overall software architecture

Use this natural title. Do not divide the discussion into “conceptual architecture” and “logical architecture.”

Describe:

- Flutter mobile application;
- Django REST application backend;
- relational database and reference data;
- scheduled processing and message delivery;
- external or independently deployed analytical services; and
- communication among these components.

The section should answer:

- Which component performs each responsibility?
- Which component owns persistent records and identifiers?
- Which interactions are scheduled, user-triggered, or asynchronous?
- Which model services are internal or external to the main backend?
- How are unavailable services or failed requests handled?

Primary figure:

- One overall architecture figure with real software components and real data/control flows.
- Use arrows only for implemented communication.
- Distinguish API calls, scheduled triggers, and persistent storage visually.

#### 2.3 Data organization and workflow coordination

Purpose:

- Explain how heterogeneous records remain usable across the application.

Describe:

- field identity;
- crop or crop-season record as a temporal database entity;
- weather, phenology, model request-response, notification, task, product, image, and advisory records;
- identifiers, timestamps, and foreign-key relationships;
- direct linkage versus shared-context association; and
- how the backend retrieves and assembles state for the frontend and model services.

Do not claim that the data entity itself is the paper’s innovation. Its importance comes from enabling orchestration.

Suggested figure or table:

- A compact entity/data-flow diagram limited to objects necessary for the two principal workflows.

#### 2.4 Integration of environmental and phenological information

Describe:

- actual environmental-data provider;
- acquisition schedule;
- transformation and storage;
- phenology calculation or service call;
- use of weather and phenology by the disease model; and
- presentation to the mobile application.

The section must distinguish deployed behavior from planned or platform-compatible alternatives.

#### 2.5 Integration of the disease-risk model

This should be one of the technical centers of the paper.

Describe the complete interface:

1. Trigger for model execution.
2. Backend assembly of weather, phenology, susceptibility, target disease, and treatment history.
3. Request schema and service endpoint.
4. Disease-service calculation sequence.
5. Response schema and interpretation.
6. Request-response persistence.
7. Translation of results into frontend risk information and notifications.
8. Supported diseases and validation status.
9. Deployed model version and configuration.

Avoid turning this subsection into a long biological-model paper. Include only enough scientific formulation to understand inputs, outputs, and software behavior; move extensive equations or parameters to the supplement.

#### 2.6 Integration of field operations and treatment feedback

This should be presented directly after the disease model because it completes the integration argument.

Describe:

1. How a user creates or completes a plant-protection task.
2. How fungicide or pesticide products are attached to a task.
3. How product, target, date, and protection information are transformed into model inputs.
4. When recalculation is initiated.
5. How the updated request and response are stored and presented.

Be exact about linkage:

- product-to-task linkage is direct;
- task and notification may share management context without a direct causal foreign key;
- do not label contextual linkage as proven notification-to-task causality.

#### 2.7 Integration of image recognition and LLM advisory

Present these as complementary post-symptomatic services.

##### Image-recognition integration

- Image acquisition and upload.
- Preprocessing or service payload.
- Classifier endpoint and deployed model version.
- Disease classes and confidence output.
- Response storage and frontend display.

##### LLM integration

- Advisory entry point in the frontend.
- Backend or hosted-service endpoint.
- Context included with the user query.
- Relationship to image-recognition output.
- Prompting, fine-tuning, or retrieval mechanism, if used.
- Response storage and conversation history.
- Failure handling and safety statement.
- Clear boundary between informational advice and regulated plant-protection decisions.

Required evidence before finalizing this subsection:

- exact deployed model and version;
- request and response examples;
- endpoint or service documentation;
- context-construction logic;
- storage relationships; and
- confirmation of which code belongs to the deployed service rather than only a published framework.

If some deployment details remain unavailable, describe the verified interface and role without overstating the internal LLM implementation.

#### 2.8 Software implementation and deployment

Describe:

- principal languages and frameworks;
- backend and model-service deployment;
- database;
- scheduling and messaging mechanisms;
- mobile platforms;
- versioning and software availability;
- hardware or cloud environment where relevant; and
- data/security mechanisms that are actually implemented.

A concise software-stack table is preferable to dispersed framework descriptions.

#### 2.9 Demonstration and supporting evidence design

This short subsection explains how the implementation is demonstrated.

Include:

- operational-record snapshot and screening rules;
- selection of the representative end-to-end case;
- criteria used to reconstruct workflow stages;
- datasets and metrics for phenology, disease-risk, and image-recognition components; and
- explicit statement that LLM quality, usability, agronomic efficacy, and economic effects were not evaluated unless new studies are added.

This is supporting methodology, not the main methodological contribution.

### 3. Results

Results should show the implemented software and its behavior. They should follow the same order as the workflows and methods.

#### 3.1 Implemented GrapeMaster application

- Present the main mobile workspaces and backend-supported functions.
- Organize by user purpose rather than screen sequence.
- Connect each visible function to the method subsection that implements it.

#### 3.2 Proactive disease-management workflow

Demonstrate:

- field setup;
- weather and phenology display;
- disease-risk output;
- warning delivery;
- task and product recording;
- treatment feedback; and
- subsequent risk review.

Use one coherent case or sequence instead of several disconnected screenshots.

#### 3.3 Post-symptomatic diagnostic and advisory workflow

Demonstrate:

- image submission;
- recognition output;
- advisory interaction;
- storage or retrieval of relevant records; and
- user-facing safety boundary.

Do not imply that the LLM’s agronomic quality has been validated if it has not.

#### 3.4 Deployment demonstration

- Summarize users, fields, analytical records, notifications, tasks, and product records.
- Use counts as evidence that the implemented software generated its intended objects.
- Present record linkage carefully.
- Avoid interpreting counts as effectiveness, adoption, or agronomic benefit.

#### 3.5 Supporting performance of analytical components

- Report phenology, downy mildew, and image-recognition results compactly.
- Explain why each result is sufficient for its role in the demonstrated software.
- Keep full model-evaluation detail in the supplement if it interrupts the software narrative.
- State directly that the results validate components, not the complete software workflow or production outcomes.

### 4. Discussion

The Discussion should return to the four contribution statements in the same order.

#### 4.1 From isolated models to operational disease-management intelligence

- Explain what becomes possible because the models and management functions are connected.
- Contrast integration with simply displaying independent model outputs.

#### 4.2 Orchestrating heterogeneous analytical services

- Discuss differences among scheduled environmental processing, disease forecasting, image inference, and conversational AI.
- Explain why backend-owned requests, records, and interfaces matter.
- Discuss replaceability and extension carefully as design implications.

#### 4.3 Connecting risk information with field operations and feedback

- Discuss treatment-aware updating as the strongest software integration example.
- Explain the limits of current provenance where notification-to-task linkage is contextual.

#### 4.4 Relationship to existing agricultural DSS and platforms

Compare systems using concrete dimensions:

- analytical services integrated;
- proactive and reactive support;
- model-to-operation connection;
- treatment feedback;
- mobile interaction;
- record persistence; and
- deployment evidence.

Do not claim universal superiority. State the specific design distinction GrapeMaster contributes.

#### 4.5 Limitations and future work

Address, where applicable:

- exact deployment/version reproducibility;
- software availability;
- service coupling and configuration;
- authentication and security;
- automated testing and failure recovery;
- direct provenance among warnings, tasks, and treatments;
- disease and regional coverage;
- independent LLM evaluation;
- usability and adoption;
- agronomic and economic outcomes; and
- multi-season or multi-region deployment.

Future work should follow from these limitations, not introduce unrelated technologies.

### 5. Conclusion

The Conclusion should contain four moves:

1. Restate the fragmentation problem.
2. State the integrated software solution.
3. Summarize model orchestration, field-operation connection, and feedback.
4. State the broader significance for agricultural decision-support software.

Crop season should not be the concluding message. Record counts and component metrics should appear only as brief supporting evidence.

## 5. Figures and tables required for a coherent paper

### Main-text figures

1. **Overall GrapeMaster software architecture**
   - Mobile frontend, backend, database, schedulers, and analytical services.

2. **Disease-model integration and management-feedback sequence**
   - State acquisition, request assembly, risk response, notification, task, treatment, and recalculation.

3. **Image-recognition and LLM advisory sequence**
   - Image/question input, service invocation, context exchange, response, and presentation.

4. **Representative mobile application workflow**
   - A small set of screens arranged as one task sequence.

5. **Deployment or record-chain demonstration**
   - Only if it adds evidence not already clear from the workflow figures.

### Main-text tables

1. User needs, software requirements, and implemented components.
2. Analytical-service interfaces: trigger, inputs, outputs, storage, and application role.
3. Technology stack and deployment roles.
4. Compact deployment and component-evidence summary.

### Supplementary material

- detailed entity relationships;
- full API/request-response schemas;
- disease-model equations and parameter tables;
- complete operational-record counts and screening rules;
- additional screenshots; and
- extended component-evaluation details.

## 6. Claim and terminology rules

Apply these rules throughout the paper:

1. Do not describe GrapeMaster as a collection of tools; describe the integration mechanism and resulting workflow.
2. Do not make crop season the primary novelty.
3. Do not use “conceptual architecture” or “logical architecture” as major manuscript headings.
4. Use “overall software architecture,” “data organization,” “model integration,” and “operational workflow.”
5. Distinguish implemented, deployed, platform-compatible, and future capabilities.
6. Distinguish direct database linkage, service communication, and contextual association.
7. Do not use “closed loop” unless the exact loop and linkage are demonstrated.
8. Do not claim scalability, reliability, usability, or security without appropriate evidence.
9. Present model accuracy as component evidence, not proof of software effectiveness.
10. Present the LLM as a verified software service integration; do not infer undocumented implementation details.
11. Do not claim that advisory quality or field outcomes were validated when they were not.
12. Use one consistent name for every software component in text, figures, tables, and supplement.

## 7. Step-by-step execution plan

### Step 1 — Approve the new central contribution

- [ ] Approve the central thesis in Section 2.2.
- [ ] Approve the four contribution statements in Section 2.4.
- [ ] Remove crop-season-centered positioning from the planned title and abstract.
- [ ] Select the preferred central phrase: `software orchestration`, `model-to-management integration`, or a combination of both.

Deliverable: one approved positioning paragraph used as the reference for all later revisions.

### Step 2 — Build the implementation evidence matrix

- [ ] Map each contribution to frontend, backend, model-service, database, and deployment evidence.
- [ ] Verify actual provider names, endpoints, model versions, and deployed configurations.
- [ ] Separate direct code evidence from external-service documentation.
- [ ] Identify claims that must be weakened or supported by additional material.

Deliverable: `SOFTWARE_CLAIM_EVIDENCE_MATRIX.md` in the root folder.

### Step 3 — Replace the manuscript outline

- [ ] Create the new top-level Introduction/Methods/Results/Discussion/Conclusion skeleton.
- [ ] Map reusable paragraphs, figures, tables, and references into the new sections.
- [ ] Do not delete useful material until it has been relocated or marked for removal.
- [ ] Remove the conceptual/logical architecture hierarchy.

Deliverable: revised LaTeX section skeleton with placeholder notes.

### Step 4 — Rewrite the Introduction

- [ ] Write the five-paragraph rationale described above.
- [ ] End with the four contribution statements.
- [ ] Check that every promised contribution has a matching Methods and Results subsection.

Deliverable: complete revised Introduction.

### Step 5 — Write Materials and methods, Sections 2.1–2.3

- [ ] System objectives and usage scenarios.
- [ ] Overall software architecture.
- [ ] Data organization and workflow coordination.
- [ ] Revise or replace the main architecture figure.

Deliverable: natural system-design foundation without abstract architecture terminology.

### Step 6 — Write disease-model and treatment integration, Sections 2.4–2.6

- [ ] Environmental and phenological data integration.
- [ ] Disease-model interface and execution.
- [ ] Field-operation and treatment-feedback integration.
- [ ] Verify the text against actual backend and disease-service behavior.

Deliverable: the principal technical contribution section.

### Step 7 — Write image-recognition and LLM integration, Section 2.7

- [ ] Obtain or verify deployed-service evidence.
- [ ] Describe image and language services separately, then explain their coordination.
- [ ] Define context, outputs, storage, and safeguards.
- [ ] Create the integration sequence figure.

Deliverable: technically supportable AI-integration subsection.

### Step 8 — Complete implementation and demonstration methods, Sections 2.8–2.9

- [ ] Consolidate technology stack and deployment description.
- [ ] Define the operational-record and component-evidence procedures concisely.

Deliverable: complete Materials and methods section.

### Step 9 — Rebuild Results around implemented workflows

- [ ] Implemented application overview.
- [ ] Proactive disease-management workflow.
- [ ] Post-symptomatic image/LLM workflow.
- [ ] Deployment demonstration.
- [ ] Supporting component results.

Deliverable: Results section that mirrors Methods and shows system behavior.

### Step 10 — Rewrite Discussion and Conclusion

- [ ] Discuss the four contributions in their original order.
- [ ] Compare with existing DSS using concrete software dimensions.
- [ ] State limitations directly.
- [ ] End with the integration contribution, not crop season or evaluation metrics.

Deliverable: a Discussion and Conclusion that answer the Introduction.

### Step 11 — Rewrite title, abstract, highlights, and keywords

- [ ] Complete only after the main paper is stable.
- [ ] Make architecture and model-to-management integration visible in the abstract.
- [ ] Reduce detailed record counts if they obscure the software contribution.
- [ ] Ensure title and keywords fit CEA’s agricultural-computing emphasis.

Deliverable: aligned high-visibility submission text.

### Step 12 — Perform cross-manuscript consistency review

- [ ] Check Introduction promises against Methods, Results, Discussion, and Conclusion.
- [ ] Check terminology across text, figures, tables, and supplement.
- [ ] Check all claims against the evidence matrix.
- [ ] Remove repetition and orphaned concepts.
- [ ] Compile the manuscript and visually inspect the PDF.
- [ ] Conduct language editing only after technical consistency is achieved.

Deliverable: internally consistent, submission-ready manuscript.

## 8. Consistency matrix for final review

| Introduction promise | Methods explanation | Results demonstration | Discussion implication |
|---|---|---|---|
| Integrates heterogeneous analytical services | Sections 2.2, 2.4, 2.5, and 2.7 | Sections 3.1–3.3 | Section 4.2 |
| Connects risk with field operations | Sections 2.5 and 2.6 | Section 3.2 | Section 4.3 |
| Incorporates treatment feedback | Section 2.6 | Section 3.2 and workflow replay | Section 4.3 |
| Supports proactive and post-symptomatic decisions | Sections 2.1, 2.5, and 2.7 | Sections 3.2 and 3.3 | Sections 4.1 and 4.2 |
| Provides an implemented mobile/backend system | Sections 2.2 and 2.8 | Sections 3.1 and 3.4 | Sections 4.1 and 4.4 |

If a row cannot be completed across all four columns, either the claim needs additional evidence or it should not be a primary contribution.

## 9. Definition of completion

The adaptation is complete when:

- the manuscript reads as one continuous argument from fragmented intelligence to integrated operational software;
- crop season is a subordinate data-design detail rather than the headline contribution;
- the Methods section uses natural headings and explains the actual implementation;
- disease-model, image-recognition, and LLM integration are described through real interfaces and workflows;
- Results follow the same order as Methods;
- Discussion answers the questions raised in the Introduction;
- deployment and component metrics support but do not dominate the software contribution;
- all major claims are technically verifiable; and
- the paper clearly advances an investigator-developed agricultural computing approach rather than merely applying existing tools to grape production.
