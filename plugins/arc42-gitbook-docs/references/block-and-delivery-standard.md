# GitBook format and delivery standard

## Page contracts

Load site-blueprint.json for the six-space order, page keys, required content and native blocks.
Expand product, decision and version tokens only from answered intake or evidence.
Preserve existing page IDs, slugs, user content, numbering and unrelated spaces.
Number standard pages consistently; preserve historical URLs rather than renaming slugs cosmetically.
Use one H1, sequential heading levels, short paragraphs and descriptive links.
Overview navigation is a six-row task table, not an exhaustive chapter outline.
Use a canonical glossary, decision index, API spec and security control register; cross-link instead of duplicating.
Apply the user's design standard when accessible; renderer-native Markdown is the portable default.
Never package an absolute personal branding path as a dependency.
Keep content understandable without custom colors, HTML or fonts.

## API template

Ask whether an API exists or a design contract is requested.
If unavailable, ask for the missing contract or an explicit decision to omit; do not fabricate one.
For approved design, confirm every material host, auth, schema and limit decision before drafting.
Preserve the built-in API renderer: builtin:openapi with models=true and downloadLink=true unless the user chooses otherwise.
Read existing computed page props and dependencies before changing them.
Use an independently owned spec for the selected destination; never mutate a shared spec that would change unrelated variants.
Create the organization spec and insert_computed_page through a space change request.
Do not manually write openapi-operation blocks or edit generated endpoint pages.
Use info.description H2 sections for welcome, servers/authentication, quickstart, lifecycle and errors.
Use OpenAPI x-parent and x-page-title for domain/resource navigation where supported.
Include schemas, success/error examples, code samples and appropriate security schemes.
Ask whether Try it should be enabled and which confirmed server it should call.
Represent that answer with x-hideTryItPanel; do not claim live testing when an example host or unimplemented API is selected.
Do not create a separate testing guide or duplicate legacy group unless requested.
Check asynchronous spec processing errors before reporting success.

## Scalable writes

Resolve target IDs through connector discovery, inspect all selected space revisions and open drafts, and build a page-ID inventory.
Use stable blueprint keys in the local run manifest: project, source fingerprint, organization, site, space key, page key, page ID, revision and change-request ID.
Never create a duplicate based on a title mismatch alone; ask which existing page or variant is authoritative.
Keep one source ledger with claim, provenance, source revision, page keys and user-confirmed decisions.
Run validate_session.py --phase write before any site, space, association, spec or content creation.
Use the GitBook connector's described operations rather than guessed IDs or endpoints.
Write only through change requests for space content.
Use expectedRevision where supported and keep batches within the connector's limit (currently at most 50 changes).
Store each returned revision and inserted page ID before continuing.
Read every changed page back from the change request and verify cross-space references normalize to real targets.
Check headings, table width, code fences, diagram syntax and secret redaction.
Inspect rendered desktop and narrow-screen output where available.
Report visual verification unavailable if the browser is blocked; source readback is not a visual test.
After uncertain writes, stop and reconcile IDs and state before retrying.
On conflict, reread the latest content and preserve concurrent human edits; never blindly replay replacement content.

## Destination modes

The final output is a GitBook site with links to its change requests or merged revisions.
Preview is an optional intermediate artifact, not successful delivery of a requested site.
Ask for delivery mode; silence never authorizes merge or publication.
Draft mode creates reviewable change requests without merging.
Merge mode requires approval of the exact reviewed revision after verification.
Site publication and visibility changes require separate explicit authorization and post-write verification.
For a new site, ask for its name and onboarding path before constructing it.
Direct authoring creates the six empty spaces in blueprint order and attaches them to one site.
Default site template import and Git Sync import are alternative onboarding paths, not steps to combine with direct structure creation.
The API computed-page template is a page-rendering choice, not a full-site template import.
Do not set up Git Sync unless explicitly selected.
Preserve existing sync ownership and ask which source is authoritative before editing synchronized content.
Do not change publication, sharing or visibility as a side effect of content generation.

## Completion report

Report exact source/ref, answered and unresolved questions, selected destination, page counts by space, native blocks used, preserved/omitted pages, and IDs/URLs.
Report Draft, Merged and Published separately.
Include content readback, link, schema, secret, API-processing and rendered checks with pass/fail/not-run evidence.
A partial failure must identify last confirmed write and recovery action.
Do not claim a successful live workflow based only on mocked tests or instruction inspection.
