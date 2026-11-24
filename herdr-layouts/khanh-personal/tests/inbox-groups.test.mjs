// Tests for mods/khanh-personal/inbox-groups.js: node --test tests/*.test.mjs

import assert from "node:assert/strict";
import test from "node:test";
import { byKind, byRepo, onlyTab, tabCounts, tabFor, TABS } from "../mods/khanh-personal/inbox-groups.js";

const row = (kind, repo, extra = {}) => ({ key: `${kind}:${repo}:${extra.n ?? 0}`, path: `/${kind}/${repo}/${extra.n ?? 0}`, kind, repo, name: `${repo} ${kind}`, text: [], children: [], ...extra });
const section = (key, children) => ({ key, path: `/${key}`, kind: "plain", name: key, title: key, children, expand: true });

const model = (extra = {}) => ({
  state: "ok",
  repos: ["o/new", "o/mid", "o/old"],
  sections: [
    section("alerts", [row("alert", "o/old")]),
    section("review", [row("review", "o/mid")]),
    section("work", [row("pr", "o/mid", { n: 1 }), row("ticket", "o/new", { n: 1 }), row("ticket", "o/new", { n: 2 }), row("ticket", "o/quiet", { n: 1 })]),
    section("runs", [row("run", "o/new", { item: { state: "running" } }), row("run", "o/old", { item: { state: "fail" } })]),
  ],
  ...extra,
});

const heads = (m) => m.sections.map((s) => [s.repo, s.children.map((r) => r.kind)]);

test("one heading per repo, with failing CI first, then review requests, then open PRs, then the rest", () => {
  const got = byRepo(model());
  assert.deepEqual(heads(got), [
    ["o/old", ["alert", "run"]], // failing
    ["o/mid", ["review", "pr"]], // waits on the person
    ["o/new", ["run", "ticket", "ticket"]], // a run is going
    ["o/quiet", ["ticket"]], // only a ticket
  ]);
});

test("inside a repo: what is wrong, runs, reviews, own PRs, tickets", () => {
  const m = model();
  m.sections.push(section("extra", [row("ticket", "o/old", { n: 9 }), row("pr", "o/old", { n: 8 }), row("review", "o/old", { n: 7 })]));
  assert.deepEqual(heads(byRepo(m))[0], ["o/old", ["alert", "run", "review", "pr", "ticket"]]);
});

test("the summary says what is wrong, what waits and what is open", () => {
  const [old, mid, neu, quiet] = byRepo(model()).sections;
  assert.deepEqual(old.parts, [{ text: "CI failing", tone: "bad" }]);
  assert.deepEqual(mid.parts, [{ text: "1 review", tone: "warn" }, { text: "1 PR" }]);
  assert.deepEqual(neu.parts, [{ text: "CI running", tone: "warn" }, { text: "2 issues" }]);
  assert.deepEqual(quiet.parts, [{ text: "1 issue" }]);
});

test("repos with something to act on start open; a repo with only tickets starts folded", () => {
  const got = Object.fromEntries(byRepo(model()).sections.map((s) => [s.repo, s.expand]));
  assert.deepEqual(got, { "o/old": true, "o/mid": true, "o/new": true, "o/quiet": false });
});

test("repos of the same need are ordered by how recently they were pushed, then by name", () => {
  const m = {
    repos: ["o/b", "o/a"],
    sections: [section("work", [row("ticket", "o/a"), row("ticket", "o/b"), row("ticket", "o/z"), row("ticket", "o/c")])],
  };
  assert.deepEqual(byRepo(m).sections.map((s) => s.repo), ["o/b", "o/a", "o/c", "o/z"]);
});

test("headings carry what the inbox draws: owner, short name, paths that differ per repo", () => {
  const [first, second] = byRepo(model()).sections;
  assert.deepEqual([first.owner, first.title, first.kind, first.depth], ["o", "old", "plain", undefined]);
  assert.notEqual(first.path, second.path);
  assert.ok(first.path.startsWith("/repo/"));
});

test("rows keep their identity, and the model's other fields", () => {
  const m = model({ updated: "10:00", prs: [1] });
  const got = byRepo(m);
  assert.equal(got.updated, "10:00");
  assert.deepEqual(got.prs, [1]);
  assert.equal(got.sections.flatMap((s) => s.children).length, 8);
  assert.strictEqual(got.sections[0].children[0], m.sections[0].children[0]);
});

test("a model whose rows name no repository stays by kind, and the today brief stays first", () => {
  const plain = { sections: [section("work", [{ key: "a", path: "/a", kind: "pr", children: [], name: "a", text: [] }])] };
  assert.deepEqual(byRepo(plain).sections.map((s) => s.key), ["prs"]);
  const withToday = model();
  withToday.sections.unshift(section("today", []));
  assert.equal(byRepo(withToday).sections[0].key, "today");
});

test("by kind: alerts, reviews, PRs, runs, tickets", () => {
  assert.deepEqual(byKind(model()).sections.map((s) => s.key), ["alerts", "review", "prs", "runs", "tickets"]);
  assert.equal(byKind(null), null);
  assert.equal(byRepo(undefined), undefined);
});

test("each tab holds its own kinds: review requests with pull requests, a failing branch with actions", () => {
  assert.deepEqual(TABS.map((t) => t.value), ["prs", "issues", "runs"]);
  assert.deepEqual(tabCounts(model()), { prs: 2, issues: 3, runs: 3 });
  assert.equal(tabFor("review"), "prs");
  assert.equal(tabFor("alert"), "runs");
  assert.equal(tabFor("ticket"), "issues");
  assert.equal(tabFor("worktree"), null);
});

test("a tab, by repository: only its rows, every repository unfolded", () => {
  const issues = byRepo(onlyTab(model(), "issues"), { open: true });
  assert.deepEqual(heads(issues), [["o/new", ["ticket", "ticket"]], ["o/quiet", ["ticket"]]]);
  assert.ok(issues.sections.every((s) => s.expand), "a repository of tickets alone is not folded away in its own tab");
  assert.deepEqual(heads(byRepo(onlyTab(model(), "runs"), { open: true })), [["o/old", ["alert", "run"]], ["o/new", ["run"]]]);
  assert.deepEqual(heads(byRepo(onlyTab(model(), "prs"), { open: true })), [["o/mid", ["review", "pr"]]]);
});

test("an empty tab has no sections, and an unknown tab falls back to the first", () => {
  const quiet = model({ sections: [section("work", [row("ticket", "o/new")])] });
  assert.deepEqual(onlyTab(quiet, "runs").sections, []);
  assert.deepEqual(byRepo(onlyTab(quiet, "runs"), { open: true }).sections, []);
  assert.deepEqual(onlyTab(model(), "nope").sections[0].children.map((r) => r.kind), ["review", "pr"]);
});

test("a row in two sections shows once in its tab", () => {
  const twice = row("pr", "o/mid", { n: 1 });
  const m = model({ sections: [section("review", [twice]), section("work", [twice])] });
  assert.equal(onlyTab(m, "prs").sections[0].children.length, 1);
});
