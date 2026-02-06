"""Target Delivery System.

This package implements the Modular Target Delivery System (Module 8),
which decouples internal data from external tool APIs using an adapter pattern.

Key components:
- base.py: Core abstractions (TargetAdapter, TargetSchema, FieldSchema)
- registry.py: TargetRegistry for managing adapters
- github.py: GitHubIssueAdapter concrete implementation

Usage:
    from backend.app.targets import TargetRegistry
    from backend.app.targets.github import GitHubIssueAdapter
    
    # Register adapter
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    
    # List available targets
    schemas = TargetRegistry.list_schemas()
    
    # Dispatch to a target
    adapter = TargetRegistry.get("github_issue")
    mcp_args = adapter.map_arguments(form_data)
"""
from backend.app.targets.base import (
    TargetAdapter,
    TargetSchema,
    FieldSchema,
    FieldType,
)

__all__ = [
    "TargetAdapter",
    "TargetSchema",
    "FieldSchema",
    "FieldType",
]
