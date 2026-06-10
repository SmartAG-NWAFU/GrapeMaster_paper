# Prompt for Figure 3.1 Backend Linkage Diagram

Create a clean scientific workflow diagram for an Electronic Agriculture journal manuscript. The figure should be designed as a SCI journal double-column figure. Use a landscape canvas with a final printable width of approximately 170--180 mm. Set the pixel size to at least 3600 px wide at 600 dpi equivalent; the height may adapt to the content but should remain compact and journal-ready. The figure should match the visual style of the existing GrapeMaster manuscript figures: white background, blue/green/purple accent colors, rounded but restrained module boxes, flat vector icons, clear arrows, high readability, and no decorative gradients or clutter.

Typography and export:
- Use Times New Roman for all text, including node labels, badges, arrow labels, and small annotations.
- Keep all text horizontal.
- Use consistent title case for node labels.
- Use crisp vector-like rendering and export as a high-resolution PNG.
- Avoid text smaller than 8 pt at the final double-column print width.

Figure topic: "Operational backend data coverage and crop-season-centered linkage in GrapeMaster".

Main visual structure:
- Use a left-to-right closed-loop workflow centered on a large middle node labeled "Crop season".
- Place "Retained accounts" and "Field" on the left side as the operational entry objects, with arrows from "Retained accounts" to "Field" and from "Field" to "Crop season".
- Arrange the diagram in clearly aligned vertical columns. Nodes in the same column must share the same x-coordinate and be vertically aligned.
- Recommended column layout:
  1. Column 1: "Retained accounts" above "Field".
  2. Column 2: large central "Crop season" node.
  3. Column 3: upper analytical-state stack, vertically aligned as "Weather payloads", "Phenology payloads", and "Disease-risk outputs".
  4. Column 4: right-side operational-delivery stack, vertically aligned as "Notifications", "Plant-protection / irrigation tasks", and "Fungicide / pesticide records". These three nodes must form a clean vertical column with identical box width and aligned left and right edges.
  5. Lower row: "Field notes / disease reports", "Image-analysis records", "Advisory / message records", and "Forum records" should be horizontally aligned under the central workflow, with equal vertical position and consistent spacing.
- From "Crop season", branch to the three upper analytical-state nodes.
- From "Disease-risk outputs", draw arrows to the right-side operational-delivery stack:
  1. "Notifications"
  2. "Plant-protection / irrigation tasks"
  3. "Fungicide / pesticide records"
- Draw a feedback arrow from "Fungicide / pesticide records" back to "Disease-risk outputs", labeled "Protection feedback".
- Connect "Crop season" to the lower-row evidence and consultation nodes.
- Show the lower-row objects as evidence and consultation records that remain linked to the crop-season context.

Include small record-count badges in each node:
- Retained operational accounts: 47
- Vineyard fields: 139
- Crop seasons: 128
- Weather payloads: 126
- Phenology payloads: 126
- Disease-risk outputs: 252
- Notifications: 3590
- Plant-protection / irrigation tasks: 151
- Fungicide / pesticide records: 234
- Field notes / disease reports: 94
- Image-analysis records: 2808
- Advisory / message records: 1360
- Forum records: 27

Design details:
- Use consistent line weights and arrowheads. Use approximately 2.0--2.5 pt strokes for main arrows and 1.2--1.5 pt strokes for box borders at final figure scale.
- Keep all module boxes visually consistent with the current manuscript figures: white interior, colored outline, subtle shadow if needed, and restrained rounded corners. Use the same corner radius across all boxes.
- Use identical box dimensions for nodes within the same vertical stack. In particular, the right-side "Notifications", "Plant-protection / irrigation tasks", and "Fungicide / pesticide records" boxes must have the same width, same height, same border thickness, and aligned vertical spacing.
- Use blue for account/field/data-entry objects, green for analytical-state objects, purple for operational delivery and task objects, and teal/green accents for evidence and consultation objects. Keep color saturation consistent with the existing GrapeMaster workflow figures.
- Use icons similar in tone to the manuscript figures: user/account icon for Retained accounts, field/plot icon for Field, calendar or grapevine icon for Crop season, cloud/rain icon for Weather, growth-stage branch icon for Phenology, gauge/shield icon for Disease-risk, bell icon for Notifications, clipboard icon for Tasks, spray bottle icon for Fungicide/Pesticide records, note icon for Field notes, leaf/image icon for Image-analysis, chat bubble icon for Advisory messages, and conversation icon for Forum records.
- Avoid implying that advisory or LLM functions replace expert diagnosis. Label them only as "Advisory / message records".
- Do not include code, database table names, raw SQL, or engineering implementation details in the figure body.
- Use a compact journal-ready layout suitable specifically for a double-column figure.
- Keep margins balanced: leave about 3--5% blank space around the outer edges.
- Avoid overlapping arrows and labels. Route feedback arrows outside the main node boxes if needed.
- Use short labels inside boxes; put the count badge as a small rounded tag in the upper-right corner of each box.
- Export as a high-resolution PNG with crisp text and anti-aliased lines.

Suggested caption:
"Operational backend data coverage and crop-season-centered linkage in GrapeMaster. After excluding accounts without field and crop-season records, the retained backend records covered field setup, crop-season objects, weather and phenology payloads, disease-risk outputs, notifications, field tasks, fungicide or pesticide records, field evidence, image-analysis records, advisory messages, and forum records. The crop season served as the central data anchor linking analytical outputs, field operations, protection feedback, and observation records."
