# Mintlify delivery

Read ../../../references/intake-and-evidence.md and ../../../references/mintlify-format-standard.md first.
Call the Mintlify `read_skill` tool before writing pages, because it holds the current component and `docs.json` rules.
Use the Mintlify tools as their descriptions define them and never guess identifiers.

## Branch and writes

Work on a new branch created with `create_branch`, named `docs/<slug>-arc42-<YYYYMMDD>`.
Pass `branch` on every call, because nothing is remembered between calls.
Never write to `main` directly.
Create pages with `write_page` and navigation with `create_node`, `move_node` or `update_config`.
Change existing pages with `edit_page` and send only the changed text.
Read a page with `read` and `forEdit` before changing it.
Pass the returned `version` as `baseVersion` and, on conflict, read the latest page again and keep concurrent human edits.
Commit diagram sources to the branch and let the export workflow create the PNGs, as references/diagram-integration.md describes.
Use `upload_file` and `finalize_file_upload` for a PNG only when the workflow cannot run.
Keep batches small and record each page path and returned version in the run manifest before continuing.
After an uncertain write, stop and reconcile state before retrying.

## Verification

Read every changed page back from the branch.
Run scripts/check_pages.py on the generated MDX before upload and again on the readback copy.
Check frontmatter, heading numbers, table width, code fences, Mermaid syntax, links, diagram sources and secret redaction.
Run `mint validate` and `mint broken-links` when the CLI is available and report them as not run otherwise.
Inspect the preview on desktop and narrow width when a browser is available.
Source readback is not a visual test.
Use `status` and `diff` to confirm that only the intended files changed.

## Delivery modes

Draft: leave the branch for review, with a draft pull request when the deployment creates one.
Merge: only after the user approves the exact reviewed revision and `validate_session.py --phase merge` passes.
Publish: a separate explicit authorization.
After publishing, the change is live only when `deployment_status` reports live.
Silence never authorizes merge or publish.
Do not change deployment settings, domains, access or navigation of other products.

## Completion report

Report the exact source ref and commit, answered and unresolved questions, detected mode, pages created, edited, unchanged and omitted, diagrams exported and pending, branch and pull request, and verification results with pass, fail or not-run for each check.
Report Draft, Merged and Published separately.
A partial failure names the last confirmed write and the recovery action.
Do not claim a live result based on mocked tests or instruction inspection.
