// Tests for mods/personal/usage.js: node --test tests/*.test.mjs

import assert from "node:assert/strict";
import test from "node:test";
import { toneOf, untilText, usageView } from "../mods/personal/usage.js";

const NOW = 1795000000000; // ms
const sec = (ms) => ms / 1000;

test("untilText writes a span the way the card shows it", () => {
  assert.equal(untilText(-5), "<1 m");
  assert.equal(untilText(30 * 1000), "<1 m");
  assert.equal(untilText(45 * 60 * 1000), "45 m");
  assert.equal(untilText((3 * 60 + 12) * 60 * 1000), "3 h 12 m");
  assert.equal(untilText(5 * 3600 * 1000), "5 h");
  assert.equal(untilText((2 * 24 + 4) * 3600 * 1000), "2 d 4 h");
  assert.equal(untilText(3 * 24 * 3600 * 1000), "3 d");
});

test("the colour turns as the share left runs low", () => {
  assert.equal(toneOf(100), "success");
  assert.equal(toneOf(50), "success");
  assert.equal(toneOf(49), "warning");
  assert.equal(toneOf(21), "warning");
  assert.equal(toneOf(20), "destructive");
  assert.equal(toneOf(0), "destructive");
});

test("the bar shows the window with the least share left, with its reset time", () => {
  const view = usageView(
    {
      state: "read",
      observed_at: sec(NOW - 60 * 1000),
      windows: [
        { name: "5h", used_percent: 40, resets_at: sec(NOW + (3 * 60 + 12) * 60 * 1000) },
        { name: "7d", used_percent: 96, resets_at: sec(NOW + (2 * 24 + 10) * 3600 * 1000) },
      ],
    },
    NOW,
  );
  assert.equal(view.state, "read");
  assert.equal(view.window, "7d");
  assert.equal(view.left, 4);
  assert.equal(view.fill, 4, "a nearly empty bar keeps a visible sliver");
  assert.equal(view.tone, "destructive");
  assert.equal(view.resetsIn, "2 d 10 h");
  assert.equal(view.readAgo, null, "a reading a minute old is not said to be old");
  assert.deepEqual(view.windows.map((w) => [w.name, w.left]), [["5h", 60], ["7d", 4]]);
});

test("an empty window is an empty bar, and a healthy one is green", () => {
  const empty = usageView({ state: "read", windows: [{ name: "5h", used_percent: 100, resets_at: sec(NOW + 60000) }] }, NOW);
  assert.equal(empty.fill, 0);
  assert.equal(empty.left, 0);
  const full = usageView({ state: "read", windows: [{ name: "5h", used_percent: 0, resets_at: sec(NOW + 3600000) }] }, NOW);
  assert.equal(full.left, 100);
  assert.equal(full.tone, "success");
  assert.equal(full.fill, 100);
});

test("a reading more than an hour old says how old it is", () => {
  const view = usageView({ state: "read", observed_at: sec(NOW - (2 * 24 + 1) * 3600 * 1000), windows: [{ name: "7d", used_percent: 96, resets_at: sec(NOW + 3600000) }] }, NOW);
  assert.equal(view.readAgo, "2 d 1 h");
});

test("a window whose figure is unknown is left out of the bar, and a reading with none is unreadable", () => {
  const partial = usageView({ state: "read", windows: [{ name: "5h", used_percent: null, resets_at: null }, { name: "7d", used_percent: 30, resets_at: sec(NOW + 3600000) }] }, NOW);
  assert.equal(partial.window, "7d");
  assert.equal(partial.left, 70);
  const none = usageView({ state: "read", windows: [{ name: "5h", used_percent: null, resets_at: null }] }, NOW);
  assert.equal(none.state, "unreadable");
  assert.match(none.reason, /before the limit reset/);
});

test("agents without a readable figure say so instead of drawing a bar", () => {
  assert.deepEqual(usageView({ state: "not_exposed", reason: "Claude keeps no figure on disk" }, NOW), { state: "not_exposed", reason: "Claude keeps no figure on disk" });
  assert.deepEqual(usageView({ state: "unreadable", reason: "no reading yet" }, NOW), { state: "unreadable", reason: "no reading yet" });
  assert.deepEqual(usageView(null, NOW), { state: "not_installed" });
});
