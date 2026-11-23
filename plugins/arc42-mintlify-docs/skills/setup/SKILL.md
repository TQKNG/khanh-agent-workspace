---
name: setup
description: Start question-driven arc42 documentation for the tqkng/docs Mintlify site, detect whether the project is already documented, and verify source and destination before construction.
---

# Set up arc42 Mintlify Docs

Read ../../references/intake-and-evidence.md before taking action.
The destination is fixed to the Mintlify deployment `kcode-workspace` and the repository `tqkng/docs`.
Always ask and receive an answer before construction, including when invoked directly.
Inspect the Mintlify connection and the existing navigation read-only while waiting.
Accept a GitHub repository, a supplied plan or an idea.
GitHub is required only for repository input.
Mintlify read and write access is required for delivery.
If the Mintlify connection is missing, say so and stop before any write.
Ask for the product name and slug, then run project detection as described in ../../references/detect-and-update.md.
Report the detected mode in one sentence and confirm it with the user.
For a new project continue with the generate-arc42-docs skill.
For an existing project give the brief update summary and let the user choose what to apply.
