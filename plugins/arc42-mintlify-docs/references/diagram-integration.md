# Diagram integration

Invoke the `diagram-standards:diagram-standards` skill for every draw.io diagram.
Do not draw an architecture diagram from scratch and do not restyle a template.
If the diagram-standards plugin is not available, stop, tell the user, and keep the page text with a `[OWNER INPUT REQUIRED: diagram]` marker until it is available.

## Which page uses which template

| Page | Diagram | Type key | Document number |
| --- | --- | --- | --- |
| 1.4 Context and Scope, business context | Business context | `bc` | `BC-<Product>-001` |
| 1.4 Context and Scope, system context | System context | `sc` | `SC-<Product>-001` |
| 2.1 Building Block View, level 1 | System whitebox | `l1-whitebox` | `LVL1_Whitebox-<Product>-001` |
| 2.1 Building Block View, level 2 | Component view, one per justified container | `l2-component` | `LVL2_ComponentView-<Product>-NNN` |
| 2.3 Deployment View | Deployment | `l1-deployment` | `LVL1-DeploymentView-<Product>-001` |

`<Product>` is the product name in PascalCase without spaces.
Number each additional diagram of the same type in sequence.
Keep the business context out of the page when the user omits it, but never merge two templates.

## Stays in Mermaid

- 2.2 Runtime View: `sequenceDiagram` with `autonumber`, one per SD-RT-nn scenario.
- 2.1.3 Level 3 code view: `classDiagram`, optional.
- 2.4.1 Domain entity model: `classDiagram`.
- Any pipeline or state sketch that has no template, kept small and labelled.

## Workflow per diagram

1. Record the diagram in the session under `diagrams` with type, document number, title and page key.
2. Work in a local checkout of `tqkng/docs` or a scratch directory with the same layout: `diagrams/src/` for sources and `images/diagrams/` for PNGs.
3. Create the working copy with the diagram-standards `new_diagram.py` script, with the product title, the confirmed author and the version `0.0.1`.
4. Edit labels from confirmed evidence only.
5. Export the PNG with the diagram-standards export script.
6. If the draw.io CLI is missing, keep the `.drawio` file and tell the user to export a PNG with the same name.
7. Upload the PNG through the Mintlify upload tools to `images/diagrams/<doc-number>.png`.
8. Keep the `.drawio` source in the git repository.
9. Embed the PNG:

```mdx
<Frame caption="Figure 1. System context of Example. Source: diagrams/src/SC-Example-001.drawio">
  <img src="/images/diagrams/SC-Example-001.png" alt="System context diagram. The User uses Example. Example connects to ..." />
</Frame>
```

The alt text names the elements and the relationships in words.
A page that embeds a PNG must have the matching `.drawio` source.
Commit source and PNG together.
Report in the completion report which PNGs were exported and which still need a manual export.

## Update mode

Bump the diagram version and date when an existing diagram changes.
Never edit a PNG by hand.
Report a diagram whose source file cannot be found instead of redrawing it.
