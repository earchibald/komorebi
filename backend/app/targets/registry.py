"""Target Registry for managing delivery adapters.

This module implements a centralized registry for all delivery target adapters.
The registry is accessed as a class-level singleton pattern (using class methods).

Usage:
    from backend.app.targets.registry import TargetRegistry
    from backend.app.targets.github import GitHubIssueAdapter
    
    # Register an adapter
    adapter = GitHubIssueAdapter()
    TargetRegistry.register(adapter)
    
    # Retrieve an adapter
    adapter = TargetRegistry.get("github_issue")
    
    # List all schemas
    schemas = TargetRegistry.list_schemas()
    
    # Get specific schema
    schema = TargetRegistry.get_schema("github_issue")
"""
from typing import Dict, List
from backend.app.targets.base import TargetAdapter, TargetSchema


class TargetRegistry:
    """Centralized registry for delivery target adapters.
    
    This is a class-level singleton pattern. All adapters are stored
    in a class variable `_targets` and accessed via class methods.
    
    Adapters should be registered at application startup (e.g., in
    backend/app/main.py event handler).
    
    Attributes:
        _targets: Dict mapping target name to adapter instance
    """
    
    _targets: Dict[str, TargetAdapter] = {}
    
    @classmethod
    def register(cls, adapter: TargetAdapter) -> None:
        """Register a delivery target adapter.
        
        Args:
            adapter: The adapter instance to register
        
        Raises:
            ValueError: If an adapter with the same name is already registered
        
        Example:
            adapter = GitHubIssueAdapter()
            TargetRegistry.register(adapter)
        """
        name = adapter.schema.name
        
        if name in cls._targets:
            raise ValueError(
                f"Target adapter '{name}' is already registered. "
                "Cannot register duplicate adapters."
            )
        
        cls._targets[name] = adapter
    
    @classmethod
    def get(cls, name: str) -> TargetAdapter:
        """Retrieve a registered adapter by name.
        
        Args:
            name: The target name (e.g., "github_issue")
        
        Returns:
            The registered adapter instance
        
        Raises:
            ValueError: If no adapter is registered with this name
        
        Example:
            adapter = TargetRegistry.get("github_issue")
            mcp_args = adapter.map_arguments(form_data)
        """
        if name not in cls._targets:
            raise ValueError(
                f"Target '{name}' is not registered. "
                f"Available targets: {list(cls._targets.keys())}"
            )
        
        return cls._targets[name]
    
    @classmethod
    def list_schemas(cls) -> List[TargetSchema]:
        """List all registered target schemas.
        
        Returns:
            List of schemas from all registered adapters
        
        Example:
            schemas = TargetRegistry.list_schemas()
            for schema in schemas:
                print(f"{schema.name}: {schema.display_name}")
        """
        return [adapter.schema for adapter in cls._targets.values()]
    
    @classmethod
    def get_schema(cls, name: str) -> TargetSchema:
        """Get the schema for a specific target.
        
        Args:
            name: The target name (e.g., "github_issue")
        
        Returns:
            The target's schema definition
        
        Raises:
            ValueError: If no adapter is registered with this name
        
        Example:
            schema = TargetRegistry.get_schema("github_issue")
            print(f"Fields: {[f.name for f in schema.fields]}")
        """
        adapter = cls.get(name)
        return adapter.schema
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered adapters.
        
        This method is primarily for testing purposes to reset
        the registry between test runs.
        
        Example:
            TargetRegistry.clear()
            assert len(TargetRegistry.list_schemas()) == 0
        """
        cls._targets = {}
