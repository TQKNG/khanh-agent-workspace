---
name: generate-arc42-docs
description: Generate or update arc42 documentation for a project in the tqkng/docs Mintlify site, in the Report Tool format, through required user questions, evidence, approved diagrams and a reviewable branch.
---

# Generate arc42 documentation in Mintlify

Read ../../references/intake-and-evidence.md, ../../references/format-profile.json and ../../references/mintlify-format-standard.md.
Read references/arc42-c4-mapping.md for architectural semantics and references/mintlify-delivery.md for connector safety.
Read ../../references/diagram-integration.md before any diagram work.
Read ../../references/detect-and-update.md when the detected mode is update.
This workflow covers all six groups, including getting started, API, security and releases.
Always ask at least one focused question and receive an answer before constructing anything.
Direct invocation must not bypass the interview, detection or the readiness validator.

## Discover and interview

Inspect the exact input: a repository with an explicitly confirmed ref and immutable commit, a supplied plan with its version, or a user-confirmed idea brief.
Run project detection and confirm the mode with the user.
Build the evidence ledger and identify conflicting or missing values for every profile page.
Ask focused follow-ups until the session is sufficient.
Existing context can answer a fact, but the user must confirm the current scope before construction.
An omission is a user decision recorded with a reason.
For plans and ideas, obtain approval of each material design decision and never describe design as implemented.
Never copy product names, endpoints, vendors, glossary terms or security claims from another product.

## Plan and validate

Create a session record from ../../references/session.example.json.
Record user answers, source evidence, page decisions, diagrams, unresolved questions and the reviewed fingerprint.
Run `python3 -I ../../scripts/validate_session.py SESSION --phase write`.
If validation fails, ask for the missing values and do not write to Mintlify.

## New project

Generate every page the profile requires and every conditional page the user keeps.
Use the page contracts in format-profile.json for titles, file paths, numbered headings, tables and register IDs.
Create the six groups, the Decision records group and the product entry in `docs.json`.
Put each architecture diagram, runtime scenario, domain model and entity lifecycle through diagram-standards.
Mark missing facts as `[OWNER INPUT REQUIRED: ...]` and report each one.

## Existing project

Do not edit before the user chooses items from the update summary.
Create only the missing pages the user chose and edit only the chosen pages.
Preserve slugs, page IDs, human edits and other products.
Bump diagram versions when a diagram changes.

## Check and deliver

Write the pages to a scratch directory first and run `python3 -I ../../scripts/check_pages.py PAGES --root REPO_ROOT`.
Fix every error before uploading.
Deliver through a branch as references/mintlify-delivery.md describes.
Read every changed page back and check links, secrets and diagram sources.
Keep merge distinct from publish.
Run `python3 -I ../../scripts/validate_session.py SESSION --phase merge` before any merge.
Report the branch, pull request, page counts, diagrams, open owner-input markers and every check as pass, fail or not run.
