---
name: session-token-audit
description: Audit Codex session and child-session token usage from local JSONL logs, estimate API cost, and record results in the Project Demo Sandbox Notion tables.
---

# Session Token Audit

Audit only an explicitly selected Research Results row or date range.

## Workflow

1. Fetch Research Results and require its `Main thread ID` property.
2. Read the selected row and use its main thread ID as the root thread ID.
3. Scan `~/.codex/sessions` recursively. Use `session_meta.payload.id` as identity and `parent_thread_id` for recursive child discovery.
4. For each session, sum each unique `token_usage_record.payload.usage` by `response_id`: input, cached input, output, reasoning output, and total tokens. Never sum cumulative `thread_token_usage`.
5. Determine models from response and session metadata, preserving multiple models as a grouped breakdown.
6. Calculate estimated USD cost from pricing.md in references folder. If the model's pricing is not available, do a quick research and update the pricing.md. Since input includes cached input, charge `(input - cached) * input_rate + cached * cached_rate + output * output_rate`. Reasoning is already part of output and is not charged twice.
7. Create or reconcile one Tasks Tracker row per session, linked to the Research Results row, and populate all token, model, duration, request, cost, status, and completion fields.
8. Verify the relation and existing `Total Task Cost` rollup with a fresh Notion fetch.
9. Return the root, child tree, per-session metrics, pricing sources, rollup total, and warnings.

Unknown model IDs must be marked `unpriced`; do not invent rates. This is an API list-price estimate, not billing reconciliation. The official Usage API is organization-level and is not a source for local Codex session IDs.

Do not expose prompt contents, overwrite unrelated Notion content, or write directly to the read-only rollup. Use `scripts/audit_sessions.py` for deterministic local parsing and read `references/pricing.md` when resolving prices.
