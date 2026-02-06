"""Execution profile models for secure command wrappers.

Profiles define environment variables, blocking policies, and
secret redaction rules for `k exec` command execution.
"""

from typing import Optional

from pydantic import BaseModel, Field


class BlockingPolicy(BaseModel):
    """Security policies for profile execution."""

    network: bool = Field(default=False, description="Block network access")
    write_files: list[str] = Field(
        default_factory=list,
        description="Glob patterns to block writes to",
    )


class ExecutionProfile(BaseModel):
    """An execution environment wrapper loaded from profiles.yaml."""

    name: str = Field(..., min_length=1, description="Profile identifier")
    parent: Optional[str] = Field(None, description="Parent profile to inherit from")
    command: Optional[list[str]] = Field(None, description="Preset command wrapper")
    args: list[str] = Field(default_factory=list, description="Default arguments")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables")
    blocking: BlockingPolicy = Field(default_factory=BlockingPolicy)
    redact_secrets: bool = Field(default=True, description="Enable secret redaction")
    stream_output: bool = Field(default=False, description="Stream output in real-time")
    capture_stdin: bool = Field(default=False, description="Capture standard input")


class ResolvedProfile(BaseModel):
    """Profile after inheritance resolution — ready for execution."""

    name: str
    command: Optional[list[str]] = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    blocking: BlockingPolicy = Field(default_factory=BlockingPolicy)
    redact_secrets: bool = True
    stream_output: bool = False
    capture_stdin: bool = False
