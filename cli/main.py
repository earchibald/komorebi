"""Komorebi CLI - Command-line interface for fast capture.

Provides commands for:
- capture: Quick inbox capture
- list: View chunks and projects
- compact: Manual compaction trigger
- serve: Start the backend server
"""

import httpx
import typer
from rich.console import Console
from rich.table import Table
from typing import Optional

app = typer.Typer(
    name="komorebi",
    help="Cognitive infrastructure CLI for capture, compaction, and context management",
)
console = Console()

# Default API URL
DEFAULT_API_URL = "http://localhost:8000/api/v1"


def get_api_url() -> str:
    """Get the API URL from environment or default."""
    import os
    return os.getenv("KOMOREBI_API_URL", DEFAULT_API_URL)


@app.command()
def capture(
    content: str = typer.Argument(..., help="Content to capture"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project ID to associate"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags"),
):
    """Quickly capture a thought, note, or task to the inbox."""
    api_url = get_api_url()
    
    data = {
        "content": content,
        "source": "cli",
    }
    
    if project:
        data["project_id"] = project
    
    if tags:
        data["tags"] = [t.strip() for t in tags.split(",")]
    
    try:
        with httpx.Client() as client:
            response = client.post(f"{api_url}/chunks", json=data)
            response.raise_for_status()
            chunk = response.json()
            
        console.print(f"✅ Captured: [bold green]{chunk['id'][:8]}...[/bold green]")
        console.print(f"   Status: {chunk['status']}")
        
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] {e.response.text}")
        raise typer.Exit(1)


@app.command("list")
def list_chunks(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (inbox, processed, compacted, archived)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of items to show"),
):
    """List chunks from the inbox or with filters."""
    api_url = get_api_url()
    
    params = {"limit": limit}
    if status:
        params["status"] = status
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{api_url}/chunks", params=params)
            response.raise_for_status()
            chunks = response.json()
        
        if not chunks:
            console.print("[dim]No chunks found.[/dim]")
            return
        
        table = Table(title="Chunks")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Content", style="white", max_width=50)
        table.add_column("Tags", style="green", width=20)
        table.add_column("Created", style="dim", width=16)
        
        for chunk in chunks:
            tags = ", ".join(chunk.get("tags", []))
            created = chunk["created_at"][:16].replace("T", " ")
            content = chunk["content"][:50] + "..." if len(chunk["content"]) > 50 else chunk["content"]
            
            table.add_row(
                chunk["id"][:8] + "...",
                chunk["status"],
                content,
                tags or "-",
                created,
            )
        
        console.print(table)
        
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)


@app.command()
def stats():
    """Show chunk statistics."""
    api_url = get_api_url()
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{api_url}/chunks/stats")
            response.raise_for_status()
            data = response.json()
        
        table = Table(title="Chunk Statistics")
        table.add_column("Status", style="cyan")
        table.add_column("Count", style="yellow", justify="right")
        
        table.add_row("📥 Inbox", str(data["inbox"]))
        table.add_row("⚙️  Processed", str(data["processed"]))
        table.add_row("📦 Compacted", str(data["compacted"]))
        table.add_row("🗄️  Archived", str(data["archived"]))
        table.add_row("", "")
        table.add_row("[bold]Total[/bold]", f"[bold]{data['total']}[/bold]")
        
        console.print(table)
        
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)


@app.command()
def compact(
    project: str = typer.Argument(..., help="Project ID to compact"),
):
    """Compact all processed chunks in a project."""
    api_url = get_api_url()
    
    try:
        with httpx.Client() as client:
            response = client.post(f"{api_url}/projects/{project}/compact")
            response.raise_for_status()
            data = response.json()
        
        console.print(f"✅ Compaction completed for project [bold]{project[:8]}...[/bold]")
        
        if data.get("context_summary"):
            console.print("\n[bold]Context Summary:[/bold]")
            console.print(data["context_summary"])
        
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] {e.response.text}")
        raise typer.Exit(1)


