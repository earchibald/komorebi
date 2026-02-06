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


if __name__ == "__main__":
    app()
