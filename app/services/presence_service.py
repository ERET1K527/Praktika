import time
from threading import Lock


ONLINE_TTL = 60  # seconds since last heartbeat to still count as online


class PresenceRegistry:
    """In-memory presence registry keyed by user_id.

    A user is considered online while they send heartbeats at least
    every ``ttl`` seconds. No persistence: online state is ephemeral.
    """

    def __init__(self, ttl: int = ONLINE_TTL):
        self._seen: dict[int, float] = {}
        self._ttl = ttl
        self._lock = Lock()

    def heartbeat(self, user_id: int) -> None:
        with self._lock:
            self._seen[user_id] = time.time()

    def _prune_locked(self, now: float) -> None:
        cutoff = now - self._ttl
        for uid in list(self._seen.keys()):
            if self._seen[uid] < cutoff:
                del self._seen[uid]

    def online_user_ids(self, exclude: int | None = None) -> list[int]:
        with self._lock:
            self._prune_locked(time.time())
            return [uid for uid in self._seen.keys() if uid != exclude]

    def is_online(self, user_id: int) -> bool:
        with self._lock:
            ts = self._seen.get(user_id)
            return ts is not None and (time.time() - ts) <= self._ttl


presence = PresenceRegistry()
