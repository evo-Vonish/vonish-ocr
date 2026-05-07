import time


class RuntimePolicyController:
    """Small runtime guard that can lower concurrency when heat is high."""

    def __init__(self, policy: dict):
        self.policy = dict(policy)
        self.current_concurrency = int(policy.get("concurrency") or 1)
        self.paused_until = 0.0
        self.last_event = "policy_loaded"

    def update_policy(self, policy: dict) -> None:
        self.policy = dict(policy)
        self.current_concurrency = int(policy.get("concurrency") or self.current_concurrency or 1)
        self.paused_until = 0.0
        self.last_event = "policy_updated"

    def adjust(self, gpu_temp: float | int | None = None, gpu_util: float | int | None = None, queue_depth: int = 0) -> dict:
        now = time.time()
        if self.paused_until and now < self.paused_until:
            return self.snapshot(paused=True)

        limit = int(self.policy.get("thermal_limit_c") or 85)
        base = int(self.policy.get("concurrency") or 1)
        temp = float(gpu_temp or 0)
        util = float(gpu_util or 0)

        if temp and temp >= limit:
            self.current_concurrency = max(1, self.current_concurrency // 2)
            self.paused_until = now + 5
            self.last_event = f"thermal_pause_{int(temp)}c"
        elif temp and temp >= limit - 8:
            self.current_concurrency = max(1, min(self.current_concurrency, base - 1))
            self.last_event = f"thermal_reduce_{int(temp)}c"
        elif util < 80 and queue_depth > 0:
            self.current_concurrency = min(base, self.current_concurrency + 1)
            self.last_event = "recover"

        return self.snapshot(paused=False)

    def snapshot(self, paused: bool = False) -> dict:
        return {
            "policy": self.policy,
            "current_concurrency": self.current_concurrency,
            "paused": paused,
            "paused_until": self.paused_until,
            "last_event": self.last_event,
        }

