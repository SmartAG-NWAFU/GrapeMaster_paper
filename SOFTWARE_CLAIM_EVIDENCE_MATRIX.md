# GrapeMaster Software Claim-Evidence Matrix

This matrix records the implementation basis and remaining submission evidence for the revised software-paper claims in `paper/manuscript_S.tex`.

| Manuscript claim | Implementation basis | Evidence used in paper | Status and boundary |
|---|---|---|---|
| GrapeMaster combines a Flutter mobile client with a Django REST backend | Frontend and backend repositories; application routes, models, serializers, and mobile screens | Overall architecture figure, implementation description, interface figures | Supported |
| The backend owns core application identifiers and persistent business records | Django models and serializers for fields, crop records, weather/model payloads, notifications, tasks, and products | Methods Sections 2.2--2.3; deployment export | Supported |
| Weather and phenology information are refreshed through scheduled backend processing | Backend scheduled jobs and weather/phenology request code | Methods Section 2.4; weather/phenology records | Supported; exact deployed weather provider and endpoint version still need confirmation |
| Disease analysis is provided through an independently deployable service | Django request construction and FastAPI disease-model service | Methods Section 2.5; disease integration figure; stored request-response records | Supported at interface level |
| Disease-model requests combine weather, phenology, cultivar susceptibility, disease target, and treatment history | Backend request assembly and disease-service request schema | Methods Section 2.5; disease-model figure | Supported |
| Model requests and responses are retained for later retrieval | Backend request/response record objects and exported analytical payloads | Methods Section 2.3; deployment Table 3 | Supported |
| Completed fungicide records can update the disease-model request and initiate renewed analysis | Task serializer converts task/product fields to `applied_fungicides`, updates the stored request, and calls the disease service in applicable branches | Methods Section 2.6; proactive workflow; Discussion Section 4.3 | Strongly supported; exact efficacy use inside the current disease model is limited |
| Product records are directly linked to plant-protection tasks | Backend product/task foreign keys | Deployment table and replay | Supported |
| Notifications directly cause tasks | No direct `source_notification` relationship was found | Not claimed in revised paper | Unsupported; paper states only contextual continuity |
| Crop-management identifiers associate time-dependent records with a field | Backend `CropSeason` UUID and frontend `Crop` resource; related record keys | Methods Section 2.3; deployment replay | Supported as data linkage; not presented as the main innovation or as an explicit annual lifecycle schema |
| The application provides field, weather, risk, notification, task, product, image, and advisory functions | Flutter screens and API calls | Results Sections 3.1--3.3 and mobile screenshots | Supported |
| Image recognition is invoked through a hosted inference service | Frontend image upload and hosted classification calls; image-analysis records | Methods Section 2.7; Results Section 3.3 | Supported at interface level; deployed checkpoint/version still need archiving |
| LLM-assisted advisory is integrated through a hosted conversational service | Frontend/backend advisory calls and message records; published CDIP-ChatGLM3 framework | Methods Section 2.7; Results Section 3.3 | Supported at interface level; exact deployed checkpoint, prompt/context rules, and service version still need archiving |
| LLM advisory quality was independently validated | No independent advisory-quality evaluation was identified | Explicitly excluded in Abstract, Methods, Results, and Limitations | Not supported and not claimed |
| Deployment records demonstrate implemented use and record generation | Exported backend tables, cleaning rules, counts, and representative replay | Results Section 3.4 and Supplement | Supported; does not establish efficacy, adoption, or causality |
| Phenology, downy mildew, and image recognition have bounded analytical support | Guangxi field observations and labeled grape disease images | Results Section 3.5 | Supported for reported datasets/configurations only |
| GrapeMaster improves disease control, reduces pesticide use, or improves economic outcomes | No controlled outcome comparison in current materials | Explicitly excluded | Not evaluated and not claimed |

## Submission evidence still required

- [ ] Confirm and document the deployed weather provider and API version.
- [ ] Archive the exact disease-service commit, configuration, and FSIM-S parameter set used for reported deployment and validation.
- [ ] Archive the deployed image-classification checkpoint, class map, preprocessing, and service version.
- [ ] Archive the deployed LLM checkpoint, fine-tuning version, prompts or context-construction rules, endpoint contract, and safety behavior.
- [ ] Decide on source-code availability and create a tagged software release or permanent archive.
- [ ] Add automated integration tests or clearly state their absence.
- [ ] Complete author, affiliation, CRediT, acknowledgement, and corresponding-author information.
