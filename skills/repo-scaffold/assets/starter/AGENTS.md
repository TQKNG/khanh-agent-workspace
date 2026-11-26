# Project: {{PROJECT_NAME}}

## Purpose

- Project summary: {{PROJECT_SUMMARY}}.
- Primary users: {{PRIMARY_USERS}}.
- Main outcome: {{PRIMARY_OUTCOME}}.
- Repository type: {{PROJECT_TYPE}}.
- Supported runtime or platform: {{SUPPORTED_RUNTIME_OR_PLATFORM}}.
- Current default branch: `{{DEFAULT_BRANCH}}`.

## Instruction precedence

- Follow this file for project-specific agent instructions.
- Follow more specific `AGENTS.md` files in nested directories when they apply.
- Follow `CONTRIBUTING.md` for contribution and pull request requirements.
- Follow `README.md` for project setup and user-facing behavior.
- Use `.github/pull_request_template.md` when preparing a pull request.
- Use `.github/workflows/ci.yml` to identify automated checks.
- Preserve existing conventions unless the requested change requires a change.
- Ask before changing externally visible behavior beyond the requested scope.

## Commands

- Install: `{{INSTALL_COMMAND}}`.
- Test: `{{TEST_COMMAND}}` (must pass before any task is done; if unavailable, document the alternative verification).
- Lint: `{{LINT_COMMAND}}`.
- Build: `{{BUILD_COMMAND}}`.
- Single test: `{{SINGLE_TEST_COMMAND}}`.
- Type check: `{{TYPECHECK_COMMAND}}`.
- Format check: `{{FORMAT_CHECK_COMMAND}}`.
- Format files: `{{FORMAT_COMMAND}}`.
- Run locally: `{{RUN_COMMAND}}`.
- Start required services: `{{SERVICE_START_COMMAND}}`.
- Stop required services: `{{SERVICE_STOP_COMMAND}}`.
- Database migration: `{{MIGRATION_COMMAND}}`.
- Database reset: `{{DATABASE_RESET_COMMAND}}`.
- Package or artifact check: `{{PACKAGE_CHECK_COMMAND}}`.
- Documentation check: `{{DOCUMENTATION_CHECK_COMMAND}}`.
- Full local verification: `{{FULL_VERIFICATION_COMMAND}}`.
- Use `Not configured` when the repository has no command for a listed task.
- Do not replace a missing command with a guessed command.
- Do not report a command as passing unless it completed successfully.
- If a command cannot run, report the command and the reason.

## Completion requirements

- Read the relevant project instructions before changing files.
- Inspect the current branch and working tree before editing.
- Understand the affected code and its callers before changing behavior.
- Keep the change within the requested scope.
- Add or update tests for behavior changes when the repository supports tests.
- Run the applicable test command before considering implementation complete.
- Review the final diff for unrelated changes and accidental generated files.
- Check that no credentials or private data appear in the diff.
- List every verification command and its result in the pull request.
- Explain any check that could not be run.

## Workflow

- Non-trivial changes: write or read the spec in `specs/<NNN-name>/spec.md`.
- Non-trivial changes: plan the implementation before editing project files.
- Non-trivial changes: use plan mode when the working environment supports it.
- Non-trivial changes: implement only after the plan matches the requested outcome.
- If implementation drifts from `plan.md`, update `plan.md` in the same commit.
- Bug fixes: reproduce the bug or identify a reliable failing case first.
- Bug fixes: write a failing regression test before changing implementation when feasible.
- Bug fixes: do not edit a test merely to make the implementation pass.
- Refactors: preserve observable behavior unless behavior change is requested.
- Keep diffs small and focused.
- Make one concern per commit.
- Do not combine unrelated cleanup with a requested fix.
- Do not revert or overwrite user changes.

## Specifications and plans

- Spec root: `{{SPEC_ROOT}}`.
- Spec file pattern: `{{SPEC_FILE_PATTERN}}`.
- Plan file pattern: `{{PLAN_FILE_PATTERN}}`.
- Use `specs/<NNN-name>/spec.md` when the project has no existing spec convention.
- Keep implementation plans aligned with the approved spec.
- Break plans into reviewable steps.
- Include validation commands in implementation plans.
- Keep plans current when implementation changes materially.

## Testing rules

