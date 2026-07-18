"""In-memory pub/sub hub.

One process holds the latest frame / sensor / CV values and fans each new item
out to any number of downstream subscribers (MJPEG endpoints, sensor WS, CV
worker, dashboard, ...). Subscriber queues drop the oldest item when full so a
slow consumer can never stall the phone -> server ingest path.
"""
import asyncio
import time
from typing import Optional, Set


class _Sub:
    """Async context manager around a subscriber queue; auto-unsubscribes on exit."""

    def __init__(self, registry: "Set[asyncio.Queue]", q: "asyncio.Queue") -> None:
        self._registry = registry
        self.q = q

    async def __aenter__(self) -> "asyncio.Queue":
        return self.q

    async def __aexit__(self, *exc) -> None:
        self._registry.discard(self.q)


class Hub:
    def __init__(self) -> None:
        self.latest_frame: Optional[bytes] = None            # raw camera JPEG
        self.latest_frame_meta: dict = {}
        self.latest_sensors: dict = {}
        self.latest_cv: dict = {}                            # CV metrics (JSON)
        self.latest_cv_frame: Optional[bytes] = None         # CV-annotated JPEG
        self.frame_seq = 0
        self.sensor_seq = 0
        self._frame_subs: Set[asyncio.Queue] = set()
        self._sensor_subs: Set[asyncio.Queue] = set()
        self._cv_subs: Set[asyncio.Queue] = set()
        self._cv_frame_subs: Set[asyncio.Queue] = set()

    # ---------------- publish (ingest + cv worker) ----------------
    def publish_frame(self, jpeg: bytes) -> None:
        self.frame_seq += 1
        self.latest_frame = jpeg
        self.latest_frame_meta = {"seq": self.frame_seq, "t": time.time(), "bytes": len(jpeg)}
        self._broadcast(self._frame_subs, jpeg)

    def publish_sensors(self, data: dict) -> None:
        self.sensor_seq += 1
        self.latest_sensors = data
        self._broadcast(self._sensor_subs, data)

    def publish_cv(self, data: dict) -> None:
        self.latest_cv = data
        self._broadcast(self._cv_subs, data)

    def publish_cv_frame(self, jpeg: bytes) -> None:
        self.latest_cv_frame = jpeg
        self._broadcast(self._cv_frame_subs, jpeg)

    @staticmethod
    def _broadcast(subs: "Set[asyncio.Queue]", item) -> None:
        for q in list(subs):
            if q.full():
                try:
                    q.get_nowait()  # drop oldest; keep consumers near real-time
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(item)
            except asyncio.QueueFull:
                pass

    # ---------------- subscribe (downstream endpoints) ----------------
    def sub_frames(self) -> _Sub:
        return self._make(self._frame_subs, maxsize=1)        # always newest raw frame

    def sub_sensors(self) -> _Sub:
        return self._make(self._sensor_subs, maxsize=512)     # keep the sample stream

    def sub_cv(self) -> _Sub:
        return self._make(self._cv_subs, maxsize=64)

    def sub_cv_frames(self) -> _Sub:
        return self._make(self._cv_frame_subs, maxsize=1)     # always newest processed frame

    @staticmethod
    def _make(registry: "Set[asyncio.Queue]", maxsize: int) -> _Sub:
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        registry.add(q)
        return _Sub(registry, q)


hub = Hub()
