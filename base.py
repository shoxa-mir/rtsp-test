from pathlib import Path
from tkinter import Menu

from PIL import Image

from customtkinter import CTk, CTkButton, CTkEntry, CTkFrame, CTkImage, CTkLabel, CTkScrollableFrame, CTkToplevel


class BaseApp(CTk):
    DEFAULT_CHANNELS = 4
    MIN_CHANNELS = 1
    MAX_CHANNELS = 40
    CHANNEL_SPACING = 8
    PANEL_WIDTH = 460
    CARD_MIN_HEIGHT = 80

    def __init__(self, num_channels: int = DEFAULT_CHANNELS) -> None:
        super().__init__()

        if not (self.MIN_CHANNELS <= num_channels <= self.MAX_CHANNELS):
            raise ValueError(f"num_channels must be between {self.MIN_CHANNELS} and {self.MAX_CHANNELS}")

        self.num_channels = num_channels
        self.entries: list[CTkEntry] = []
        self.channel_boxes: list[CTkFrame] = []
        self.channel_labels: list[CTkLabel] = []
        self.connect_buttons: list[CTkButton] = []
        self.disconnect_buttons: list[CTkButton] = []
        self.stats_rows: list[CTkFrame] = []
        self.stats_badges: list[CTkLabel] = []
        self.stats_value_labels: list[dict[str, CTkLabel]] = []
        self.delete_buttons: list[CTkButton] = []
        self.channel_tags: list[str] = []
        self.tag_entries: list[CTkEntry] = []
        self.tag_save_btns: list[CTkButton] = []
        self.options_window: CTkToplevel | None = None
        self.about_window: CTkToplevel | None = None
        self.active_entry: CTkEntry | None = None
        self.button_icons = self._load_button_icons()

        self.title("RTSP Test")
        self.geometry("1000x800")
        self.minsize(1000, 800)

        self.menu_bar = CTkFrame(self, height=28, corner_radius=0)
        self.menu_bar.pack(fill="x")
        self.menu_bar_layout()
        self.entry_context_menu = self._create_entry_context_menu()

        self.scroll_frame = CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(padx=16, pady=24, fill="both", expand=True)
        self.scroll_frame.grid_columnconfigure(0, weight=1)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

        self.rtsp_box = CTkFrame(self.scroll_frame, width=self.PANEL_WIDTH)
        self.rtsp_box.grid(row=0, column=0, padx=(0, 8), sticky="new")

        self.stats_box = CTkFrame(self.scroll_frame, width=self.PANEL_WIDTH)
        self.stats_box.grid(row=0, column=1, padx=(8, 0), sticky="new")

        self.channel_box_layout()
        self.stats_box_layout()

        for i in range(self.num_channels):
            self._add_channel_row(i)

        self.add_channel_btn = CTkButton(
            self.scroll_frame,
            text="+ Add Channel",
            width=200,
            command=self.add_channel,
        )
        self.add_channel_btn.grid(row=1, column=0, columnspan=2, pady=(12, 8))
        if self.num_channels >= self.MAX_CHANNELS:
            self.add_channel_btn.configure(state="disabled")

        self.label = CTkLabel(self, text="Enter RTSP URL")
        self.label.pack(pady=(0, 16))

        self.bind_shortcuts()

    def menu_bar_layout(self) -> None:
        self.menu_button = CTkButton(
            self.menu_bar,
            text="Menu",
            width=80,
            bg_color="transparent",
            fg_color="transparent",
            hover_color="#454040",
            command=self.show_menu_dropdown,
        )
        self.menu_button.pack(side="left")

        self.options_button = CTkButton(
            self.menu_bar,
            text="Options",
            width=80,
            bg_color="transparent",
            fg_color="transparent",
            hover_color="#454040",
            command=self.open_options_window,
        )
        self.options_button.pack(side="left")

        self.about_button = CTkButton(
            self.menu_bar,
            text="About",
            width=80,
            bg_color="transparent",
            fg_color="transparent",
            hover_color="#454040",
            command=self.open_about_window,
        )
        self.about_button.pack(side="left")

        self.menu_dropdown = Menu(self, tearoff=0)
        self.menu_dropdown.add_command(
            label="Open from...",
            accelerator="Ctrl+O",
            command=self.open_from,
        )
        self.menu_dropdown.add_command(
            label="Save config",
            accelerator="Ctrl+S",
            command=self.save_config,
        )
        self.menu_dropdown.add_command(
            label="Exit",
            accelerator="Ctrl+Q",
            command=self.exit_app,
        )

    def channel_box_layout(self) -> None:
        header = CTkFrame(self.rtsp_box, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 10))

        title = CTkLabel(header, text="RTSP Sources", anchor="w")
        title.pack(fill="x")

        CTkLabel(
            header,
            text="Connect each channel to a live RTSP endpoint.",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(2, 0))

    def stats_box_layout(self) -> None:
        header = CTkFrame(self.stats_box, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(16, 10))

        title = CTkLabel(header, text="Channel Stats", anchor="w")
        title.pack(fill="x")

        CTkLabel(
            header,
            text="Live connection and processing state for each channel.",
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(2, 0))

    def _add_channel_row(self, idx: int) -> None:
        # --- RTSP panel card ---
        channel_box = CTkFrame(self.rtsp_box, corner_radius=14, height=self.CARD_MIN_HEIGHT)
        channel_box.pack(fill="x", padx=16, pady=(0, self.CHANNEL_SPACING))
        channel_box.pack_propagate(False)
        self.channel_boxes.append(channel_box)

        channel_header = CTkFrame(channel_box, fg_color="transparent")
        channel_header.pack(fill="x", padx=14, pady=(8, 2))

        tag_save_btn = CTkButton(
            channel_header, text="Save", width=48,
            fg_color="transparent", hover_color="#454040",
            text_color=("gray10", "gray90"),
        )
        tag_save_btn.pack(side="right")
        self.tag_save_btns.append(tag_save_btn)
        tag_save_btn.configure(
            command=lambda b=tag_save_btn: self._save_tag(self.tag_save_btns.index(b))
        )

        tag_entry = CTkEntry(channel_header, width=120, placeholder_text="label...")
        tag_entry.pack(side="right", padx=(4, 4))
        self.tag_entries.append(tag_entry)

        self.channel_tags.append("")

        channel_label = CTkLabel(channel_header, text=f"Channel {idx + 1} :", anchor="w")
        channel_label.pack(side="left")
        self.channel_labels.append(channel_label)

        row = CTkFrame(channel_box, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 8))

        entry = CTkEntry(row, width=200, placeholder_text="rtsp://camera-address/stream")
        entry.pack(side="left", padx=(0, 10), expand=True, fill="x")
        entry.bind("<Button-3>", lambda event, e=entry: self.show_entry_context_menu(event, e))
        self.entries.append(entry)

        disc_btn = CTkButton(
            row, text="", width=40, state="disabled",
            fg_color="#ff9999", hover_color="#ff9999",
            text_color="white", text_color_disabled="#fff5f5",
            image=self.button_icons["stop"], compound="left",
        )
        disc_btn.configure(command=lambda b=disc_btn: self.stop_stream(self.disconnect_buttons.index(b)))
        disc_btn.pack(side="right", padx=(10, 0))
        self.disconnect_buttons.append(disc_btn)

        conn_btn = CTkButton(
            row, text="", width=40,
            fg_color="#6DCD01", hover_color="#4D7A01",
            image=self.button_icons["play"], compound="left",
        )
        conn_btn.configure(command=lambda b=conn_btn: self.submit_entry(self.connect_buttons.index(b)))
        conn_btn.pack(side="right")
        self.connect_buttons.append(conn_btn)

        # --- Stats panel card ---
        stats_row = CTkFrame(self.stats_box, corner_radius=14, height=self.CARD_MIN_HEIGHT)
        stats_row.pack(fill="x", padx=16, pady=(0, self.CHANNEL_SPACING))
        stats_row.pack_propagate(False)
        self.stats_rows.append(stats_row)

        stats_content = CTkFrame(stats_row, fg_color="transparent")
        stats_content.pack(fill="both", expand=True, padx=14, pady=(8, 6))
        stats_content.grid_columnconfigure(0, weight=1)
        stats_content.grid_columnconfigure(1, weight=1)
        stats_content.grid_columnconfigure(2, weight=0)
        stats_content.grid_rowconfigure(0, weight=1)
        stats_content.grid_rowconfigure(1, weight=1)

        frames_label = CTkLabel(stats_content, text="Frames: 0", anchor="w")
        frames_label.grid(row=0, column=0, sticky="w", padx=(0, 12), pady=(0, 1))

        fps_label = CTkLabel(stats_content, text="FPS: 0.0", anchor="w")
        fps_label.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(0, 1))

        badge = CTkLabel(stats_content, text="Idle", anchor="e", width=96, height=16)
        badge.grid(row=0, column=2, sticky="e", pady=0)
        self.stats_badges.append(badge)

        resolution_label = CTkLabel(stats_content, text="Resolution: -", anchor="w")
        resolution_label.grid(row=1, column=0, sticky="w", padx=(0, 12))

        extra_label = CTkLabel(stats_content, text="Latency: -", anchor="w")
        extra_label.grid(row=1, column=1, sticky="w")

        self.stats_value_labels.append({
            "frames": frames_label,
            "fps": fps_label,
            "resolution": resolution_label,
            "extra": extra_label,
        })

        del_btn = CTkButton(
            stats_content, text="✕", width=32, height=20,
            fg_color="#555555", hover_color="#333333", text_color="white",
        )
        del_btn.configure(command=lambda b=del_btn: self.delete_channel(self.delete_buttons.index(b)))
        del_btn.grid(row=1, column=2, sticky="e")
        self.delete_buttons.append(del_btn)

        self._update_delete_button_states()

    def _remove_channel_row(self, idx: int) -> None:
        self.channel_boxes[idx].destroy()
        self.stats_rows[idx].destroy()

        self.channel_boxes.pop(idx)
        self.channel_labels.pop(idx)
        self.entries.pop(idx)
        self.connect_buttons.pop(idx)
        self.disconnect_buttons.pop(idx)
        self.stats_rows.pop(idx)
        self.stats_badges.pop(idx)
        self.stats_value_labels.pop(idx)
        self.delete_buttons.pop(idx)
        self.channel_tags.pop(idx)
        self.tag_entries.pop(idx)
        self.tag_save_btns.pop(idx)

        for i, lbl in enumerate(self.channel_labels):
            lbl.configure(text=f"Channel {i + 1} :")

        self._update_delete_button_states()
        self.add_channel_btn.configure(state="normal")

    def _update_delete_button_states(self) -> None:
        state = "normal" if len(self.delete_buttons) > self.MIN_CHANNELS else "disabled"
        for btn in self.delete_buttons:
            btn.configure(state=state)

    def _save_tag(self, idx: int) -> None:
        self.channel_tags[idx] = self.tag_entries[idx].get()
        self.tag_entries[idx].configure(state="disabled")
        btn = self.tag_save_btns[idx]
        btn.configure(text="Edit",
                      command=lambda b=btn: self._edit_tag(self.tag_save_btns.index(b)))

    def _edit_tag(self, idx: int) -> None:
        self.tag_entries[idx].configure(state="normal")
        self.tag_entries[idx].focus()
        btn = self.tag_save_btns[idx]
        btn.configure(text="Save",
                      command=lambda b=btn: self._save_tag(self.tag_save_btns.index(b)))

    def set_channel_tag(self, idx: int, tag: str) -> None:
        self.channel_tags[idx] = tag
        self.tag_entries[idx].configure(state="normal")
        self.tag_entries[idx].delete(0, "end")
        btn = self.tag_save_btns[idx]
        if tag:
            self.tag_entries[idx].insert(0, tag)
            self.tag_entries[idx].configure(state="disabled")
            btn.configure(text="Edit",
                          command=lambda b=btn: self._edit_tag(self.tag_save_btns.index(b)))
        else:
            btn.configure(text="Save",
                          command=lambda b=btn: self._save_tag(self.tag_save_btns.index(b)))

    def set_channel_stats(
        self,
        channel_index: int,
        *,
        state: str = "Idle",
        frames: str = "0",
        fps: str = "0.0",
        resolution: str = "-",
        extra: str = "Latency: -",
    ) -> None:
        if 0 <= channel_index < len(self.stats_value_labels):
            labels = self.stats_value_labels[channel_index]
            labels["frames"].configure(text=f"Frames: {frames}")
            labels["fps"].configure(text=f"FPS: {fps}")
            labels["resolution"].configure(text=f"Resolution: {resolution}")
            labels["extra"].configure(text=extra)

            if channel_index < len(self.stats_badges):
                self.stats_badges[channel_index].configure(text=state)

    def set_channel_controls(
        self,
        channel_index: int,
        *,
        connect_text: str = "Connect",
        connect_enabled: bool = True,
        disconnect_enabled: bool = False,
    ) -> None:
        if 0 <= channel_index < len(self.connect_buttons):
            is_reconnect_mode = connect_text == "Retry"
            connect_image = self.button_icons["reconnect"] if is_reconnect_mode else self.button_icons["play"]
            self.connect_buttons[channel_index].configure(
                text="",
                image=connect_image,
                state="normal" if connect_enabled else "disabled",
                fg_color="#00AB5E" if is_reconnect_mode else "#6DCD01",
            )

        if 0 <= channel_index < len(self.disconnect_buttons):
            if disconnect_enabled:
                self.disconnect_buttons[channel_index].configure(
                    state="normal",
                    fg_color="#ED2F2F",
                    hover_color="#b32424",
                    image=self.button_icons["stop"],
                )
            else:
                self.disconnect_buttons[channel_index].configure(
                    state="disabled",
                    fg_color="#ff9999",
                    hover_color="#ff9999",
                    image=self.button_icons["stop"],
                )

    def _load_button_icons(self) -> dict[str, CTkImage]:
        icon_size = (20, 20)
        base_path = Path(__file__).resolve().parent

        return {
            "play": self._load_single_icon(base_path / "play.png", icon_size),
            "reconnect": self._load_single_icon(base_path / "reconnect.png", icon_size),
            "stop": self._load_single_icon(base_path / "stop.png", icon_size),
        }

    @staticmethod
    def _load_single_icon(path: Path, size: tuple[int, int]) -> CTkImage:
        image = Image.open(path)
        return CTkImage(light_image=image, dark_image=image, size=size)

    def submit_entry(self, channel_index: int) -> None:
        raise NotImplementedError("submit_entry must be implemented in a subclass.")

    def stop_stream(self, channel_index: int) -> None:
        raise NotImplementedError("stop_stream must be implemented in a subclass.")

    def add_channel(self) -> None:
        raise NotImplementedError("add_channel must be implemented in a subclass.")

    def delete_channel(self, channel_index: int) -> None:
        raise NotImplementedError("delete_channel must be implemented in a subclass.")

    def bind_shortcuts(self) -> None:
        self.bind_all("<Control-o>", self.open_from)
        self.bind_all("<Control-s>", self.save_config)
        self.bind_all("<Control-q>", self.exit_app)

    def show_menu_dropdown(self) -> None:
        x_position = self.menu_button.winfo_rootx()
        y_position = self.menu_button.winfo_rooty() + self.menu_button.winfo_height()
        self.menu_dropdown.tk_popup(x_position, y_position)
        self.menu_dropdown.grab_release()

    def _create_entry_context_menu(self) -> Menu:
        context_menu = Menu(self, tearoff=0)
        context_menu.add_command(label="Cut", command=self._cut_entry_text)
        context_menu.add_command(label="Copy", command=self._copy_entry_text)
        context_menu.add_command(label="Paste", command=self._paste_entry_text)
        context_menu.add_separator()
        context_menu.add_command(label="Select All", command=self._select_all_entry_text)
        return context_menu

    def show_entry_context_menu(self, event, entry: CTkEntry) -> str:
        self.active_entry = entry
        entry.focus()
        self.entry_context_menu.tk_popup(event.x_root, event.y_root)
        self.entry_context_menu.grab_release()
        return "break"

    def _copy_entry_text(self) -> None:
        if self.active_entry is None or not self.active_entry.select_present():
            return

        selected_text = self._get_selected_entry_text()
        if selected_text is None:
            return

        self.clipboard_clear()
        self.clipboard_append(selected_text)

    def _cut_entry_text(self) -> None:
        if self.active_entry is None or not self.active_entry.select_present():
            return

        selected_text = self._get_selected_entry_text()
        if selected_text is None:
            return

        self.clipboard_clear()
        self.clipboard_append(selected_text)
        selection_start, selection_end = self._get_entry_selection_range()
        if selection_start is not None and selection_end is not None:
            self.active_entry.delete(selection_start, selection_end)

    def _paste_entry_text(self) -> None:
        if self.active_entry is None:
            return

        try:
            clipboard_text = self.clipboard_get()
        except Exception:  # noqa: BLE001
            return

        if self.active_entry.select_present():
            selection_start, selection_end = self._get_entry_selection_range()
            if selection_start is not None and selection_end is not None:
                self.active_entry.delete(selection_start, selection_end)
                insert_index = selection_start
            else:
                insert_index = self.active_entry.index("insert")
        else:
            insert_index = self.active_entry.index("insert")

        self.active_entry.insert(insert_index, clipboard_text)

    def _get_entry_selection_range(self) -> tuple[int | None, int | None]:
        if self.active_entry is None:
            return None, None

        try:
            selection_start = self.active_entry.index("sel.first")
            selection_end = self.active_entry.index("sel.last")
        except Exception:  # noqa: BLE001
            return None, None

        return selection_start, selection_end

    def _get_selected_entry_text(self) -> str | None:
        if self.active_entry is None:
            return None

        selection_start, selection_end = self._get_entry_selection_range()
        if selection_start is None or selection_end is None:
            return None

        return self.active_entry.get()[selection_start:selection_end]

    def _select_all_entry_text(self) -> None:
        if self.active_entry is not None:
            self.active_entry.select_range(0, "end")
            self.active_entry.icursor("end")

    def save_config(self, event=None) -> None:
        self.label.configure(text="Config saved")

    def open_from(self, event=None) -> None:
        self.label.configure(text="Open from is not implemented")

    def exit_app(self, event=None) -> None:
        self.destroy()

    def open_options_window(self) -> None:
        self.options_window = self._open_or_focus_window(
            window=self.options_window,
            title="Options",
            size="400x300",
        )

    def open_about_window(self) -> None:
        self.about_window = self._open_or_focus_window(
            window=self.about_window,
            title="About",
            size="320x220",
        )

    def _open_or_focus_window(
        self,
        window: CTkToplevel | None,
        title: str,
        size: str,
    ) -> CTkToplevel:
        if window is not None and window.winfo_exists():
            window.focus()
            window.lift()
            return window

        new_window = CTkToplevel(self)
        new_window.title(title)
        new_window.geometry(size)

        if title == "Options":
            new_window.protocol("WM_DELETE_WINDOW", self.close_options_window)
        else:
            new_window.protocol("WM_DELETE_WINDOW", self.close_about_window)

        return new_window

    def close_options_window(self) -> None:
        if self.options_window is not None and self.options_window.winfo_exists():
            self.options_window.destroy()
        self.options_window = None

    def close_about_window(self) -> None:
        if self.about_window is not None and self.about_window.winfo_exists():
            self.about_window.destroy()
        self.about_window = None
