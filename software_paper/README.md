# GrapeMaster software-paper workspace

This folder contains the manuscript adapted from `paper/manuscript_S.tex` into a software paper.

## Main files

- `manuscript_software.tex`: revised main manuscript.
- `supplementary_software_stack.tex`: revised technical supplement.
- `IMPLEMENTATION_EVIDENCE.md`: claim-to-implementation evidence and remaining archive needs.
- `REVISION_PLAN.md`: the step-by-step revision plan used for this adaptation.
- `fig/`: figures required by the manuscript and supplement.
- `reference/Grape.bib`: bibliography used for compilation.
- `output/pdf/`: compiled deliverables.

## Paper positioning

The manuscript presents GrapeMaster as a developed agricultural software system. Its primary contributions are:

1. a field-linked crop-season software architecture;
2. service-oriented integration of weather, phenology, disease, image, and LLM advisory components;
3. a risk-to-action-to-feedback workflow connecting disease results with tasks and treatment history; and
4. an implemented Flutter, Django, PostgreSQL, and analytical-service platform.

Deployment records and analytical metrics are supporting demonstrations rather than the paper's primary contribution.

## Compile

From this folder, compile the main paper with:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error manuscript_software.tex
```

Compile the supplement with:

```sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error supplementary_software_stack.tex
```

Stable delivery PDFs are copied to `output/pdf/` after verification.

## Submission actions still requiring author input

- Complete author names, affiliations, CRediT roles, and acknowledgements.
- Confirm the target journal and article category.
- Archive versioned frontend, backend, disease, image, and LLM service artifacts.
- Confirm the model/configuration version used for historical deployment records.
- Provide the hosted image-service and LLM-service availability statements.
- Decide whether source code and derived data will be public or available on request.
