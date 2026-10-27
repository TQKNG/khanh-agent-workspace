---
name: setup
description: Set up GitBook documentation creation or the arc42 repository-to-GitBook workflow by checking connections and routing the request to the correct packaged skill.
---

# Set up arc42 GitBook Docs

Prepare the plugin for either a new GitBook documentation site or a repository-to-GitBook architecture workflow.

## Route the request

When the user asks to create, start, scaffold, or set up new GitBook documentation, run the `create-gitbook-documentation-site` skill first.

That skill must ask for the site name before creating the GitBook structure.

For repository inspection and arc42 generation, default to direct GitBook delivery with empty editable spaces and change requests.

Do not configure Git Sync or apply the default GitBook template unless the user explicitly requests that alternative workflow.

When the user asks to generate or refresh arc42 architecture documentation for an existing destination, continue with the repository workflow below.

## Required inputs

Obtain these values from the user or from an unambiguous current context:

- GitHub repository in `owner/repository` form.
- Repository ref or branch, defaulting to the repository default branch only when the user does not specify one.
- GitBook organization and existing destination space.
- Documentation mode: create a new architecture section or refresh an existing one.
- Delivery mode: draft only, open change request, or publish.

Do not invent identifiers or select a similarly named repository or space when more than one candidate exists.

## Connection checks

Use the installed GitHub and GitBook connectors.

Verify read access to the selected repository and read access to the selected GitBook space before reporting setup as complete.

If the user requests a change request or publication, also verify that the GitBook connection exposes the required write operations.

If a connector is missing or disconnected, explain which connection is required and stop before generating content that cannot be delivered as requested.

## Existing documentation

Read the current GitBook page tree before choosing where arc42 pages will live.

Preserve existing labels, order, nesting, links, and unrelated pages.

If an architecture section already exists, use it unless the user asks for a separate version.

## Completion

Report the selected repository, ref, GitBook space, destination section, and delivery mode.

Then offer to run the `generate-arc42-gitbook-docs` skill.
