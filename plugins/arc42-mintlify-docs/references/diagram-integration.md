# Diagram integration

Invoke the `diagram-standards:diagram-standards` skill for every draw.io diagram.
This workflow needs diagram-standards version 0.2.0 or later, which adds the `seq` template and the export workflow.
Do not draw an architecture diagram from scratch and do not restyle a template.
If the diagram-standards plugin is not available, stop, tell the user, and keep the page text with a `[OWNER INPUT REQUIRED: diagram]` marker until it is available.

## Which page uses which template

| Page | Diagram | Type key | Document number |
| --- | --- | --- | --- |
| 1.4 Context and Scope, business context | Business context | `bc` | `BC-<Product>-001` |
| 1.4 Context and Scope, system context | System context | `sc` | `SC-<Product>-001` |
| 2.1 Building Block View, level 1 | System whitebox | `l1-whitebox` | `LVL1_Whitebox-<Product>-001` |
| 2.1 Building Block View, level 2 | Component view, one per justified container | `l2-component` | `LVL2_ComponentView-<Product>-NNN` |
| 2.2 Runtime View | Runtime scenario, one per SD-RT-nn | `seq` | `SEQ-<Product>-NNN` |
| 2.3 Deployment View | Deployment | `l1-deployment` | `LVL1-DeploymentView-<Product>-001` |

`<Product>` is the product name in PascalCase without spaces.
Number each additional diagram of the same type in sequence.
Keep the business context out of the page when the user omits it, but never merge two templates.

## Stays in Mermaid

- 2.1.3 Level 3 code view: `classDiagram`, optional.
- 2.4.1 Domain entity model: `classDiagram`.
- Any pipeline or state sketch that has no template, kept small and labelled.

## Runtime scenarios

Write each SD-RT-nn scenario as a Mermaid `sequenceDiagram` with `autonumber`.
Save it as `diagrams/src/SEQ-<Product>-NNN.mmd`.
Add one `%% kind` comment line that sets the kind of every participant, for example `%% kind Customer=person API=container Repo=component Stripe=system`.
Convert it with the diagram-standards `mermaid_seq_to_drawio.py` script.
Keep the `.mmd` next to the `.drawio`.
Regenerate from the `.mmd` before any hand edit in draw.io, because hand edits are not written back.
Use at most six participants and one scenario per diagram.

## Workflow per diagram

1. Record the diagram in the session under `diagrams` with type, document number, title and page key.
2. Work in a local checkout of `tqkng/docs` or a scratch directory with the same layout: `diagrams/src/` for sources and `images/diagrams/` for PNGs.
3. Create the working copy with the diagram-standards `new_diagram.py` script, with the product title, the confirmed author and the version `0.0.1`.
4. Edit labels from confirmed evidence only.
5. Make sure `.github/workflows/export-diagrams.yml` exists in the destination repository.
   If it is missing, install it with the diagram-standards `setup_ci.sh` script on the same branch.
6. Commit the `.drawio` source, and the `.mmd` source for runtime scenarios, to the delivery branch.
   The workflow exports `images/diagrams/<doc-number>.png` and commits it to the same branch.
7. Reference the PNG path in the page right away.
   The image appears after the workflow run finishes, usually within two minutes.
8. If a local draw.io CLI is available, export the PNG with the diagram-standards export script instead.
   If neither route works, upload a manually exported PNG through the Mintlify upload tools as a last resort.
9. Embed the PNG:

```mdx
<Frame caption="Figure 1. System context of Example. Source: diagrams/src/SC-Example-001.drawio">
  <img src="/images/diagrams/SC-Example-001.png" alt="System context diagram. The User uses Example. Example connects to ..." />
</Frame>
```

The alt text names the elements and the relationships in words.
A page that embeds a PNG must have the matching `.drawio` source.
Commit source and PNG together.
Report in the completion report which PNGs the workflow exported and which still need a manual export.
Do not merge the delivery branch while a referenced PNG is missing from it.

## Update mode

Bump the diagram version and date when an existing diagram changes.
Never edit a PNG by hand.
Report a diagram whose source file cannot be found instead of redrawing it.
