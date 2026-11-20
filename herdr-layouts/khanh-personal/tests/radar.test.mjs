// Tests for mods/personal/radar.js: node --test tests/*.test.mjs

import assert from "node:assert/strict";
import test from "node:test";
import { CENTRE, RIM, polygon, radarTip, radarView, shares, spokePoint } from "../mods/personal/radar.js";

const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} is not ${b}`);

test("a zero value is drawn at the centre, not dropped", () => {
  const p = spokePoint(2, 6, 0);
  near(p.x, CENTRE);
  near(p.y, CENTRE);
});

test("a full value reaches the rim, and the first spoke points up", () => {
  const up = spokePoint(0, 6, 1);
  near(up.x, CENTRE);
  near(up.y, CENTRE - RIM);
  const opposite = spokePoint(3, 6, 1);
  near(opposite.x, CENTRE);
  near(opposite.y, CENTRE + RIM);
});

test("spokes go clockwise from the top, evenly spaced", () => {
  const right = spokePoint(1, 4, 1);
  near(right.x, CENTRE + RIM);
  near(right.y, CENTRE);
});

test("values outside 0 to 1 are clamped, and missing ones count as zero", () => {
  near(spokePoint(0, 4, 3).y, CENTRE - RIM);
  near(spokePoint(0, 4, -1).y, CENTRE);
  near(spokePoint(0, 4, undefined).y, CENTRE);
  assert.equal(polygon([0, 1, 0.5]).length, 3);
});

test("each area is a share of the busiest one, and all are zero when nothing was counted", () => {
  assert.deepEqual(shares([{ count: 50 }, { count: 25 }, { count: 0 }]), [1, 0.5, 0]);
  assert.deepEqual(shares([{ count: 0 }, { count: 0 }]), [0, 0]);
  assert.deepEqual(shares([{ count: null }, { count: 4 }]), [0, 1]);
});

test("a read activity keeps its areas in order, with counts and shares", () => {
  const view = radarView({
    state: "read",
    days: 30,
    axes: [
      { key: "edits", label: "Edits", count: 162 },
      { key: "reads", label: "Reads", count: 81 },
      { key: "mcp", label: "MCP", count: 0 },
    ],
  });
  assert.equal(view.state, "read");
  assert.equal(view.days, 30);
  assert.deepEqual(
    view.axes.map((a) => [a.label, a.count, a.value]),
    [["Edits", 162, 1], ["Reads", 81, 0.5], ["MCP", 0, 0]],
  );
  assert.equal(radarTip(view), "Edits 162 · Reads 81 · MCP 0");
});

test("an agent whose logs cannot draw a shape says why, and so does one with nothing used", () => {
  assert.deepEqual(radarView({ state: "not_enough", reason: "Too few kinds of work." }), { state: "not_enough", reason: "Too few kinds of work." });
  assert.equal(radarView({ state: "not_enough" }).reason, "");
  assert.equal(radarTip(radarView({ state: "not_enough", reason: "x" })), "");
});

test("unreadable logs and a missing agent are their own states", () => {
  assert.deepEqual(radarView({ state: "unreadable", reason: "permission denied" }), { state: "unreadable", reason: "permission denied" });
  assert.deepEqual(radarView(null), { state: "not_installed" });
  assert.deepEqual(radarView(undefined), { state: "not_installed" });
});
