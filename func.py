from collections import deque
from time import time
from datetime import datetime
from pathlib import Path
from threading import Lock
from tkinter import filedialog

from base import BaseApp
from capture import CaptureManager, FramePacket


class App(BaseApp):
    UI_REFRESH_MS = 250
    INFERENCE_EVERY_N = 3

    def __init__(self, num_channels: int = 12) -> None:
        super().__init__(num_channels=num_channels)
        self.capture_manager = CaptureManager()
        self.frame_counts = [0] * self.num_channels
        self.fps_timestamps: list[deque] = [deque(maxlen=30) for _ in range(self.num_channels)]
        self.resolutions: list[tuple[int, int] | None] = [None] * self.num_channels
        self.frame_skip_counters = [0] * self.num_channels
        self.channel_state_lock = Lock()
        self.channel_states = [self._default_channel_state() for _ in range(self.num_channels)]
        self._rendered_states: list[dict] = [{} for _ in range(self.num_channels)]
        self.protocol("WM_DELETE_WINDOW", self.exit_app)
        self._initialize_channel_controls()
        self._start_ui_refresh()

    @staticmethod
    def is_valid_rtsp(text: str) -> bool:
        return text.startswith("rtsp://") and len(text) > len("rtsp://") and len(text) <= 200

    def submit_entry(self, channel_index: int) -> None:
        entered_text = self.entries[channel_index].get().strip()

        if self.is_valid_rtsp(entered_text):
            self.frame_counts[channel_index] = 0
            self.fps_timestamps[channel_index].clear()
            self.resolutions[channel_index] = None
            self.frame_skip_counters[channel_index] = 0
            self._set_channel_state(
                channel_index,
                state="Connecting",
                frames="0",
                fps="0.0",
                resolution="-",
                extra="Latency: -",
                connect_text="Retry",
                connect_enabled=True,
                disconnect_enabled=True,
            )
            self.capture_manager.start_stream(
                channel_index=channel_index,
                source=entered_text,
                processor=self.process_frame,
                convert_to_rgb=False,
            )
            message = f"Channel {channel_index + 1}: connecting to RTSP stream"
        else:
            self.stop_stream(channel_index, reason="Invalid URL")
            message = f"Channel {channel_index + 1}: invalid format, use rtsp://..."

        self.label.configure(text=message)

    def save_config(self, event=None) -> None:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
        config_path = filedialog.asksaveasfilename(
            title="Save Config",
            defaultextension=".cfg",
            initialfile=f"{timestamp}.cfg",
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")],
            initialdir=Path.cwd(),
        )

        if not config_path:
            return

        lines = []
        for channel_index, entry in enumerate(self.entries, start=1):
            value = entry.get().strip()
            lines.append(f'channel{channel_index}: "{value}"')

        config_file = Path(config_path)
        config_file.write_text("\n".join(lines), encoding="utf-8")
        self.label.configure(text=f"Config saved: {config_file.name}")

    def open_from(self, event=None) -> None:
        config_path = filedialog.askopenfilename(
            title="Open Config",
            filetypes=[("Config files", "*.cfg"), ("All files", "*.*")],
            initialdir=Path.cwd(),
        )

        if not config_path:
            return

        lines = Path(config_path).read_text(encoding="utf-8").splitlines()

        for entry in self.entries:
            entry.delete(0, "end")

        loaded_channels = 0
        for line in lines:
            if ":" not in line:
                continue

            channel_name, raw_value = line.split(":", maxsplit=1)
            channel_name = channel_name.strip().lower()
            raw_value = raw_value.strip()

            if not channel_name.startswith("channel"):
                continue

            channel_number_text = channel_name.removeprefix("channel")
            if not channel_number_text.isdigit():
                continue

            channel_index = int(channel_number_text) - 1
            if not 0 <= channel_index < len(self.entries):
                continue

            value = raw_value.strip().strip('"')
            self.entries[channel_index].insert(0, value)
            loaded_channels += 1

        self.label.configure(
            text=f"Loaded {loaded_channels} channel(s) from {Path(config_path).name}"
        )

    def process_frame(self, packet: FramePacket) -> None:
        idx = packet.channel_index

        self.frame_counts[idx] += 1
        self.resolutions[idx] = (packet.width, packet.height)
        self.fps_timestamps[idx].append(time())

        self.frame_skip_counters[idx] += 1
        if self.frame_skip_counters[idx] % self.INFERENCE_EVERY_N == 0:
            pass  # CV pipeline goes here — packet.frame_rgb is the RGB numpy array

    def _get_fps(self, idx: int) -> float:
        ts = self.fps_timestamps[idx]
        if len(ts) < 2:
            return 0.0
        return (len(ts) - 1) / max(ts[-1] - ts[0], 1e-6)

    def exit_app(self, event=None) -> None:
        self.capture_manager.stop_all_nowait()
        super().exit_app(event=event)

    def stop_stream(self, channel_index: int, reason: str = "Stopped") -> None:
        self.capture_manager.stop_stream(channel_index)
        self._set_channel_state(
            channel_index,
            state=reason,
            connect_text="Connect",
            connect_enabled=True,
            disconnect_enabled=False,
        )
        self.label.configure(text=f"Channel {channel_index + 1}: stream {reason.lower()}")

    def _start_ui_refresh(self) -> None:
        self.after(self.UI_REFRESH_MS, self._refresh_ui)

    def _refresh_ui(self) -> None:
        for channel_index in range(self.num_channels):
            if self.capture_manager.is_running(channel_index):
                error = self.capture_manager.get_latest_error(channel_index)
                if error:
                    self._set_channel_state(
                        channel_index,
                        state="Error",
                        frames=str(self.frame_counts[channel_index]),
                        fps=f"{self._get_fps(channel_index):.1f}",
                        resolution="-",
                        extra=f"Error: {error[:12]}",
                        connect_text="Retry",
                        connect_enabled=True,
                        disconnect_enabled=True,
                    )
                elif self.frame_counts[channel_index] > 0:
                    res = self.resolutions[channel_index]
                    resolution = f"{res[0]}x{res[1]}" if res else "-"
                    self._set_channel_state(
                        channel_index,
                        state="Streaming",
                        frames=str(self.frame_counts[channel_index]),
                        fps=f"{self._get_fps(channel_index):.1f}",
                        resolution=resolution,
                        extra="Latency: Live",
                        connect_text="Retry",
                        connect_enabled=True,
                        disconnect_enabled=True,
                    )

        with self.channel_state_lock:
            channel_states = [state.copy() for state in self.channel_states]

        for channel_index, state in enumerate(channel_states):
            prev = self._rendered_states[channel_index]

            stats_keys = ("state", "frames", "fps", "resolution", "extra")
            if any(state.get(k) != prev.get(k) for k in stats_keys):
                self.set_channel_stats(
                    channel_index,
                    state=state["state"],
                    frames=state["frames"],
                    fps=state["fps"],
                    resolution=state["resolution"],
                    extra=state["extra"],
                )

            control_keys = ("connect_text", "connect_enabled", "disconnect_enabled")
            if any(state.get(k) != prev.get(k) for k in control_keys):
                self.set_channel_controls(
                    channel_index,
                    connect_text=state["connect_text"],
                    connect_enabled=state["connect_enabled"],
                    disconnect_enabled=state["disconnect_enabled"],
                )

            self._rendered_states[channel_index] = state

        if self.winfo_exists():
            self.after(self.UI_REFRESH_MS, self._refresh_ui)

    def _initialize_channel_controls(self) -> None:
        for channel_index in range(self.num_channels):
            self._set_channel_state(channel_index)

    @staticmethod
    def _default_channel_state() -> dict[str, str | bool]:
        return {
            "state": "Idle",
            "frames": "0",
            "fps": "0.0",
            "resolution": "-",
            "extra": "Latency: -",
            "connect_text": "Connect",
            "connect_enabled": True,
            "disconnect_enabled": False,
        }

    def _set_channel_state(self, channel_index: int, **updates) -> None:
        with self.channel_state_lock:
            self.channel_states[channel_index].update(updates)
