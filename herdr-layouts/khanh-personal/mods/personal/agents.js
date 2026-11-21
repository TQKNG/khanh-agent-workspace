// The Agents page: a trading card per coding agent on this machine (Claude, Codex, Copilot), and under the picked one
// what it is set up with: its instructions, skills, plugins and MCP servers, from the hub's `agent_profiles`.
// Plugins and skills turn on and off with a switch (the hub does it, through the agent's CLI or config); the
// instructions file and a skill's SKILL.md open in Herdr's editor here and save with ⌘S, refused when the file changed
// on disk meanwhile. A click or 1–3 picks an agent, i s p m pick the section, e edits the instructions, R reads again.

import { div, image, PathBuilder, Background } from "gpui-kit";
import { h_flex, v_flex, Editor, EditorState } from "gpui-base";
import { settings, shared, setShared, theme, readTextFile, writeTextFile } from "herdr";
import * as hub from "./hub.js";
import { tokens, alpha, TEXT, RADIUS, Icon, Button, Badge, Chip, Tabs, PageHeader, ErrorState, Skeleton, Mono, KeyHints, Callout, Toggle, Toaster, Spinner, agentMark } from "./ui.js";
import { usageView } from "./usage.js";

// Each agent's colours (the card's frame and the deep end of its artwork), its line of flavour text, and its number.
const LOOK = {
  claude: { color: "#D97757", deep: "#7A2E17", flavor: "Anthropic's coding agent. Reads the room, then the repo.", no: 1 },
  codex: { color: "#10A37F", deep: "#0A4D3C", flavor: "OpenAI's coding agent, at home in the terminal and the cloud.", no: 2 },
  copilot: { color: "#8957E5", deep: "#3B1D78", flavor: "GitHub's coding agent, fluent in issues and pull requests.", no: 3 },
};
const SECTIONS = [
  { value: "instructions", label: "Instructions", icon: "scroll-text", key: "i" },
  { value: "skills", label: "Skills", icon: "sparkles", key: "s" },
  { value: "plugins", label: "Plugins", icon: "layers", key: "p" },
  { value: "mcp", label: "MCP servers", icon: "server", key: "m" },
];
const CARD = { w: 304, h: 472, art: 112 };
// The artwork's two halves: the logo's share, and the usage radar's panel. The panel is the card's own surface, so its
// labels read on every frame colour, and it is wide enough for the labels outside the radar's rim (a 44px label at
// 10px out from the rim) to stay inside it. The radar's square is 80px, so its rim is 24px from the centre.
const PICK_KEY = "cockpit.agents.pick";
const SECTION_KEY = "cockpit.agents.section";

const needsSignIn = (m) => /auth/i.test(m.status ?? "") && !/signed in/i.test(m.status ?? "");
const onFirst = (a, b) => b.enabled - a.enabled || a.name.localeCompare(b.name);
const enabledOf = (items) => `${items.filter((i) => i.enabled).length} enabled of ${items.length}`;

/** Every skill, plugin and MCP server says the same: enabled or disabled. */
const stateBadge = (item) => Badge(item.enabled ? "enabled" : "disabled", item.enabled ? "success" : "secondary");

/** An MCP server's connection state, when its agent reports one: a second badge beside enabled or disabled. */
function linkBadge(m) {
  if (!m.status || /^(enabled|disabled)$/i.test(m.status)) return null;
  return Badge(m.status, needsSignIn(m) ? "warning" : /fail|error/i.test(m.status) ? "destructive" : "outline"); // fine states stay quiet: the layout's info colour is its red accent
}

/** A long path cut to its start and its last two parts, `~/.claude/…/pdf/SKILL.md`: synced skills sit under long ids. */
function brief(path) {
  const parts = String(path ?? "").split("/");
  return parts.length > 5 ? [...parts.slice(0, 2), "…", ...parts.slice(-2)].join("/") : String(path ?? "");
}

/** A rectangle filling its box, for painting a background into. */
function box() {
  return PathBuilder.fill().move_to("0%", "0%").line_to("100%", "0%").line_to("100%", "100%").line_to("0%", "100%").close().build();
}

