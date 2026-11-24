// The review window for a pull request: its changes read in the cockpit's diff view, line comments written on them, its
// checks with the log of a failed job, and one verdict (approve, request changes or comment), the merge or a re-run of
// the failed jobs sent to GitHub through the hub. Opened from an inbox row with `openPrReview(item)`.
//
// Two rules keep a verdict honest: every verdict, merge and re-run asks first, listing what GitHub says about the pull request
// (failing checks, unresolved threads, a draft), and it is sent pinned to the commit that was read. The hub refuses it
// when the author pushed since, and the window then offers to read the new commits. Merging is offered only when GitHub
// says the pull request is ready, in the ways the repository allows.

import { div } from "gpui-kit";
import { h_flex, v_flex, InputState } from "gpui-base";
import { props, openOverlay, closeOverlay } from "herdr";
import * as hub from "./hub.js";
import { DiffView } from "./diff.js";
import { ChecksPanel } from "./prchecks.js";
import { Markdown } from "./reader.js";
import { tokens, alpha, TEXT, RADIUS, Icon, Badge, Button, ToneButton, Kbd, Tabs, Empty, Toaster, Spinner, Skeleton, TextField, Avatar, Overline } from "./ui.js";

/** Opens the review window on a pull request: `item` is an inbox row's item ({ repo, number }). */
export function openPrReview(item) {
  openOverlay({ mod: "khanh-personal", kind: "window", key: `prreview:${item.repo}#${item.number}`, width: 0.92, height: 0.92, props: { app: "prreview", repo: item.repo, number: item.number } });
}

const VERDICTS = {
  APPROVE: { label: "Approve", key: "a", icon: "circle-check" },
  REQUEST_CHANGES: { label: "Request changes", key: "x", icon: "circle-x" },
  COMMENT: { label: "Comment", key: "m", icon: "message-square" },
  MERGE: { label: "Merge", key: "shift-m", icon: "git-merge", hint: "M" },
  RERUN: { label: "Re-run failed jobs", icon: "refresh-cw" }, // asked for from the Checks tab, not a key of its own
};
const TEXTLESS = new Set(["MERGE", "RERUN"]); // these ask for no summary
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
const short = (sha) => String(sha ?? "").slice(0, 7);

export default class PrReview {
  init(p, cx) {
    const pr = props() ?? p ?? {};
    this.repo = pr.repo;
    this.number = pr.number;
    this.model = null;
    this.error = null;
    this.loading = false;
    this.tab = "files";
    this.dialog = null; // { event, method (a merge), busy, error, stale }
    this.width = 900;
    this.toasts = new Toaster();
    this.handle = cx.focus_handle();
    // Both inputs are made here: a state cannot be made later.
    this.input = InputState.new({ placeholder: "Leave a comment…" });
    this.input.on("submit", (_e, cx) => {
      this.diff.commit();
      this.handle.focus();
      cx.notify();
    });
    this.bodyInput = InputState.new({ placeholder: "A summary for the author" });
    this.diff = new DiffView("prreview", this.input);
    this.checks = new ChecksPanel(this);
    cx.timer.every(2000, (cx) => this.checks.tick(cx));
    this.load(cx);
  }

  // -------------------------------------------------------------------------------------------------------------------
  // Reading

  /** Reads the pull request again; the comments written so far stay on the lines that still exist. */
  async read() {
    this.loading = true;
    try {
      const m = await hub.fetchDetails("pr_diff", { repo: this.repo, number: this.number });
      this.model = m;
      this.error = null;
      this.diff.set(m);
    } catch (e) {
      this.error = String(e?.message ?? e);
    }
    this.loading = false;
  }

  /** Everything the window shows, read again. */
  refresh() {
    return Promise.all([this.read(), this.checks.read()]);
  }

  load(cx) {
    if (this.loading) return;
    cx.spawn(async (cx) => {
      await this.refresh();
      this.checks.refreshLog(cx);
      if (this.tab === "checks") this.checks.shown(cx);
      this.handle.focus();
      cx.notify();
    });
    cx.notify();
  }

  // -------------------------------------------------------------------------------------------------------------------
  // The verdict

  /** Why a verdict, the merge or a re-run cannot be done at all. */
  blocker(event) {
    const m = this.model;
    if (!m) return "Still reading the pull request.";
    if (m.state !== "open") return `This pull request is ${m.state}.`;
    if (event === "RERUN" && !this.checks.failedRuns().length) return "No failed GitHub Actions job to re-run.";
    if (event === "APPROVE" && m.own) return "You cannot approve your own pull request.";
    if (event === "MERGE" && !m.merge.choices.length) return m.merge.why;
    return null;
  }

