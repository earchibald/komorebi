"""Filesystem watcher daemon.

Uses ``watchdog`` to monitor paths for file events, recording
each change as a ``FileEvent`` via the Komorebi REST API.

Runs as a foreground process started by ``k watch <path>``.
The daemon posts events to the Komorebi API so it's decoupled
from the server lifecycle.
"""

from __future__ import annotations

import hashlib
import json
import logging
import mimetypes
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default max depth for recursive watching
MAX_DEPTH = int(os.getenv("KOMOREBI_WATCH_MAX_DEPTH", "5"))

# Patterns to ignore
IGNORE_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
}


def _hash_prefix(path: str, size: int = 8192) -> Optional[str]:
    """SHA256 of the first ``size`` bytes of a file."""
    try:
        with open(path, "rb") as f:
            data = f.read(size)
        return hashlib.sha256(data).hexdigest()
    except (OSError, PermissionError):
        return None


def _should_ignore(path: str) -> bool:
    """Check if a path should be ignored based on patterns."""
    parts = Path(path).parts
    return any(p in IGNORE_PATTERNS for p in parts)


class FileWatcherDaemon:
    """Foreground filesystem watcher daemon.

    Posts ``FileEvent`` records to the Komorebi REST API
    whenever files are created, modified, or deleted.

    Args:
        path: Root directory to watch.
        api_url: Base URL of the Komorebi API.
        recursive: Whether to watch subdirectories.
    """

    def __init__(
        self,
        path: str,
        api_url: str = "http://localhost:8000/api/v1",
        recursive: bool = True,
    ) -> None:
        self.path = path
        self.api_url = api_url
        self.recursive = recursive
        self._running = False
        self._observer = None

    def run(self) -> None:
        """Start watching. Blocks until stop() or SIGINT."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler, FileSystemEvent
        except ImportError:
            raise ImportError(
                "watchdog is required for filesystem watching. "
                "Install with: pip install watchdog"
            )

        daemon = self

        class _Handler(FileSystemEventHandler):
            def on_created(self, event: FileSystemEvent) -> None:
                if not event.is_directory:
                    daemon._handle_event(event.src_path, "created")

            def on_modified(self, event: FileSystemEvent) -> None:
                if not event.is_directory:
                    daemon._handle_event(event.src_path, "modified")

            def on_deleted(self, event: FileSystemEvent) -> None:
                if not event.is_directory:
                    daemon._handle_event(event.src_path, "deleted")

            def on_moved(self, event: FileSystemEvent) -> None:
                if not event.is_directory:
                    daemon._handle_event(getattr(event, "dest_path", event.src_path), "moved")

        self._observer = Observer()
        self._observer.schedule(_Handler(), self.path, recursive=self.recursive)
        self._observer.start()
        self._running = True

        # Register watcher state
        self._register()

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the watcher gracefully."""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
        self._unregister()

    def _handle_event(self, file_path: str, crud_op: str) -> None:
        """Process a single filesystem event."""
        if _should_ignore(file_path):
            return

        # Compute metadata
        hash_prefix = _hash_prefix(file_path) if crud_op != "deleted" else None
        size_bytes = None
        mime_type = None
        if crud_op != "deleted":
            try:
                size_bytes = os.path.getsize(file_path)
            except OSError:
                pass
            mime_type = mimetypes.guess_type(file_path)[0]

        # Post to API
        payload = {
            "path": file_path,
            "crud_op": crud_op,
            "size_bytes": size_bytes,
            "hash_prefix": hash_prefix,
            "mime_type": mime_type,
        }

        try:
            # Get active trace ID first
            import httpx
            with httpx.Client(timeout=5) as client:
                trace_resp = client.get(f"{self.api_url}/traces/active")
                if trace_resp.status_code != 200 or not trace_resp.json():
                    logger.debug("No active trace — skipping file event for %s", file_path)
                    return
                trace_data = trace_resp.json()
                payload["trace_id"] = trace_data["id"]

                # Create file event via internal DB write
                # (We use the REST API approach for decoupling)
                # NOTE: file-events endpoint is read-only; we write directly
                from backend.app.db.database import async_session
                from backend.app.db.file_event_repository import FileEventRepository
                from backend.app.models.file_event import FileEventCreate, CrudOp
                import asyncio
                from uuid import UUID

                async def _write():
                    async with async_session() as session:
                        repo = FileEventRepository(session)
                        await repo.create(FileEventCreate(
                            trace_id=UUID(payload["trace_id"]),
                            path=payload["path"],
                            crud_op=CrudOp(payload["crud_op"]),
                            size_bytes=payload.get("size_bytes"),
                            hash_prefix=payload.get("hash_prefix"),
                            mime_type=payload.get("mime_type"),
                        ))

                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(_write())
                    else:
                        asyncio.run(_write())
                except RuntimeError:
                    asyncio.run(_write())

        except Exception:
            logger.warning("Failed to record file event for %s", file_path, exc_info=True)

    def _register(self) -> None:
        """Register this watcher in ~/.komorebi/watchers.json."""
        watchers_file = Path.home() / ".komorebi" / "watchers.json"
        watchers_file.parent.mkdir(parents=True, exist_ok=True)

        watchers = []
        if watchers_file.exists():
            try:
                watchers = json.loads(watchers_file.read_text())
            except (json.JSONDecodeError, OSError):
                watchers = []

        # Remove stale entry for same path
        watchers = [w for w in watchers if w.get("path") != self.path]
        watchers.append({
            "path": self.path,
            "recursive": self.recursive,
            "pid": os.getpid(),
        })
        watchers_file.write_text(json.dumps(watchers, indent=2))

    def _unregister(self) -> None:
        """Remove this watcher from ~/.komorebi/watchers.json."""
        watchers_file = Path.home() / ".komorebi" / "watchers.json"
        if not watchers_file.exists():
            return

        try:
            watchers = json.loads(watchers_file.read_text())
            watchers = [w for w in watchers if w.get("path") != self.path]
            watchers_file.write_text(json.dumps(watchers, indent=2))
        except (json.JSONDecodeError, OSError):
            pass
