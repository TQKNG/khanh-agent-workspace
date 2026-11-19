// How the inbox's rows are arranged: by repository (the default) or by kind of thing. Pure functions of the inbox model,
// so they run, and are tested, without the app. The model's sections hold the rows by kind (alerts, reviews, work, runs);
// each row of the local GitHub hub also names its `repo`.

const walk = (rows, out = []) => {
  for (const row of rows) {
    out.push(row);
    walk(row.children ?? [], out);
  }
  return out;
};

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
  if (tickets.length) out.push(section("tickets", "Tickets", "ticket", tickets));
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
function repoHeading(repo, rows) {
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
  if (tickets) parts.push({ text: plural(tickets, "ticket", "tickets") });
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
    expand: bad || live || reviews > 0 || prs > 0,
    children: kids,
    acts: [],
    text: [],
    info: [],
  };
}

/** The inbox by repository: one heading per repo holding its alerts, runs, review requests, PRs and tickets. Repos that
 *  need the person come first (failing CI, then review requests, then open PRs), the rest by how recently they were pushed
 *  (`model.repos`, newest first). A model whose rows name no repository stays by kind. */
export function byRepo(model) {
  if (!model?.sections) return model;
  const rows = walk(model.sections).filter((r) => r.repo && r.kind !== "plain");
  if (!rows.length) return byKind(model);
  const groups = new Map();
  for (const row of rows) groups.set(row.repo, [...(groups.get(row.repo) ?? []), row]);
  const recency = new Map((model.repos ?? []).map((name, i) => [name, i]));
  const heads = [...groups].map(([repo, kids]) => repoHeading(repo, kids));
  const later = (h) => recency.get(h.repo) ?? Number.MAX_SAFE_INTEGER;
  heads.sort((a, b) => {
    for (let i = 0; i < a.rank.length; i++) if (a.rank[i] !== b.rank[i]) return a.rank[i] - b.rank[i];
    return later(a) - later(b) || a.repo.localeCompare(b.repo);
  });
  const today = model.sections.find((s) => s.key === "today");
  return { ...model, sections: today ? [today, ...heads] : heads };
}
