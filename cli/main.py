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
