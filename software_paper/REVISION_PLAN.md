# GrapeMaster Software-Paper Revision Plan

## Implementation status

An initial full implementation of this plan was completed in the `software_paper` workspace on 2026-07-19. The manuscript was reorganized as a software paper, the technical supplement was aligned with the implementation, a claim-to-code evidence matrix was added, and both PDFs were compiled and visually verified. Remaining items require author or deployment-owner input: journal/article-type confirmation, author metadata, immutable software/model releases, hosted image/LLM artifacts, and final public availability statements.

## Purpose of this plan

This document provides a step-by-step plan for adapting `paper/manuscript_S.tex` into a software paper centered on the design, architecture, implementation, functions, and analytical-model integration of GrapeMaster.

The revision should not present GrapeMaster primarily as a software-evaluation experiment. Deployment records, workflow replay, and model-performance results will remain in the paper, but they will support the description and credibility of the software rather than define its main contribution.

## Target paper identity

### Central thesis

GrapeMaster is an integrated vineyard disease-management software system that uses a field-linked crop-season context to coordinate environmental and phenological data, disease-risk models, warning and task services, treatment feedback, image recognition, and LLM-assisted advisory functions within one mobile and backend workflow.

### Main software contributions

The revised paper should consistently present four contributions:

1. **Crop-season-centered software architecture**
   - Organizes persistent field information and season-specific analytical and management records.
   - Provides a shared context for data exchange, retrieval, and historical review.

2. **Service-oriented analytical-model integration**
   - Integrates weather, phenology, disease-risk, image-recognition, and LLM advisory services through backend interfaces.
   - Separates analytical services from application and management services so models can be updated or replaced.

3. **Risk-to-action-to-feedback workflow**
   - Connects disease-risk interpretation to notifications, field tasks, applied products, treatment feedback, and subsequent model updating.
   - Converts analytical outputs into usable software functions rather than leaving them as isolated predictions.

4. **Implemented mobile and backend platform**
   - Combines a Flutter mobile frontend, Django backend, relational records, scheduled processing, and independently deployable model services.
   - Demonstrates the architecture through implemented functions, deployment records, and a representative end-to-end workflow.

### Role of evaluation evidence

The evidence should have a supporting role:

- Deployment records show that the software was implemented and used to generate connected records.
- Workflow replay illustrates how the architecture operates in a real record chain.
- Phenology, disease-risk, and image-recognition results establish that the integrated analytical components provide credible outputs.
- LLM advisory should be described as an integrated auxiliary service. Its quality should not be claimed as validated unless an independent evaluation is added.

## Terminology and claim rules

These rules should be applied throughout the revision.

1. Use **software**, **platform**, or **system** for GrapeMaster; avoid switching among these terms without purpose.
2. Use **crop-season context** or **crop-season management unit** for the central software object.
3. Do not make annual lifecycle claims stronger than the implemented schema and deployment records support. If necessary, describe annual renewal as an operational convention.
4. Use **risk-to-action-to-feedback workflow** or **traceable management workflow** rather than claiming a fully causal closed loop.
5. Distinguish direct database linkage from records that are connected only through a shared crop-season context.
6. Present the disease-risk model as a pre-symptomatic decision-support service.
7. Present image recognition as a post-symptomatic diagnostic service.
8. Present the LLM as an advisory and interaction service that interprets diagnostic or management context.
9. Do not describe the LLM as independently validated unless new evidence is provided.
10. Avoid broad claims such as “no integrated platform exists” or “the challenge is no longer model development.”
11. Use **modular** or **service-oriented** only where the service boundaries and interfaces are documented.
12. Use **extensible** as a design property, not as a measured result, unless an extension experiment is added.

## Target manuscript structure

### 1. Introduction

- Vineyard disease-management problem.
- Existing weather, phenology, disease-risk, image-recognition, and LLM technologies.
- Software-integration problem: heterogeneous inputs, outputs, time scales, interfaces, and operational roles.
- Requirements for a unified vineyard disease-management application.
- GrapeMaster overview and explicit software contributions.

