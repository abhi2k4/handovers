"""FalkorDB connection management.

One `FalkorDB` client (async, pooled) per process. Graphs are selected per tenant; callers never
pass graph names from user input.
"""

from dataclasses import dataclass
from typing import Any

from falkordb.asyncio import FalkorDB

from core.config import Settings


@dataclass(frozen=True)
class FalkorDBStatus:
    ok: bool
    module_version: int | None = None
    error: str | None = None


class FalkorDBClient:
    """Thin owner of the async FalkorDB client and the tenant graph handle."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graph_name = settings.tenant_graph
        self._client: FalkorDB | None = None

    @property
    def _db(self) -> FalkorDB:
        """The underlying client, created on first use.

        `falkordb.asyncio.FalkorDB()` contacts the server in its constructor (cluster check), so
        building it eagerly would raise when FalkorDB is down. Lazily, `status()` can report the
        outage, the app can start degraded, and tests can skip.
        """
        if self._client is None:
            password = self._settings.falkordb_password
            self._client = FalkorDB(
                host=self._settings.falkordb_host,
                port=self._settings.falkordb_port,
                password=password.get_secret_value() if password else None,
                socket_connect_timeout=3,
                socket_timeout=30,
            )
        return self._client

    @property
    def graph_name(self) -> str:
        return self._graph_name

    def graph(self, name: str | None = None) -> Any:
        """Handle to the tenant graph, or another named graph (`falkordb.asyncio.AsyncGraph`)."""
        return self._db.select_graph(name or self._graph_name)

    async def graph_exists(self, name: str | None = None) -> bool:
        graphs: list[str] = await self._db.list_graphs()
        return (name or self._graph_name) in graphs

    async def status(self) -> FalkorDBStatus:
        """Ping the server and read the graph module version."""
        try:
            conn = self._db.connection
            await conn.ping()
            modules = await conn.execute_command("MODULE", "LIST")
            version = _graph_module_version(modules)
            return FalkorDBStatus(ok=True, module_version=version)
        except Exception as exc:  # reported to the caller, never raised from a health probe
            return FalkorDBStatus(ok=False, error=f"{type(exc).__name__}: {exc}")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


def _graph_module_version(modules: Any) -> int | None:
    """Extract the `graph` module version from a `MODULE LIST` reply (RESP2 flat lists)."""
    for module in modules or []:
        fields = dict(zip(module[::2], module[1::2], strict=False))
        if fields.get("name") == "graph":
            return int(fields["ver"])
    return None
