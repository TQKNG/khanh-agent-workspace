import { View, div, image, svg } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { theme, run, props, openOverlay, window, shared, setShared, updates, layout, readTextFile, appHome } from "herdr";

// The brand (workspace name and logos) belongs to whoever installs this: `brand.json` in the Herdr home,
//   { "name": "Acme Workspace", "logo": "brand/logo.png", "shortcut_logo": "brand/shortcut.png" }
// Logo paths are relative to the Herdr home. Without the file the header shows a neutral name and an initial.
const DEFAULT_BRAND = { name: "Workspace", logo: null, shortcut_logo: null };

/** A path inside the Herdr home, or null (absolute paths and ".." are refused). */
const homePath = (p) => {
  if (typeof p !== "string" || !p.trim()) return null;
  const clean = p.trim().replace(/\\/g, "/");
  return clean.startsWith("/") || /^[A-Za-z]:/.test(clean) || clean.split("/").includes("..") ? null : clean;
};

function parseBrand(text) {
  if (!text) return DEFAULT_BRAND;
  try {
    const raw = JSON.parse(text);
    const logo = homePath(raw.logo);
    return {
      name: typeof raw.name === "string" && raw.name.trim() ? raw.name.trim().slice(0, 40) : DEFAULT_BRAND.name,
      logo,
      shortcut_logo: homePath(raw.shortcut_logo) ?? logo,
    };
  } catch {
    return DEFAULT_BRAND;
  }
}

function find(node, id) {
  if (node?.id === id) return node;
  for (const child of node?.children ?? []) {
    const found = find(child, id);
    if (found) return found;
  }
  return null;
}

// The sidebar's rail goes by its width, not a flag: dragging its edge narrows it too.
const narrow = () => (find(layout(), "sidebar")?.size?.px ?? Infinity) < 160;

// To the rail (on macOS wide enough for the traffic lights), or back to the width it had.
function toggleSidebar() {
  const width = find(layout(), "sidebar")?.size?.px;
  if (!narrow()) setShared("sidebar.width", width);
  // Mods edited before the rail went by width still read the flag.
  setShared("sidebar.collapsed", !narrow());
  run("layout.resize", { id: "sidebar", px: narrow() ? (shared("sidebar.width") ?? 268) : window()?.platform === "macos" ? 76 : 44 });
}

export default class WorkspaceChrome extends View {
  init(_props, cx) {
    this.brand = DEFAULT_BRAND;
    this.brandText = null;
    const load = (cx) => cx.spawn(async (cx) => {
      const text = await readTextFile(`${appHome()}/brand.json`).catch(() => null);
      if (text === this.brandText) return;
      this.brandText = text;
      this.brand = parseBrand(text);
      cx.notify();
    });
    load(cx);
    cx.timer.every(4000, (cx) => load(cx));
  }

  /** The logo, or a tile with the name's first letter when there is none. */
  logo(path, size, radius, t) {
    if (path) return image(path).size(size).flex_none().rounded(radius);
    const initial = Array.from(this.brand.name)[0]?.toUpperCase() ?? "W";
    return div().size(size).flex_none().flex().items_center().justify_center().rounded(radius).bg(t.accent).text_color(t.accent_foreground).font_semibold().text_size(size * 0.55).child(initial);
  }

  button(id, label, action) {
    const t = theme();
    return div().id(id).size(26).flex_none().flex().items_center().justify_center().rounded(6).text_color(t.muted).hover(s => s.bg(t.hover).text_color(t.foreground))
      .on_mouse_down("left", (_e, cx) => cx.stop_propagation()).on_click(action).child(label);
  }
  render() {
    const t = theme();
    const collapsed = narrow();
    if (props()?.shortcut) {
      return h_flex().size_full().bg(t.chrome).items_center().justify_center()
        .child(div().id("shortcuts").size(30).flex_none().flex().items_center().justify_center().rounded(7)
          .hover(s => s.bg(t.hover)).on_mouse_down("left", (_e, cx) => cx.stop_propagation())
          .on_click(() => openOverlay({ mod: "help", kind: "dialog", width: 720, height: 680 }))
          .child(this.brand.shortcut_logo ? image(this.brand.shortcut_logo).size(23) : div().text_color(t.muted).font_semibold().child("?")));
    }
    if (props()?.footer) {
      const row = (id, icon, label, dim, action) => h_flex().id(id).h(28).px(8).gap(9).items_center().rounded(8)
        .when(collapsed, el => el.relative().w(32).px(0).justify_center().tooltip(label))
        .text_color(dim ? t.dim : t.muted).hover(s => s.bg(t.hover).text_color(t.foreground)).cursor_pointer()
        .on_click(action).child(svg(`mods/workspace-chrome-swiss/${icon}.svg`).size(14))
        .when(!collapsed, el => el.child(label));
      const ready = div().size(6).rounded_full().bg(t.accent);
      return v_flex().size_full().bg(t.chrome).border_t(1).border_color(t.border).px(8).pt(4).pb(8).text_size(13)
        .when(collapsed, el => el.px(0).items_center())
        .child(row("settings", "settings", "Settings", false, () => run("app.settings"))
          .when(Boolean(updates().app.ready), el => el.child(collapsed ? ready.absolute().top(5).right(6) : ready)))
        .child(row("machine", "plus", "Add machine", true, () => run("mod.open", { name: "machine-add" })));
    }
    return h_flex().size_full().bg(t.chrome).pl(collapsed ? 6 : 14).pr(10).gap(4).items_center().text_size(13.5)
      .when(window()?.platform === "macos" && !window()?.fullscreen && !collapsed, el => el.pl(76))
      .when(!collapsed, el => el.child(h_flex().flex_1().gap(8).items_center().child(this.logo(this.brand.logo, 22, 5, t)).child(div().min_w(0).truncate().font_semibold().text_color(t.foreground).child(this.brand.name))))
      .when(!collapsed, el => el.child(this.button("search", svg("mods/workspace-chrome-swiss/search.svg").size(15), () => run("mod.open", { name: "picker" }))))
      // On the macOS rail the traffic lights fill the row; the agents list's » unfolds it.
      .when(!(collapsed && window()?.platform === "macos"), el => el.child(this.button("sidebar-toggle", svg("mods/workspace-chrome-swiss/sidebar.svg").size(15), toggleSidebar)));
  }
}
