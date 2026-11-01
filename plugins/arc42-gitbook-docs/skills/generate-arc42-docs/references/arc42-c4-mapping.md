# arc42 and C4 generation reference

This reference defines how to turn repository evidence into arc42 architecture documentation and C4 views.

It is based on the official arc42 and C4 documentation listed at the end of this file.

Research was refreshed on 2026-10-27.

The shared intake gate takes precedence over any evidence-placeholder wording below.
Unknowns and inferences must trigger questions before content construction; do not silently fill them with TBD.
Use the site blueprint for placement and user answers for applicability.

## Operating principles

Use arc42 as the documentation structure and C4 as the visual model inside relevant arc42 sections.

Do not treat C4 as a replacement for arc42.

Do not generate every possible diagram merely because the source repository is large.

The official C4 guidance says System Context and Container diagrams are sufficient for most teams.

Add Component, Dynamic, Deployment, or Code views only when they answer a concrete stakeholder question and repository evidence supports them.

Keep facts, inferences, and unresolved questions visibly separate.

## Evidence classification

Classify every material architectural claim as one of these values:

| Status | Meaning | Allowed presentation |
| --- | --- | --- |
| Confirmed | Directly supported by an authoritative repository artifact. | State as fact and cite the source path or URL. |
| Inferred | Supported by multiple implementation signals but not stated authoritatively. | Label as an inference and cite the signals. |
| Unknown | Not established by available evidence. | Use `TBD` and ask a focused question when it blocks useful documentation. |
| Conflicting | Two or more authoritative artifacts disagree. | Present the conflict and do not choose a winner without evidence. |

Good repository evidence includes entry points, package manifests, API contracts, schema migrations, infrastructure definitions, deployment workflows, runtime configuration schemas, architecture decisions, and focused tests.

Do not use generated files, vendored dependencies, secrets, local credentials, or unverified sample configuration as architecture authority.

## The 12 arc42 sections

Generate these sections with the exact numbering and order shown below.

### 1. Introduction and Goals

Capture the requirements overview, the three to five most important architecture quality goals, and the relevant stakeholders with their expectations.

Keep the requirements overview short and link to detailed requirements when they exist.

Do not invent business goals, stakeholder authority, or priorities from implementation code.

Use a table for quality goals with priority, concrete scenario, evidence, and status.

The official arc42 guidance distinguishes architecture quality goals from project goals and defers the complete quality catalogue to section 10.

### 2. Architecture Constraints

Capture technical, organizational, regulatory, and convention constraints that limit architecture choices.

Distinguish a hard constraint from an observed choice.

Examples of evidence include supported runtime versions, required platforms, repository policies, deployment restrictions, licensing rules, and compliance requirements.

Do not present a technology already in use as immutable unless an authoritative source says it is constrained.

### 3. Context and Scope

Describe the business context, technical context, system boundary, people, and external systems.

Include a C4 System Context view when enough evidence exists.

The System Context view covers one software system and its directly connected people and external software systems.

Keep internal containers, frameworks, protocols, deployment nodes, and code-level detail out of this diagram.

Document every external interface with direction, purpose, exchanged information, and protocol when known.

### 4. Solution Strategy

Summarize the small number of fundamental decisions that shape the solution.

Relate each strategy item to a goal or constraint from sections 1 and 2.

Examples include architectural style, decomposition approach, integration approach, persistence strategy, security boundary, and deployment strategy.

Do not manufacture rationale when the repository only establishes the selected technology.

### 5. Building Block View

Describe the static decomposition of the system as black boxes and progressively useful white-box views.

Use a C4 Container diagram as the default level-one building block view.

In C4, a container is an application or data store that executes or stores data independently.

It does not mean only a container image.

For every container, document its responsibility, technology, owned data, inbound relationships, and outbound relationships.

Add a Component view only for a container whose internal structure matters to the audience and can be maintained from evidence.

Avoid Code views unless explicitly requested or generated reliably on demand.

### 6. Runtime View

Describe the most important runtime scenarios across building blocks.

Use a C4 Dynamic diagram or Mermaid sequence diagram for scenarios such as authentication, primary user journeys, asynchronous processing, failure recovery, or external callbacks.

Base the sequence on routes, handlers, events, tests, or tracing evidence.

Number steps when sequence order matters.

Show alternatives and failures separately rather than overloading one diagram.

### 7. Deployment View

Describe how software-system and container instances map to infrastructure for a specific environment.

Use one C4 Deployment view per environment when development, staging, and production differ materially.

Include deployment nodes, container instances, software-system instances, and relevant infrastructure nodes such as gateways or load balancers.

Do not infer production topology from Docker Compose, local emulators, or developer configuration alone.

### 8. Crosscutting Concepts

Document recurring architectural approaches that affect multiple building blocks.

Candidate topics include authentication, authorization, tenancy, data ownership, validation, errors, observability, configuration, localization, resilience, privacy, and secure secret handling.

Include only concepts that genuinely recur.

Reference implementation locations and avoid duplicating detailed API contracts.

### 9. Architecture Decisions

