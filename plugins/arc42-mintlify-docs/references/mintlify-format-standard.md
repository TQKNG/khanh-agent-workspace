# Mintlify format standard

This standard is derived from the Report Tool product in `tqkng/docs`.
The machine-readable page contracts are in format-profile.json.
This file explains the rules that the profile cannot express.

## Structure

Each product is one entry in `docs.json` under `navigation.products`.
The entry has six groups in this order: Overview, Solution architecture and design, Getting started, API reference, Security and privacy, Release notes.
A nested group named "Decision records" holds the AD pages inside the architecture group.
Group names are not numbered.
Page titles carry the section numbers 1.1 to 6.6.
File paths use `<slug>/<section>/<file>.mdx`, which is the convention of the newer products.
Overview and architecture file names keep the arc42 prefix 01 to 12, so `01-introduction-and-goals` is page 1.2 and `12-glossary` is page 2.8.
Preserve existing slugs and paths in update mode.
Never rename a slug for cosmetic reasons.

## Frontmatter

Every page has `title`, `description` and `keywords`.
The title is the numbered title from the profile.
The description is one sentence.
Keywords hold the product name and one domain keyword.
The quickstart page also sets `sidebarTitle`.
Do not add an H1, because Mintlify renders the title.

## Headings and body

Section headings are numbered `## 1.2.1 Introduction`, with numbers that match the page number.
Use H2 for numbered sections and H3 or H4 for sub-blocks.
Keep paragraphs short and write each full sentence on its own physical line.
Never use the em dash character.
Use plain tables for registers: IDs such as QG-1, TC1, OC1, C1, F1, R-001, TD-001, SEC-01, AD-001.
Use `<Info>` for the source repository and commit on the landing page.
Use `<Tabs>` for example servers.
Use `<Frame caption="...">` around diagrams.
Use `<Callout>` or `<Note>` sparingly.
Link with descriptive text and root-relative paths.
Link to canonical pages instead of repeating content: glossary, decision index, API reference, control register.

## Evidence and placeholders

Pin the source to a 40-character commit and cite it on the landing page, the getting-started pages and the glossary lead sentence.
Link implementation evidence as permalinks at that commit.
Show an abbreviated seven-character SHA as link text.
Mark a fact the evidence does not establish as `[OWNER INPUT REQUIRED: <what is missing>]`.
Mark design content as design, never as implemented.
Do not copy product names, endpoints, vendors, security claims or glossary terms from another product.
Never include secret values, even to document an exposure.
Add `Last documentation review: YYYY-MM-DD` to the release index page.

## Diagrams

Architecture diagrams use the approved draw.io templates through the diagram-standards plugin.
See references/diagram-integration.md.
Runtime scenarios, the Level 3 code view and the domain model stay in Mermaid.
Mintlify renders fenced `mermaid` blocks.

## API reference

Use a reviewed OpenAPI file from the repository when one exists and register it in `docs.json` so Mintlify generates operation pages.
Write only the narrative pages (4.1 to 4.5) by hand.
Keep example hosts labelled as examples and disable Try it unless a confirmed server exists.
Never invent routes, schemas, examples or error codes.
Omit the whole group when no API exists and the user confirms the omission.