- Test framework: {{TEST_FRAMEWORK}}.
- Unit test location: {{UNIT_TEST_LOCATION}}.
- Integration test location: {{INTEGRATION_TEST_LOCATION}}.
- Use the narrowest useful test while developing.
- Run the broader relevant suite before reporting completion.
- Prefer tests that assert externally observable behavior.
- Add a regression test for each reproducible bug fix when feasible.
- Include boundary cases when they affect correctness.
- Include failure cases for validation and error-handling changes.
- Update snapshots only after reviewing the intended output change.
- Do not weaken assertions to make a failing test pass.
- Record the exact test command and result in the pull request.
- Test exclusions or unavailable services: {{TEST_LIMITATIONS}}.

## Build and quality checks

- Linter: {{LINTER}}.
- Formatter: {{FORMATTER}}.
- Type checker: {{TYPECHECKER}}.
- Build system: {{BUILD_SYSTEM}}.
- Required CI workflow: `.github/workflows/ci.yml`.
- Required CI status check: `{{REQUIRED_CI_STATUS_CHECK}}`.
- Run formatting checks without rewriting unrelated files.
- Fix new warnings introduced by the change.
- Do not commit generated output unless repository policy requires it.
- Generated file policy: {{GENERATED_FILE_POLICY}}.
- CI-specific limitations: {{CI_LIMITATIONS}}.

## Repository layout

- Application entrypoint: `{{APPLICATION_ENTRYPOINT}}`.
- Main source directory: `{{SOURCE_DIRECTORY}}`.
- Test directory: `{{TEST_DIRECTORY}}`.
- Configuration directory: `{{CONFIGURATION_DIRECTORY}}`.
- Documentation directory: `{{DOCUMENTATION_DIRECTORY}}`.
- Keep code in the directory that owns its behavior.
- Avoid introducing a second location for an existing responsibility.
- Keep private implementation details out of public interfaces.
- Do not create empty directories or placeholder modules without a requirement.
- Add new top-level directories only when they have a clear project purpose.
- Update the README project tree when the repository structure changes.
- Do not list files in the README that are absent from the repository.

## Conventions

- Record only verified project conventions in this section.
- Replace each convention placeholder with a rule confirmed by repository evidence.
- Mark convention slots without a verified rule as `Not configured`.
- Error handling: {{ERROR_HANDLING_CONVENTION}}.
- Naming: {{NAMING_CONVENTION}}.
- Folder layout: {{FOLDER_LAYOUT_CONVENTION}}.
- Logging: {{LOGGING_CONVENTION}}.
- Configuration: {{CONFIGURATION_CONVENTION}}.
- API or interface design: {{INTERFACE_CONVENTION}}.

## Architecture boundaries

- Architecture overview: {{ARCHITECTURE_OVERVIEW}}.
- Main components: {{MAIN_COMPONENTS}}.
- Component ownership: {{COMPONENT_OWNERSHIP}}.
- Dependency direction: {{DEPENDENCY_DIRECTION}}.
- Public boundaries: {{PUBLIC_BOUNDARIES}}.
- External systems: {{EXTERNAL_SYSTEMS}}.
- Keep dependencies moving in the documented direction.
- Avoid circular imports or service dependencies.
- Keep domain rules out of transport and presentation layers.
- Update architecture documentation when a component boundary changes.
- Identify affected callers before changing a shared interface.
- Confirm compatibility before changing a public package or API.
- Known architectural constraints: {{ARCHITECTURAL_CONSTRAINTS}}.

## API and user-facing behavior

- API contract location: {{API_CONTRACT_LOCATION}}.
- Route or command conventions: {{ROUTE_OR_COMMAND_CONVENTIONS}}.
- Authentication model: {{AUTHENTICATION_MODEL}}.
- Authorization model: {{AUTHORIZATION_MODEL}}.
- Error response format: {{API_ERROR_FORMAT}}.
- Versioning policy: {{API_VERSIONING_POLICY}}.
- Validate untrusted input at the established boundary.
- Keep response and error shapes compatible unless a breaking change is approved.
- Do not expose internal errors, stack traces, or secrets to callers.
- Preserve authentication and authorization checks on every affected path.
- Test both allowed and denied access when authorization changes.
- Document public API changes in the canonical contract.

## Data and persistence

- Primary data stores: {{DATA_STORES}}.
- Schema location: {{SCHEMA_LOCATION}}.
- Migration location: {{MIGRATION_LOCATION}}.
- Data access boundary: {{DATA_ACCESS_BOUNDARY}}.
- Transaction convention: {{TRANSACTION_CONVENTION}}.
- Retention policy: {{DATA_RETENTION_POLICY}}.
- Treat persisted data as durable and potentially sensitive.
- Validate data before writing it to persistent storage.
- Preserve existing records during schema changes.
- Make migrations reversible when the storage system supports it.
- Never edit an applied migration unless project policy explicitly allows it.
- Add a new migration for changes to an already released schema.
- Include upgrade and rollback considerations in migration plans.
- Do not log secrets or unnecessary personal data from records.
- Do not use production data in local fixtures or tests.

