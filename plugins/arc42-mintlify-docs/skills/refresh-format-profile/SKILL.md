---
name: refresh-format-profile
description: Re-read existing products in the tqkng/docs Mintlify site and propose updates to the format profile when the documentation format has evolved.
---

# Refresh the format profile

Read ../../references/format-profile.json and ../../references/mintlify-format-standard.md first.
The Report Tool product is the reference format unless the user names another one.
This skill never changes a product page.
It only proposes changes to the plugin's own reference files.

## Steps

1. List the products in `docs.json` through the Mintlify connection and ask which two or three to learn from.
2. For each chosen product read a few pages per group: the landing page, one overview page, a building block or runtime page, an AD page, a getting-started page, a security page and a release page.
3. Compare frontmatter, numbered headings, register IDs, components, diagram embedding and file paths with the profile.
4. List differences as proposed edits to format-profile.json or mintlify-format-standard.md.
   Separate differences that look like improvements from one-off variations or mistakes.
5. Ask the user which differences become the standard.
6. Apply only the approved edits, then run the plugin tests.

## Rules

Do not copy product content into the profile, only structure and patterns.
Do not add a page to the profile without the user's approval, and keep the page keys stable because sessions refer to them.
Keep sentences on separate lines and never use the em dash.
Report which products and pages were read.
