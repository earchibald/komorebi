#!/usr/bin/env python3
"""
Telemetry Tracker for Komorebi Prompts & Skills

Tracks usage of custom prompts and skills for:
- Usage patterns (which prompts/skills are used most)
- Model tier distribution
- Cost estimation
- Time savings estimation

Usage:
    python telemetry_tracker.py log <prompt_or_skill> <model_tier> [--duration <seconds>]
    python telemetry_tracker.py report [--days <n>]
    python telemetry_tracker.py costs [--days <n>]

Example:
    python telemetry_tracker.py log implement-feature standard --duration 120
    python telemetry_tracker.py report --days 7
    python telemetry_tracker.py costs --days 30
"""

import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error


# Telemetry data file location
TELEMETRY_DIR = Path.home() / ".komorebi" / "telemetry"
TELEMETRY_FILE = TELEMETRY_DIR / "usage.jsonl"

# MCP endpoint (if configured)
MCP_ENDPOINT = os.getenv("KOMOREBI_MCP_TELEMETRY_ENDPOINT")

# Model tier cost multipliers (relative to Haiku = 1x)
COST_MULTIPLIERS = {
    "economy": 1.0,       # Haiku
    "standard": 7.0,      # Auto (Sonnet/GPT-4o average)
    "premium": 60.0,      # Opus
    "research": 50.0,     # Gemini 3 Pro
}

# Estimated baseline time (seconds) without prompt/skill
BASELINE_TASK_TIME = 300  # 5 minutes to set up context manually


