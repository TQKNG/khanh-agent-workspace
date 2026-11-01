# Reference site analysis

Reviewed on 2026-11-01 from the connected GitBook site Documentation - ReportGeneratorTool.
Read all 46 content pages across six spaces, including nested architecture decisions and generated API pages.
The live revision and per-page heading/block inventory are recorded in [reference-site-analysis.json](reference-site-analysis.json).
The inventory contains structural metadata, not repository secrets or copied customer content.

## Standard information architecture

| Space | Required content | Native blocks |
| --- | --- | --- |
| 1. Overview | Landing/navigation, goals, constraints, context, strategy | Compact navigation table, source hint, comparison tables, C4 context diagram |
| 2. Solution Architecture and Design | Building blocks, runtime, deployment, crosscutting concerns, decision index and children, quality, risks, glossary | C4 container diagrams, sequence/deployment diagrams, decision and quality tables |
| 3. Getting Started | Setup-path index, prerequisites/configuration, local run, containers, first result, deployment, troubleshooting | Procedure steppers, language-tagged code, configuration and troubleshooting tables |
| 4. API Reference | Welcome, servers/auth, quickstart, lifecycle, errors, domain/resource groups, models, download | Built-in OpenAPI computed pages, tabs, stepper, error tables, code samples, Try it according to user choice |
| 5. Security and Privacy | Assets/boundaries, access/secrets, data inventory/retention, control register, incident response | Responsibility, permission, retention, risk and severity tables; ordered actions |
| 6. Release Notes | Release index, Unreleased, actual release entries, development milestones, known issues, upgrade/rollback | Linked release table, categorized changes, issue table, operational steps |

Use [site-blueprint.json](../plugins/arc42-gitbook-docs/references/site-blueprint.json) for each page's content requirements, parent, applicability and blocks.
Product-specific names, vendors, release versions and API domains are not reusable template facts.
The original site's standalone testing guide and duplicate bottom legacy section were intentionally removed, so the new blueprint does not recreate them by default.
Container/deployment pages and release entries require evidence or explicit applicability decisions.
Use the site's reading hierarchy while preserving stable IDs and existing URLs during updates.

## Defects found in the previous plugin

- The six-space order placed Getting Started before Architecture, unlike the reference site.
- Setup could select a repository default branch without an explicit source answer.
- The generation skill only handled repositories and excluded full API/product documentation.
- Skill frontmatter names did not match their directories.
- No shared page-level content and block contract covered the six spaces.
- No executable prerequisite rejected unanswered questions or unreviewed scope changes.
- General evidence guidance could silently leave required details as TBD.
- The API workflow lacked independent spec ownership and explicit Try it selection.

## Changes

Version 0.3.0 preserves plugin identity, marketplace identity, default prompts and branding.
All three entry points load one intake/evidence contract and the shared blueprint.
Repository, plan and idea inputs use the same readiness gate with source-specific validation.
Plans and ideas require approved design facts rather than fictitious implemented behavior.
A source/scope fingerprint invalidates stale user confirmation automatically.
Merge approval is bound to the exact reviewed GitBook revision.
GitBook change requests, publication separation, bounded batches and retry reconciliation are part of the delivery standard.
The validator is a structural guard invoked by skill instructions; it is not an interception layer around connector tools.
An agent must still verify semantic sufficiency, evidence accuracy and the actual user answers.
