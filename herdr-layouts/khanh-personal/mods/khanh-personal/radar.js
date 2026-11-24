// The usage radar on an agent's card: one spoke per area of work, its length the share of the agent's busiest area.
// Pure functions only (the card draws them): tested by tests/radar.test.mjs.

/** The radar's centre and its rim, in percent of its box. The first spoke points up; the others go clockwise. */
export const CENTRE = 50;
export const RIM = 30;

/** The angle of spoke `i` of `n`, in radians, from straight up. */
export function spokeAngle(i, n) {
  return -Math.PI / 2 + (2 * Math.PI * i) / n;
}

/** Where a value on spoke `i` of `n` sits, in percent of the box: 0 is the centre, 1 is the rim. */
export function spokePoint(i, n, value, rim = RIM) {
  const v = Number.isFinite(value) ? Math.max(0, Math.min(1, value)) : 0;
  const a = spokeAngle(i, n);
  return { x: CENTRE + rim * v * Math.cos(a), y: CENTRE + rim * v * Math.sin(a) };
}

/** The polygon through one value per spoke, in percent of the box. */
export function polygon(values, rim = RIM) {
  return values.map((v, i) => spokePoint(i, values.length, v, rim));
}

/** Each area's count as a share of the busiest area, 0 to 1. Every share is 0 when nothing was counted. */
export function shares(axes) {
  const counts = axes.map((a) => (Number.isFinite(a.count) && a.count > 0 ? a.count : 0));
  const max = Math.max(0, ...counts);
  return counts.map((c) => (max > 0 ? c / max : 0));
}

/**
 * What the card draws for an agent's activity (the hub's `activity`, see hub/agent_activity.py):
 * - {state: "read", days, axes: [{key, label, count, value}]} with each value a share of the busiest area;
 * - {state: "not_enough", reason} when the agent's logs cannot draw a shape, or nothing was used in the window;
 * - {state: "unreadable", reason} when the logs could not be read;
 * - {state: "not_installed"} when the agent is not on this machine.
 */
export function radarView(activity) {
  if (!activity) return { state: "not_installed" };
  if (activity.state === "unreadable") return { state: "unreadable", reason: activity.reason ?? "" };
  if (activity.state !== "read") return { state: "not_enough", reason: activity.reason ?? "" };
  const axes = Array.isArray(activity.axes) ? activity.axes : [];
  const values = shares(axes);
  return {
    state: "read",
    days: activity.days,
    axes: axes.map((a, i) => ({ key: a.key, label: a.label, count: Number.isFinite(a.count) ? a.count : 0, value: values[i] })),
  };
}

/** A tooltip's words for a read: "Edits 162 · Reads 187 · …", the counts as the hub gave them. */
export function radarTip(view) {
  if (view.state !== "read") return "";
  return view.axes.map((a) => `${a.label} ${a.count}`).join(" · ");
}
