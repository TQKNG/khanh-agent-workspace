---
name: diagram-standards
description: >
  This skill should be used when writing or updating architecture documentation, especially
  Mintlify pages, that needs a diagram: "document the architecture", "add a system context
  diagram", "business context diagram", "whitebox view", "deployment view", "component view",
  "C4 diagram", "class diagram", "domain model", "state diagram", "draw.io diagram for the docs", or any request to draw, update or embed a
  diagram in documentation. It makes Claude start from the approved draw.io templates instead
  of drawing from scratch, fill the title block, export a PNG and embed it correctly.
metadata:
  version: "0.2.0"
---

# Diagram standards

Paths in this file are relative to this skill folder.

Every architecture diagram in the documentation starts from one of the approved draw.io templates stored in `templates/`.
Never draw an architecture diagram from scratch, never restyle a template, and never invent new colours, fonts or legend entries.
The templates already carry the frame, bottom title block, legend, C4 colours, Roboto fonts and dashed, labelled relationships.

## Choose the template

| Diagram needed | Type key | Template file | Document number prefix |
|---|---|---|---|
| System context: the system, its users and neighbouring systems | `sc` | `system-context.drawio` | `SC` |
| Business context: the same picture in business language, no technology | `bc` | `business-context.drawio` | `BC` |
| Level 1 whitebox: inside one system, its containers | `l1-whitebox` | `l1-whitebox.drawio` | `LVL1_Whitebox` |
| Level 1 deployment: where it runs (cloud tenant, subscription, resource group) | `l1-deployment` | `l1-deployment.drawio` | `LVL1-DeploymentView` |
| Level 2 component view: inside one container, its components | `l2-component` | `l2-component.drawio` | `LVL2_ComponentView` |
| Runtime view: one scenario as a sequence diagram (arc42 section 6) | `seq` | `sequence.drawio` | `SEQ` |
| Class diagram: the domain model or an interface with its implementations (arc42 sections 5 and 8) | `class` | `class.drawio` | `CLS` |
| State diagram: the lifecycle of one entity (arc42 section 8) | `state` | `state.drawio` | `STM` |

Document number format: `<prefix>-<ProductName>-<NNN>`, for example `SC-ReportingGeneratorTool-001`.
When unsure which type fits, read `references/template-catalog.md` for what each template contains and when to pick it.

## Sequence diagrams (`seq`)

Sequence diagrams are authored in Mermaid and delivered as draw.io, so they share the frame, title block, legend, Roboto and C4 colours of the other diagrams.

1. Write or reuse a Mermaid `sequenceDiagram` and save it as `diagrams/src/<doc-number>.mmd`.
   Add one comment line that sets each participant's kind: `%% kind Customer=person API=container Repo=component Stripe=system` (see `references/sequence-example.mmd`).
   Supported syntax: `autonumber`, `actor`, `participant X as Label`, `->>`, `-->>`, `->`, `-->`, `loop`, `alt`/`else`, `opt`, `end`.
   Calls are solid arrows, returns are dashed arrows.
2. Convert (an `.mdx` page with the Mermaid block also works as input; pick the block with `--block N`):
   ```bash
   python3 scripts/mermaid_seq_to_drawio.py diagrams/src/<doc-number>.mmd diagrams/src/<doc-number>.drawio \
     --title "<Product> – Runtime View – <scenario>" --number <doc-number> --author "<name>"
   ```
3. Continue at step 4 below (PNG) and step 5 (embed).
   Replace the page's Mermaid block with the image.
4. Keep the `.mmd` next to the `.drawio`.
   Regenerate from the `.mmd` before any hand edits in draw.io; hand edits are not written back to the `.mmd`.
5. One scenario per diagram, at most six participants.
   Split larger flows into several diagrams.

## Class diagrams (`class`) and state diagrams (`state`)

Class and state diagrams follow the same flow as sequence diagrams: they are authored in Mermaid and delivered as draw.io, so they share the frame, title block, legend, Roboto and C4 colours of the other diagrams.

1. Write or reuse a Mermaid `classDiagram` or `stateDiagram-v2` and save it as `diagrams/src/<doc-number>.mmd` (see `references/class-example.mmd` and `references/state-example.mmd`).
   Take names, members, enum values and states from the code or the approved design, and draw only what they show.
   Class diagram syntax: `class` blocks with members, `<<interface>>` and `<<enumeration>>`, and the relationships `<|--`, `<|..`, `*--`, `o--`, `-->`, `..>`, `--`, `--|>`, `..|>` with optional cardinalities and labels.
   State diagram syntax: `A --> B: event [guard] / action`, `[*]`, `state "Name" as id`, `<<choice>>`, one level of composite state, and `direction TB|LR`.
