// A right-click menu (shadcn's <ContextMenu>), opened by ui.js's openMenu() at the pointer: each item runs
// `personal.<command>`, which reaches the shown views' command(). An item shows an `icon`, or an `image` in its own
// colours (an agent's mark), and a check when `checked`. ↑/↓ and Enter work, Esc closes.

import { div, image } from "gpui-kit";
import { h_flex, v_flex } from "gpui-base";
import { props, run, closeOverlay } from "herdr";
import { tokens, TEXT, RADIUS, Icon, Kbd } from "./ui.js";

export default class Menu {
  init(_props, cx) {
    this.at = -1;
    this.handle = cx.focus_handle();
    this.handle.focus();
  }

  choose(item) {
    closeOverlay(props().overlay);
    if (item?.command) run(`personal.${item.command}`);
  }

  render() {
    const k = tokens();
    const items = props()?.items ?? [];
    const pickable = items.filter((i) => i !== "separator");
    return v_flex()
      .id("menu")
      .track_focus(this.handle)
      .size_full()
      .p(4)
      .rounded(RADIUS.lg)
      .border_1()
      .border_color(k.border)
      .bg(k.popover)
      .shadow_lg()
      .text_size(TEXT.base)
      .on_key_down((e, cx) => {
        if (e.key === "escape") return closeOverlay(props().overlay);
        if (e.key === "down") this.at = Math.min(this.at + 1, pickable.length - 1);
        else if (e.key === "up") this.at = Math.max(this.at - 1, 0);
        else if (e.key === "enter") return this.choose(pickable[this.at]);
        else return;
        cx.stop_propagation();
        cx.notify();
      })
      .children(
        items.map((item, i) =>
          item === "separator"
            ? div().h(1).my(4).mx(-4).bg(k.border)
            : h_flex()
                .id(`menu-${i}`)
                .h(32)
                .px(8)
                .gap(8)
                .items_center()
                .rounded(RADIUS.md)
                .cursor_pointer()
                .text_color(item.destructive ? k.destructive : k.foreground)
                .when(pickable[this.at] === item, (e) => e.bg(k.accent))
                .hover((s) => s.bg(k.accent))
                .on_click(() => this.choose(item))
                .child(item.image ? image(item.image).size(16).flex_none() : item.icon ? Icon(item.icon, { size: 16, color: item.destructive ? k.destructive : k.mutedFg }) : div().w(16))
                .child(div().flex_1().truncate().child(item.label))
                .when(Boolean(item.checked), (e) => e.child(Icon("check", { size: 14, color: k.mutedFg })))
                .when(Boolean(item.kbd), (e) => e.child(Kbd(item.kbd))),
        ),
      );
  }
}