  /** What to weigh before the verdict or the merge: GitHub's own signals about the pull request, and the state of the comments. */
  cautions(event) {
    const m = this.model;
    const out = [];
    if (event === "RERUN") return out;
    if (m.draft) out.push("It is a draft.");
    if (m.checks.fail) out.push(`${plural(m.checks.fail, "check")} failing.`);
    if (m.checks.pending) out.push(`${plural(m.checks.pending, "check")} still running.`);
    if (m.threads.length) out.push(`${plural(m.threads.length, "review thread")} unresolved.`);
    if (m.mine && m.mine.sha !== m.head_sha) out.push(`Your last review (${m.mine.state.toLowerCase().replace("_", " ")}) was of an older commit.`);
    const stale = this.diff.comments.filter((c) => c.stale).length;
    if (event === "MERGE") {
      const unsent = this.diff.comments.length;
      if (unsent) out.push(`${plural(unsent, "line comment")} written here ${unsent === 1 ? "is" : "are"} not sent: merging does not send them.`);
    } else if (stale) out.push(`${plural(stale, "comment")} sit on lines the new commits changed, and will not be sent.`);
    return out;
  }

  openVerdict(event, cx) {
    const why = this.blocker(event);
    if (why) return this.toasts.push(cx, why, { kind: "error" });
    this.dialog = { event, method: this.model.merge.choices[0]?.method, busy: false, error: null, stale: false };
    if (!TEXTLESS.has(event)) {
      this.bodyInput.set_value("");
      this.bodyInput.focus();
    }
    cx.notify();
  }

  closeDialog(cx) {
    if (this.dialog?.busy) return;
    this.dialog = null;
    this.handle.focus();
    cx.notify();
  }

  submit(cx) {
    const d = this.dialog;
    if (!d || d.busy) return;
    const merging = d.event === "MERGE";
    const textless = TEXTLESS.has(d.event);
    const body = textless ? "" : this.bodyInput.value().trim();
    const comments = textless ? [] : this.diff.review();
    if (d.event === "REQUEST_CHANGES" && !body) d.error = "Say what has to change: a request for changes needs a text.";
    else if (d.event === "COMMENT" && !body && !comments.length) d.error = "A comment review needs a text or a line comment.";
    else d.error = null;
    if (d.error) return cx.notify();
    d.busy = true;
    cx.notify();
    const item = { repo: this.repo, number: this.number, head_sha: this.model.head_sha };
    cx.spawn(async (cx) => {
      try {
        const r = merging
          ? await hub.act("inbox", "merge", [item, d.method])
          : d.event === "RERUN"
            ? await hub.act("inbox", "rerun_failed", [{ ...item, run_ids: this.checks.failedRuns() }])
            : await hub.act("inbox", "submit_review", [{ ...item, event: d.event, body, comments }]);
        this.toasts.push(cx, r.note || "Done", { kind: "success" });
        if (!textless) this.diff.comments = this.diff.comments.filter((c) => c.stale);
        this.dialog = null;
        await this.refresh();
        this.handle.focus();
      } catch (e) {
        d.busy = false;
        d.error = String(e?.message ?? e);
        d.stale = d.error.startsWith("New commits were pushed");
      }
      cx.notify();
    });
  }

  /** After a refused verdict: the new commits are read, the comments stay, and the verdict is asked for again. */
  rereadAfterPush(cx) {
    this.dialog = null;
    cx.spawn(async (cx) => {
      await this.refresh();
      this.toasts.push(cx, "Read the new commits. Look at what changed, then give your verdict again.", { kind: "info", ms: 6000 });
      this.handle.focus();
      cx.notify();
    });
    cx.notify();
  }

  setTab(tab, cx) {
    this.tab = tab;
    if (tab === "checks") this.checks.shown(cx);
    cx.notify();
  }

  // -------------------------------------------------------------------------------------------------------------------
  // Keys

  key(e, cx) {
    const key = e.keystroke;
    if (this.dialog) {
      if (key === "escape") this.closeDialog(cx);
      else if (key === "ctrl-enter" || key === "cmd-enter") this.submit(cx);
      else return false; // the rest is the text being typed
      return true;
    }
    if (this.tab === "checks" && this.checks.key(e, cx)) return true;
    if (this.tab === "files" && this.diff.key(e)) return true;
    if (this.diff.composer) return false;
    const verdict = Object.entries(VERDICTS).find(([, v]) => v.key === key);
    if (verdict) this.openVerdict(verdict[0], cx);
    else if (key === "1" || key === "2" || key === "3") this.setTab(["files", "conversation", "checks"][Number(key) - 1], cx);
    else if (key === "r") this.load(cx);
    else if (key === "o" && this.model) hub.openUrl(this.model.url);
    else if (key === "escape") closeOverlay(props().overlay);
    else return false;
    return true;
  }

