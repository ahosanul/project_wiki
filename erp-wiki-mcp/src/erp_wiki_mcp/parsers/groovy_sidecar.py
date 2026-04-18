"""Groovy AST Sidecar Manager - manages the Groovy subprocess for AST parsing."""
import asyncio
import json
from dataclasses import dataclass
from typing import AsyncContextManager, AsyncIterator
from pathlib import Path
import structlog

log = structlog.get_logger()


@dataclass
class GroovyParseResult:
    file_path: str
    status: str  # ok | failed
    ast: dict | None = None
    error: str | None = None
    artifact_type: str = "plain_groovy"


class GroovySidecar(AsyncContextManager["GroovySidecar"]):
    """Manages a single Groovy AST server process for the duration of a run."""

    def __init__(self, groovy_executable: str, project_root: Path):
        self.groovy_executable = groovy_executable
        self.project_root = project_root
        self._process: asyncio.subprocess.Process | None = None
        self._restart_count = 0
        self._max_restarts = 1

    async def __aenter__(self) -> "GroovySidecar":
        script_path = Path(__file__).parent.parent.parent.parent / "tools" / "groovy_ast_server.groovy"
        try:
            self._process = await asyncio.create_subprocess_exec(
                self.groovy_executable,
                str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=10 * 1024 * 1024,  # 10MB buffer
            )
            log.info("groovy_sidecar_started", executable=self.groovy_executable)
            return self
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Groovy executable not found: {self.groovy_executable}. "
                "Install Groovy 3+ and verify MCP_GROOVY_EXECUTABLE."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to start Groovy sidecar: {e}") from e

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._process:
            try:
                self._process.stdin.close()
                await self._process.stdin.wait_closed()
            except Exception:
                pass
            
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            
            log.info("groovy_sidecar_stopped")
        return False

    async def parse_file(self, file_path: str, artifact_type: str) -> GroovyParseResult:
        """Parse a single Groovy file through the sidecar."""
        if not self._process or self._process.returncode is not None:
            raise RuntimeError("Groovy sidecar is not running")

        # Send file path to sidecar
        try:
            self._process.stdin.write((file_path + "\n").encode())
            await self._process.stdin.drain()
        except Exception as e:
            log.error("groovy_sidecar_write_failed", error=str(e))
            return GroovyParseResult(
                file_path=file_path,
                status="failed",
                error=f"Failed to send to sidecar: {e}",
                artifact_type=artifact_type,
            )

        # Read response
        try:
            line = await asyncio.wait_for(self._process.stdout.readline(), timeout=60.0)
            if not line:
                # EOF - sidecar died
                return await self._handle_sidecar_death(file_path, artifact_type)
            
            response = json.loads(line.decode())
        except asyncio.TimeoutError:
            log.error("groovy_sidecar_timeout", file_path=file_path)
            return GroovyParseResult(
                file_path=file_path,
                status="failed",
                error="Timeout waiting for sidecar response",
                artifact_type=artifact_type,
            )
        except json.JSONDecodeError as e:
            log.error("groovy_sidecar_malformed_json", file_path=file_path, error=str(e))
            return await self._handle_malformed_response(file_path, artifact_type)

        if response.get("status") == "ok":
            return GroovyParseResult(
                file_path=file_path,
                status="ok",
                ast=response.get("ast"),
                artifact_type=artifact_type,
            )
        else:
            return GroovyParseResult(
                file_path=file_path,
                status="failed",
                error=response.get("error", "Unknown error"),
                artifact_type=artifact_type,
            )

    async def _handle_sidecar_death(self, file_path: str, artifact_type: str) -> GroovyParseResult:
        """Handle sidecar process death."""
        log.error("groovy_sidecar_died", file_path=file_path)
        
        if self._restart_count < self._max_restarts:
            self._restart_count += 1
            log.info("groovy_sidecar_restarting", attempt=self._restart_count)
            
            # Try to restart
            try:
                await self.__aenter__()
                # Retry the parse
                return await self.parse_file(file_path, artifact_type)
            except Exception as e:
                log.error("groovy_sidecar_restart_failed", error=str(e))
        
        return GroovyParseResult(
            file_path=file_path,
            status="failed",
            error="Groovy sidecar died and could not be restarted",
            artifact_type=artifact_type,
        )

    async def _handle_malformed_response(self, file_path: str, artifact_type: str) -> GroovyParseResult:
        """Handle malformed JSON response."""
        if self._restart_count < self._max_restarts:
            self._restart_count += 1
            log.info("groovy_sidecar_restarting_after_malformed", attempt=self._restart_count)
            
            try:
                await self.__aenter__()
                return await self.parse_file(file_path, artifact_type)
            except Exception as e:
                log.error("groovy_sidecar_restart_failed", error=str(e))
        
        return GroovyParseResult(
            file_path=file_path,
            status="failed",
            error="Malformed JSON from sidecar and restart failed",
            artifact_type=artifact_type,
        )

    async def check_alive(self) -> bool:
        """Check if sidecar process is still alive."""
        if not self._process:
            return False
        return self._process.returncode is None