### 2. Software design requirements

- Intended users and operational setting.
- Core management scenarios.
- Functional requirements.
- Data and traceability requirements.
- Analytical-service integration requirements.
- Design principles and boundaries.

### 3. System architecture

- Conceptual architecture.
- Logical and data architecture.
- Frontend, backend, and analytical-service layers.
- Service communication and deployment architecture.
- Crop-season context and identifier relationships.

### 4. Analytical-model integration

- Common model-integration pattern.
- Weather and phenology integration.
- Disease-risk service inputs, outputs, scheduling, and storage.
- Treatment-feedback translation and risk-model updating.
- Image-recognition service integration.
- LLM context construction, service interaction, response storage, and safeguards.
- Failure handling, unavailable services, and interface limitations.

### 5. Software functions and operational workflows

- Account, field, and crop-season configuration.
- Weather, phenology, and risk workspace.
- Notification and warning delivery.
- Task creation and treatment-product recording.
- Treatment feedback and risk review.
- Symptom-image recognition and LLM advisory.
- Historical record review.

### 6. Implementation and deployment demonstration

- Technology stack and deployment configuration.
- Operational-record coverage.
- Representative end-to-end workflow replay.
- Supporting analytical-module performance.
- Clearly stated interpretation boundaries.

### 7. Discussion

- Advantages of the software architecture.
- Value of combining proactive and reactive analytical services.
- Value of connecting model outputs with management functions.
- Model replacement and extension possibilities.
- Comparison with existing vineyard DSS and agricultural platforms.
- Current software, evidence, and deployment limitations.

### 8. Conclusion

- Restate the software problem and implemented solution.
- Summarize architecture, integration, and workflow contributions.
- Avoid presenting model accuracy or record counts as the main conclusion.

## Mapping from the current manuscript

| Current section | Revision action | Target location |
|---|---|---|
| Introduction | Substantially rewrite the rationale and contributions | Introduction |
| System architecture | Retain, tighten, and add explicit frontend/backend/model boundaries | System architecture |
| Analytical Services subsection | Expand into integration patterns and data contracts | Analytical-model integration |
| Implementation | Split between architecture, model integration, and implementation demonstration | Sections 3, 4, and 6 |
| Platform Features and Functionalities | Retain but organize by user workflow rather than screenshots | Software functions and operational workflows |
| Deployment and Operational-Record Audit | Rename and reposition as implementation/deployment evidence | Implementation and deployment demonstration |
| Evaluation of Platform-Compatible Analytical Modules | Condense and present as supporting component evidence | Implementation and deployment demonstration |
| Discussion | Reorganize around software-design decisions and integration lessons | Discussion |
| Conclusion | Rewrite around the software contribution | Conclusion |

## Step-by-step revision workflow

### Step 1 — Freeze the software-paper positioning

**Objective:** Establish one consistent paper identity before rewriting individual sections.

Tasks:

- [ ] Confirm the target journal and article type.
- [ ] Confirm the preferred software name and capitalization: `GrapeMaster`.
- [ ] Approve the central thesis in this plan.
- [ ] Approve the four primary software contributions.
- [ ] Decide whether “crop-season-centered” remains in the title and abstract.
- [ ] Select one principal term for the central object: crop season, crop-season context, or crop-season management unit.

Completion check:

- The title, one-sentence thesis, and contribution list describe the same software paper.

### Step 2 — Build a claim-to-implementation evidence table

**Objective:** Ensure every important software claim is supported by code, deployment records, figures, or documentation.

Tasks:

- [ ] Create one row for every architectural and integration claim.
- [ ] Record the relevant frontend file, backend model/API, model-service endpoint, database relationship, and manuscript figure/table.
- [ ] Classify each relationship as direct identifier linkage, contextual linkage, runtime communication, or conceptual association.
- [ ] Mark claims requiring external deployment information or source code.
- [ ] Resolve inconsistencies such as weather-provider naming and deployed disease-model configuration.
- [ ] Record the exact evidence available for the deployed image-recognition and LLM services.

