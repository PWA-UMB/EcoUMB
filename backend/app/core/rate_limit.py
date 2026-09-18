"""Límite de solicitudes por ventana deslizante, en memoria (por proceso).

Suficiente para el piloto con un solo worker. Al escalar horizontalmente debe
reemplazarse por un contador en Redis detrás de la misma interfaz (ADR-008).
"""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock


class SlidingWindowRateLimiter:
    def __init__(
        self,
        limit: int,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, key: str) -> float | None:
        """Registra un intento. ``None`` si se permite; si no, los segundos de espera."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return self._window - (now - hits[0])
            hits.append(now)
            return None
