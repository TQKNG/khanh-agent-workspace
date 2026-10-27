---
name: create-gitbook-documentation-site
description: Create the standard GitBook site and six-space structure. Use whenever the user asks to create, start, scaffold, initialize, or set up new GitBook documentation or a new documentation site.
---

# Create a GitBook documentation site

Create the standard documentation structure before generating or publishing documentation content.

Use the GitBook connector for all reads and writes.

## Ask for the site name first

For every new GitBook documentation request, first ask the requester:

`What is the name of the site?`

Do not create the site or spaces until the requester answers.

Trim surrounding whitespace from the answer.

If the answer already starts with `Documentation - `, remove that prefix before constructing the final title so the prefix appears only once.

The final site title must be exactly:

`Documentation - <site name>`

## Use direct GitBook delivery by default

When the request is to inspect a repository and generate arc42 documentation, use direct GitBook delivery.

Create the site and empty editable spaces through the GitBook connector, then let the repository generation skill write through GitBook change requests.

Do not configure Git Sync and do not apply GitBook's default site template in this mode.

Do not ask the requester to choose between Git Sync and the default template when the request already establishes direct repository inspection and GitBook delivery.

Use Git Sync only when the requester explicitly asks for Git Sync.

If Git Sync is explicitly selected, stop this standard six-space workflow and follow the Git Sync onboarding path instead.

Do not combine Git Sync, the default template, and this standard structure.

## Resolve the organization

Use an organization already selected unambiguously in the request or current context.

If more than one organization is available and none is selected, ask one targeted organization question after obtaining the site name.

Never guess an opaque organization ID.

## Prevent duplicates

List the organization's existing sites before creating anything.

Compare normalized titles for an exact match with the final site title.

If a matching site exists, do not create a duplicate.

Ask whether the requester wants to use the existing site or provide a different name.

## Create the site

Create one site with the final title.

Keep the new site in its default unpublished or draft state unless the current request explicitly asks to publish it.

Record the returned site ID and URL.

## Create the spaces

Create these six spaces in this exact order:

1. Overview
2. Getting Started
3. Solution Architecture and Design
4. API Reference
5. Security and Privacy
6. Release Notes

Before each creation, inspect the spaces already associated with the new site and reuse an exact-name match created during the current operation.

Create each new space as an empty editable space with `empty: true` and `editMode: live`.

Associate the existing space ID with the site after the space is created.

Do not pass a site-specific title override when associating the space.

The site navigation title must inherit the underlying space title so a later rename stays consistent.

Do not create additional spaces, page groups, variants, or sections unless the user requests them.

Associate each space with the site and preserve the required order in the site's content structure.

Do not silently substitute pages for spaces.

## Recover safely from partial failure

After any failed write, re-fetch the site and its associated spaces before retrying.

Resume from the first missing space rather than recreating the site or completed spaces.

Stop and report the partial result when the connector cannot confirm whether a write succeeded.

## Verify the result

Re-fetch the site after all writes.

Verify:

- The site title exactly matches `Documentation - <site name>`.
- Exactly the six requested spaces were added by this workflow.
- All six names match exactly.
- Their order matches the required sequence.
- Every space is associated with the created site.
- The underlying space title and the site navigation title match for every space.
- No Git Sync installation was created or used by the direct-delivery workflow.
- The site remains unpublished unless publication was explicitly requested.

Report the organization, site title, site ID, site URL, space names and IDs, order, and publication state.

Only after this verification may another packaged skill generate content inside the spaces.