Summarize important, expensive, risky, or contentious decisions.

Prefer existing architecture decision records.

For each decision, capture context, decision, alternatives, consequences, status, date, and evidence when those values are known.

If only the implemented choice is visible, label the rationale and rejected alternatives `Unknown`.

### 10. Quality Requirements

Capture the full set of relevant quality requirements and measurable quality scenarios.

Reference the top goals from section 1 rather than duplicating them.

The official arc42 guidance recommends concrete usage and change scenarios.

For each scenario, capture context, source or stimulus, affected artifact, expected response, and measurable acceptance criteria.

Do not convert existing timeouts, cache durations, or test thresholds into business service-level objectives without explicit evidence.

### 11. Risks and Technical Debt

List identified architecture risks and technical debt in priority order.

Include impact, likelihood when known, evidence, mitigation, owner, and status.

The official arc42 guidance treats this as an input to management risk analysis and recommends measures to minimize, mitigate, avoid, or reduce each item.

Do not classify every `TODO` or missing optional feature as architecture debt.

### 12. Glossary

Define important domain terms, acronyms, architecture element names, and repository-specific language.

Prefer authoritative domain definitions.

Keep each term defined once and link other pages to the canonical definition.

## Official C4 mapping to arc42

The official C4 FAQ maps its static views to arc42 as follows:

| arc42 location | C4 view | Scope |
| --- | --- | --- |
| Context and Scope | System Context | One software system, its users, and directly connected external systems. |
| Building Block View, level 1 | Container | Applications and data stores inside the software system. |
| Building Block View, level 2 | Component | Components inside one selected container. |
| Building Block View, level 3 | Code | Implementation detail inside one selected component. |

Use C4 Dynamic diagrams in Runtime View.

Use C4 Deployment diagrams in Deployment View.

Use a System Landscape view only when the documentation scope covers multiple software systems rather than one system.

## C4 notation and review rules

C4 is notation independent, but every generated diagram must stand on its own.

Apply all of these rules:

- Give the diagram a title that names its type and scope.
- State the scope and intended audience near the diagram.
- Include a key or legend when visual styling carries meaning.
- Give every element an explicit type.
- Give every element a short responsibility description.
- Name the technology for every Container and Component when known.
- Make every relationship directional.
- Label every relationship with a specific action or data flow.
- Include the technology or protocol on inter-process Container relationships when known.
- Use consistent names across every diagram and page.
- Explain acronyms in the legend or glossary.
- Avoid crossed lines, dense all-in-one views, and mixed abstraction levels.

Use Mermaid `flowchart` syntax for static C4 views when GitBook rendering support for C4-specific syntax is uncertain.

Express the C4 type in each node label or surrounding boundary.

Use Mermaid `sequenceDiagram` syntax for runtime scenarios.

The rendering syntax may be Mermaid, but the semantic model must still follow C4.

## Placement in the standard GitBook spaces

When the standard six-space site exists, use this default placement unless the user supplies another approved information architecture:

| GitBook space | Default content |
| --- | --- |
| Overview | Architecture landing page, arc42 sections 1 through 4, System Context view, quality summary, and glossary links. |
| Getting Started | Evidence-based prerequisites, local setup, first successful run, and verification steps. |
| Solution Architecture and Design | arc42 sections 5 through 12, Container and optional Component views, runtime scenarios, and deployment views. |
| API Reference | Implemented operations generated or documented from a reviewed OpenAPI contract. |
| Security and Privacy | Security and privacy portions of crosscutting concepts, quality requirements, risks, and data handling. |
| Release Notes | Confirmed releases, tags, migrations, breaking changes, and upgrade notes. |

Cross-link related pages instead of duplicating authoritative content.

Ask the user when evidence does not establish required content.
Do not construct the affected page until the user resolves it or explicitly omits it.

## Completion checklist

- All 12 arc42 sections exist or are explicitly marked not applicable with a reason.
- Every material claim has an evidence status.
- System names and boundaries are consistent.
- System Context and Container views exist when evidence supports them.
- Optional diagrams have a documented reason to exist.
- Every diagram passes the notation rules above.
- Quality scenarios are measurable rather than aspirational.
- Risks distinguish evidence from inference.
- API pages do not invent routes or schemas.
- Security pages contain no credentials, private URLs, personal data, or exploitable operational details.

## Official sources

- arc42 documentation and 12-section index: https://docs.arc42.org/
- arc42 Introduction and Goals: https://docs.arc42.org/section-1/
- arc42 Quality Requirements: https://docs.arc42.org/section-10/
- arc42 Risks and Technical Debt: https://docs.arc42.org/section-11/
- arc42 complete examples: https://docs.arc42.org/examples/
- C4 model overview: https://c4model.com/
- C4 diagram types: https://c4model.com/diagrams
- C4 notation guidance: https://c4model.com/diagrams/notation
- C4 System Context guidance: https://c4model.com/diagrams/system-context
- C4 Deployment guidance: https://c4model.com/diagrams/deployment
- C4 and arc42 mapping: https://c4model.com/faq#can-we-combine-c4-and-arc42
