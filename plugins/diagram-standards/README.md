# diagram-standards

Makes Claude start every architecture diagram in your Mintlify docs from the approved draw.io C4 templates.

## What is included
- **diagram-standards skill**: picks the right template, fills the title block, exports a PNG, embeds it with alt text.
- **/new-diagram skill**: `/new-diagram <sc|bc|l1-whitebox|l1-deployment|l2-component|class|state> <doc-number> [title]` creates the working file.
- **Check hook** (after file writes): flags `.mdx` pages that embed a diagram without a `.drawio` source or PNG, and `.drawio` files that lost the title block or legend.
  Remove `hooks/` to turn it off.
- **Templates**: system context, business context, level 1 whitebox, level 1 deployment, level 2 component, sequence (runtime view), class (domain model) and state (lifecycle).
  Class and state diagrams are written in Mermaid and converted to draw.io by `scripts/mermaid_class_to_drawio.py` and `scripts/mermaid_state_to_drawio.py`.
  Sequence diagrams are written in Mermaid and converted to draw.io by `scripts/mermaid_seq_to_drawio.py`.

## Requirements
- Python 3 for the scripts.
- PNG export: the draw.io desktop CLI when available.
  Otherwise Claude installs `.github/workflows/export-diagrams.yml` (`scripts/setup_ci.sh`) so GitHub renders the PNGs on push and Mintlify picks them up.
  Manual export is the last resort.
- Docs repository with `docs.json` at its root; sources in `diagrams/src`, images in `images/diagrams`.

## Updating a template
Replace the file in `skills/diagram-standards/templates/` keeping the same file name.
If the title-block cell ids change, update the table in `scripts/new_diagram.py` and `references/template-catalog.md`.