/** The card's artwork window: the agent's colours as a gradient, a fine diagonal foil over it, and its mark on a disc. */
/** The agent's logo: the hub's sharp copy, else Herdr's own. */
const markOf = (agent) => agent.mark ?? agentMark(agent.id);

function art(agent, look, k) {
  const zoom = settings().zoom ?? 1;
  const mark = markOf(agent);
  const on = agent.installed;
  const from = on ? look.color : k.muted;
  const to = on ? look.deep : k.border;
  const skillsOn = agent.skills.filter((skill) => skill.enabled).length;
  const mcpOn = agent.mcp.filter((server) => server.enabled).length;
  return div()
    .relative()
    .mx(10)
    .h(CARD.art)
    .flex_none()
    .rounded(RADIUS.lg)
    .overflow_hidden()
    .child(window.paint_path(box(), Background.linear_gradient(120, Background.stop(from, 0), Background.stop(to, 100))).absolute().inset_0())
    .child(window.paint_path(box(), Background.pattern_slash("#ffffff", 1 * zoom, 12 * zoom).opacity(0.08)).absolute().inset_0())
    .child(h_flex().absolute().inset_0().px(16).gap(14).items_center()
      .child(h_flex().size(70).flex_none().rounded(20).items_center().justify_center().bg("#ffffff")
        .child(mark ? image(mark).size(46) : Icon("bot", { size: 34, color: k.mutedFg })))
      .child(v_flex().flex_1().min_w(0).gap(7).text_color("#ffffff")
        .child(div().text_size(TEXT.xs).font_bold().child(agent.maker.toUpperCase()))
        .child(h_flex().gap(14)
          .child(v_flex().gap(1).child(div().text_size(TEXT.xl).font_bold().child(String(skillsOn)))
            .child(div().text_size(TEXT.xs).child("skills active")))
          .child(v_flex().gap(1).child(div().text_size(TEXT.xl).font_bold().child(String(mcpOn)))
            .child(div().text_size(TEXT.xs).child("MCP active"))))));
}

/** One of the card's "moves":an energy disc with the section's icon, its name and what it holds, and the count. */
function move(icon, name, detail, value, look, k, on) {
  return h_flex()
    .h(36)
    .gap(10)
    .items_center()
    .child(h_flex().size(24).flex_none().rounded(12).items_center().justify_center().bg(on ? look.color : k.muted).child(Icon(icon, { size: 13, color: "#ffffff" })))
    .child(v_flex().flex_1().min_w(0).child(div().text_size(TEXT.sm).font_semibold().child(name)).child(div().text_size(TEXT.xs).text_color(k.mutedFg).truncate().child(detail)))
    .child(div().flex_none().text_size(TEXT.lg).font_bold().text_color(on ? k.foreground : k.mutedFg).child(String(value)));
}

export default class Agents {
  init(_props, cx) {
    this.handle = cx.focus_handle();
    this.data = null;
    this.error = null;
    this.loading = false;
    this.editing = null; // { agent, title, file, original (null: a new file), state, saving }
    this.busy = new Set(); // switches in flight: `<agent> <kind> <key>`
    this.toasts = new Toaster();
    this.pick = shared(PICK_KEY) ?? "claude";
    this.section = SECTIONS.some((s) => s.value === shared(SECTION_KEY)) ? shared(SECTION_KEY) : "instructions";
    this.load(cx, false);
    this.handle.focus();
  }

  /** Reads the profiles: `refresh` reads every agent again, `agent` only that one. */
  load(cx, refresh, agent = null) {
    if (this.loading) return;
    this.loading = true;
    cx.notify();
    cx.spawn(async (cx) => {
      try {
        const value = await hub.fetchDetails("agent_profiles", { refresh, ...(agent ? { agent } : {}) });
        if (value?.error) this.error = value.error;
        else {
          this.data = value;
          this.error = null;
        }
      } catch (e) {
        this.error = String(e?.message ?? e);
      }
      this.loading = false;
      // A first read can meet a hub that is still starting: try once more before showing the error.
      if (!this.data && this.error && !this.retried) {
        this.retried = true;
        cx.timer.after(2000, (cx) => this.load(cx, false));
      }
      cx.notify();
    });
  }

  agents() {
    return this.data?.agents ?? [];
  }

