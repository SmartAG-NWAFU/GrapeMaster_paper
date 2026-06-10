# EJA formatting requirements used for `manuscript_R.tex`

Target journal: **Computers and Electronics in Agriculture** (Elsevier; EJA).

Source checked: ScienceDirect Guide for Authors, Computers and Electronics in Agriculture:
https://www.sciencedirect.com/journal/computers-and-electronics-in-agriculture/publish/guide-for-authors

## Official requirements extracted

- Submit editable source files. For LaTeX manuscripts, `.tex` files are acceptable; a PDF alone is not an acceptable source file.
- Word files should use a single-column layout. Double-column formatting is only permitted for LaTeX submissions.
- The title page should include article title, author names, affiliations, corresponding author information, and any present/permanent address notes.
- The abstract must be concise, factual, able to stand alone, avoid references, avoid uncommon abbreviations, and not exceed **250 words**.
- Provide **1 to 7** English keywords for indexing.
- Highlights are required at submission: **3 to 5** bullet points, each no more than **85 characters including spaces**.
- Tables should be editable text, numbered consecutively, cited in the manuscript, and supplied with captions. Avoid vertical rules and shading.
- Figures should be numbered, cited in text, supplied with captions, and submitted as separate files where required.
- Article sections should be clearly defined and numbered; subsections should use numbered hierarchy.
- Acknowledgements should appear in a separate section before the reference list.
- CRediT author contributions are required.
- A data availability statement is required; this journal applies Elsevier research data Option C.
- References cited in the text must appear in the reference list, and vice versa.

## Formatting applied in this repository

The current `paper/manuscript_R.tex` is formatted as an EJA-compatible initial-submission/review manuscript:

- Document class: `article`, 12 pt.
- Layout: single-column review layout.
- Margins: 1 inch on all sides.
- Line spacing: double-spaced main text.
- Paragraph style: no first-line indentation; paragraphs are left-aligned in review-manuscript style.
- Font: Times-compatible text/math through `newtxtext,newtxmath`.
- Sectioning: numbered sections/subsections/subsubsections.
- Tables: editable LaTeX tables using `booktabs`; no vertical rules in the table body.
- Citation style: author-year via `natbib`, using `elsarticle-harv`.
- Bibliography file: `../reference/Grape.bib`.
- Abstract word count: currently 214 words, below the 250-word EJA limit.

## Notes for future revision

- Do not expand the abstract beyond 250 words.
- Add finalized author names, affiliations, and corresponding author information before submission.
- Add a separate highlights file or highlights section for submission metadata.
- Add Acknowledgements, CRediT author contributions, declaration of competing interests, generative AI disclosure if applicable, and data availability statement before final submission.
- If the journal requests the Elsevier `elsarticle` class after initial screening, convert to `elsarticle` using `preprint,12pt,authoryear` while preserving the same abstract and section logic.
