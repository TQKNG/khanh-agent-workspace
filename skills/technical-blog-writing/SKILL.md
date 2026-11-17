---
name: technical-blog-writing
description: Write or revise first-person technical blog posts in Khanh's preferred style - grounded, reflective, technically concrete, and concise. Use for engineering articles, especially experience-led posts about software development, architecture, developer workflows, or AI-assisted engineering. Do not use for corporate marketing copy, general documentation, or short social posts.
---

## Technical Blog Writing Style

Write as a practicing software engineer reflecting on something observed through real work.
The author's experience should drive the argument, while external evidence supports it.
The result should feel like an engineer thinking through a change in the profession, not a content writer explaining technology to engineers.

## Voice and tone

- Use a professional, thoughtful, technical, and conversational voice.
- Prefer calm confidence, honest uncertainty, and specific observations over hype or sweeping predictions.
- Sound experienced without becoming academic, corporate, promotional, or overly polished.
- Use concrete engineering language when it adds precision, such as architecture boundaries, CI/CD, testing, coupling, validation, security, observability, and maintainability.
- Explain specialized terms when the intended audience may not know them.
- Avoid buzzwords such as "revolutionary" or "transformative" unless the evidence truly justifies them.

## Narrative structure

Build a coherent argument rather than a collection of observations.
Use this progression when it fits the topic, but do not force every article into an identical outline:

1. Open with one sharp engineering observation or tension.
2. Explain the underlying technical or workflow problem.
3. Ground it in a concrete example.
4. Reflect on how the author's own thinking or workflow is changing.
5. Draw the broader engineering implication.
6. End with a compact practical takeaway.

Use a small number of purposeful sections with descriptive headings.
Make each section advance the argument and remove sections that repeat an earlier point.
Use transitions so the reasoning feels continuous.

## Paragraph density and emphasis

- Prefer medium-length, substantive paragraphs.
- Keep related sentences together without blank lines between every sentence.
- Use short standalone lines, blockquotes, bold text, and rhetorical questions selectively for genuine emphasis.
- Avoid fragmented, sentence-per-paragraph formatting associated with promotional or LinkedIn-style writing.
- Use bullets only when a real list improves scanning, such as review questions or engineering guardrails.

## Self-reflection

Make personal experience the lens, not the entire subject.
Use first-person phrasing such as "I have started to notice," "in my own workflow," or "I increasingly find myself asking" only when it represents a genuine observation supplied by the user.
Show the movement from what the author used to do, to what changed, to where attention now goes, and finally to what that implies.
Do not invent experiences, results, emotions, tools, or opinions.
Ask for missing personal context when it is essential to the article's premise.

## Evidence and factual integrity

- Keep the post fact-based but lightly sourced.
- Use credible primary sources or authoritative industry sources to reinforce the author's observation, not to replace it.
- Verify claims that are current, quantitative, disputed, or attributed to someone else.
- Link sources near the claims they support and distinguish sourced facts from personal interpretation.
- Prefer one strong relevant source over a literature-review style list of citations.
- Paraphrase accurately and use direct quotations sparingly.
- Do not present assumptions, illustrative numbers, or predictions as established facts.

## Diagrams and examples

Use diagrams only when a workflow, architecture, comparison, or change over time becomes materially clearer visually.
Prefer a compact Mermaid diagram for process flows in Markdown-first technical posts.
Do not add a diagram that merely repeats the adjacent paragraph.
Keep node labels short, the direction easy to follow, and the diagram valid for the target publishing platform.
Use concrete software-engineering examples that clarify the argument without turning the post into a tutorial unless requested.

## Anti-patterns

Avoid:

- corporate whitepaper or marketing language
- AI hype, exaggerated certainty, and unsupported trend claims
- generic introductions that delay the main tension
- excessive headings, bullets, bolding, or one-line paragraphs
- repeated conclusions or multiple versions of the same insight
- decorative diagrams and examples unrelated to the argument
- external sources dominating the author's perspective
- invented self-reflection or claims of experience
- conclusions that summarize every section instead of resolving the argument

## Output expectations

Unless the user requests another format, deliver publication-ready Markdown that is visually engaging as well as coherent.
Do not rely on plain paragraphs separated only by H2 headings.
Create a restrained visual rhythm using the formats that best support the argument:

- Use a clear title, either as an H1 or in the publishing platform's frontmatter.
- Make the opening hook visually distinct with a short blockquote, a bold standalone statement, or another platform-supported treatment.
- Bold a small number of complete, high-value ideas that deserve emphasis.
- Use blockquotes as pull quotes for an important observation, question, or takeaway, not only for quotations from external sources.
- Use compact bullet or numbered lists for genuinely scannable material such as review questions, comparisons, principles, or guardrails.
- Use fenced code, compact tables, or Mermaid diagrams when they communicate technical information more clearly than prose.
- Use a simple callout pattern such as `> **Key takeaway:** ...` when one conclusion or caution deserves special attention.
- Use horizontal rules sparingly to separate a conclusion, attribution, or major shift when the platform renders them well.

For a substantial article, normally use at least two forms of emphasis beyond headings, such as a pull quote plus selective bolding, or a callout plus a diagram.
Every visual element must clarify hierarchy, improve scanning, or strengthen an important idea.
Do not highlight routine sentences, repeat the same statement in multiple formats, or turn every section into a callout.

The finished post should also include:

- a concise, coherent body with purposeful sections
- valid code fences and Mermaid syntax where used
- descriptive inline links for supporting evidence
- a compact conclusion that resolves the central argument

Preserve any requested platform metadata, such as DEV Community frontmatter, and follow the platform's syntax.
Use only formatting supported by the target platform, and prefer portable Markdown when platform capabilities are unknown.
When revising a draft, retain the author's core insight and recognizable phrasing while removing repetition, improving transitions, checking factual claims, and strengthening the self-reflective thread.
Return the finished article, not an outline or commentary, unless the user asks for analysis.