## Security and privacy

- Secret storage method: {{SECRET_STORAGE_METHOD}}.
- Identity provider: {{IDENTITY_PROVIDER}}.
- Security policy location: {{SECURITY_POLICY_LOCATION}}.
- Treat user input, files, and external responses as untrusted.
- Keep credentials out of source code, logs, tests, and documentation.
- Use environment or managed secret stores according to project policy.
- Do not weaken authentication, authorization, or input validation to make a test pass.
- Use least privilege for application identities and automation tokens.
- Do not expose personal, confidential, or customer data in diagnostics.
- Sanitize data before rendering it in HTML, logs, or command output.
- Report a discovered security issue through the repository's private process.
- Security-sensitive changes require: {{SECURITY_REVIEW_REQUIREMENTS}}.
- Privacy requirements: {{PRIVACY_REQUIREMENTS}}.

## Dependencies and configuration

- Package manager: {{PACKAGE_MANAGER}}.
- Dependency manifest: {{DEPENDENCY_MANIFEST}}.
- Lockfile: {{LOCKFILE}}.
- Runtime version source: {{RUNTIME_VERSION_SOURCE}}.
- Environment configuration source: {{ENVIRONMENT_CONFIGURATION_SOURCE}}.
- Prefer existing dependencies over adding overlapping libraries.
- Pin or constrain versions according to repository policy.
- Keep lockfiles synchronized with manifest changes.
- Never commit local secrets or machine-specific configuration.
- Document required environment variables in the approved example file.
- Keep defaults safe for local development and production.

## Documentation

- Canonical user documentation: {{USER_DOCUMENTATION_LOCATION}}.
- Canonical API documentation: {{API_DOCUMENTATION_LOCATION}}.
- Operational documentation: {{OPERATIONS_DOCUMENTATION_LOCATION}}.
- Update documentation when setup, behavior, or operations change.
- Keep examples executable or label them clearly as illustrative.
- Use real project paths and commands in documentation.
- Remove stale instructions when the implementation changes.
- Do not claim unsupported features, integrations, or guarantees.

## Git and pull requests

- Branch naming policy: {{BRANCH_NAMING_POLICY}}.
- Commit convention: {{COMMIT_CONVENTION}}.
- Merge strategy: {{MERGE_STRATEGY}}.
- Pull request review policy: {{PULL_REQUEST_REVIEW_POLICY}}.
- Keep each change focused and reviewable.
- Use `.github/pull_request_template.md` for every pull request.
- Link the issue or specification when one exists.
- Describe behavior changes, migrations, and operational impact.
- Include verification commands and their actual results.
- Remove credentials, customer data, and personal information from examples and screenshots.
- Do not force-push shared branches unless repository policy permits it.
- Do not rewrite commits authored by another contributor without coordination.
- Do not create commits unless the task or established workflow calls for them.
- Never include agent attribution in commit messages.

## Things Claude gets wrong here

- Add an entry only after the same mistake has happened at least twice.
- State the observed mistake and the correct project-specific behavior.
- Keep each entry short, factual, and actionable.
- Do not list one-time mistakes or general advice.
- Do not duplicate a rule already stated above.
- Known repeated mistake 1: {{REPEATED_MISTAKE_1}}.
- Correct behavior 1: {{CORRECT_BEHAVIOR_1}}.
- Known repeated mistake 2: {{REPEATED_MISTAKE_2}}.
- Correct behavior 2: {{CORRECT_BEHAVIOR_2}}.
- Known repeated mistake 3: {{REPEATED_MISTAKE_3}}.
- Correct behavior 3: {{CORRECT_BEHAVIOR_3}}.

## Maintenance

- Owner of these instructions: {{INSTRUCTIONS_OWNER}}.
- Review trigger: {{INSTRUCTIONS_REVIEW_TRIGGER}}.
- Update this file when commands, architecture, or verified conventions change.
- Keep placeholders out of the project-level copy after scaffolding is complete.
- Keep every section; mark values that do not apply as `Not configured`.
- Add a short reason to each `Not configured` value when it helps.
- Keep the file aligned with `CLAUDE.md` and `.github/copilot-instructions.md` entrypoints.
- Keep shared agent rules in this file rather than duplicating them in tool-specific files.
- Last reviewed: {{LAST_REVIEWED_DATE}}.