  // -------------------------------------------------------------------------------------------------------------------
  // Drawing

  render(cx) {
    const k = tokens();
    const m = this.model;
    let root = v_flex().id("prreview").size_full().relative().bg(k.background).text_color(k.foreground).text_size(TEXT.base).track_focus(this.handle)
      .on_size_change((size, cx) => {
        if (Math.abs(size.width - this.width) > 1) {
          this.width = size.width;
          cx.notify();
        }
      })
      .on_key_down((e, cx) => {
        if (this.key(e, cx)) {
          cx.stop_propagation();
          cx.notify();
        }
      })
      .child(this.header(k));
    if (this.error && !m) {
      root = root.child(Empty({ icon: "alert", title: "Could not read the pull request", description: this.error, action: Button("prreview-retry", { label: "Try again", icon: "refresh-cw", kbd: "r", onClick: (_e, cx) => this.load(cx) }) }));
    } else if (!m) {
      root = root.child(v_flex().p(24).gap(10).children([240, 400, 320].map((w) => Skeleton({ w }))));
    } else {
      const body = { files: () => this.files(k, cx), conversation: () => this.conversation(k), checks: () => this.checks.render(k, cx) }[this.tab]();
      root = root.child(this.banner(k)).child(body).child(this.footer(k));
    }
    if (this.dialog) root = root.child(this.dialogEl(k));
    const toasts = this.toasts.render();
    return toasts ? root.child(toasts) : root;
  }

  checksBadge(m, k) {
    const c = m.checks;
    if (c.fail) return Badge(`${c.fail} failing`, "destructive", { icon: "circle-x" });
    if (c.pending) return Badge(`${c.pending} running`, "warning", { icon: "clock" });
    return c.pass ? Badge(`${c.pass} passing`, "success", { icon: "circle-check" }) : null;
  }

  mineBadge(m) {
    if (!m.mine) return null;
    const old = m.mine.sha !== m.head_sha;
    const what = { APPROVED: "You approved", CHANGES_REQUESTED: "You requested changes", COMMENTED: "You commented", DISMISSED: "Your review was dismissed" }[m.mine.state] ?? m.mine.state;
    return Badge(old ? `${what} (older commit)` : what, old ? "warning" : "info", { icon: "user" });
  }

  header(k) {
    const m = this.model;
    const title = m ? m.title : `${this.repo}#${this.number}`;
    return v_flex().flex_none().border_b_1().border_color(k.border)
      .child(h_flex().h(56).px(16).gap(10).items_center()
        .child(h_flex().size(28).flex_none().rounded(RADIUS.md).items_center().justify_center().bg(alpha(k.ring, 0.14)).child(Icon("git-pull-request", { size: 15, color: k.ring })))
        .child(v_flex().flex_1().min_w(0)
          .child(div().truncate().text_size(TEXT.lg).font_semibold().child(title))
          .child(div().truncate().text_size(TEXT.xs).text_color(k.mutedFg).child(m ? `${m.repo}#${m.number} · ${m.author} · ${m.branch} into ${m.base} · ${short(m.head_sha)}` : this.repo)))
        .when(Boolean(m), (e) => e.child(h_flex().gap(6).items_center()
          .child(Badge(m.draft ? "draft" : m.state, m.state === "open" && !m.draft ? "success" : "secondary"))
          .children([this.checksBadge(m, k), this.mineBadge(m)].filter(Boolean))
          .child(h_flex().gap(4).items_center().text_size(TEXT.xs).font_family("JetBrains Mono").child(div().text_color(k.success).child(`+${m.additions}`)).child(div().text_color(k.destructive).child(`−${m.deletions}`)))))
        .when(this.loading, (e) => e.child(Spinner({ size: 14, color: k.mutedFg })))
        .child(Button("prreview-reload", { icon: "refresh-cw", size: "icon-sm", variant: "ghost", tooltip: "Read it again  r", onClick: (_e, cx) => this.load(cx) }))
        .child(Button("prreview-open", { icon: "external", size: "icon-sm", variant: "ghost", tooltip: "Open on GitHub  o", onClick: () => m && hub.openUrl(m.url) }))
        .child(Button("prreview-close", { icon: "x", size: "icon-sm", variant: "ghost", tooltip: "Close  esc", onClick: () => closeOverlay(props().overlay) })))
      .child(h_flex().h(44).px(16).gap(8).items_center()
        .child(Tabs("prreview-tab", {
          items: [
            { value: "files", label: "Files", icon: "file-diff", count: m?.files.length },
            { value: "conversation", label: "Conversation", icon: "message-square", count: m ? m.threads.length : undefined },
            { value: "checks", label: "Checks", icon: "circle-check", count: this.checks.counts().fail || undefined },
          ],
          value: this.tab,
          onChange: (v, cx) => this.setTab(v, cx),
        })));
  }