  current() {
    return this.agents().find((a) => a.id === this.pick) ?? this.agents()[0] ?? null;
  }

  choose(id) {
    if (this.editing && !this.dirty()) {
      this.editing.state.release();
      this.editing = null;
    }
    this.pick = id;
    setShared(PICK_KEY, id);
  }

  show(section) {
    this.section = section;
    setShared(SECTION_KEY, section);
  }

  command(c, cx) {
    if (c === "focus" || c === "show:agents") this.handle.focus();
    cx.notify();
  }

  key(e, cx) {
    const k = e.keystroke;
    if (this.editing) {
      if (k === "cmd-s" || k === "ctrl-s") return this.save(cx), true;
      if (k === "escape") return this.stopEditing(cx), true;
      return false;
    }
    const agents = this.agents();
    if (/^[1-9]$/.test(k) && agents[Number(k) - 1]) this.choose(agents[Number(k) - 1].id);
    else if (k === "shift-r") this.load(cx, true);
    else if (k === "e" && this.section === "instructions" && this.current()?.installed) {
      const agent = this.current();
      this.edit(cx, agent, `${agent.label}'s instructions`, agent.instructions.file, agent.instructions.path);
    }
    else if (k === "left" || k === "right") {
      const at = agents.findIndex((a) => a.id === this.current()?.id);
      if (at >= 0) this.choose(agents[(at + (k === "right" ? 1 : agents.length - 1)) % agents.length].id);
    } else {
      const section = SECTIONS.find((s) => s.key === k);
      if (!section) return false;
      this.show(section.value);
    }
    cx.notify();
    return true;
  }

  // -------------------------------------------------------------------------------------------------------------------
  // Changing things

  /** Turns a plugin or a skill on or off through the hub, which answers when the agent has it. */
  flip(cx, agent, kind, item) {
    const id = `${agent.id} ${kind} ${item.key}`;
    if (this.busy.has(id)) return;
    this.busy.add(id);
    cx.notify();
    cx.spawn(async (cx) => {
      try {
        const r = await hub.request("act", { app: "agents", action: "toggle", args: [{ agent: agent.id, kind, key: item.key, enabled: !item.enabled }] });
        if (r.error) this.toasts.push(cx, `Could not turn ${item.name} ${item.enabled ? "off" : "on"}`, { kind: "error", description: r.error, ms: 7000 });
        else this.toasts.push(cx, r.note, { kind: "success" });
      } catch (e) {
        this.toasts.push(cx, "The hub did not answer", { kind: "error", description: String(e?.message ?? e) });
      }
      this.busy.delete(id);
      this.load(cx, false);
    });
  }

  /** Opens a file of the agent's in the editor: its instructions, or a skill's SKILL.md; a missing file starts empty. */
  /** `shown`: the path as the page shows it (`~/…`). */
  edit(cx, agent, title, file, shown = file) {
    cx.spawn(async (cx) => {
      const text = await readTextFile(file).catch(() => null);
      const t = theme();
      this.editing?.state.release();
      this.editing = {
        agent: agent.id,
        title,
        file,
        shown,
        original: text,
        saving: false,
        state: EditorState.new({
          language: "markdown",
          value: text ?? "",
          font_family: settings().font_family,
          font_size: 13,
          soft_wrap: true,
          syntax: { keyword: t.ansi5, string: t.ansi2, comment: t.dim, function: t.ansi4, type: t.ansi3, number: t.ansi1, constant: t.ansi6, boolean: t.ansi6 },
        }),
      };
      this.editing.state.on("change", (_e, cx) => cx.notify());
      this.editing.state.focus();
      cx.notify();
    });
  }

  dirty() {
    const ed = this.editing;
    return Boolean(ed) && ed.state.value() !== (ed.original ?? "");
  }

  /** Saves the editor's text, only when the file is still what was opened (an agent may have changed it). */
  save(cx) {
    const ed = this.editing;
    if (!ed || ed.saving || !this.dirty()) return;
    ed.saving = true;
    cx.notify();
    cx.spawn(async (cx) => {
      const text = ed.state.value();
      try {
        await writeTextFile(ed.file, text, ed.original);
        ed.original = text;
        this.toasts.push(cx, `Saved ${ed.title}`, { kind: "success" });
        this.load(cx, false, ed.agent);
      } catch (e) {
        this.toasts.push(cx, `Could not save ${ed.title}`, { kind: "error", description: /stale|match|expected/i.test(String(e)) ? "The file changed on disk since it was opened: close the editor and open it again." : String(e?.message ?? e), ms: 8000 });
      }
      ed.saving = false;
      cx.notify();
    });
  }

