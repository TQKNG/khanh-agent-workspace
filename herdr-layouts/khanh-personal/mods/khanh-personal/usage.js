// The usage figure on an agent's card, as the health bar shows it: the share of the limit still left, the colour as it
// runs low, and the time until that window resets. Pure functions, tested by tests/usage.test.mjs.

/** Below this share left the bar turns amber, below CRITICAL red. */
export const LOW = 50;
export const CRITICAL = 20;
/** A reading older than this is said to be old, since the limit may have moved on since. */
const STALE_MS = 60 * 60 * 1000;

const clamp = (n) => Math.max(0, Math.min(100, n));

/** A span as the card writes it: "45 m", "3 h 12 m", "2 d 4 h", "<1 m". */
export function untilText(ms) {
  const m = Math.floor(Math.max(0, ms ?? 0) / 60000);
  if (m < 1) return "<1 m";
  if (m < 60) return `${m} m`;
  const h = Math.floor(m / 60);
  const rest = m % 60;
  if (h < 48) return rest ? `${h} h ${rest} m` : `${h} h`;
  const days = Math.floor(h / 24);
  const hours = h % 24;
  return hours ? `${days} d ${hours} h` : `${days} d`;
}

/** The colour token of a share left: success, then warning under LOW, then destructive under CRITICAL. */
export function toneOf(left) {
  if (left <= CRITICAL) return "destructive";
  if (left < LOW) return "warning";
  return "success";
}

/**
 * What the card draws for an agent's usage (the hub's `usage`, see hub/agent_profiles.py):
 * - {state: "read", left, fill, tone, window, resetsIn, readAgo, windows} with the window that has the least left;
 * - {state: "not_exposed", reason} for an agent whose CLI keeps no figure on disk;
 * - {state: "unreadable", reason} when a figure should exist but could not be read;
 * - {state: "not_installed"} when the agent is not on this machine.
 * `now` is in milliseconds, the hub's reset times and reading time in seconds.
 */
export function usageView(usage, now = Date.now()) {
  if (!usage) return { state: "not_installed" };
  if (usage.state === "not_exposed") return { state: "not_exposed", reason: usage.reason ?? "" };
  if (usage.state !== "read") return { state: "unreadable", reason: usage.reason ?? "" };
  const windows = (usage.windows ?? []).map((w) => {
    const known = typeof w.used_percent === "number";
    return {
      name: w.name,
      left: known ? clamp(100 - w.used_percent) : null,
      resetsIn: typeof w.resets_at === "number" ? untilText(w.resets_at * 1000 - now) : null,
    };
  });
  const known = windows.filter((w) => w.left !== null);
  if (!known.length) return { state: "unreadable", reason: "The last reading is from before the limit reset, so the share left is not known." };
  const low = known.reduce((a, b) => (b.left < a.left ? b : a));
  const readAge = typeof usage.observed_at === "number" ? now - usage.observed_at * 1000 : null;
  return {
    state: "read",
    left: Math.round(low.left),
    // A sliver stays visible at a near-empty bar, so "almost out" does not look like "out".
    fill: low.left > 0 ? Math.max(low.left, 4) : 0,
    tone: toneOf(low.left),
    window: low.name,
    resetsIn: low.resetsIn,
    readAgo: readAge !== null && readAge > STALE_MS ? untilText(readAge) : null,
    windows,
  };
}
