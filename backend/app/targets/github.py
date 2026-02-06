"""GitHub Issue adapter for Target Delivery System.

This adapter maps Komorebi's internal data to GitHub's issue creation API
via the GitHub MCP server tool `github.create_issue`.

Schema Fields:
- title (TEXT, required): Issue title
- body (MARKDOWN, required): Issue description
- labels (TAGS, optional): Comma-separated labels
- assignees (TAGS, optional): Comma-separated GitHub usernames

Context Requirements:
The adapter expects context to provide:
- repo_owner: GitHub organization or user
- repo_name: Repository name

Example Usage:
    adapter = GitHubIssueAdapter()
    
    form_data = {
        "title": "Bug in login",
        "body": "Users cannot log in with special characters",
        "labels": "bug,priority-high",
        "assignees": "alice,bob"
    }
    
    context = {
        "repo_owner": "myorg",
        "repo_name": "myproject"
    }
    
    # Merge context into form data
    data = {**form_data, **context}
    
    # Map to MCP arguments
    mcp_args = adapter.map_arguments(data)
    # => {
    #   "owner": "myorg",
    #   "repo": "myproject",
    #   "title": "Bug in login",
    #   "body": "Users cannot log in...",
    #   "labels": ["bug", "priority-high"],
    #   "assignees": ["alice", "bob"]
    # }
"""
from typing import Dict, Any
from backend.app.targets.base import (
    TargetAdapter,
    TargetSchema,
    FieldSchema,
    FieldType,
)


class GitHubIssueAdapter(TargetAdapter):
    """Adapter for creating GitHub issues via MCP.
    
    This adapter transforms form data into arguments for the
    `github.create_issue` MCP tool from the GitHub MCP server.
    
    MCP Tool: github.create_issue
    Required Args: owner, repo, title, body
    Optional Args: labels (array), assignees (array)
    """
    
    @property
    def schema(self) -> TargetSchema:
        """Define the GitHub Issue form schema."""
        return TargetSchema(
            name="github_issue",
            display_name="GitHub Issue",
            description="Create a new issue in a GitHub repository",
            icon="🐙",
            fields=[
                FieldSchema(
                    name="title",
                    type=FieldType.TEXT,
                    label="Title",
                    placeholder="Brief issue summary",
                    required=True,
                    help_text="One-line summary of the issue"
                ),
                FieldSchema(
                    name="body",
                    type=FieldType.MARKDOWN,
                    label="Description",
                    placeholder="Detailed issue description with markdown formatting",
                    required=True,
                    help_text="Full issue description (supports Markdown)"
                ),
                FieldSchema(
                    name="labels",
                    type=FieldType.TAGS,
                    label="Labels",
                    placeholder="bug, enhancement, documentation",
                    required=False,
                    help_text="Comma-separated list of labels (e.g., 'bug,urgent')"
                ),
                FieldSchema(
                    name="assignees",
                    type=FieldType.TAGS,
                    label="Assignees",
                    placeholder="alice, bob",
                    required=False,
                    help_text="Comma-separated GitHub usernames (e.g., 'alice,bob')"
                ),
            ]
        )
    
    @property
    def mcp_tool_name(self) -> str:
        """Return the GitHub MCP tool name."""
        return "github.create_issue"
    
    def map_arguments(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Map form data to GitHub MCP tool arguments.
        
        Args:
            data: Dictionary containing both form fields and context.
                  Must include: title, body, repo_owner, repo_name
                  Optional: labels, assignees
        
        Returns:
            Dictionary formatted for github.create_issue MCP tool:
            - owner: Repository owner/organization
            - repo: Repository name
            - title: Issue title
            - body: Issue description
            - labels: Array of label strings
            - assignees: Array of GitHub usernames
        
        Raises:
            KeyError: If required fields are missing
        """
        # Extract required fields
        owner = data.get("repo_owner")
        repo = data.get("repo_name")
        title = data["title"]
        body = data["body"]
        
        # Build base arguments
        mcp_args = {
            "owner": owner,
            "repo": repo,
            "title": title,
            "body": body,
        }
        
        # Parse comma-separated labels into array
        labels_str = data.get("labels", "")
        if labels_str and isinstance(labels_str, str):
            labels = [label.strip() for label in labels_str.split(",") if label.strip()]
            mcp_args["labels"] = labels
        else:
            mcp_args["labels"] = []
        
        # Parse comma-separated assignees into array
        assignees_str = data.get("assignees", "")
        if assignees_str and isinstance(assignees_str, str):
            assignees = [user.strip() for user in assignees_str.split(",") if user.strip()]
            mcp_args["assignees"] = assignees
        else:
            mcp_args["assignees"] = []
        
        return mcp_args
    
    def validate_prerequisites(self) -> bool:
        """Validate that GitHub MCP server is accessible.
        
        TODO (v1.1): Implement actual validation by:
        1. Checking if GitHub MCP server is running
        2. Verifying GITHUB_TOKEN is configured
        3. Ensuring repo context is available
        
        For MVP, we assume GitHub MCP is properly configured.
        
        Returns:
            True (placeholder implementation)
        """
        # Placeholder: Always return True for MVP
        # In production, query MCP registry/health endpoint
        return True