  /** Closes the editor; with unsaved edits the first Esc warns and the second discards them. */
  stopEditing(cx) {
    const ed = this.editing;
    if (!ed) return;
    if (this.dirty() && !ed.warned) {
      ed.warned = true;
      this.toasts.push(cx, "Unsaved changes", { description: "⌘S saves them; Esc again closes without saving." });
      cx.notify();
      return;
    }
    ed.state.release();
    this.editing = null;
    this.handle.focus();
    cx.notify();
  }

  editorEl(k) {
    const ed = this.editing;
    const dirty = this.dirty();
    return v_flex()
      .gap(10)
      .child(
        h_flex()
          .gap(8)
          .items_center()
          .child(Icon("pencil", { size: 14, color: k.mutedFg }))
          .child(div().text_size(TEXT.base).font_semibold().child(ed.title))
          .child(Mono(ed.shown, { size: TEXT.xs }))
          .when(ed.original === null, (e) => e.child(Badge("new file", "info")))
          .when(dirty, (e) => e.child(Badge("unsaved", "warning")))
          .child(div().flex_1())
          .child(Button("edit-cancel", { label: "Close", variant: "ghost", size: "sm", kbd: "esc", onClick: (_e, cx) => this.stopEditing(cx) }))
          .child(Button("edit-save", { label: ed.saving ? "Saving…" : "Save", icon: "check", size: "sm", kbd: "⌘S", disabled: !dirty || ed.saving, onClick: (_e, cx) => this.save(cx) })),
      )
      .child(div().h(460).rounded(RADIUS.md).border_1().border_color(k.border).overflow_hidden().child(Editor.new(ed.state).size_full()));
  }

  /** A switch for an item that can be turned on and off, a spinner while the hub does it. */
  switchEl(agent, kind, item) {
    if (!item.toggle) return null;
    if (this.busy.has(`${agent.id} ${kind} ${item.key}`)) return Spinner({ size: 14 });
    return Toggle(`flip-${kind}-${item.key}`, item.enabled, (cx) => this.flip(cx, agent, kind, item), { tooltip: item.enabled ? "Turn off" : "Turn on" });
  }

  // -------------------------------------------------------------------------------------------------------------------
  // The cards

