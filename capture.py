from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Lock, Thread
from time import time
from typing import Callable

import av


FrameProcessor = Callable[["FramePacket"], None]


@dataclass(slots=True)
class FramePacket:
    channel_index: int
    source: str
    frame_rgb: object | None
    width: int
    height: int
    pts: int | None
    timestamp: float


class StreamWorker:
    def __init__(
        self,
        channel_index: int,
        source: str,
        processor: FrameProcessor | None = None,
        convert_to_rgb: bool = False,
        reconnect_delay: float = 2.0,
        reconnect_max_delay: float = 30.0,
    ) -> None:
        self.channel_index = channel_index
        self.source = source
        self.processor = processor
        self.convert_to_rgb = convert_to_rgb
        self.reconnect_delay = reconnect_delay
        self.reconnect_max_delay = reconnect_max_delay

        self._latest_frame: FramePacket | None = None
        self._latest_error: str | None = None
        self._lock = Lock()
        self._stop_event = Event()
        self._thread = Thread(
            target=self._run,
            name=f"rtsp-worker-{channel_index + 1}",
            daemon=True,
        )

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=3)

    def stop_nowait(self) -> None:
        self._stop_event.set()

    def get_latest_frame(self) -> FramePacket | None:
        with self._lock:
            return self._latest_frame

    def get_latest_error(self) -> str | None:
        with self._lock:
            return self._latest_error

    def _run(self) -> None:
        delay = self.reconnect_delay
        while not self._stop_event.is_set():
            try:
                self._capture_loop()
                delay = self.reconnect_delay
            except Exception as error:  # noqa: BLE001
                with self._lock:
                    self._latest_error = str(error)

                if self._stop_event.wait(delay):
                    break
                delay = min(delay * 2, self.reconnect_max_delay)

    def _capture_loop(self) -> None:
        container = av.open(
            self.source,
            timeout=5.0,
            options={
                "rtsp_transport": "tcp",
                "fflags": "nobuffer",
                "flags": "low_delay",
            },
        )

        try:
            stream = container.streams.video[0]
            stream.thread_type = "FRAME"

            for frame in container.decode(stream):
                if self._stop_event.is_set():
                    break

                packet = FramePacket(
                    channel_index=self.channel_index,
                    source=self.source,
                    frame_rgb=frame.to_ndarray(format="rgb24") if self.convert_to_rgb else None,
                    width=frame.width,
                    height=frame.height,
                    pts=frame.pts,
                    timestamp=time(),
                )

                with self._lock:
                    self._latest_frame = packet
                    self._latest_error = None

                if self.processor is not None:
                    self.processor(packet)
        finally:
            container.close()


class CaptureManager:
    def __init__(self) -> None:
        self._workers: dict[int, StreamWorker] = {}
        self._lock = Lock()

    def start_stream(
        self,
        channel_index: int,
        source: str,
        processor: FrameProcessor | None = None,
        convert_to_rgb: bool = False,
    ) -> None:
        self.stop_stream(channel_index)

        worker = StreamWorker(
            channel_index=channel_index,
            source=source,
            processor=processor,
            convert_to_rgb=convert_to_rgb,
        )
        worker.start()

        with self._lock:
            self._workers[channel_index] = worker

    def stop_stream(self, channel_index: int) -> None:
        with self._lock:
            worker = self._workers.pop(channel_index, None)

        if worker is not None:
            worker.stop()

    def stop_all(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()

        for worker in workers:
            worker.stop()

    def stop_all_nowait(self) -> None:
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()

        for worker in workers:
            worker.stop_nowait()

    def get_latest_frame(self, channel_index: int) -> FramePacket | None:
        with self._lock:
            worker = self._workers.get(channel_index)

        if worker is None:
            return None

        return worker.get_latest_frame()

    def get_latest_error(self, channel_index: int) -> str | None:
        with self._lock:
            worker = self._workers.get(channel_index)

        if worker is None:
            return None

        return worker.get_latest_error()

    def is_running(self, channel_index: int) -> bool:
        with self._lock:
            return channel_index in self._workers

    def set_processor(
        self,
        channel_index: int,
        processor: FrameProcessor | None,
    ) -> None:
        with self._lock:
            worker = self._workers.get(channel_index)

        if worker is not None:
            worker.processor = processor
