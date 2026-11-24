---
name: new-diagram
description: >
  This skill should be used when the user runs "/new-diagram" or asks to "create a new
  diagram from the template", "start a system context diagram", "new whitebox/deployment/
  component/class/state diagram". Creates the working .drawio file from the approved template with the
  title block filled in.
argument-hint: "<sc|bc|l1-whitebox|l1-deployment|l2-component|seq|class|state> <doc-number> [title]"
metadata:
  version: "0.3.0"
---

# /new-diagram

Arguments: `<type> <doc-number> [title]`.

1. Load the `diagram-standards` skill and follow its rules.
2. Validate `<type>` against `sc`, `bc`, `l1-whitebox`, `l1-deployment`, `l2-component`, `seq`, `class`, `state`.
   For `seq`, `class` and `state`, do not run `new_diagram.py`: follow the skill's "Sequence diagrams" or "Class diagrams (`class`) and state diagrams (`state`)" section (write the `.mmd`, then run the converter).
   When missing or invalid, show the options with one-line descriptions from the skill's template table and wait for a choice.
3. When `<doc-number>` is missing, build it as `<prefix>-<ProductName>-001` from the skill's table, using the product name found in the repository (docs.json name or the existing diagrams), and state the number chosen.
4. Take the author from the user's request or from existing diagrams in `diagrams/src`; ask when neither exists.
   Default title: `<Product> – <diagram type name>`.
5. Run:
   ```bash
   python3 ../diagram-standards/scripts/new_diagram.py <type> <doc-number> --title "<title>" --author "<author>"
   ```
6. Report the created path in one line, then offer to fill the diagram for the system being documented (continue at step 3 of the skill's workflow).
