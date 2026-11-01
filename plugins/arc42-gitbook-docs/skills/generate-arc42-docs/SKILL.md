---
name: generate-arc42-docs
description: Generate consistent six-space GitBook documentation from a repository, plan or idea through required user questions, evidence and reviewable changes.
---

# Generate consistent GitBook documentation

Read ../../references/intake-and-evidence.md, ../../references/site-blueprint.json and ../../references/block-and-delivery-standard.md.
Read references/arc42-c4-mapping.md for architectural semantics and references/gitbook-delivery.md for connector safety.
This workflow covers the whole six-space site, including setup, API, security and releases.
Always ask at least one focused question and receive an answer before constructing documentation.
Direct invocation must not bypass the interview or readiness validator.

## Discover and interview

Inspect the exact input: repository with explicitly confirmed branch and immutable commit, supplied plan/version, or user-confirmed idea brief.
Inspect the target site, every selected space and its page tree read-only.
Build the evidence ledger and identify conflicting or missing material values for every blueprint page.
Ask focused follow-ups until the session is sufficient; never assume values from silence or technology conventions.
Existing context can answer a fact, but the user must confirm the current scope before construction.
An explicit omission is a user decision recorded with a reason, not a guessed default.
For ideas and plans, obtain approval of each material design decision; do not describe design as implemented.
Never copy reference-site product names, endpoints, vendors or security claims into another project's content.

## Plan and validate

Create a session record from ../../references/session.example.json.
Record user answers, source evidence, selected page decisions, unresolved questions and the reviewed fingerprint.
Run ../../scripts/validate_session.py SESSION --phase write.
If validation fails, ask for the missing values and do not mutate GitBook.
Use the approved blueprint to plan stable page keys and canonical links.
For a new destination, route through create-gitbook-site after readiness passes.

## Generate and deliver

Generate content and native blocks according to each blueprint page contract.
Keep arc42 sections 1-4 in Overview and 5-12 in Architecture, including Quality Requirements as section 10.
Retain existing page IDs and slugs, use focused updates and preserve human content.
Write through the selected GitBook change requests and reread every changed page.
Maintain resumable run metadata and bounded batches.
Validate the OpenAPI source before generated API pages, and keep Try it consistent with explicit user choices.
Do not create fictional releases or success claims to fill a page.
Run content, link, secret, schema and rendered checks and report unsupported checks honestly.
For merge, run readiness --phase merge with approval bound to the exact reviewed revision.
Keep merge distinct from site publication.
Deliver the GitBook site and per-space change-request URLs plus the verification report.