  /** A line under the header when the pull request cannot be reviewed as it is, or the read failed on a refresh. */
  banner(k) {
    const m = this.model;
    const line = this.error ? [this.error, "destructive"] : m.state !== "open" ? [`This pull request is ${m.state}: it can be read, not reviewed.`, "warning"] : m.own ? ["It is your own pull request: you can comment on it, not approve it.", "mutedFg"] : null;
    if (!line) return div();
    const color = k[line[1]];
    return h_flex().flex_none().px(16).py(6).gap(8).items_center().bg(alpha(color, 0.1)).text_size(TEXT.sm).child(Icon("info", { size: 14, color })).child(div().flex_1().min_w(0).child(line[0]));
  }

  files(k, cx) {
    if (!this.diff.files().length) return Empty({ icon: "circle-check", title: "No file changes", description: "GitHub lists no changed files for this pull request." });
    return this.diff.render(cx, { narrow: this.width < 560 });
  }

  conversation(k) {
    const m = this.model;
    const threads = m.threads.map((t, i) => h_flex().id(`prreview-thread-${i}`).gap(10).p(10).items_start().rounded(RADIUS.md).border_1().border_color(k.border).cursor_pointer().hover((s) => s.bg(k.accent))
      .on_click((_e, cx) => this.goTo(t.path, cx))
      .child(Avatar(t.author || "?", { size: 22 }))
      .child(v_flex().flex_1().min_w(0).gap(2)
        .child(div().truncate().text_size(TEXT.xs).font_family("JetBrains Mono").text_color(k.mutedFg).child(`${t.path}${t.line ? `:${t.line}` : ""}`))
        .child(div().text_size(TEXT.sm).child(t.body))));
    const reviewers = m.reviews.map((r) => h_flex().gap(8).items_center().child(Avatar(r.login, { size: 20 })).child(div().flex_1().text_size(TEXT.sm).child(r.login)).child(Badge(r.state.toLowerCase().replace("_", " "), r.state === "APPROVED" ? "success" : r.state === "CHANGES_REQUESTED" ? "destructive" : "secondary")));
    return v_flex().id("prreview-conversation").flex_1().min_h(0).overflow_y_scrollbar().p(24).gap(20)
      .child(v_flex().gap(8).child(Overline("Description")).child(m.body.trim() ? Markdown("prreview-md", m.body, { size: TEXT.base }) : div().text_color(k.mutedFg).child("No description.")))
      .when(reviewers.length > 0, (e) => e.child(v_flex().gap(8).child(Overline("Reviews")).children(reviewers)))
      .child(v_flex().gap(8).child(Overline(`Unresolved threads · ${m.threads.length}`)).children(threads.length ? threads : [div().text_size(TEXT.sm).text_color(k.mutedFg).child("None.")]));
  }

  /** A thread's file, shown in the Files tab. */
  goTo(path, cx) {
    const f = this.diff.files().findIndex((x) => x.path === path);
    this.tab = "files";
    if (f >= 0) {
      this.diff.cursor = { f, l: null };
      this.diff.reveal();
    }
    cx.notify();
  }

  verdictButton(event, k) {
    const v = VERDICTS[event];
    const why = this.blocker(event);
    if (why) return Button(`prreview-${event}`, { label: v.label, icon: v.icon, size: "sm", variant: "outline", disabled: true, tooltip: why });
    const onClick = (_e, cx) => this.openVerdict(event, cx);
    if (event === "COMMENT") return Button(`prreview-${event}`, { label: v.label, icon: v.icon, size: "sm", variant: "outline", kbd: v.key, onClick });
    if (event === "MERGE") return Button(`prreview-${event}`, { label: v.label, icon: v.icon, size: "sm", kbd: v.hint, onClick });
    return ToneButton(`prreview-${event}`, { label: v.label, icon: v.icon, kbd: v.key, tone: event === "APPROVE" ? k.success : k.destructive, onClick });
  }

