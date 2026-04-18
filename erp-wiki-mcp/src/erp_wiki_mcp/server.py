"""MCP server for erp-wiki-mcp."""

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from mcp.server import Server
import mcp.types as types

from erp_wiki_mcp.config import settings
from erp_wiki_mcp.registry.db import RegistryDB
from erp_wiki_mcp.tools.index_project import index_project
from erp_wiki_mcp.tools.status import get_status


def setup_logging() -> None:
    """Configure structlog JSON logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set root logger level
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=getattr(logging, settings.log_level.upper()),
    )


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def server_lifespan(server: Server):
    """Manage server lifespan and resources."""
    # Initialize database
    registry = RegistryDB(settings.db_path)
    await registry.init_db()

    # Store registry in server state
    server.state.registry = registry

    logger.info("Server starting", extra={"data_dir": str(settings.db_path.parent)})

    try:
        yield
    finally:
        logger.info("Server shutting down")


def create_server() -> Server:
    """Create and configure the MCP server."""
    server = Server("erp-wiki-mcp", lifespan=server_lifespan)

    @server.call_tool()
    async def call_index_project(name: str, arguments: dict) -> list:
        """Handle index_project tool calls."""
        registry: RegistryDB = server.state.registry

        path = arguments.get("path")
        if not path:
            return [{"type": "text", "text": "Error: 'path' argument is required"}]

        mode = arguments.get("mode", "dry_run")
        scope = arguments.get("scope", "full")
        profile_override = arguments.get("profile_override")

        result = await index_project(
            registry=registry,
            path=path,
            mode=mode,
            scope=scope,
            profile_override=profile_override,
        )

        return [{"type": "text", "text": str(result)}]

    @server.call_tool()
    async def call_status(name: str, arguments: dict) -> list:
        """Handle status tool calls."""
        registry: RegistryDB = server.state.registry

        run_id = arguments.get("run_id")
        project_id = arguments.get("project_id")

        result = await get_status(
            registry=registry,
            run_id=run_id,
            project_id=project_id,
        )

        return [{"type": "text", "text": str(result)}]

    # Register tools with MCP
    @server.list_tools()
    async def list_tools() -> list:
        """List available MCP tools."""
        return [
            types.Tool(
                name="index_project",
                description="Index a Grails/Java project into the knowledge graph",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the project root directory",
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["dry_run", "full"],
                            "default": "dry_run",
                            "description": "Indexing mode",
                        },
                        "scope": {
                            "type": "string",
                            "default": "full",
                            "description": "Scope filter (full, file:<rel>, module:<dir>, etc.)",
                        },
                        "profile_override": {
                            "type": "object",
                            "description": "Optional language profile override",
                        },
                    },
                    "required": ["path"],
                },
            ),
            types.Tool(
                name="status",
                description="Get status of an indexing run or project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "run_id": {
                            "type": "string",
                            "description": "Run ID to query",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Project ID to query (if run_id not provided)",
                        },
                    },
                },
            ),
        ]

    return server


def main() -> None:
    """Main entry point."""
    setup_logging()

    server = create_server()

    # Run the server using stdio transport
    from mcp.server.stdio import stdio_server

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(run())


if __name__ == "__main__":
    main()