  card(agent, k) {
    const look = LOOK[agent.id] ?? { color: k.ring, deep: k.border, flavor: "", no: 0 };
    const on = agent.installed;
    const picked = agent.id === this.current()?.id;
    const signIn = agent.mcp.filter(needsSignIn).length;
    const frame = on ? look.color : k.border;
    const inner = v_flex()
      .size_full()
      .rounded(RADIUS.xl)
      .bg(k.card)
      .border_1()
      .border_color(on ? alpha(look.deep, 0.5) : k.border)
      .overflow_hidden()
      .gap(8)
      .pb(10)
      // Name, version and availability stay visible above the summary banner.
      .child(
        h_flex()
          .px(14)
          .pt(10)
          .items_end()
          .gap(6)
          .child(div().text_size(TEXT.xl).font_bold().child(agent.label))
          .child(Mono(agent.version ? `v${agent.version}` : "", { color: k.mutedFg }))
          .child(div().flex_1())
          .child(Badge(on ? "Installed" : "Not installed", on ? "success" : "secondary")),
      )
      .child(art(agent, look, k))
      .child(
        v_flex()
          .px(14)
          .gap(2)
          .child(move("scroll-text", "Instructions", agent.instructions.exists ? agent.instructions.path : "no instructions file", agent.instructions.exists ? agent.instructions.lines : "—", look, k, on && agent.instructions.exists))
          .child(move("sparkles", "Skills", enabledOf(agent.skills), agent.skills.length, look, k, on))
          .child(move("layers", "Plugins", enabledOf(agent.plugins), agent.plugins.length, look, k, on))
          .child(move("server", "MCP servers", `${enabledOf(agent.mcp)}${signIn ? ` · ${signIn} sign-in` : ""}`, agent.mcp.length, look, k, on)),
      )
      .child(div().flex_1())
      // A distinct footer gives the allowance and launch command a clear home.
      .child(
        v_flex()
          .mx(12)
          .h(110)
          .flex_none()
          .p(10)
          .gap(6)
          .rounded(RADIUS.lg)
          .bg(k.muted)
          .child(h_flex().items_center().child(div().text_size(TEXT.xs).font_bold().text_color(k.mutedFg).child("ACCOUNT CAPACITY")))
          .child(this.hp(agent, k))
          .child(h_flex().gap(7).items_center().text_size(TEXT.xs).text_color(k.mutedFg)
            .child(div().font_semibold().child("RUN"))
            .child(Mono(agent.command))
            .child(div().flex_1())
            .child(div().child("View setup →"))),
      );
    return v_flex()
      .id(`agent-card-${agent.id}`)
      .w(CARD.w)
      .min_w(CARD.w)
      .max_w(420)
      .h(CARD.h)
      .flex_grow_1()
      .p(7)
      .rounded(18)
      .bg(frame)
      .cursor_pointer()
      // The picked card stands out in the page's own ink, so it reads on every frame colour.
      .when(picked, (e) => e.border_3().border_color(k.foreground).shadow_lg())
      .when(!picked, (e) => e.border_3().border_color(alpha(frame, 0)).opacity(0.86).hover((s) => s.opacity(1)))
      .on_click((_e, cx) => {
        this.choose(agent.id);
        this.handle.focus();
        cx.notify();
      })
      .child(inner);
  }

  /**
   * The card's health bar, as an HP bar: the share of the agent's usage still left in its tightest window, the colour
   * going amber and then red as it runs low, and under it the window and the time until it resets. An agent that keeps no
   * figure, or whose figure cannot be read, says so in place of a bar.
   */
  hp(agent, k) {
    const view = usageView(agent.usage);
    const label = (color) => div().w(72).flex_none().text_size(TEXT.xs).font_bold().text_color(color).child("USAGE LEFT");
    if (view.state !== "read") {
      const note = { not_exposed: "Provider does not share usage", unreadable: "No current reading", not_installed: "Waiting for usage data" }[view.state];
      return v_flex()
        .id(`agent-hp-${agent.id}`)
        .h(43)
        .gap(3)
        .when(Boolean(view.reason), (e) => e.tooltip(view.reason))
        .child(h_flex().h(22).gap(8).items_center()
          .child(label(k.mutedFg))
          .child(div().relative().flex_1().h(12).rounded(6).bg(k.border))
          .child(Mono("—", { size: TEXT.xs, color: k.mutedFg })))
        .child(div().pl(80).text_size(TEXT.xs).text_color(k.mutedFg).truncate().child(note));
    }
    const tone = k[view.tone];
    const tip = view.windows.map((w) => `${w.name}: ${w.left === null ? "not known" : `${Math.round(w.left)}% left`}${w.resetsIn ? `, resets in ${w.resetsIn}` : ""}`).join(" · ");
    return v_flex()
      .id(`agent-hp-${agent.id}`)
      .h(43)
      .gap(3)
      .tooltip(tip)
      .child(
        h_flex()
          .gap(8)
          .items_center()
          .child(label(tone))
          .child(
            div()
              .relative()
              .flex_1()
              .h(12)
              .rounded(6)
              .border_1()
              .border_color(alpha(tone, 0.5))
              .bg(k.muted)
              .overflow_hidden()
              .child(div().absolute().left(0).top(0).h_full().bg(tone).w(`${view.fill}%`).transition("width", { duration: 400, easing: "ease-out" })),
          )
          .child(Mono(`${view.left}%`, { size: TEXT.xs, color: tone })),
      )
      .child(
        h_flex()
          .pl(80)
          .gap(6)
          .flex_wrap()
          .text_size(TEXT.xs)
          .text_color(k.mutedFg)
          .child(`${view.window} window`)
          .child(div().child(view.resetsIn ? `· resets in ${view.resetsIn}` : "· window reset"))
          .when(Boolean(view.readAgo), (e) => e.child(div().text_color(k.warning).child(`· read ${view.readAgo} ago`))),
      );
  }

