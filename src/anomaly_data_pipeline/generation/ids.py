from __future__ import annotations

import uuid

NAMESPACE = uuid.UUID("fe5c61e2-89af-4d71-99f0-891c88a6df5b")


def stable_id(seed: int, kind: str, index: str | int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{seed}:{kind}:{index}"))
