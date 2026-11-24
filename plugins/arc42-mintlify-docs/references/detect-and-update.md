# Detect and update

## Detect

1. Read `docs.json` from `tqkng/docs` through the Mintlify connection and save it to a local file.
2. Run `python3 -I scripts/detect_project.py --docs-json DOCS_JSON --product "Product name" --slug product-slug`.
3. The script reports `mode` as `new` or `update`, the navigation entry it found, the profile pages that are present, missing or extra, and structural deviations such as a missing group.
4. Read a few of the existing pages when the result is `update`.
   Compare their frontmatter, numbered headings, register IDs and diagrams with format-profile.json.
5. Treat the script as a structural check only.
   Content freshness needs the pinned commit of the page compared with the current source.

## New project

Follow the generate-arc42-docs skill from interview to delivery.

## Existing project

Do not edit anything yet.
Give the user a brief update summary, at most one screen, in this order:

1. **Status:** product entry, page count found against the profile, pinned commit found on the landing page and the current source commit.
2. **Missing:** profile pages that do not exist, with a one-line reason each.
3. **Out of format:** pages that exist but break the format standard, such as a missing frontmatter field, unnumbered headings, an external image URL, or a Mermaid diagram where a template applies.
   A Mermaid runtime scenario is out of format.
   A Mermaid class or state diagram is reported as a warning, not as out of format.
4. **Possibly stale:** pages whose evidence predates the current commit.
5. **Proposed changes:** the minimal list of pages to create or edit, plus anything intentionally left alone.

Wait for the user to choose which items to apply.
Record the chosen pages as `ready` and everything else as `unchanged`.
Preserve existing page IDs, slugs, human edits and unrelated products.
Use focused `edit_page` changes instead of rewriting whole pages.
Never delete a page.
