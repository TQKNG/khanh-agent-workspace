# Style guide (taken from the approved templates)

## Shapes
- Person: `shape=mxgraph.c4.person2`, fill/stroke `#08427b`, white text.
- Software System: rounded box, fill `#1168bd`, stroke `#0b4884`, white text.
  External systems use the same shape and colour; mark them with `External System` on the type line.
- Container: rounded box, fill `#438dd5`, stroke `#3c7fc0`, white text.
- Component: rounded box, fill `#85bbf0`, stroke `#78a8d8`, dark text.
- Database: `shape=cylinder3`, container colours.
- Whitebox frame: dashed boundary box with its name top-left, as in the whitebox and component templates.
- Cloud boundaries (deployment): nested boxes with the Azure icon at top-left; keep the nesting order Provider > Tenant > Subscription > Resource Group > service.

## Text
- Font: Roboto everywhere.
  Do not change fonts.
- Element label pattern: bold name, then `[Type: technology]` line in small text, then a one-line description.
  Example: `Report Archive` / `[Container: Azure Blob Storage]` / `Store generated PDF reports`.
- Business context diagrams drop the technology part of the type line.
- Title block text is 18 px (24 px on the component template), black.

## Relationships
- Dashed (`dashed=1`), 2.25 px, black, end arrow on the receiving side.
- Label is a short verb phrase (`Send HTTP POST request`, `Archive PDF Report with Azure Blob API`), white label background, centred on the line.
- Route lines orthogonally; avoid crossing boxes.
  Move a label rather than a line when space is tight.

## Layout
- Keep the page size of the template.
  If content does not fit, remove detail before enlarging the page.
- Keep the legend lower left or lower right where the template puts it.
- Leave the title block at the bottom edge inside the frame.

## Editing approach
1. Relabel existing shapes first; duplicate a shape of the right kind when more are needed.
2. Delete unused example shapes and their relationships.
3. Check every relationship has a label and an arrow.
4. Open the exported PNG and confirm nothing overlaps and all text is legible at 100%.

## Sequence diagrams
- Participants use the C4 colours of their kind (Person, Container, Component, External System) and show `[Kind]` under the name.
- Calls: solid black 2 px arrow.
  Returns: dashed arrow.
  Message text sits above the arrow, numbered when `autonumber` is on.
- `loop`, `alt`, `opt`: UML frame with the keyword in the tab and the condition in square brackets; `else` branches are separated by a dashed line.
- Lifelines are dashed grey.
  The legend lists the kinds, call, return and frame notation.

## Class diagrams
- A class is a three-compartment box: name, attributes, operations.
  An interface adds the `«interface»` stereotype above the name and an enumeration adds `«enumeration»` with its values as rows.
- Header fill: class `#438dd5`, interface `#85bbf0`, enumeration `#1168bd`, white bold name.
  Body rows are black on white, 13 px, `+` public and `-` private.
- Relationships use solid 2 px black lines, except realization and dependency, which are dashed.
  Composition has a filled diamond at the whole, association an open arrow, realization a hollow triangle at the interface.
- Put multiplicities (`1`, `0..*`) next to the line ends and a short verb label on the line.

## State diagrams
- State: rounded box in `#438dd5`, white bold name.
  Composite state: rounded outline in `#3d81c3` with its name top-left and the inner states drawn inside.
- Initial state is a filled black circle, final state a bullseye, choice a white diamond.
- Transitions are solid 2 px black arrows labelled `event [guard] / action` on a white background.