2. Convert (an `.mdx` page with the Mermaid block also works as input; pick the block with `--block N`):
   ```bash
   python3 scripts/mermaid_class_to_drawio.py diagrams/src/<doc-number>.mmd diagrams/src/<doc-number>.drawio \
     --title "<Product> – Domain Model – <scope>" --number <doc-number> --author "<name>"
   python3 scripts/mermaid_state_to_drawio.py diagrams/src/<doc-number>.mmd diagrams/src/<doc-number>.drawio \
     --title "<Product> – State Machine – <entity>" --number <doc-number> --author "<name>"
   ```
3. Continue at step 4 below (PNG) and step 5 (embed).
   Replace the page's Mermaid block with the image.
4. Keep the `.mmd` next to the `.drawio`.
   Regenerate from the `.mmd` before any hand edits in draw.io; hand edits are not written back to the `.mmd`.
5. One aggregate, interface family or entity lifecycle per diagram, at most eight classes.
   Show the key attributes and operations, not every field; point to the API reference for full field lists.
   A diagram wider than the page stops with an error: split it.

## Workflow

1. Identify the diagram type from the table.
   If the page needs several levels, create each diagram separately, each with its own document number.
2. Create the working copy with the script (deterministic, fills the title block):
   ```bash
   python3 scripts/new_diagram.py <type-key> <doc-number> \
     --title "<Product> – <diagram title>" --author "<name>" [--version 0.0.1] [--out-dir diagrams/src]
   ```
The file lands in `diagrams/src/<doc-number>.drawio` at the docs repository root (the folder that holds `docs.json`).
Create `diagrams/src` when it is missing.
3. Edit the copy for the new system.
   Follow `references/style-guide.md`: reuse the template's shape kinds, keep every legend entry, keep the frame and title block, relabel existing shapes, then add or delete shapes of the same kinds.
   Keep relationship labels short verbs or noun phrases.
   Keep connectors dashed with an arrow at the end that receives the call.
4. Produce the PNG.
   Never stop at the `.drawio`; the page needs an image.
   Try in order:
   1. Local draw.io CLI:
      ```bash
      bash scripts/export_png.sh diagrams/src/<doc-number>.drawio images/diagrams/<doc-number>.png
      ```
      The script exits with code 2 when the CLI is missing.
   2. CI export (CLI missing, for example in a cloud session): install the workflow once per
      docs repository, then commit the `.drawio` source. The workflow renders
      `images/diagrams/<doc-number>.png` and commits it; Mintlify redeploys with the image.
      ```bash
      bash scripts/setup_ci.sh <docs-repo-root>
      ```
      Write or update the page in the same commit so it already references the PNG path.
      Tell the user the image appears after the workflow run completes (about a minute).
   3. Manual: ask the user to export a PNG from draw.io (File > Export as > PNG, 2x, crop on)
      named `<doc-number>.png` and replace the page's image when they send it.
Say which route was used.
Never claim the page shows the new diagram until the PNG exists in the repository and the page references it.
5. Embed the PNG in the page with descriptive alt text and a one-line caption:
   ```mdx
   ![System context diagram showing the Facility Manager, the Facility Management Platform and the Report Generation Service](/images/diagrams/<doc-number>.png)
   ```
Link the source for editors: `Source: diagrams/src/<doc-number>.drawio`.
6. Run `mint validate` and `mint broken-links` when the CLI is available.
   Do not publish unless the user asks.

## Rules that never bend

- One template per diagram.
  Do not merge templates or mix two levels in one diagram.
- Keep the title block at the bottom: Document Title, Document Number, Version Number, Prepared By, Date.
  The script fills them; confirm the author and date with the user when they are not given.
- Keep the legend exactly as the template has it, including entries the diagram does not use.
- Colours: Person `#08427b`, Software System `#1168bd`, Container and Database `#438dd5`, Component `#85bbf0`.
  Font: Roboto.
  Relationships: dashed, 2.25 px, black, white label background.
- Commit the `.drawio` source and the exported PNG together.
  Never edit the PNG by hand.
- A page that embeds `/images/diagrams/<name>.png` must have `diagrams/src/<name>.drawio`.
  A check hook in this plugin reports pages that break this rule; fix the reported problem.

## Where to look next

- `references/template-catalog.md`: what is inside each template, cell ids to edit, when to use it.
- `references/style-guide.md`: exact styles, fonts, sizes, colours and connector rules.
- `references/docs-repo-layout.md`: where files live in the Mintlify repository.
