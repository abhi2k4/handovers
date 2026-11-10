"""Per-key locks for steps that read, decide, then write in several queries.

Two clicks on "Approve" (or "Create plan") arrive together; without a lock both pass the check
and the graph gets two transfers. The backend runs as one uvicorn worker (app/backend/Dockerfile),
so an in-process lock is enough. Single-statement guards stay in Cypher where they fit
(graph/queries/handover_create.cypher).
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

_locks: dict[str, asyncio.Lock] = {}


@asynccontextmanager
async def hold(key: str) -> AsyncIterator[None]:
    """Run the block alone for this key (e.g. "transfer:ho:123")."""
    lock = _locks.setdefault(key, asyncio.Lock())
    async with lock:
        yield
