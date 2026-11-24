// The Checks tab of the review window: every check run and commit status of the pull request's head, failing ones first,
// and for a GitHub Actions job the part of its log that says why it failed. Re-running the failed jobs is the window's
// own confirmed action (`openVerdict("RERUN")`); this panel only knows which runs failed.

import { div } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import * as hub from "./hub.js";
import { tokens, alpha, TEXT, RADIUS, Icon, Button, Empty, Spinner, Skeleton } from "./ui.js";

const POLL_MS = 10_000;
const STATE = {
  fail: { icon: "circle-x", tone: "destructive", label: "failing" },
  running: { icon: "loader", tone: "warning", label: "running" },
  queued: { icon: "clock", tone: "warning", label: "queued" },
  pass: { icon: "circle-check", tone: "success", label: "passed" },
  skip: { icon: "minus", tone: "mutedFg", label: "skipped" },
};
const SUMMARY_ORDER = ["fail", "running", "queued", "pass", "skip"];
const keyOf = (c) => `${c.name}|${c.job_id ?? ""}`;

/** 65 -> "1m 5s". */
function duration(seconds) {
  if (seconds === null || seconds === undefined) return "";
  return seconds >= 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${seconds}s`;
}

export class ChecksPanel {
  /** `owner` is the review window: its repo, number, model, current tab and error toasts. */
  constructor(owner) {
    this.owner = owner;
    this.items = null;
    this.error = null;
    this.loading = false;
    this.selected = null; // keyOf(check)
    this.log = null; // { key, loading, error, lines, before, after, focus }
    this.next = 0;
  }

  async read() {
    this.loading = true;
    try {
      const got = await hub.fetchDetails("pr_checks", { repo: this.owner.repo, number: this.owner.number });
      this.items = got.checks;
      this.error = null;
      if (!this.items.some((c) => keyOf(c) === this.selected)) this.selected = null;
      this.next = Date.now() + POLL_MS;
    } catch (e) {
      this.error = String(e?.message ?? e);
    }
    this.loading = false;
  }

  /** Polls while the tab is shown and something is still running. */
  tick(cx) {
    const busy = this.items?.some((c) => c.state === "running" || c.state === "queued");
    if (this.owner.tab !== "checks" || this.loading || !busy || Date.now() < this.next) return;
    cx.spawn(async (cx) => {
      await this.read();
      this.refreshLog(cx);
      cx.notify();
    });
  }

  /** The first failing job opens by itself the first time the tab is shown: that is the question the tab answers. */
  shown(cx) {
    if (this.selected || !this.items) return;
    const first = this.items.find((c) => c.state === "fail" && c.job_id) ?? this.items.find((c) => c.state === "fail");
    if (first) this.select(first, cx);
  }

  /** j and k move through the checks. */
  key(e, cx) {
    const step = { j: 1, down: 1, k: -1, up: -1 }[e.keystroke];
    if (!step || !this.items?.length) return false;
    const at = this.items.findIndex((c) => keyOf(c) === this.selected);
    this.select(this.items[Math.max(0, Math.min(this.items.length - 1, at + step))], cx);
    return true;
  }

  /** The workflow runs with a failed job: what a re-run would restart. */
  failedRuns() {
    return [...new Set((this.items ?? []).filter((c) => c.state === "fail" && c.run_id).map((c) => c.run_id))];
  }

  failedJobs() {
    return (this.items ?? []).filter((c) => c.state === "fail" && c.run_id).map((c) => c.name);
  }

  counts() {
    const out = {};
    for (const c of this.items ?? []) out[c.state] = (out[c.state] ?? 0) + 1;
    return out;
  }

  select(check, cx) {
    this.selected = keyOf(check);
    this.log = null;
    if (check.job_id) this.loadLog(check, cx);
    cx.notify();
  }

  loadLog(check, cx) {
    const key = keyOf(check);
    this.log = { ...(this.log?.key === key ? this.log : {}), key, loading: true, error: null };
    cx.spawn(async (cx) => {
      try {
        const got = await hub.fetchDetails("check_log", { repo: this.owner.repo, job_id: check.job_id });
        if (this.log?.key === key) this.log = { key, ...got, loading: false, error: null };
      } catch (e) {
        if (this.log?.key === key) this.log = { key, loading: false, error: String(e?.message ?? e) };
      }
      cx.notify();
    });
  }

  /** While a job runs its log grows: read it again with the list. */
  refreshLog(cx) {
    const check = (this.items ?? []).find((c) => keyOf(c) === this.selected);
    if (check?.job_id && (check.state === "running" || check.state === "queued")) this.loadLog(check, cx);
  }

  // -------------------------------------------------------------------------------------------------------------------
  // Drawing

  render(k, cx) {
    if (this.error && !this.items) {
      return Empty({ icon: "alert", title: "Could not read the checks", description: this.error, action: Button("prchecks-retry", { label: "Try again", icon: "refresh-cw", onClick: (_e, cx) => (this.read().then(() => cx.notify()), cx.notify()) }) });
    }
    if (!this.items) return v_flex().p(24).gap(10).children([260, 340, 300].map((w) => Skeleton({ w })));
    if (!this.items.length) return Empty({ icon: "circle-dashed", title: "No checks", description: "No check runs or statuses are reported for this commit." });
    return v_flex().flex_1().min_h(0)
      .child(this.toolbar(k, cx))
      .child(h_flex().flex_1().min_h(0)
        .child(v_flex().id("prchecks-list").w(Math.min(400, Math.max(260, this.owner.width * 0.34))).flex_none().h_full().overflow_y_scrollbar().border_r_1().border_color(k.border).p(8).gap(2)
          .children(this.items.map((c, i) => this.row(c, i, k))))
        .child(this.logPane(k)));
  }

  toolbar(k, cx) {
    const counts = this.counts();
    const why = this.owner.blocker("RERUN");
    return h_flex().h(44).flex_none().px(16).gap(12).items_center().border_b_1().border_color(k.border)
      .children(SUMMARY_ORDER.filter((s) => counts[s]).map((s) => h_flex().gap(4).items_center().text_size(TEXT.sm).text_color(k[STATE[s].tone]).child(Icon(STATE[s].icon, { size: 13 })).child(`${counts[s]} ${STATE[s].label}`)))
      .when(this.loading, (e) => e.child(Spinner({ size: 12, color: k.mutedFg })))
      .child(div().flex_1())
      .child(Button("prchecks-rerun", { label: "Re-run failed", icon: "refresh-cw", size: "sm", variant: "outline", disabled: Boolean(why), tooltip: why ?? "Run the failed jobs again", onClick: (_e, cx) => this.owner.openVerdict("RERUN", cx) }));
  }

  row(c, i, k) {
    const s = STATE[c.state] ?? STATE.fail;
    const on = keyOf(c) === this.selected;
    const icon = c.state === "running" ? Spinner({ size: 14, color: k[s.tone] }) : Icon(s.icon, { size: 14, color: k[s.tone] });
    return h_flex().id(`prcheck-${i}`).min_h(34).px(10).gap(8).items_center().rounded(RADIUS.md).cursor_pointer()
      .when(on, (e) => e.bg(k.selected)).when(!on, (e) => e.hover((x) => x.bg(k.accent)))
      .on_click((_e, cx) => this.select(c, cx))
      .child(icon)
      .child(div().flex_1().min_w(0).truncate().text_size(TEXT.sm).when(c.state === "fail", (e) => e.font_medium()).child(c.name))
      .child(div().flex_none().text_size(TEXT.xs).text_color(k.mutedFg).child(duration(c.seconds)));
  }

  logPane(k) {
    const check = this.items.find((c) => keyOf(c) === this.selected);
    if (!check) return v_flex().flex_1().min_w(0).items_center().justify_center().text_size(TEXT.sm).text_color(k.mutedFg).child("Pick a check to see why it ran the way it did.");
    const s = STATE[check.state] ?? STATE.fail;
    const head = h_flex().h(40).flex_none().px(16).gap(8).items_center().border_b_1().border_color(k.border)
      .child(Icon(s.icon, { size: 14, color: k[s.tone] }))
      .child(div().flex_1().min_w(0).truncate().text_size(TEXT.base).font_semibold().child(check.name))
      .when(Boolean(check.url), (e) => e.child(Button("prchecks-open", { label: "Open", icon: "external", size: "sm", variant: "ghost", onClick: () => hub.openUrl(check.url) })));
    return v_flex().flex_1().min_w(0).min_h(0).h_full().child(head).child(this.logBody(check, k));
  }

  logBody(check, k) {
    const log = this.log;
    if (!check.job_id) {
      return v_flex().flex_1().p(16).gap(8)
        .child(div().text_size(TEXT.sm).text_color(k.mutedFg).child(check.note || "This check does not come from GitHub Actions, so it has no log here."))
        .child(div().text_size(TEXT.xs).text_color(k.dim).child("Open it to see the service's own page."));
    }
    if (!log || (log.loading && !log.lines)) return v_flex().flex_1().items_center().justify_center().gap(8).child(Spinner({ size: 18 })).child(div().text_size(TEXT.sm).text_color(k.mutedFg).child("Reading the log…"));
    if (log.error) return v_flex().flex_1().p(16).child(div().text_size(TEXT.sm).text_color(k.destructive).child(log.error));
    const mono = "JetBrains Mono";
    const lineEl = ([text, kind], i) => h_flex().id(`prlog-${i}`).px(16).min_h(18).items_start().text_size(TEXT.xs).font_family(mono)
      .when(kind === "error", (e) => e.bg(alpha(k.destructive, 0.12)).text_color(k.destructive))
      .when(kind === "warning", (e) => e.text_color(k.warning))
      .when(kind === "group", (e) => e.font_semibold().pt(6).text_color(k.foreground))
      .when(!kind, (e) => e.text_color(k.foreground))
      .child(div().flex_1().min_w(0).whitespace_normal().child(text || " "));
    const note = log.focus === "failure" ? "The failing step" : log.before ? "The end of the log" : "The whole log";
    const more = [log.before ? `${log.before} earlier line${log.before === 1 ? "" : "s"}` : null, log.after ? `${log.after} later line${log.after === 1 ? "" : "s"}` : null].filter(Boolean);
    return v_flex().flex_1().min_h(0)
      .child(h_flex().flex_none().px(16).py(6).gap(8).items_center().text_size(TEXT.xs).text_color(k.mutedFg)
        .child(note)
        .when(more.length > 0, (e) => e.child(`· ${more.join(" and ")} not shown, open it for the full log`))
        .when(Boolean(log.loading), (e) => e.child(Spinner({ size: 11, color: k.mutedFg }))))
      .child(v_flex().id("prlog").flex_1().min_h(0).overflow_y_scrollbar().pb(12).children((log.lines ?? []).map(lineEl)));
  }
}
