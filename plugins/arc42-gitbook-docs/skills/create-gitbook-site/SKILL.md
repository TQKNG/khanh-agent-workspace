---
name: create-gitbook-site
description: Create the approved six-space GitBook site after mandatory user questions and readiness validation.
---

# Create the documentation site

Read ../../references/intake-and-evidence.md, ../../references/site-blueprint.json and ../../references/block-and-delivery-standard.md.
Always ask and receive an answer before construction; a user request to skip questions does not supply missing product information.
Complete the source, destination and page readiness record and run `python3 ../../scripts/validate_session.py SESSION --phase write`.
Do not create even an empty site until readiness passes.
Ask the site name, organization, new/existing choice and direct/template/Git Sync onboarding path.
Use exactly Documentation - <confirmed product name>, avoiding a duplicated prefix.
List existing sites and reuse only an explicitly selected exact match.
For direct authoring, create six empty spaces in blueprint order: Overview, Solution Architecture and Design, Getting Started, API Reference, Security and Privacy, Release Notes.
Use the numbered blueprint display titles unless the user explicitly requires other labels.
Create the space and attach its returned ID to the selected site, inheriting its title.
Keep the site unpublished unless separately authorized.
Never replace selected existing variants or alter unrelated sites.
Verify associations, order, names, IDs and publication state after writes.
Recover from partial failures using the run manifest and server readback, not blind recreation.
Continue with generate-arc42-docs for content and reviewable change requests.
