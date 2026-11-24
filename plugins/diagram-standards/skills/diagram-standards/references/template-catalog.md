# Template catalog

All templates share: outer frame, bottom title block (Document Title, Document Number, Version Number, Prepared By, Date), a Legend box (Person, Software System, Container, Component, Database, and a "Uses [technology]" relationship), Roboto font, C4 colours, dashed labelled relationships.

| Type key | File | Page size (px) | Use when | Contains |
|---|---|---|---|---|
| `sc` | system-context.drawio | 2454 x 1155 | Showing the system as one box with its users and neighbouring systems | Person x2, central Software System, external systems, database, 5 relationships |
| `bc` | business-context.drawio | 2454 x 1155 | Same scope as `sc` for a non-technical audience: no technology labels, business wording on edges | Same shapes as `sc`, descriptions only |
| `l1-whitebox` | l1-whitebox.drawio | 2454 x 1714 | Opening the system box: its containers (apps, functions, databases) | Surrounding people and systems, a "Whitebox Container" frame holding the containers |
| `l1-deployment` | l1-deployment.drawio | 3260 x 2273 | Where containers run: cloud provider, tenant, subscription, resource group, services | Nested Azure boundaries with Azure icons, monitoring services, storage, 7 relationships |
| `l2-component` | l2-component.drawio | 3260 x 2832 | Opening one container: its components and how they call each other | Whitebox frames, component boxes, 24 px title-block text, 12+ relationships |
| `seq` | sequence.drawio | 2454 x variable | One runtime scenario: who calls whom, in order | Participants in C4 colours, lifelines, call and return arrows, loop and alt frames, legend |

## Cell ids worth knowing

Title block cell ids (the script fills these):

| Type | title | number | version | author | date |
|---|---|---|---|---|---|
| sc | t1 | t2 | t3 | t4 | t5 |
| bc, l1-whitebox, l2-component | v4 | v6 | v7 | v9 | v10 |
| l1-deployment | v224 | v225 | v226 | v227 | v228 |

## Choosing between neighbouring types

- Audience is business or management, or technology must stay out: `bc`.
- Audience is engineers and technology names matter: `sc`.
- Question is "what is inside the system?": `l1-whitebox`. "Where does it run?": `l1-deployment`. "What is inside this one container?": `l2-component`.
- A doc set usually has one `sc` or `bc`, one `l1-whitebox`, one `l1-deployment`, and one `l2-component` per container worth explaining.

## Document numbers

`<prefix>-<ProductName>-<NNN>`: `SC`, `BC`, `LVL1_Whitebox`, `LVL1-DeploymentView`, `LVL2_ComponentView`, `SEQ`.
Product name in PascalCase without spaces, sequence number zero-padded to three digits.
Bump the version number (0.0.1, 0.0.2, ...) and the date whenever the diagram changes.