  footer(k) {
    const n = this.diff.review().length;
    const hints = this.diff.composer ? [["⏎", "add"], ["esc", "cancel"]] : [["j/k", "line"], ["c", "comment"], ["s", "split"], ["1/2/3", "tab"]];
    return h_flex().h(48).flex_none().px(16).gap(10).items_center().border_t_1().border_color(k.border)
      .children(hints.map(([key, what]) => h_flex().flex_none().gap(4).items_center().text_size(TEXT.xs).text_color(k.mutedFg).child(Kbd(key)).child(what)))
      .child(div().flex_1())
      .when(n > 0, (e) => e.child(div().text_size(TEXT.sm).text_color(k.mutedFg).child(plural(n, "line comment"))))
      .children(["COMMENT", "REQUEST_CHANGES", "APPROVE", "MERGE"].map((event) => this.verdictButton(event, k)));
  }

  /** The question every verdict asks first. */
  dialogEl(k) {
    const d = this.dialog;
    const m = this.model;
    const v = VERDICTS[d.event];
    const merging = d.event === "MERGE";
    const cautions = this.cautions(d.event);
    const comments = this.diff.review().length;
    const row = (icon, color, text) => h_flex().gap(8).items_start().child(Icon(icon, { size: 14, color })).child(div().flex_1().min_w(0).text_size(TEXT.sm).child(text));
    const body = v_flex().gap(12)
      .child(v_flex().gap(6)
        .child(row("git-commit", k.mutedFg, `Pinned to commit ${short(m.head_sha)}. It is refused if the author pushes before you send it.`))
        .child(row("file-diff", k.mutedFg, d.event === "RERUN" ? `Restarts the failed jobs of ${plural(this.checks.failedRuns().length, "workflow run")}, only of this commit:` : merging ? `Into ${m.base}, ${plural(m.files.length, "file")} read.` : `${plural(m.files.length, "file")} read, ${comments ? plural(comments, "line comment") : "no line comments"} to send.`))
        .children(cautions.map((c) => row("triangle-alert", k.warning, c))))
      .when(d.event === "RERUN", (e) => e.child(v_flex().gap(4).children(this.checks.failedJobs().slice(0, 8).map((name) => div().text_size(TEXT.sm).font_family("JetBrains Mono").truncate().child(name)))))
      .when(merging, (e) => e.child(Tabs("prreview-method", { items: m.merge.choices.map((c) => ({ value: c.method, label: c.label })), value: d.method, onChange: (v, cx) => { d.method = v; cx.notify(); } })))
      .when(!TEXTLESS.has(d.event), (e) => e.child(TextField(this.bodyInput)))
      .when(Boolean(d.error), (e) => e.child(row("circle-x", k.destructive, d.error)));
    const actions = [Button("prreview-cancel", { label: "Cancel", variant: "outline", kbd: "esc", disabled: d.busy, onClick: (_e, cx) => this.closeDialog(cx) })];
    if (d.stale) actions.push(Button("prreview-reread", { label: "Read the new commits", icon: "refresh-cw", onClick: (_e, cx) => this.rereadAfterPush(cx) }));
    else {
      const go = (_e, cx) => this.submit(cx);
      actions.push(d.event === "REQUEST_CHANGES"
        ? Button("prreview-send", { label: d.busy ? "Sending…" : v.label, variant: "destructive", disabled: d.busy, kbd: "⌃⏎", onClick: go })
        : Button("prreview-send", { label: d.busy ? (merging ? "Merging…" : d.event === "RERUN" ? "Starting…" : "Sending…") : v.label, icon: v.icon, disabled: d.busy, kbd: "⌃⏎", onClick: go }));
    }
    return div().id("prreview-dialog").absolute().inset_0().bg("#00000066").on_mouse_down("left", (_e, cx) => cx.stop_propagation())
      .child(v_flex().size_full().items_center().justify_center()
        .child(v_flex().id("prreview-dialog-card").w(480).p(20).gap(14).rounded(RADIUS.lg).border_1().border_color(k.border).bg(k.popover).shadow_lg()
          .child(v_flex().gap(4)
            .child(div().text_size(TEXT.lg).font_semibold().child(`${v.label}: ${m.repo}#${m.number}`))
            .child(div().truncate().text_size(TEXT.sm).text_color(k.mutedFg).child(m.title)))
          .child(body)
          .child(h_flex().justify_end().gap(8).children(actions))));
  }
}
