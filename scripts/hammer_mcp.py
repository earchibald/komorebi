#!/usr/bin/env python3
"""hammer_mcp.py – MCP Aggregator Load Test ("The Hammer")

Validates the Capture Pipeline under concurrent load:
  1. Registers an Echo MCP server (simple python subprocess)
  2. Fires N concurrent tool calls with capture=True
  3. Verifies N chunks were created in the DB
  4. Checks for zombie processes

Usage:
    python scripts/hammer_mcp.py --count 50 --base-url http://localhost:8000
"""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Echo MCP Server – a minimal MCP server that echoes tool arguments
# ---------------------------------------------------------------------------
ECHO_SERVER_SCRIPT = '''
import json, sys

def respond(msg_id, result):
    msg = json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result})
    sys.stdout.write(msg + "\\n")
    sys.stdout.flush()

def notify(method, params=None):
    msg = json.dumps({"jsonrpc": "2.0", "method": method, "params": params or {}})
    sys.stdout.write(msg + "\\n")
    sys.stdout.flush()

for line in sys.stdin:
    try:
        msg = json.loads(line.strip())
    except json.JSONDecodeError:
        continue

    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        respond(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "echo-server", "version": "1.0.0"},
        })
    elif method == "notifications/initialized":
        pass  # notification, no response
    elif method == "tools/list":
        respond(msg_id, {
            "tools": [{
                "name": "echo",
                "description": "Echoes the input back",
                "inputSchema": {
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                },
            }]
        })
    elif method == "tools/call":
        params = msg.get("params", {})
        args = params.get("arguments", {})
        respond(msg_id, {
            "content": [{"type": "text", "text": f"Echo: {json.dumps(args)}"}]
        })
    else:
        if msg_id:
            respond(msg_id, {})
'''


async def main(count: int, base_url: str):
    api = f"{base_url}/api/v1"

    # Write echo server script to a temp file
    echo_path = Path("/tmp/komorebi_echo_mcp.py")
    echo_path.write_text(ECHO_SERVER_SCRIPT)
    print(f"📝 Echo server script written to {echo_path}")

    async with httpx.AsyncClient(timeout=30) as client:
        # ─── 1. Register echo server ───────────────────────
        print("📡 Registering echo MCP server…")
        reg = await client.post(f"{api}/mcp/servers", json={
            "name": "echo-hammer",
            "server_type": "test",
            "command": sys.executable,
            "args": [str(echo_path)],
            "enabled": True,
        })
        if reg.status_code != 201:
            print(f"❌ Failed to register server: {reg.text}")
            return
        server_id = reg.json()["id"]
        print(f"   Server ID: {server_id}")

        # ─── 2. Connect ───────────────────────────────────
        print("🔌 Connecting…")
        conn = await client.post(f"{api}/mcp/servers/{server_id}/connect")
        if conn.status_code != 200:
            print(f"❌ Failed to connect: {conn.text}")
            return
        tools = conn.json().get("tools", [])
        print(f"   Connected! Tools: {tools}")

        # ─── 3. Get baseline chunk count ──────────────────
        stats_before = (await client.get(f"{api}/chunks/stats")).json()
        total_before = stats_before.get("total", 0)
        print(f"📊 Chunks before: {total_before}")

        # ─── 4. Fire concurrent tool calls ────────────────
        print(f"🔨 Firing {count} concurrent tool calls with capture=True…")
        start = time.monotonic()

        async def fire_one(i: int):
            r = await client.post(
                f"{api}/mcp/tools/echo/call",
                params={"capture": "true"},
                json={"message": f"hammer-{i}"},
            )
            return r.status_code, r.json() if r.status_code == 200 else r.text

        tasks = [fire_one(i) for i in range(count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.monotonic() - start

        successes = sum(1 for r in results if not isinstance(r, Exception) and r[0] == 200)
        failures = count - successes
        chunk_ids = [
            r[1].get("chunk_id")
            for r in results
            if not isinstance(r, Exception) and r[0] == 200 and "chunk_id" in r[1]
        ]

        print(f"   ✅ {successes} OK  ❌ {failures} failed  ⏱ {elapsed:.2f}s  ({count/elapsed:.0f} req/s)")

        # ─── 5. Verify chunks in DB ───────────────────────
        await asyncio.sleep(1)  # small grace period for background tasks
        stats_after = (await client.get(f"{api}/chunks/stats")).json()
        total_after = stats_after.get("total", 0)
        new_chunks = total_after - total_before
        print(f"📊 Chunks after: {total_after}  (new: {new_chunks})")

        if new_chunks >= successes:
            print(f"✅ PASS: {new_chunks} chunks captured (expected ≥ {successes})")
        else:
            print(f"❌ FAIL: Only {new_chunks} chunks captured (expected ≥ {successes})")

        # ─── 6. Disconnect & cleanup ─────────────────────
        print("🧹 Cleaning up…")
        await client.post(f"{api}/mcp/servers/{server_id}/disconnect")
        await client.delete(f"{api}/mcp/servers/{server_id}")

        # ─── 7. Zombie process check ─────────────────────
        try:
            zombie_check = subprocess.run(
                ["pgrep", "-f", "komorebi_echo_mcp"],
                capture_output=True, text=True
            )
            if zombie_check.stdout.strip():
                pids = zombie_check.stdout.strip().split('\n')
                print(f"⚠️ WARNING: {len(pids)} potential zombie process(es): {pids}")
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                print("   Killed remaining processes")
            else:
                print("✅ No zombie processes detected")
        except FileNotFoundError:
            print("   (pgrep not available – skipping zombie check)")

    print("\n🏁 Hammer test complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Hammer Load Test")
    parser.add_argument("--count", type=int, default=50, help="Number of concurrent tool calls")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Komorebi API base URL")
    args = parser.parse_args()
    asyncio.run(main(args.count, args.base_url))