@app.command()
def projects():
    """List all projects."""
    api_url = get_api_url()
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{api_url}/projects")
            response.raise_for_status()
            project_list = response.json()
        
        if not project_list:
            console.print("[dim]No projects found.[/dim]")
            return
        
        table = Table(title="Projects")
        table.add_column("ID", style="cyan", width=10)
        table.add_column("Name", style="white", width=30)
        table.add_column("Chunks", style="yellow", justify="right", width=10)
        table.add_column("Description", style="dim", max_width=40)
        
        for project in project_list:
            desc = project.get("description") or "-"
            if len(desc) > 40:
                desc = desc[:37] + "..."
            
            table.add_row(
                project["id"][:8] + "...",
                project["name"],
                str(project["chunk_count"]),
                desc,
            )
        
        console.print(table)
        
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)


@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Text to search for in chunk content"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (inbox, processed, compacted, archived)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filter by project ID"),
    entity_type: Optional[str] = typer.Option(None, "--entity-type", help="Filter by entity type (error, url, tool_id, decision, code_ref)"),
    entity_value: Optional[str] = typer.Option(None, "--entity-value", help="Filter by entity value (partial match)"),
    created_after: Optional[str] = typer.Option(None, "--after", help="Filter chunks created after (ISO 8601)"),
    created_before: Optional[str] = typer.Option(None, "--before", help="Filter chunks created before (ISO 8601)"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results to return"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full content and metadata"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output raw JSON"),
):
    """Search chunks by content text, entities, date range, and filters.
    
    Examples:
        komorebi search "error traceback"
        komorebi search --status inbox --limit 5
        komorebi search "deploy" --entity-type decision -v
        komorebi search --after 2026-02-01 --before 2026-02-05
        komorebi search --json  # all chunks as JSON
    """
    api_url = get_api_url()
    
    params: dict = {"limit": limit, "offset": 0}
    if query:
        params["q"] = query
    if status:
        params["status"] = status
    if project:
        params["project_id"] = project
    if entity_type:
        params["entity_type"] = entity_type
    if entity_value:
        params["entity_value"] = entity_value
    if created_after:
        params["created_after"] = created_after
    if created_before:
        params["created_before"] = created_before
    
    try:
        with httpx.Client() as client:
            response = client.get(f"{api_url}/chunks/search", params=params)
            response.raise_for_status()
            result = response.json()
        
        if json_output:
            import json
            console.print(json.dumps(result, indent=2))
            return
        
        items = result.get("items", [])
        total = result.get("total", 0)
        
        # Summary line
        search_desc = f'"{query}"' if query else "all chunks"
        filter_parts = []
        if status:
            filter_parts.append(f"status={status}")
        if project:
            filter_parts.append(f"project={project[:8]}...")
        if entity_type:
            filter_parts.append(f"entity_type={entity_type}")
        if entity_value:
            filter_parts.append(f"entity_value={entity_value}")
        if created_after:
            filter_parts.append(f"after={created_after}")
        if created_before:
            filter_parts.append(f"before={created_before}")
        filter_str = f" ({', '.join(filter_parts)})" if filter_parts else ""
        
        console.print(
            f"🔍 Search for {search_desc}{filter_str}: "
            f"[bold]{total}[/bold] result{'s' if total != 1 else ''} "
            f"(showing {len(items)})"
        )
        
        if not items:
            console.print("[dim]No matching chunks found.[/dim]")
            return
        
        if verbose:
            # Verbose: one panel per chunk
            for i, chunk in enumerate(items, 1):
                console.print(f"\n{'─' * 60}")
                console.print(
                    f"[bold cyan]#{i}[/bold cyan] "
                    f"[cyan]{chunk['id'][:8]}...[/cyan] "
                    f"[yellow]{chunk['status']}[/yellow]"
                )
                if chunk.get("project_id"):
                    console.print(f"  📁 Project: {chunk['project_id'][:8]}...")
                tags = chunk.get("tags", [])
                if tags:
                    console.print(f"  🏷️  Tags: {', '.join(tags)}")
                created = chunk["created_at"][:19].replace("T", " ")
                console.print(f"  📅 Created: {created}")
                if chunk.get("token_count"):
                    console.print(f"  🔢 Tokens: {chunk['token_count']}")
                console.print(f"\n  [white]{chunk['content']}[/white]")
                if chunk.get("summary"):
                    console.print(f"\n  [green]💡 {chunk['summary']}[/green]")
        else:
            # Table view
            table = Table(title=None)
            table.add_column("#", style="dim", width=3)
            table.add_column("ID", style="cyan", width=10)
            table.add_column("Status", style="yellow", width=12)
            table.add_column("Content", style="white", max_width=50)
            table.add_column("Created", style="dim", width=16)
            
            for i, chunk in enumerate(items, 1):
                content = chunk["content"]
                if len(content) > 50:
                    content = content[:47] + "..."
                created = chunk["created_at"][:16].replace("T", " ")
                
                table.add_row(
                    str(i),
                    chunk["id"][:8] + "...",
                    chunk["status"],
                    content,
                    created,
                )
            
            console.print(table)
    
    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        console.print("[dim]Is the server running? Start with: komorebi serve[/dim]")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] {e.response.text}")
        raise typer.Exit(1)


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the Komorebi backend server."""
    import uvicorn
    
    console.print(f"🌸 Starting Komorebi server on [bold]{host}:{port}[/bold]")
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@app.command("mcp-serve")
def mcp_serve():
    """Start Komorebi as an MCP server (stdio transport).

    Coding agents (Claude Code, Cursor, Windsurf) connect by
    spawning this command as a subprocess and communicating
    via JSON-RPC over stdin/stdout.
    """
    import asyncio
    from backend.app.mcp.server import KomorebiMCPServer

    server = KomorebiMCPServer()
    console.print("🔌 Komorebi MCP Server starting (stdio)", err=True)
    asyncio.run(server.run_stdio())


# ── Trace sub-commands ──────────────────────────────────────

trace_app = typer.Typer(name="trace", help="Manage traces (context sessions)")
app.add_typer(trace_app)


@trace_app.command("rename")
def trace_rename(
    new_name: str = typer.Argument(..., help="New name for the trace"),
    trace_id: Optional[str] = typer.Option(None, "--id", help="Trace ID (defaults to active)"),
):
    """Rename the active trace (or a specific trace by --id)."""
    api_url = get_api_url()

    try:
        with httpx.Client() as client:
            if trace_id:
                tid = trace_id
            else:
                # Get active trace
                resp = client.get(f"{api_url}/traces/active")
                resp.raise_for_status()
                active = resp.json()
                if not active:
                    console.print("[red]No active trace. Create one with `k switch <name>`.[/red]")
                    raise typer.Exit(1)
                tid = active["id"]

            resp = client.patch(f"{api_url}/traces/{tid}", json={"name": new_name})
            resp.raise_for_status()
            trace = resp.json()
            console.print(f"✅ Trace renamed to [bold green]{trace['name']}[/bold green]")

    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] {e.response.text}")
        raise typer.Exit(1)


@app.command("switch")
def switch_trace(
    name: str = typer.Argument(..., help="Trace name to switch to (or create)"),
):
    """Create or switch to a trace by name with fuzzy matching.

    If an exact or close match exists, activates it.
    Otherwise creates a new trace with the given name.
    """
    api_url = get_api_url()

    try:
        with httpx.Client() as client:
            # Search for existing traces matching the name
            resp = client.get(f"{api_url}/traces", params={"limit": 100})
            resp.raise_for_status()
            traces = resp.json()

            # Try exact match first
            exact = [t for t in traces if t["name"].lower() == name.lower()]
            if exact:
                target = exact[0]
                resp = client.post(f"{api_url}/traces/{target['id']}/activate")
                resp.raise_for_status()
                console.print(f"🔀 Switched to trace [bold green]{target['name']}[/bold green]")
                return

            # Fuzzy match using difflib
            from difflib import get_close_matches
            names = [t["name"] for t in traces]
            matches = get_close_matches(name, names, n=1, cutoff=0.6)
            if matches:
                matched = [t for t in traces if t["name"] == matches[0]][0]
                resp = client.post(f"{api_url}/traces/{matched['id']}/activate")
                resp.raise_for_status()
                console.print(
                    f"🔀 Switched to trace [bold green]{matched['name']}[/bold green] "
                    f"(fuzzy match for '{name}')"
                )
                return

            # No match — create new trace
            resp = client.post(f"{api_url}/traces", json={"name": name})
            resp.raise_for_status()
            trace = resp.json()
            console.print(f"✨ Created and activated trace [bold green]{trace['name']}[/bold green]")

    except httpx.RequestError as e:
        console.print(f"[bold red]Error:[/bold red] Could not connect to server: {e}")
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[bold red]Error:[/bold red] {e.response.text}")
        raise typer.Exit(1)


# ── Watch sub-commands ──────────────────────────────────────

watch_app = typer.Typer(name="watch", help="Filesystem watcher management")
app.add_typer(watch_app)


@watch_app.callback(invoke_without_command=True)
def watch_start(
    ctx: typer.Context,
    path: Optional[str] = typer.Argument(None, help="Path to watch"),
    recursive: bool = typer.Option(True, "--recursive/--no-recursive", "-r", help="Watch recursively"),
):
    """Start a filesystem watcher on a path.

    If no sub-command is given and a path is provided, starts watching.
    """
    if ctx.invoked_subcommand is not None:
        return

    if not path:
        console.print("[red]Provide a path to watch, e.g.: k watch ./src[/red]")
        raise typer.Exit(1)

    from pathlib import Path as P
    target = P(path).resolve()
    if not target.exists():
        console.print(f"[red]Path does not exist: {target}[/red]")
        raise typer.Exit(1)

    # Lazy import — watchdog may not be installed
    try:
        from backend.app.core.watcher import FileWatcherDaemon
    except ImportError:
        console.print("[red]watchdog not installed. Run: pip install watchdog[/red]")
        raise typer.Exit(1)

    api_url = get_api_url()
    console.print(f"👁️  Watching [bold]{target}[/bold] {'recursively' if recursive else 'non-recursively'}")
    console.print("Press Ctrl+C to stop.\n")

    daemon = FileWatcherDaemon(
        path=str(target),
        api_url=api_url,
        recursive=recursive,
    )
    try:
        daemon.run()
    except KeyboardInterrupt:
        daemon.stop()
        console.print("\n⏹️  Watcher stopped.")


@watch_app.command("status")
def watch_status():
    """List active filesystem watchers.

    Currently reads from ~/.komorebi/watchers.json if present.
    """
    from pathlib import Path as P
    import json

    watchers_file = P.home() / ".komorebi" / "watchers.json"
    if not watchers_file.exists():
        console.print("[dim]No active watchers.[/dim]")
        return

    try:
        data = json.loads(watchers_file.read_text())
        watchers = data if isinstance(data, list) else data.get("watchers", [])
    except (json.JSONDecodeError, OSError):
        console.print("[dim]No active watchers.[/dim]")
        return

    if not watchers:
        console.print("[dim]No active watchers.[/dim]")
        return

    table = Table(title="Active Watchers")
    table.add_column("Path", style="cyan")
    table.add_column("Recursive", style="yellow")
    table.add_column("PID", style="dim")

    for w in watchers:
        table.add_row(
            w.get("path", "?"),
            "✓" if w.get("recursive") else "✗",
            str(w.get("pid", "-")),
        )
    console.print(table)


if __name__ == "__main__":
    app()