class TelemetryEntry:
    """A single telemetry log entry."""
    
    def __init__(
        self,
        prompt_or_skill: str,
        model_tier: str,
        duration_seconds: Optional[float] = None,
        success: bool = True,
        timestamp: Optional[str] = None,
    ):
        self.prompt_or_skill = prompt_or_skill
        self.model_tier = model_tier
        self.duration_seconds = duration_seconds
        self.success = success
        self.timestamp = timestamp or datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        return {
            "prompt_or_skill": self.prompt_or_skill,
            "model_tier": self.model_tier,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TelemetryEntry":
        return cls(
            prompt_or_skill=data["prompt_or_skill"],
            model_tier=data["model_tier"],
            duration_seconds=data.get("duration_seconds"),
            success=data.get("success", True),
            timestamp=data.get("timestamp"),
        )


def ensure_telemetry_dir():
    """Ensure telemetry directory exists."""
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


def send_to_mcp(entry_dict: dict) -> bool:
    """Send telemetry to MCP endpoint if configured."""
    if not MCP_ENDPOINT:
        return False
    
    try:
        data = json.dumps(entry_dict).encode('utf-8')
        req = urllib.request.Request(
            MCP_ENDPOINT,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                return True
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        # Silently fail - don't block on telemetry
        pass
    
    return False


def log_usage(
    prompt_or_skill: str,
    model_tier: str,
    duration_seconds: Optional[float] = None,
    success: bool = True,
):
    """Log a prompt/skill usage event."""
    ensure_telemetry_dir()
    
    entry = TelemetryEntry(
        prompt_or_skill=prompt_or_skill,
        model_tier=model_tier,
        duration_seconds=duration_seconds,
        success=success,
    )
    
    entry_dict = entry.to_dict()
    
    # Write to local file
    with open(TELEMETRY_FILE, "a") as f:
        f.write(json.dumps(entry_dict) + "\n")
    
    # Send to MCP endpoint if configured
    mcp_sent = send_to_mcp(entry_dict)
    
    status = "✅" if success else "❌"
    mcp_status = " [MCP ✓]" if mcp_sent else ""
    print(f"{status} Logged: {prompt_or_skill} ({model_tier}) - {duration_seconds or 'N/A'}s{mcp_status}")


def load_entries(days: Optional[int] = None) -> list[TelemetryEntry]:
    """Load telemetry entries, optionally filtering by days."""
    if not TELEMETRY_FILE.exists():
        return []
    
    entries = []
    cutoff = None
    if days:
        cutoff = datetime.utcnow() - timedelta(days=days)
    
    with open(TELEMETRY_FILE, "r") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entry = TelemetryEntry.from_dict(data)
                
                if cutoff:
                    entry_time = datetime.fromisoformat(entry.timestamp.replace("Z", "+00:00").replace("+00:00", ""))
                    if entry_time < cutoff:
                        continue
                
                entries.append(entry)
            except (json.JSONDecodeError, KeyError):
                continue
    
    return entries


def generate_usage_report(days: Optional[int] = None):
    """Generate a usage report."""
    entries = load_entries(days)
    
    if not entries:
        print("\n📊 No telemetry data found.")
        print("   Start logging with: python telemetry_tracker.py log <prompt> <tier>")
        return
    
    period = f"Last {days} days" if days else "All time"
    
    # Aggregate by prompt/skill
    by_prompt = {}
    by_tier = {}
    total_duration = 0
    success_count = 0
    
    for entry in entries:
        # By prompt/skill
        if entry.prompt_or_skill not in by_prompt:
            by_prompt[entry.prompt_or_skill] = 0
        by_prompt[entry.prompt_or_skill] += 1
        
        # By tier
        if entry.model_tier not in by_tier:
            by_tier[entry.model_tier] = 0
        by_tier[entry.model_tier] += 1
        
        # Duration
        if entry.duration_seconds:
            total_duration += entry.duration_seconds
        
        # Success
        if entry.success:
            success_count += 1
    
    print(f"\n📊 Telemetry Report ({period})")
    print("=" * 60)
    
    print("\n📈 Overview")
    print(f"   Total invocations: {len(entries)}")
    print(f"   Success rate: {success_count / len(entries) * 100:.1f}%")
    if total_duration:
        print(f"   Total time: {total_duration / 60:.1f} minutes")
        print(f"   Avg time per task: {total_duration / len(entries):.1f} seconds")
    
    print("\n🔧 By Prompt/Skill")
    for name, count in sorted(by_prompt.items(), key=lambda x: -x[1]):
        pct = count / len(entries) * 100
        print(f"   {name}: {count} ({pct:.1f}%)")
    
    print("\n🎯 By Model Tier")
    for tier, count in sorted(by_tier.items(), key=lambda x: -x[1]):
        pct = count / len(entries) * 100
        print(f"   {tier}: {count} ({pct:.1f}%)")
    
    print()


def generate_cost_report(days: Optional[int] = None):
    """Generate a cost analysis report."""
    entries = load_entries(days)
    
    if not entries:
        print("\n💰 No telemetry data found for cost analysis.")
        return
    
    period = f"Last {days} days" if days else "All time"
    
    # Calculate cost units
    by_tier = {}
    for entry in entries:
        tier = entry.model_tier
        if tier not in by_tier:
            by_tier[tier] = 0
        by_tier[tier] += 1
    
    # Calculate actual cost (with tier optimization)
    actual_cost_units = 0
    for tier, count in by_tier.items():
        multiplier = COST_MULTIPLIERS.get(tier, 7.0)  # Default to standard
        actual_cost_units += count * multiplier
    
    # Calculate hypothetical cost (all on premium)
    premium_cost_units = len(entries) * COST_MULTIPLIERS["premium"]
    
    # Calculate time savings
    estimated_time_saved = len(entries) * BASELINE_TASK_TIME / 60  # minutes
    
    print(f"\n💰 Cost Analysis ({period})")
    print("=" * 60)
    
    print("\n📊 Cost by Tier (relative units)")
    for tier, count in sorted(by_tier.items(), key=lambda x: -x[1]):
        multiplier = COST_MULTIPLIERS.get(tier, 7.0)
        tier_cost = count * multiplier
        print(f"   {tier}: {count} invocations × {multiplier}x = {tier_cost:.0f} units")
    
    print("\n💵 Cost Summary")
    print(f"   Actual cost (optimized): {actual_cost_units:.0f} units")
    print(f"   Hypothetical (all premium): {premium_cost_units:.0f} units")
    print(f"   Savings: {(1 - actual_cost_units / premium_cost_units) * 100:.1f}%")
    
    print("\n⏱️ Time Savings")
    print(f"   Estimated time saved: {estimated_time_saved:.0f} minutes ({estimated_time_saved / 60:.1f} hours)")
    print(f"   (Assumes {BASELINE_TASK_TIME / 60} min context setup per task without prompts)")
    
    print("\n📈 Efficiency Metrics")
    if actual_cost_units > 0:
        efficiency = estimated_time_saved / actual_cost_units * 60  # minutes per cost unit
        print(f"   Time saved per cost unit: {efficiency:.2f} minutes")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Track usage of Komorebi prompts and skills"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Log command
    log_parser = subparsers.add_parser("log", help="Log a usage event")
    log_parser.add_argument("prompt_or_skill", help="Name of the prompt or skill used")
    log_parser.add_argument(
        "model_tier",
        choices=["economy", "standard", "premium", "research"],
        help="Model tier used"
    )
    log_parser.add_argument(
        "--duration",
        type=float,
        help="Duration of task in seconds"
    )
    log_parser.add_argument(
        "--failed",
        action="store_true",
        help="Mark as failed task"
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate usage report")
    report_parser.add_argument(
        "--days",
        type=int,
        help="Filter to last N days"
    )
    
    # Costs command
    costs_parser = subparsers.add_parser("costs", help="Generate cost analysis")
    costs_parser.add_argument(
        "--days",
        type=int,
        help="Filter to last N days"
    )
    
    args = parser.parse_args()
    
    if args.command == "log":
        log_usage(
            prompt_or_skill=args.prompt_or_skill,
            model_tier=args.model_tier,
            duration_seconds=args.duration,
            success=not args.failed,
        )
    elif args.command == "report":
        generate_usage_report(days=args.days)
    elif args.command == "costs":
        generate_cost_report(days=args.days)


if __name__ == "__main__":
    main()
