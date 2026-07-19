# Understanding the CEA Example Papers

## Purpose and scope

This document records a close reading of the two example papers in `CEA_papers/` and translates their research and writing strategies into practical lessons for the GrapeMaster manuscript. The papers represent two different kinds of contribution published in *Computers and Electronics in Agriculture* (CEA): an integrated modeling-software paper and a method-and-dataset paper.

The observations below are based on these two examples, not on a systematic review of the journal. They are therefore useful patterns and comparison points rather than universal publication rules.

## Papers reviewed

1. A.-L. Toba et al. (2025), “ITreeForeCast: An integrated modeling software to simulate tree level growth and forest carbon storage,” *Computers and Electronics in Agriculture*, 237, 110495. [Local PDF](CEA_papers/ITreeForeCast.pdf) · [DOI](https://doi.org/10.1016/j.compag.2025.110495)
2. Yu Wang et al. (2026), “NearStitch: Robust near-surface image stitching for phenotyping,” *Computers and Electronics in Agriculture*, 252, 112100. [Local PDF](<CEA_papers/NearStitch: Robust near-surface image stitching for phenotyping.pdf>) · [DOI](https://doi.org/10.1016/j.compag.2026.112100)

## Executive synthesis

The two papers obtain novelty in different ways.

- **ITreeForeCast is an integration and software-architecture paper.** Its central contribution is not a new individual growth equation. It combines established tree-growth, competition, mortality, biomass, carbon, management, and harvested-product calculations into one extensible, individual-tree simulation environment. Its evidence is primarily architectural coherence, equation provenance, module checking, expert review, and a 100-year executable scenario.
- **NearStitch is an algorithm, dataset, and benchmark paper.** It proposes a specific hypothesis—that separating crop and ground feature planes can reduce parallax-related stitching errors—and tests it across crops, imaging heights, platforms, and overlap conditions against six existing methods. It supports the method with a new 34,299-image dataset, quantitative metrics, qualitative mosaics, runtime measurements, and downstream phenotyping demonstrations.

Together, they show two credible CEA routes:

1. demonstrate a genuinely new agricultural computing system by showing what previously separate processes have been integrated and what new workflow the integration enables; or
2. demonstrate a new technical method through a clear mechanism, controlled data, fair baselines, quantitative improvement, robustness analysis, and agricultural use.

GrapeMaster is closer to ITreeForeCast in its main contribution: it is an integrated platform that connects analytical results to an operational workflow. However, its independent phenology, disease-risk, and image-recognition evaluations allow it to use some of NearStitch’s stronger evidence pattern. The most convincing positioning is therefore **system-level integration supported by traceable deployment evidence, plus bounded module-level validation**.

---

## 1. ITreeForeCast

### 1.1 Research problem

Forest growth simulators and forest-carbon tools commonly operate as separate systems or at different levels of resolution. Stand- or landscape-level models can obscure variation among individual trees, while individual-tree simulators do not necessarily connect tree growth to carbon storage, management operations, mortality, competition, harvested wood volume, and product allocation.

The paper’s problem is therefore an **integration and resolution gap**: forest managers lack a unified environment in which changes to individual trees can be propagated into stand development, carbon storage, harvesting, and product outcomes.

### 1.2 Claimed contribution

ITreeForeCast is a Python-based, object-oriented simulation platform that models yearly change at the individual-tree level. It unifies:

- tree diameter and height growth;
- crown competition and stand conditions;
- mortality;
- thinning and harvesting operations;
- biomass and carbon storage;
- harvested volume; and
- allocation to solid wood, pulpwood, and energy products.

Its novelty lies mainly in the **coordinated software environment and the interactions among modeled objects**, rather than in replacing all underlying empirical forestry equations. The paper repeatedly emphasizes modularity, user extension, and the capacity to observe how management changes influence multiple ecological and product outcomes within one simulation.

### 1.3 System design

The software was developed in Python 3.10.11. Its architecture consists of six principal classes or modules:

- `Tree`: represents individual-tree attributes and state;
- `Growth`: updates diameter and height;
- `Mortality`: estimates tree death from factors including age, stress, competition, and stochasticity;
- `Management`: applies thinning or harvesting rules;
- `Carbon`: calculates biomass and carbon storage; and
- `Simulation`: coordinates annual execution and outputs.

A shared function layer connects these objects to species, location, habitat, growth, and biomass coefficients. The growth logic draws on the Inland Empire variant of the Forest Vegetation Simulator and published species-level biomass equations. Wood biomass is converted to carbon using an assumed carbon fraction of 0.5.

The annual workflow is approximately:

1. read and validate tree, plot, location, and coefficient data;
2. calculate basal area and crown competition;
3. calculate diameter and height increments;
4. update individual-tree state;
5. apply mortality and management rules;
6. optionally replace removed trees;
7. calculate biomass, carbon, harvested volume, and product allocation; and
8. repeat for the requested simulation horizon.

This sequence is important to the paper’s argument: the software is presented as a connected state-transition system, not as a collection of unrelated functions.

### 1.4 Data and demonstration context

The demonstration uses tree-inventory and site information representative of the Inland Empire region, with a study context in the Kaniksu National Forest/Selkirk Mountains of northern Idaho. Tree inputs include species, diameter at breast height, height, crown ratio, coordinates, and plot or stand identifiers. Plot inputs include elevation, slope, aspect, site index, and forest type.

The main experiment simulates 100 years under two thinning strategies:

- thinning from below, removing smaller trees; and
- thinning from above, removing larger trees.

The paper then visualizes consequences for species-specific diameter, individual-tree carbon, crown competition, mortality, harvested volume, and allocation among wood-product classes. The demonstration is intended to show that a single management rule can propagate through multiple connected outputs.

### 1.5 Evaluation logic

The evaluation is notably different from a machine-learning benchmark. The paper explains that long-horizon empirical validation is difficult because sufficiently detailed individual-tree observations over the modeled period are unavailable. It therefore relies on:

- previously published and operationally used forestry equations;
- conceptual-model checking;
- structured walkthroughs and correctness reasoning;
- independent testing of modules;
- consultation with U.S. Forest Service expertise; and
- inspection of whether the long-term simulation produces plausible trends.

This supports a claim that the implementation is coherent and produces plausible scenario behavior. It does **not** establish predictive accuracy for 100-year outcomes, superiority to another simulator, or improved forest-management outcomes.

### 1.6 Main strengths

- The integration gap is concrete and relevant to forest-management decisions.
- The object-oriented architecture matches the scientific entities and processes being modeled.
- Inputs, modules, execution sequence, and outputs are all made visible.
- The 100-year use case shows why integration matters: one intervention affects growth, competition, mortality, carbon, harvest, and product streams.
- The paper is candid about the difficulty of long-term empirical validation.
- Limitations and extensions are tied directly to the software design.

### 1.7 Limitations and claim boundaries

- No held-out longitudinal field dataset is used to measure predictive accuracy.
- No comparison with an existing simulator is reported.
- Uncertainty and sensitivity are not quantified.
- Natural regeneration is not represented in the demonstrated configuration.
- Within-stand spatial interactions are limited despite the availability of tree coordinates.
- The coefficient structure is region- and species-dependent, so transfer requires suitable local data.
- The paper says that data are available on request and supplies coefficients as supplementary material, but it does not identify a public source-code repository.

The paper is strongest as a software-integration and scenario-exploration contribution, and weakest if interpreted as evidence of forecast accuracy or management effectiveness.

### 1.8 Writing and figure strategy

The paper follows an architecture-led structure:

1. establish the fragmentation and scale mismatch in existing tools;
2. state the need for a unified individual-tree platform;
3. introduce the study context and required data;
4. explain software architecture, objects, workflow, and equations;
5. execute a representative management scenario;
6. present many linked outputs; and
7. discuss validation constraints and future extensions.

The figures do much of the explanatory work. Early diagrams communicate software structure and execution flow; later figures demonstrate the range of coupled outputs. The results section is therefore a **system-behavior narrative**, not a table of isolated performance scores.

### 1.9 Relevance to GrapeMaster

ITreeForeCast is the closer structural analogue to GrapeMaster. Both systems:

- integrate several scientific or analytical components;
- organize them around a persistent domain object;
- coordinate state changes through a defined workflow;
- use modular software architecture; and
- seek value from the connections among components, not merely from the presence of each component.

The important lesson is that an integration paper must explain exactly what becomes possible because the components share objects and state. For GrapeMaster, that is the ability to connect a crop season, disease-risk interpretation, notification, plant-protection task, treatment record, and later review through persistent identifiers and records.

GrapeMaster can provide stronger evidence than ITreeForeCast in one respect: it has a deployment-record audit and quantitative validation for several analytical modules. Those two evidence types should remain clearly separated so that model metrics are not misrepresented as proof of platform or production effectiveness.

---

## 2. NearStitch

### 2.1 Research problem and hypothesis

Near-surface phenotyping images are difficult to stitch because plants and soil occupy different depth planes. Short imaging distance makes parallax pronounced; repetitive plant textures weaken feature matching; shadows and exposure differences affect seams; and leaves can move or occlude one another. Methods designed for conventional panoramas or higher-altitude aerial imagery can therefore produce ghosting, bending, incomplete mosaics, and accumulated geometric error.

NearStitch starts from a specific mechanistic hypothesis: **feature points from crop and ground layers should not be forced into one geometric transformation**. Segmenting those layers and estimating their transformations separately should reduce interference from depth differences.

### 2.2 Explicit contributions

The introduction enumerates three contributions:

1. **PlantStitch**, a 34,299-image dataset spanning crop, platform, height, stage, lighting, and overlap conditions;
2. **NearStitch**, a three-part method for layered feature extraction, layered alignment, and warped-image fusion; and
3. evidence of generalizability across imaging platforms, crops, heights, and additional sensing modalities.

This explicit contribution list makes the subsequent evaluation easy to audit: the dataset must be diverse, the layered mechanism must be technically explained, and robustness must be shown across conditions.

### 2.3 Method

NearStitch contains three main modules.

#### Layered feature extraction

A U-Net segments each image into crop, ground, and background. SIFT extracts feature points. Crop and ground features are retained as separate groups, while background features are excluded.

#### Layered image alignment

Features are matched with FLANN and filtered with RANSAC. Separate homography matrices are estimated for the crop and ground layers. The final transformation fuses the two homographies using a weight derived from the proportion of ground pixels in the reference and target images. This adaptive weighting is intended to reflect the visible content of each image pair.

#### Warping and post-processing

The target is warped into the reference frame. Seam-based gradient fusion and exposure compensation reduce visible boundaries and illumination differences.

The architecture diagram is followed by equations and implementation details, allowing the reader to connect the hypothesis to a reproducible computation.

### 2.4 Dataset and experimental design

PlantStitch was collected at the Baima Experimental Station of Nanjing Agricultural University in 2022 and 2023. It includes wheat and soybean imagery from a gantry system and a DJI Mavic 2 Pro at heights from 3 to 25 m.

The seven image groups are:

| Dataset | Crop/platform/height | Images |
|---|---|---:|
| GW3 | Wheat, gantry, 3 m | 19,710 |
| GS3 | Soybean, gantry, 3 m | 5,220 |
| DW5 | Wheat, UAV, 5 m | 25 |
| DW10 | Wheat, UAV, 10 m | 3,962 |
| DW15 | Wheat, UAV, 15 m | 2,728 |
| DW20 | Wheat, UAV, 20 m | 1,936 |
| DW25 | Wheat, UAV, 25 m | 718 |
| **Total** |  | **34,299** |

Images were generally collected at 80% forward and 60% side overlap. Reduced-overlap experiments were created by interval sampling. Checkerboards placed in the field supplied geometric reference points, and the camera was calibrated.

For semantic segmentation, 197 images were manually annotated and expanded to 394 through brightness augmentation. The reported split was 300 training, 47 validation, and 47 test images. Crop, ground, and background segmentation performance was reported separately; crop precision and recall were 0.91 and 0.94, while ground precision and recall were 0.99 and 0.98.

### 2.5 Comparison design and metrics

NearStitch is compared with six existing approaches: AutoStitch, Microsoft ICE, APAP, SPW, ELA, and UDIS. The experiments vary crop, imaging platform, altitude, and image overlap.

Evidence is deliberately mixed:

- qualitative inspection of bending, ghosting, seam artifacts, accumulated drift, and incomplete mosaics;
- ILNIQE, a no-reference image-quality metric for which lower is better;
- AADC, a checkerboard-based angular-distortion measure introduced in the paper, for which lower is better; and
- processing time, averaged across 32 runs for each dataset.

This combination is useful because a single perceptual score cannot fully describe geometric registration, and a geometric score based on visible checkerboards cannot be computed in every image.

### 2.6 Main results

NearStitch gives the best ILNIQE result for GS3, GW3, and DW5, and the second-best result for DW10. It gives the best AADC for GW3 and DW10 and the second-best result for GS3 and DW5. The paper summarizes these results as average improvements of about 7% in ILNIQE and 10% in AADC relative to the compared methods.

Representative results include:

| Dataset | NearStitch ILNIQE | Rank among reported methods | NearStitch AADC | Rank among valid reported methods |
|---|---:|---:|---:|---:|
| GS3 | 22.97 | 1st | 1.68 | 2nd |
| GW3 | 23.12 | 1st | 0.40 | 1st |
| DW5 | 26.00 | 1st | 0.48 | 2nd |
| DW10 | 27.66 | 2nd | 0.33 | 1st |

The method generally completes a stitching task in under five seconds and is much faster than APAP in the reported experiments. The relative advantage is clearest for near-surface and gantry images. At greater UAV height, the geometry becomes closer to conventional aerial stitching, so the special benefit of layer separation decreases.

The authors also construct full-field time-series mosaics and calculate green fraction for the whole field and selected plots. This downstream demonstration shows that stitching is not only visually attractive: it enables spatial and temporal phenotyping that would be difficult from disconnected frames. Exploratory thermal and multispectral examples suggest that the method is transferable, but the thermal results retain more distortion.

### 2.7 Main strengths

- The failure mechanism and the proposed solution correspond directly.
- Contributions are explicit and separately testable.
- The dataset was collected by the authors under reported agricultural conditions and is itself a substantial contribution.
- Comparisons cover six baselines and several sources of variation.
- Visual results, quantitative quality, geometric distortion, and speed are all reported.
- Downstream phenotyping is shown only after core stitching performance is established.
- Failure cases and changing performance with overlap, altitude, and sensing modality remain visible.
- The implementation is linked to a public GitHub repository: <https://github.com/Jinlab-AiPhenomics/NearStitch>.

### 2.8 Limitations and questions left open

- There is no clear ablation study isolating the contribution of semantic layering, separate homographies, adaptive fusion, and post-processing.
- The description of the segmentation split does not establish whether images from the same plots, dates, or acquisition sequences occur across training and test sets.
- ILNIQE measures perceptual image quality, not registration accuracy directly.
- AADC depends on detectable checkerboards and is unavailable for some outputs.
- The DW5 set contains only 25 images.
- The runtime description does not provide enough hardware and variability information for a fully controlled computational comparison across implementations written in different languages.
- Two rigid homographies cannot represent all non-rigid leaf motion, complex canopy heights, wind, or occlusion.
- Most acquisition uses high overlap; the lower-overlap evidence is narrower.
- Thermal and multispectral stitching and green-fraction extraction are demonstrations rather than full downstream validation studies.
- The abstract’s “artifact-free” wording is stronger than the paper’s own discussion of residual artifacts.

The algorithm is convincingly useful, but evidence for the proposed mechanism would be stronger with component ablations and explicitly independent data splits.

### 2.9 Writing and figure strategy

NearStitch follows a hypothesis-and-benchmark structure:

1. show the agricultural imaging problem and its physical cause;
2. state a mechanism-based hypothesis;
3. enumerate the contributions;
4. introduce the dataset and acquisition conditions;
5. explain the architecture and equations;
6. define baselines, metrics, and experimental factors;
7. present qualitative and quantitative comparisons;
8. demonstrate downstream phenotyping; and
9. retain limitations and extended cases in the appendix.

Its figures progress from **problem → method → benchmark → application**. Large qualitative grids let readers verify whether metric improvements correspond to visible reductions in distortion. The appendices extend, rather than merely repeat, the main evaluation.

### 2.10 Relevance to GrapeMaster

NearStitch is not a close system analogue, but it is a strong model for evidence design. GrapeMaster should emulate its:

- concise statement of the technical and agricultural gap;
- explicit, countable contributions;
- definition of datasets, selection rules, sites, and denominators;
- separation of core-method evidence from downstream-use examples;
- use of metrics appropriate to each claim;
- honest presentation of weaker conditions and unavailable measurements; and
- software/data availability statement.

For GrapeMaster, this means independently validating phenology, disease-risk timing, and image recognition with module-appropriate metrics while treating the deployment audit and workflow replay as different evidence for platform traceability.

---

## 3. Cross-paper comparison

| Dimension | ITreeForeCast | NearStitch | Implication for GrapeMaster |
|---|---|---|---|
| Primary paper type | Integrated modeling software | Algorithm + dataset + benchmark | Integrated platform with separately evaluated analytical services |
| Central gap | Fragmented models and mismatched resolution | Parallax and depth-plane errors in proximal image stitching | Analytical outputs disconnected from field action, feedback, and review |
| Source of novelty | Coupling domain objects and processes in an extensible simulator | Layer-aware geometry and a new agricultural dataset | Crop-season-centered traceability and risk-to-feedback workflow |
| Organizational anchor | Individual tree | Crop/ground image layers and image pairs | Vineyard field and crop season |
| Main evidence | Architecture, equation provenance, module checks, expert review, executable scenario | Six baselines, multiple datasets and conditions, quantitative metrics, runtime, qualitative mosaics | Architecture + deployment-record audit + record-level replay + independent module metrics |
| Downstream demonstration | Management effects on growth, carbon, harvest, and products | Field mosaics and green-fraction time series | Warning, task, treatment feedback, protected-state update, and retrospective review |
| Strongest valid claim | The integrated simulator executes coherent, plausible multi-output scenarios | The method generally improves near-surface stitching quality and geometric stability | The deployed platform retains the objects and links needed to reconstruct a traceable disease-management workflow |
| Claim not established | Long-term predictive accuracy or improved forest outcomes | Universal artifact-free performance or validated phenotype accuracy | Improved disease control, reduced fungicide use, economic benefit, adoption, or advisory quality |
| Reproducibility posture | Data on request; supplementary coefficients; no public code link identified | Public implementation; data on request | State exactly which de-identified summaries/scripts can be shared and why raw operational data cannot be public |

## 4. What these examples suggest about CEA papers

### 4.1 Agricultural computing novelty must be identifiable

Neither paper argues that using software in agriculture is novel by itself. ITreeForeCast identifies a new integration of modeled entities and outcomes. NearStitch identifies a new layer-aware alignment mechanism and supplies a purpose-built dataset. This is consistent with CEA’s emphasis on an advance in agricultural computing or electronics rather than simply applying an off-the-shelf technology to a crop.

For GrapeMaster, the novelty should not be “a mobile app that contains several vineyard functions.” It should be the **crop-season-centered data and workflow architecture that converts analytical outputs into traceable operational records and feedback**.

### 4.2 The paper’s evidence must match its paper type

The examples do not use a single universal validation formula. A simulator is assessed through model provenance, implementation logic, module checking, and scenario behavior. An image-processing algorithm is assessed through datasets, baselines, metrics, and robustness tests.

GrapeMaster similarly needs two evidence tracks:

- **platform evidence:** deployed objects, retained identifiers, linkage coverage, and a reconstructable risk-to-feedback sequence; and
- **analytical-module evidence:** phenology agreement, infection-timing error, and image-recognition class performance.

Neither evidence track substitutes for the other.

### 4.3 Integration must be shown through state and consequences

ITreeForeCast does not prove integration by listing modules; it shows an annual execution sequence and how a thinning rule changes several downstream outputs. NearStitch does not prove layering by showing a segmentation screenshot; it carries separated features through alignment and then measures the mosaic.

GrapeMaster should likewise demonstrate the actual state transition:

`risk interpretation → notification → task → treatment record → protected-state update → review`

The shared crop-season and task identifiers are the mechanism that makes this a connected workflow rather than a group of screens.

### 4.4 Figures should carry the argument

Both papers use early architecture/workflow figures and later result figures. The figures are not decorative screenshots; they make the contribution inspectable.

For GrapeMaster, the most important visual sequence is:

1. crop season as the conceptual anchor;
2. logical objects, identifiers, and workflow states;
3. service and implementation architecture;
4. the user-visible risk-to-feedback pathway;
5. operational-record coverage and record-level replay; and
6. separate analytical-module results.

Interface screenshots are useful only when they demonstrate where a workflow state is created, reviewed, or updated.

### 4.5 Limitations increase credibility when tied to claims

Both papers acknowledge where their evidence weakens: long-term field validation for ITreeForeCast, and complex height, low overlap, non-rigid motion, and additional modalities for NearStitch. The limitation sections therefore define the systems’ operating boundaries.

GrapeMaster should be equally direct that the present study does not evaluate long-term disease suppression, fungicide savings, economics, user adoption, or LLM advisory quality. These are future outcomes, not conclusions that can be inferred from record linkage or offline module metrics.

## 5. Recommended framing for the GrapeMaster manuscript

### 5.1 One-sentence positioning

> GrapeMaster is a crop-season-centered digital platform that connects disease-risk interpretation to notifications, executable field tasks, treatment feedback, and retrospective review through traceable operational records, while allowing analytical services to be independently evaluated and replaced.

This sentence identifies the domain problem, organizational mechanism, workflow consequence, and modular architecture without claiming production effectiveness.

### 5.2 Suggested contribution structure

The paper can state three contributions in the style of NearStitch while retaining ITreeForeCast’s system emphasis:

1. **Architecture:** a crop-season-centered object and service architecture for integrating field context, weather, phenology, disease risk, image recognition, advisory support, tasks, and treatment records.
2. **Operational workflow:** a risk-to-feedback design that converts analytical outputs into notifications, plant-protection tasks, treatment feedback, protected-state interpretation, and reviewable management history.
3. **Evidence:** a deployment-record audit and record-level workflow replay demonstrating retained traceability, together with independent evaluation of the current platform-compatible analytical modules.

### 5.3 Evidence hierarchy and wording

| Evidence | Supports | Does not support |
|---|---|---|
| Architecture and implementation description | The system was designed to connect specified objects and services | That users consistently followed the workflow |
| Operational-record counts and linkage audit | The deployment retained objects and identifiers needed for reconstruction | Improved decisions or agronomic outcomes |
| Representative record-level replay | A connected workflow occurred and can be reconstructed in the selected crop season | Frequency or causal effectiveness across all users |
| Phenology validation | Accuracy of the evaluated broad-stage configuration in the stated Guangxi data | Universal transfer across cultivars and regions |
| FSIM-S timing validation | Error of first-infection timing in the evaluated data | Reduced disease severity or fungicide use after deployment |
| Image-model validation | Category-level recognition performance on the evaluated image dataset | Field diagnostic effectiveness under every acquisition condition |
| Presence of an LLM advisory interface | Advisory capability is integrated into the workflow | Advisory correctness, safety, or agronomic benefit |

This table should govern verbs throughout the abstract, results, discussion, and conclusion. Prefer “retained,” “linked,” “reconstructed,” “achieved,” and “was evaluated” over “improved,” “optimized,” or “ensured” unless those stronger claims have direct evidence.

### 5.4 Methods and results order

A CEA-oriented narrative would read most clearly in this order:

1. agricultural and information-flow problem;
2. crop-season-centered design requirements;
3. conceptual, logical, and service architecture;
4. implementation of the mobile client, backend, jobs, records, and analytical services;
5. user-facing risk-to-feedback functionality;
6. deployment-record selection and audit protocol;
7. record-level workflow replay;
8. independent analytical-module evaluation; and
9. discussion of integration, modular replacement, transfer, and unevaluated outcomes.

This moves from design to implementation to operational evidence, while preventing screenshots or module metrics from obscuring the principal platform contribution.

### 5.5 Specific improvements suggested by the examples

- Give all deployment counts explicit denominators and screening rules, as NearStitch does for dataset composition.
- Keep a flow diagram showing how the 95 deduplicated accounts become the 47 retained operational accounts.
- Explain why one crop season was selected for record-level replay and whether it is representative, illustrative, or exceptional.
- Distinguish “126 crop seasons with linked environmental and analytical records” from the full set of 128 retained seasons.
- Keep model calibration and validation sets distinct wherever possible and report site-year independence.
- Where a meaningful baseline exists for a module, report it; otherwise explain why absolute metrics are the appropriate evidence.
- Include uncertainty or sample size next to headline metrics, not only in supplementary material.
- Treat the LLM component as an integrated but unevaluated service and avoid implying validated advisory quality.
- Make regional transfer a property of the modular architecture—services can be replaced after local validation—not a claim that the current Guangxi models transfer unchanged.
- Provide an exact data/code availability statement, including de-identified derived tables, analysis scripts, restrictions on raw platform records, and access conditions.

## 6. Practical manuscript checklist

Before submission, verify that the manuscript can answer each question clearly.

### Novelty

- What previously disconnected vineyard processes are now connected?
- Why is the crop season a technically meaningful organizational object?
- What is investigator-developed rather than off-the-shelf?
- What is reusable beyond the single deployment?

### Architecture and reproducibility

- Are input objects, identifiers, state transitions, services, and outputs defined?
- Can a reader trace one risk event through notification, task, treatment, and review?
- Are model versions, calibration contexts, and update boundaries stated?
- Are software and derived-data access conditions explicit?

### Evaluation

- Are account and crop-season screening rules reproducible?
- Are record-linkage metrics defined with denominators?
- Is the replay’s selection rationale stated?
- Does each analytical metric map to one bounded module claim?
- Are missing evaluations, including advisory quality and production outcomes, explicit?

### Presentation

- Does the abstract distinguish deployment evidence from module validation?
- Do figures progress from architecture to workflow to evidence?
- Are screenshots used as evidence of workflow state rather than as a feature catalogue?
- Does the discussion compare GrapeMaster with integrated agricultural DSS/platform work, not only disease models?
- Does the conclusion remain within the demonstrated claim boundary?

## Final assessment

The most valuable lesson from these papers is not that CEA requires either a large benchmark or a complete long-term field trial in every study. It requires a recognizable computing contribution and evidence appropriate to that contribution.

ITreeForeCast shows how an integrated scientific software system can be organized around domain objects and demonstrated through connected scenario outputs, even when long-horizon predictive validation is constrained. NearStitch shows the stronger standard for a new technical method: a mechanism-based hypothesis, purpose-built agricultural data, baselines, multiple metrics, robustness conditions, runtime, and downstream use.

GrapeMaster can combine the strengths of both patterns. Its principal contribution is the crop-season-centered, traceable operational architecture; its deployment records can demonstrate that the workflow objects and links exist in practice; and its analytical services can be evaluated independently with module-specific evidence. Keeping these three layers distinct will make the paper’s novelty clearer and its conclusions more defensible.