  cardSkeleton(i, k) {
    return v_flex().id(`agent-card-loading-${i}`).w(CARD.w).min_w(CARD.w).max_w(420).h(CARD.h).flex_grow_1().p(7).rounded(18).bg(k.muted).child(v_flex().size_full().rounded(RADIUS.xl).bg(k.card).p(14).gap(12).child(Skeleton({ w: 140, h: 22 })).child(Skeleton({ h: CARD.art })).child(Skeleton({ w: 200 })).child(Skeleton({ w: 220 })).child(Skeleton({ w: 180 })));
  }

  // -------------------------------------------------------------------------------------------------------------------
  // The picked agent's set-up

  row(id, k, { title, chips = [], detail, mono, controls = [] }) {
    return v_flex()
      .id(id)
      .px(12)
      .py(10)
      .gap(4)
      .rounded(RADIUS.md)
      .hover((s) => s.bg(k.accent))
      .child(h_flex().gap(8).items_center().child(div().text_size(TEXT.base).font_semibold().child(title)).children(chips.filter(Boolean)).child(div().flex_1()).when(Boolean(mono), (e) => e.child(Mono(mono))).children(controls.filter(Boolean)))
      .when(Boolean(detail), (e) => e.child(div().text_size(TEXT.sm).text_color(k.mutedFg).child(detail.length > 260 ? `${detail.slice(0, 257)}…` : detail)));
  }

  list(rows, empty, k) {
    if (!rows.length) return div().px(12).py(16).text_size(TEXT.sm).text_color(k.mutedFg).child(empty);
    return v_flex().gap(2).children(rows);
  }

  details(agent, k) {
    const look = LOOK[agent.id] ?? { color: k.ring };
    const counts = { instructions: agent.instructions.exists ? 1 : 0, skills: agent.skills.length, plugins: agent.plugins.length, mcp: agent.mcp.length };
    const pane = v_flex().gap(4);
    let body;
    if (!agent.installed) {
      body = div().px(12).py(16).text_size(TEXT.sm).text_color(k.mutedFg).child(`${agent.label} is not installed: \`${agent.command}\` was not found on PATH.`);
    } else if (this.editing?.agent === agent.id) {
      body = this.editorEl(k);
    } else if (this.section === "instructions") {
      const ins = agent.instructions;
      body = !ins.exists
        ? h_flex().px(12).py(16).gap(12).items_center().child(div().text_size(TEXT.sm).text_color(k.mutedFg).child(`No instructions file at ${ins.path}.`)).child(Button("ins-create", { label: "Create it", icon: "plus", size: "sm", variant: "outline", onClick: (_e, cx) => this.edit(cx, agent, `${agent.label}'s instructions`, ins.file, ins.path) }))
        : v_flex()
            .gap(10)
            .child(h_flex().gap(8).items_center().flex_wrap().child(Mono(ins.path, { size: TEXT.sm, color: k.foreground })).child(Badge(`${ins.lines} line${ins.lines === 1 ? "" : "s"}`, "secondary")).children(ins.imports.map((p, i) => Badge(`imports ${p}`, "info", { id: `import-${i}`, icon: "link" }))).child(div().flex_1()).child(Button("ins-edit", { label: "Edit", icon: "pencil", size: "sm", variant: "outline", onClick: (_e, cx) => this.edit(cx, agent, `${agent.label}'s instructions`, ins.file, ins.path) })))
            .child(
              div()
                .p(14)
                .rounded(RADIUS.md)
                .border_1()
                .border_color(k.border)
                .bg(k.canvas)
                .font_family("JetBrains Mono")
                .text_size(TEXT.sm)
                .whitespace_normal()
                .children(ins.text.split("\n").map((line, i) => div().id(`ins-${i}`).min_h(18).child(line || " "))),
            )
            .when(ins.cut, (e) => e.child(div().text_size(TEXT.xs).text_color(k.mutedFg).child("The file is longer: only its start is shown.")));
    } else if (this.section === "skills") {
      body = this.list(
        [...agent.skills].sort(onFirst).map((s, i) =>
          this.row(`skill-${i}`, k, {
            title: s.name,
            chips: [s.source && Chip(s.source, {}), stateBadge(s)],
            detail: s.description,
            mono: brief(s.path),
            controls: [s.file && Button(`skill-edit-${i}`, { icon: "pencil", variant: "ghost", size: "icon-sm", tooltip: "Edit SKILL.md", onClick: (_e, cx) => this.edit(cx, agent, `${s.name}/SKILL.md`, s.file, s.path) }), this.switchEl(agent, "skill", s)],
          }),
        ),
        "No skills.",
        k,
      );
    } else if (this.section === "plugins") {
      body = this.list(
        [...agent.plugins].sort(onFirst).map((p, i) => this.row(`plugin-${i}`, k, { title: p.name, chips: [p.source && Chip(p.source, {}), stateBadge(p)], mono: p.version ? `v${p.version}` : "", controls: [this.switchEl(agent, "plugin", p)] })),
        "No plugins installed.",
        k,
      );
    } else {
      body = this.list(
        [...agent.mcp].sort(onFirst).map((m, i) => this.row(`mcp-${i}`, k, { title: m.name, chips: [m.source && Chip(m.source, {}), stateBadge(m), linkBadge(m), Chip(m.transport, {})], mono: m.host ?? "", controls: [this.switchEl(agent, "mcp", m)] })),
        "No MCP servers configured.",
        k,
      );
    }
    return pane
      .child(
        h_flex()
          .gap(12)
          .items_center()
          .child(h_flex().size(28).rounded(14).items_center().justify_center().bg("#ffffff").border_2().border_color(look.color).child(markOf(agent) ? image(markOf(agent)).size(18) : Icon("bot", { size: 16 })))
          .child(div().text_size(TEXT.lg).font_bold().child(agent.label))
          .child(Tabs("agent-sections", { items: SECTIONS.map((s) => ({ value: s.value, label: s.label, icon: s.icon, count: s.value === "instructions" ? null : counts[s.value] })), value: this.section, onChange: (v, cx) => (this.show(v), cx.notify()) })),
      )
      .when(agent.errors.length > 0, (e) => e.child(Callout("agent-errors", { tone: k.warning, icon: "triangle-alert", title: "Some of it could not be read", body: agent.errors.join(" · ") })))
      .child(v_flex().pt(6).child(body));
  }