Required evidence for the LLM section:

- [ ] Model name and version.
- [ ] Hosting or deployment location.
- [ ] Request endpoint and request schema.
- [ ] Context supplied to the model.
- [ ] Response schema and storage mechanism.
- [ ] Relationship between image recognition and advisory generation.
- [ ] Prompt, fine-tuning, or retrieval mechanism, if applicable.
- [ ] Failure behavior and user-facing safeguards.
- [ ] Evidence distinguishing the published framework from the deployed GrapeMaster service.

Completion check:

- No primary contribution depends on an undocumented service or unsupported relationship.

### Step 3 — Rewrite the Introduction

**Objective:** Make software integration, rather than evaluation, the rationale of the paper.

Tasks:

- [ ] Retain the applied vineyard disease-management motivation.
- [ ] Reorganize analytical technologies by software role rather than listing features.
- [ ] Explain why heterogeneous models are difficult to combine in operational software.
- [ ] Review vite.net, MISFITS-DSS, and broader platforms specifically for their software architecture and integration approach.
- [ ] Define the remaining software-design requirements without claiming that prior systems lack all integration.
- [ ] Introduce crop season as GrapeMaster’s design choice for maintaining management context.
- [ ] End with the four explicit software contributions.
- [ ] Mention deployment and module results only as supporting evidence.

Completion check:

- A reader can identify the software problem, design response, and contributions without reading the abstract.

### Step 4 — Add the Software design requirements section

**Objective:** Explain why the architecture was designed in its present form.

Tasks:

- [ ] Define users and main usage scenarios.
- [ ] Translate vineyard-management needs into functional requirements.
- [ ] Define requirements for temporal state, identifiers, model inputs/outputs, task records, treatment feedback, and historical retrieval.
- [ ] Explain the need for both proactive and post-symptomatic services.
- [ ] Explain frontend requirements for use in field conditions.
- [ ] Define non-functional requirements that are genuinely supported, such as modularity and service separation.
- [ ] Avoid unsupported claims about scalability, reliability, or security.

Suggested output:

- A compact requirements table linking each operational problem to a software requirement and implemented component.

Completion check:

- Every major architectural element can be traced to a stated design requirement.

### Step 5 — Refocus the System architecture section

**Objective:** Present a clear software architecture instead of a general conceptual description.

Tasks:

- [ ] Separate the mobile presentation layer, backend application layer, storage layer, scheduled services, and analytical services.
- [ ] Explain which component owns identifiers and persistent records.
- [ ] Show the crop-season context as the coordinating data object.
- [ ] Distinguish synchronous API calls, scheduled processing, asynchronous operations, and stored records.
- [ ] Show external services explicitly rather than implying that all models run inside the backend.
- [ ] Revise the architecture figure so arrows represent actual data or control flows.
- [ ] Use different line styles for direct database relationships, API communication, and contextual association.

Completion check:

- The architecture description agrees with both the frontend and backend implementation.

### Step 6 — Create the Analytical-model integration section

**Objective:** Make model integration a major software contribution.

#### 6.1 Common integration pattern

- [ ] Define how the backend constructs requests, calls a service, validates responses, stores payloads, and presents results.
- [ ] Describe shared identifiers and timestamps.
- [ ] Explain how analytical services remain replaceable or separately deployable.

#### 6.2 Weather and phenology

- [ ] Document actual weather provider and data flow.
- [ ] Explain scheduled updates and crop-context storage.
- [ ] Describe how phenology output becomes an input to disease interpretation and the frontend display.

#### 6.3 Disease-risk model

- [ ] Document actual request parameters and response structure.
- [ ] Explain weather-window construction, phenology/susceptibility inputs, disease selection, and stored request-response records.
- [ ] Distinguish currently active disease pathways from platform-compatible but unvalidated pathways.
- [ ] Archive or identify the deployed model configuration and version.

