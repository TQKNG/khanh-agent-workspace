// How the inbox's rows are arranged: a tab per kind of thing (pull requests, issues, actions), and inside it by repository
// (the default) or by kind. Pure functions of the inbox model, so they run, and are tested, without the app. The model's
// sections hold the rows by kind (alerts, reviews, work, runs); each row of the local GitHub hub also names its `repo`.

const walk = (rows, out = []) => {
  for (const row of rows) {
    out.push(row);
    walk(row.children ?? [], out);
  }
  return out;
};

/** The inbox's tabs and the kinds of rows each holds. A failing default branch (an alert) is about Actions, so it shows
 *  there; review requests are pull requests. */
export const TABS = [
  { value: "prs", label: "Pull requests", icon: "git-pull-request", kinds: ["review", "pr"], empty: "No open pull requests of yours, and no review requests." },
  { value: "issues", label: "Issues", icon: "circle-dot", kinds: ["ticket"], empty: "No open issues assigned to you or opened by you." },
  { value: "runs", label: "Actions", icon: "play", kinds: ["alert", "run"], empty: "No failing or running workflows." },
];

const tabOf = (value) => TABS.find((t) => t.value === value) ?? TABS[0];

/** The tab a row belongs in, by its kind; null for a kind no tab shows. */
export function tabFor(kind) {
  return TABS.find((t) => t.kinds.includes(kind))?.value ?? null;
}

/** How many rows each tab holds: { prs, issues, runs }. */
export function tabCounts(model) {
  const rows = model?.sections ? walk(model.sections) : [];
  return Object.fromEntries(TABS.map((t) => [t.value, rows.filter((r) => t.kinds.includes(r.kind)).length]));
}

/** The model with only one tab's rows, in one section, for byRepo or byKind to arrange. */
export function onlyTab(model, value) {
  if (!model?.sections) return model;
  const tab = tabOf(value);
  const rows = walk(model.sections).filter((r) => tab.kinds.includes(r.kind));
  const seen = new Set();
  const unique = rows.filter((r) => !seen.has(r.key) && seen.add(r.key));
  const sections = unique.length ? [{ key: tab.value, path: `s:${tab.value}`, kind: "plain", name: tab.label, title: tab.label, icon: tab.icon, expand: true, children: unique, acts: [], text: [] }] : [];
  return { ...model, sections };
}

/** The inbox by kind of thing rather than the TUI's tree: alerts, reviews, your PRs, tickets, then what is left. */
export function byKind(model) {
  if (!model?.sections) return model;
  const flat = walk(model.sections);
  const section = (key, title, icon, children, extra = "") => ({ key, path: `s:${key}`, kind: "plain", name: title, title, icon, extra, expand: true, children, acts: [], text: [] });
  const keep = (key) => model.sections.find((s) => s.key === key);
  const prs = flat.filter((r) => r.kind === "pr");
  const tickets = flat.filter((r) => r.kind === "ticket").map((t) => ({ ...t, children: (t.children ?? []).filter((c) => c.kind !== "pr" && c.kind !== "ticket") }));
  const trees = flat.filter((r) => r.kind === "worktree");
  const runs = flat.filter((r) => r.kind === "run");
  const review = keep("review");
  const out = [keep("today"), keep("alerts")].filter(Boolean);
  if (review) out.push({ ...review, title: "Reviews", name: "Reviews" });
  if (prs.length) out.push(section("prs", "Your PRs", "git-pull-request", prs));
  if (runs.length) out.push(section("runs", "Runs", "play", runs, "failing or running"));
  if (tickets.length) out.push(section("tickets", "Issues", "circle-dot", tickets));
  if (trees.length) out.push(section("cleanup", "To clean up", "folder-git", trees));
  return { ...model, sections: out };
}

// Within a repository: what is wrong first, then what waits on the person, then their own work, then tickets.
const ORDER = { alert: 0, run: 1, review: 2, pr: 3, ticket: 4 };
const failing = (row) => row.kind === "alert" || (row.kind === "run" && row.item?.state === "fail");
const running = (row) => row.kind === "run" && row.item?.state === "running";
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** A repository's heading: its rows, and a summary of them (`parts`: text and tone) for the heading to show. A repository
 *  with something failing, running, waiting or open starts unfolded; one with only tickets starts folded. */
function repoHeading(repo, rows, open = false) {
  const [owner, short] = repo.split("/");
  const kids = [...rows].sort((a, b) => (ORDER[a.kind] ?? 9) - (ORDER[b.kind] ?? 9));
  const count = (kind) => kids.filter((r) => r.kind === kind).length;
  const [reviews, prs, tickets] = [count("review"), count("pr"), count("ticket")];
  const bad = kids.some(failing);
  const live = kids.some(running);
  const parts = [];
  if (bad) parts.push({ text: "CI failing", tone: "bad" });
  else if (live) parts.push({ text: "CI running", tone: "warn" });
  if (reviews) parts.push({ text: plural(reviews, "review", "reviews"), tone: "warn" });
  if (prs) parts.push({ text: plural(prs, "PR", "PRs") });
  if (tickets) parts.push({ text: plural(tickets, "issue", "issues") }); // the hub's tickets are GitHub issues
  return {
    key: `repo:${repo}`,
    path: `/repo/${owner}.${short}`,
    kind: "plain",
    name: short,
    title: short,
    owner: owner ?? "",
    repo,
    icon: "folder-git",
    parts,
    rank: [bad ? 0 : 1, reviews ? 0 : 1, prs || live ? 0 : 1],
    expand: open || bad || live || reviews > 0 || prs > 0,
    children: kids,
    acts: [],
    text: [],
    info: [],
  };
}

/** The inbox by repository: one heading per repo holding its alerts, runs, review requests, PRs and tickets. Repos that
 *  need the person come first (failing CI, then review requests, then open PRs), the rest by how recently they were pushed
 *  (`model.repos`, newest first). A model whose rows name no repository stays by kind. `open` starts every repository
 *  unfolded (a tab of one kind of thing has nothing to fold away). */
export function byRepo(model, { open = false } = {}) {
  if (!model?.sections) return model;
  const rows = walk(model.sections).filter((r) => r.repo && r.kind !== "plain");
  if (!rows.length) return byKind(model);
  const groups = new Map();
  for (const row of rows) groups.set(row.repo, [...(groups.get(row.repo) ?? []), row]);
  const recency = new Map((model.repos ?? []).map((name, i) => [name, i]));
  const heads = [...groups].map(([repo, kids]) => repoHeading(repo, kids, open));
  const later = (h) => recency.get(h.repo) ?? Number.MAX_SAFE_INTEGER;
  heads.sort((a, b) => {
    for (let i = 0; i < a.rank.length; i++) if (a.rank[i] !== b.rank[i]) return a.rank[i] - b.rank[i];
    return later(a) - later(b) || a.repo.localeCompare(b.repo);
  });
  const today = model.sections.find((s) => s.key === "today");
  return { ...model, sections: today ? [today, ...heads] : heads };
}