  render(cx) {
    const k = tokens();
    const agents = this.agents();
    const agent = this.current();
    const installed = agents.filter((a) => a.installed).length;
    let content;
    if (!this.data && this.error && !this.loading && this.retried) content = ErrorState({ title: "Could not read the agents", message: this.error });
    else
      content = v_flex()
        .gap(28)
        .child(h_flex().gap(22).flex_wrap().justify_center().children(this.data ? agents.map((a) => this.card(a, k)) : [0, 1, 2].map((i) => this.cardSkeleton(i, k))))
        .when(Boolean(agent), (e) => e.child(v_flex().p(16).rounded(RADIUS.lg).border_1().border_color(k.border).bg(k.card).child(this.details(agent, k))));
    return v_flex()
      .id("agents-page")
      .track_focus(this.handle)
      .size_full()
      .relative()
      .bg(k.background)
      .text_color(k.foreground)
      .text_size(TEXT.base)
      .on_key_down((e, cx) => {
        if (this.key(e, cx)) cx.stop_propagation();
      })
      .child(
        PageHeader({
          icon: "bot",
          title: "Agents",
          description: this.data ? `${installed} of ${agents.length} installed · read ${this.data.updated}` : "Reading each agent's set-up…",
          actions: [Button("agents-refresh", { icon: this.loading ? "loader" : "refresh-cw", variant: "ghost", size: "icon", tooltip: "Read again  R", onClick: (_e, cx) => this.load(cx, true) })],
        }),
      )
      .child(v_flex().id("agents-scroll").flex_1().min_h(0).overflow_y_scroll().px(24).pt(8).pb(24).child(content))
      .child(KeyHints(this.editing ? [["⌘S", "save"], ["esc", "close"]] : [["1 2 3", "agent"], ["i s p m", "section"], ["e", "edit instructions"], ["R", "read again"]]))
      .children([this.toasts.render()].filter(Boolean));
  }
}