#### 6.4 Treatment feedback

- [ ] Explain the conversion of task/product records into applied-fungicide inputs.
- [ ] Explain when and how the disease service is called again.
- [ ] State exactly which treatment attributes affect current calculations.
- [ ] Present this as the strongest example of software-level model/management integration.

#### 6.5 Image recognition and LLM advisory

- [ ] Separate image classification from language-model advisory generation.
- [ ] Describe the service endpoint, payload, response, frontend presentation, and backend storage for each service.
- [ ] Explain what diagnostic or management context is passed to the LLM.
- [ ] State whether the LLM explains classifier output, answers general questions, or generates treatment recommendations.
- [ ] Describe safeguards and the boundary between advisory output and regulated pesticide decisions.
- [ ] Clearly identify any part documented from a published framework rather than verified in the deployed source.

Completion check:

- Each model is described through its software interface and operational role, not only through its scientific algorithm.

### Step 7 — Reorganize Software functions and workflows

**Objective:** Show how users experience the architecture as connected functions.

Tasks:

- [ ] Organize the section around two principal workflows.
- [ ] Workflow A: setup → state updating → disease risk → warning → task → product → treatment feedback → risk review.
- [ ] Workflow B: symptom image → classification → LLM advisory → optional field record or management action.
- [ ] Connect each screen to the corresponding backend object or service.
- [ ] Reduce repetitive screen-by-screen description.
- [ ] Use screenshots to demonstrate workflow transitions and decision points.
- [ ] Ensure captions explain the software function, not only the visible interface.

Completion check:

- The section demonstrates how architecture and model services become user-facing functions.

### Step 8 — Reposition deployment and analytical results

**Objective:** Retain useful evidence without allowing evaluation to dominate the paper.

Tasks:

- [ ] Rename the section to emphasize implementation and deployment demonstration.
- [ ] Present record counts as evidence of implemented objects and operational use.
- [ ] Present one representative workflow replay as an architecture demonstration.
- [ ] Avoid interpreting record counts as effectiveness, adoption, or agronomic impact.
- [ ] Condense module metrics into a supporting subsection or table.
- [ ] Explain that module validation evaluates component outputs, not the software architecture as a whole.
- [ ] Retain the explicit statement that LLM advisory quality was not independently evaluated.

Completion check:

- Removing the numerical evaluation would not remove the paper’s core software contribution, but the retained evidence strengthens its credibility.

### Step 9 — Rewrite the Discussion

**Objective:** Discuss software-design knowledge that other developers or researchers can reuse.

Tasks:

- [ ] Discuss why field identity and crop-season context are separated.
- [ ] Discuss service-oriented integration of heterogeneous analytical models.
- [ ] Discuss proactive disease risk versus post-symptomatic image/LLM services.
- [ ] Discuss conversion of model output into tasks and management feedback.
- [ ] Compare GrapeMaster with existing systems using specific architectural dimensions.
- [ ] Discuss replaceability of models and extension to other crops or diseases carefully.
- [ ] Address deployment coupling, model provenance, data linkage, authentication, testing, and LLM validation as limitations where applicable.
- [ ] Separate current capabilities from future development.

Completion check:

- The Discussion extracts reusable software-design lessons rather than repeating features and results.

### Step 10 — Rewrite the Abstract, title, keywords, and Conclusion

**Objective:** Align all high-visibility elements with the completed software-paper narrative.

Tasks:

- [ ] Revise the title only after the main text structure is stable.
- [ ] Write the abstract in this order: problem → software design → architecture/integration → implemented workflows → supporting evidence → significance.
- [ ] Reduce detailed record counts and model metrics if they crowd out the software description.
- [ ] Include `software architecture`, `decision support system`, or `model integration` in the keywords as appropriate.
- [ ] Rewrite the Conclusion around the four software contributions.
- [ ] Keep evidence and limitations concise but explicit.

Completion check:

- The title, abstract, Introduction contributions, Discussion, and Conclusion all tell the same story.

### Step 11 — Revise figures, tables, and supplementary material

**Objective:** Make the visual material explain the software design and integrations.

Priority figures:

- [ ] Overall software architecture.
- [ ] Crop-season data/object relationships.
- [ ] Disease-model request-response integration.
- [ ] Risk-to-action-to-treatment-feedback sequence.
- [ ] Image-recognition and LLM advisory sequence.
- [ ] Representative frontend workflow.

Tasks:

- [ ] Ensure every architecture arrow has a defined meaning.
- [ ] Use consistent names for services and data objects.
- [ ] Move large schemas, endpoint tables, and technology details to the supplement where necessary.
- [ ] Add a software-stack and deployment table.
- [ ] Add an analytical-service interface table covering inputs, outputs, invocation, storage, and user-facing role.
- [ ] Remove or combine figures that repeat the same workflow.

Completion check:

- A reader can understand the software structure and main workflows from the figures and captions alone.

### Step 12 — Final consistency and journal-readiness review

**Objective:** Verify scientific accuracy, software accuracy, and manuscript consistency.

Tasks:

- [ ] Check every software claim against the code and available deployment evidence.
- [ ] Check every model claim against the corresponding model documentation and validation result.
- [ ] Verify all service names, data providers, model versions, and technology versions.
- [ ] Check that “crop season,” “field,” “task,” “notification,” and “treatment feedback” are used consistently.
- [ ] Check that the LLM claims match the deployed implementation evidence.
- [ ] Check that figures, tables, source text, and supplement agree.
- [ ] Remove duplicate explanations across architecture, implementation, and functionality sections.
- [ ] Compile the LaTeX manuscript and inspect the complete PDF visually.
- [ ] Perform language editing only after the technical structure is stable.
- [ ] Conduct a final review against the selected journal’s software-paper expectations.

Completion check:

- The compiled manuscript is internally consistent, technically supportable, and clearly recognizable as a software paper.

## Recommended order for our future revision sessions

To keep the work controlled, revise the manuscript in the following sequence:

1. Approve positioning, terminology, and contribution statements.
2. Produce the claim-to-implementation evidence table.
3. Rewrite the Introduction.
4. Add Software design requirements.
5. Revise System architecture and its main figure.
6. Write Analytical-model integration, beginning with the disease-risk service.
7. Complete the image-recognition and LLM integration description.
8. Reorganize user functions into two end-to-end workflows.
9. Reposition deployment and module evidence.
10. Rewrite Discussion and Conclusion.
11. Rewrite Abstract, title, and keywords.
12. Complete figures, supplement, compilation, and final consistency review.

## Decisions needed during revision

The following decisions should be made when their corresponding steps begin:

- Target journal and article category.
- Whether the central term is `crop season` or `crop-season management context`.
- Whether the current code represents the exact deployed backend and frontend versions.
- Which weather provider was used in the reported deployment.
- Which disease-model version and configuration produced the reported records and validation results.
- Whether source code or complete interface documentation is available for the deployed image-recognition and LLM services.
- Whether the paper will provide a software repository, archived release, data repository, or availability statement.
- Whether additional evidence is needed for reliability, usability, performance, security, or deployment reproducibility.

## Definition of completion

The adaptation will be complete when:

- The manuscript’s primary contribution is unmistakably the GrapeMaster software system.
- The design requirements explain the architecture.
- The architecture explains the frontend, backend, data, and analytical-service boundaries.
- The disease model and LLM are described as integrated software services with documented interfaces and roles.
- User functions are presented as operational workflows generated by the architecture.
- Deployment and model results support, but do not dominate, the software narrative.
- All major claims are traceable to implementation, records, documentation, or cited prior work.
- The abstract, Introduction, figures, Discussion, and Conclusion use the same contribution hierarchy.
